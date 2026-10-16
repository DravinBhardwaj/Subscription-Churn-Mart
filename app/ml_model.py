
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)
from sqlalchemy import text

from app.config import BASE_DIR
from app.database import engine


MODEL_PATH = BASE_DIR / "models" / "churn_model.joblib"
METRICS_PATH = BASE_DIR / "models" / "metrics.json"

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


def build_model():
    """Build one consistent preprocessing + ML pipeline."""

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(
            strategy="constant", fill_value=0,
            add_indicator=True,
        )),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(
            strategy="constant",
            fill_value="missing",
        )),
        ("encoder", OneHotEncoder(
            handle_unknown="ignore"
        )),
    ])

    preprocessing = ColumnTransformer([
        ("numeric", numeric_pipeline, NUMERIC_FEATURES),
        ("categorical", categorical_pipeline,
         CATEGORICAL_FEATURES),
    ])

    return Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", LogisticRegression(
            max_iter=1000,
            random_state=42,
        )),
    ])


def load_features():
    """Read the feature mart created entirely in SQL."""

    with engine.connect() as connection:
        return pd.read_sql_query(
            text("""
                SELECT *
                FROM customer_churn_mart
                ORDER BY month_start, customer_id
            """),
            connection,
        )


def prepare_frame(df):
    df = df.copy()

    df["month_start"] = pd.to_datetime(
        df["month_start"]
    )

    for column in NUMERIC_FEATURES:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    for column in CATEGORICAL_FEATURES:
        df[column] = df[column].astype("string")

    return df


def temporal_split(df):
    """
    Train on earlier months and evaluate on later months.

    The latest month has no future cancellation label
    and is reserved for new predictions.
    """

    labeled = df[
        df["has_future_label"] == True
    ].copy()

    months = sorted(labeled["month_start"].unique())

    if len(months) < 9:
        raise ValueError(
            "At least nine labeled months are required"
        )

    # Most recent 3 labeled months: test
    # Previous 3 labeled months: validation
    # Remaining earlier months: training
    train_months = months[:-6]
    val_months = months[-6:-3]
    test_months = months[-3:]

    train = labeled[
        labeled["month_start"].isin(train_months)
    ].copy()

    validation = labeled[
        labeled["month_start"].isin(val_months)
    ].copy()

    test = labeled[
        labeled["month_start"].isin(test_months)
    ].copy()

    return train, validation, test


def evaluate(model, frame):
    y_true = frame["churn_next_month"].astype(int)
    probabilities = model.predict_proba(
        frame[FEATURES]
    )[:, 1]

    predicted = (probabilities >= 0.5).astype(int)

    return {
        "rows": int(len(frame)),
        "actual_churn_rate": float(y_true.mean()),
        "roc_auc": (
            float(roc_auc_score(y_true, probabilities))
            if y_true.nunique() == 2 else None
        ),
        "pr_auc": float(
            average_precision_score(y_true, probabilities)
        ),
        "brier_score": float(
            brier_score_loss(y_true, probabilities)
        ),
        "precision_at_0_5": float(
            precision_score(
                y_true, predicted, zero_division=0
            )
        ),
        "recall_at_0_5": float(
            recall_score(
                y_true, predicted, zero_division=0
            )
        ),
    }


def risk_level(probability):
    """
    Illustrative probability bands.

    These are operational thresholds, not
    an independently validated business policy.
    """

    if probability >= 0.20:
        return "HIGH"
    if probability >= 0.08:
        return "MEDIUM"
    return "LOW"


def save_predictions(model, df):
    """Generate and store predictions for the latest month."""

    latest_month = df["month_start"].max()

    current = df[
        df["month_start"] == latest_month
    ].copy()

    probabilities = model.predict_proba(
        current[FEATURES]
    )[:, 1]

    prediction_month = latest_month.date()

    target_month = (
        latest_month + pd.DateOffset(months=1)
    ).date()

    rows = []

    for customer_id, probability in zip(
        current["customer_id"], probabilities
    ):
        p = float(probability)

        rows.append({
            "customer_id": int(customer_id),
            "prediction_month": prediction_month,
            "target_month": target_month,
            "churn_probability": p,
            "risk_level": risk_level(p),
            "model_name": "logistic_regression_v1",
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
        ON CONFLICT (customer_id, prediction_month)
        DO UPDATE SET
            target_month = EXCLUDED.target_month,
            churn_probability = EXCLUDED.churn_probability,
            risk_level = EXCLUDED.risk_level,
            model_name = EXCLUDED.model_name,
            created_at = NOW()
    """)

    with engine.begin() as connection:
        for start in range(0, len(rows), 5000):
            connection.execute(
                query, rows[start:start + 5000]
            )

    print(f"Saved {len(rows):,} customer predictions.")


def main():
    print("Loading SQL-engineered ML features...")

    df = prepare_frame(load_features())
    train, validation, test = temporal_split(df)

    model = build_model()

    print(f"Training records: {len(train):,}")
    print(f"Validation records: {len(validation):,}")
    print(f"Test records: {len(test):,}")

    y_train = train["churn_next_month"].astype(int)

    if y_train.nunique() < 2:
        raise ValueError(
            "Training data must contain both classes"
        )

    model.fit(train[FEATURES], y_train)

    validation_metrics = evaluate(model, validation)
    test_metrics = evaluate(model, test)

    print("\nValidation metrics:")
    print(json.dumps(validation_metrics, indent=2))

    print("\nHeld-out test metrics:")
    print(json.dumps(test_metrics, indent=2))

    MODEL_PATH.parent.mkdir(
        parents=True, exist_ok=True
    )

    joblib.dump(model, MODEL_PATH)

    METRICS_PATH.write_text(
        json.dumps({
            "validation": validation_metrics,
            "test": test_metrics,
            "features": FEATURES,
            "training_end": str(
                train["month_start"].max().date()
            ),
            "test_end": str(
                test["month_start"].max().date()
            ),
        }, indent=2),
        encoding="utf-8",
    )

    save_predictions(model, df)

    print("\nML training completed successfully.")


if __name__ == "__main__":
    main()
