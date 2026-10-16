
import json
import math

import joblib
import numpy as np
import pandas as pd

from sqlalchemy import text

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    StandardScaler,
    OneHotEncoder,
)

from app.config import BASE_DIR
from app.database import engine


# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

MODEL_NAME = "logistic_regression_v2"

MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "churn_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"

BATCH_SIZE = 5000

NUMERIC_FEATURES = [
    "monthly_price",
    "payment_failures",
    "current_month_hours",
    "current_month_sessions",
    "previous_month_hours",
    "usage_decline_percent",
    "avg_usage_3_months",
    "tenure_months",
]

CATEGORICAL_FEATURES = [
    "plan_name",
    "usage_data_status",
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# -----------------------------------------
# BUILD ML MODEL
# -----------------------------------------

def build_model():
    """Build preprocessing and ML model."""

    numeric_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="constant",
                fill_value=0,
                add_indicator=True,
            ),
        ),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="constant",
                fill_value="missing",
            ),
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
        ),
    ])

    preprocessor = ColumnTransformer([
        (
            "numeric",
            numeric_pipeline,
            NUMERIC_FEATURES,
        ),
        (
            "categorical",
            categorical_pipeline,
            CATEGORICAL_FEATURES,
        ),
    ])

    model = Pipeline([
        ("preprocessor", preprocessor),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ])

    return model


# -----------------------------------------
# LOAD SQL FEATURES
# -----------------------------------------

def load_features():
    """Retrieve SQL-engineered features."""

    query = text("""
        SELECT *
        FROM customer_churn_mart
        ORDER BY month_start, customer_id
    """)

    with engine.connect() as connection:
        return pd.read_sql_query(
            query,
            connection,
        )


def prepare_frame(df):
    """Prepare SQL feature data for ML."""

    df = df.copy()

    df["month_start"] = pd.to_datetime(
        df["month_start"]
    )

    for column in NUMERIC_FEATURES:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    for column in CATEGORICAL_FEATURES:
        df[column] = (
            df[column]
            .fillna("missing")
            .astype(str)
        )

    return df


# -----------------------------------------
# CHRONOLOGICAL DATA SPLITTING
# -----------------------------------------

def temporal_split(df):
    """Split data without using future labels."""

    labeled = df[
        df["has_future_label"] == True
    ].copy()

    months = sorted(
        labeled["month_start"].unique()
    )

    if len(months) < 9:
        raise ValueError(
            "At least 9 labeled months required"
        )

    training_months = months[:-6]
    validation_months = months[-6:-3]
    testing_months = months[-3:]

    train = labeled[
        labeled["month_start"].isin(training_months)
    ].copy()

    validation = labeled[
        labeled["month_start"].isin(validation_months)
    ].copy()

    test = labeled[
        labeled["month_start"].isin(testing_months)
    ].copy()

    return train, validation, test


# -----------------------------------------
# EVALUATE MODEL
# -----------------------------------------

def evaluate(model, dataset):
    """Evaluate probabilities and classification."""

    actual = dataset[
        "churn_next_month"
    ].astype(int)

    probabilities = model.predict_proba(
        dataset[FEATURES]
    )[:, 1]

    predicted = (
        probabilities >= 0.5
    ).astype(int)

    return {
        "total_records": int(len(dataset)),

        "actual_churn_rate": float(
            actual.mean()
        ),

        "average_predicted_probability": float(
            probabilities.mean()
        ),

        "roc_auc": (
            float(
                roc_auc_score(
                    actual,
                    probabilities,
                )
            )
            if actual.nunique() == 2
            else None
        ),

        "pr_auc": float(
            average_precision_score(
                actual,
                probabilities,
            )
        ),

        "brier_score": float(
            brier_score_loss(
                actual,
                probabilities,
            )
        ),

        "precision_at_0_5": float(
            precision_score(
                actual,
                predicted,
                zero_division=0,
            )
        ),

        "recall_at_0_5": float(
            recall_score(
                actual,
                predicted,
                zero_division=0,
            )
        ),
    }


# -----------------------------------------
# ASSIGN RELATIVE REVIEW PRIORITIES
# -----------------------------------------

def assign_relative_priorities(
    customer_ids,
    probabilities,
):
    """
    HIGH   = top 10%
    MEDIUM = next 20%
    LOW    = remaining 70%

    These are relative priorities, not
    absolute probabilities.
    """

    if len(customer_ids) != len(probabilities):
        raise ValueError(
            "Customer/probability count mismatch"
        )

    if len(set(customer_ids)) != len(customer_ids):
        raise ValueError(
            "Duplicate customer IDs found"
        )

    records = []

    for customer_id, probability in zip(
        customer_ids,
        probabilities,
    ):
        probability = float(probability)

        if (
            not math.isfinite(probability)
            or not 0 <= probability <= 1
        ):
            raise ValueError(
                "Invalid churn probability"
            )

        records.append({
            "customer_id": int(customer_id),
            "probability": probability,
        })

    # Highest predicted probability first.
    # Customer ID makes tied rankings reproducible.
    records.sort(
        key=lambda record: (
            -record["probability"],
            record["customer_id"],
        )
    )

    total = len(records)

    high_count = math.ceil(
        total * 0.10
    )

    medium_end = math.ceil(
        total * 0.30
    )

    for index, record in enumerate(records):

        if index < high_count:
            priority = "HIGH"

        elif index < medium_end:
            priority = "MEDIUM"

        else:
            priority = "LOW"

        record["risk_level"] = priority
        record["risk_rank"] = index + 1

    return records


# -----------------------------------------
# SAVE PREDICTIONS IN POSTGRESQL
# -----------------------------------------

def save_predictions(model, df):
    """Predict and save latest-month priorities."""

    latest_month = df["month_start"].max()

    current = df[
        df["month_start"] == latest_month
    ].copy()

    if current.empty:
        raise ValueError(
            "No active customers available for prediction"
        )

    probabilities = model.predict_proba(
        current[FEATURES]
    )[:, 1]

    customer_ids = (
        current["customer_id"]
        .astype(int)
        .tolist()
    )

    ranked_customers = assign_relative_priorities(
        customer_ids,
        probabilities,
    )

    prediction_month = latest_month.date()

    target_month = (
        latest_month + pd.DateOffset(months=1)
    ).date()

    records = []

    for customer in ranked_customers:
        records.append({
            "customer_id": customer["customer_id"],
            "prediction_month": prediction_month,
            "target_month": target_month,
            "churn_probability": customer["probability"],
            "risk_level": customer["risk_level"],
            "model_name": MODEL_NAME,
        })

    query = text("""
        INSERT INTO customer_risk_predictions (
            customer_id,
            prediction_month,
            target_month,
            churn_probability,
            risk_level,
            model_name
        )
        VALUES (
            :customer_id,
            :prediction_month,
            :target_month,
            :churn_probability,
            :risk_level,
            :model_name
        )

        ON CONFLICT (
            customer_id,
            prediction_month
        )

        DO UPDATE SET
            target_month = EXCLUDED.target_month,
            churn_probability = EXCLUDED.churn_probability,
            risk_level = EXCLUDED.risk_level,
            model_name = EXCLUDED.model_name,
            created_at = NOW()
    """)

    # Update stored predictions atomically.
    with engine.begin() as connection:

        for start in range(
            0,
            len(records),
            BATCH_SIZE,
        ):
            batch = records[
                start:start + BATCH_SIZE
            ]

            connection.execute(
                query,
                batch,
            )

    print("\nPredictions saved successfully.")
    print(f"Model: {MODEL_NAME}")
    print(f"Customers scored: {len(records):,}")

    for priority in ("HIGH", "MEDIUM", "LOW"):

        count = sum(
            customer["risk_level"] == priority
            for customer in records
        )

        print(
            f"{priority} priority: {count:,}"
        )

    print(
        "Average estimated cancellation probability: "
        f"{np.mean(probabilities) * 100:.2f}%"
    )

    print(
        "Maximum estimated cancellation probability: "
        f"{np.max(probabilities) * 100:.2f}%"
    )


# -----------------------------------------
# MAIN TRAINING PIPELINE
# -----------------------------------------

def main():
    print("=" * 55)
    print("SUBSCRIPTION CHURN - ML PIPELINE V2")
    print("=" * 55)

    print("\nLoading SQL-engineered features...")

    df = prepare_frame(
        load_features()
    )

    train, validation, test = temporal_split(df)

    print(f"Training records: {len(train):,}")
    print(f"Validation records: {len(validation):,}")
    print(f"Testing records: {len(test):,}")

    model = build_model()

    y_train = train[
        "churn_next_month"
    ].astype(int)

    if y_train.nunique() < 2:
        raise ValueError(
            "Training dataset must contain both "
            "churn and non-churn examples"
        )

    print("\nTraining Logistic Regression...")

    model.fit(
        train[FEATURES],
        y_train,
    )

    print("\nEvaluating model...")

    validation_metrics = evaluate(
        model,
        validation,
    )

    test_metrics = evaluate(
        model,
        test,
    )

    print("\nValidation Metrics:")
    print(
        json.dumps(
            validation_metrics,
            indent=2,
        )
    )

    print("\nHeld-Out Test Metrics:")
    print(
        json.dumps(
            test_metrics,
            indent=2,
        )
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    METRICS_PATH.write_text(
        json.dumps(
            {
                "model_name": MODEL_NAME,
                "validation": validation_metrics,
                "test": test_metrics,
                "features": FEATURES,
                "priority_policy": {
                    "HIGH": "Top 10%",
                    "MEDIUM": "Next 20%",
                    "LOW": "Remaining 70%",
                },
                "limitations": (
                    "Trained on synthetic data. "
                    "Relative review priorities are not "
                    "absolute cancellation-risk categories."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nUpdating PostgreSQL predictions...")

    save_predictions(
        model,
        df,
    )

    print("\nML pipeline completed successfully!")


if __name__ == "__main__":
    main()
