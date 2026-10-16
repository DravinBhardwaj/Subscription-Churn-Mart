
import numpy as np
import pandas as pd

from app.ml_model import (
    FEATURES,
    assign_relative_priorities,
    build_model,
    temporal_split,
)


def test_relative_priority_counts():
    customer_ids = list(range(1, 101))
    probabilities = np.linspace(
        0.001, 0.08, 100
    )

    result = assign_relative_priorities(
        customer_ids,
        probabilities,
    )

    assert len(result) == 100

    assert sum(
        row["risk_level"] == "HIGH"
        for row in result
    ) == 10

    assert sum(
        row["risk_level"] == "MEDIUM"
        for row in result
    ) == 20

    assert sum(
        row["risk_level"] == "LOW"
        for row in result
    ) == 70


def test_highest_probability_gets_high_priority():
    ids = list(range(1, 101))
    probabilities = [0.01] * 100
    probabilities[49] = 0.09

    result = assign_relative_priorities(
        ids, probabilities
    )

    assert result[0]["customer_id"] == 50
    assert result[0]["risk_level"] == "HIGH"
    assert result[0]["probability"] == 0.09


def test_invalid_probability_rejected():
    import pytest

    with pytest.raises(
        ValueError,
        match="Invalid churn probability",
    ):
        assign_relative_priorities(
            [1, 2],
            [0.1, 1.5],
        )


def test_model_can_train():
    rows = []

    for i in range(60):
        rows.append({
            "monthly_price": 299,
            "payment_failures": i % 2,
            "current_month_hours": float(i + 1),
            "current_month_sessions": i % 10,
            "previous_month_hours": float(i + 5),
            "usage_decline_percent": float(i % 30),
            "avg_usage_3_months": float(i + 3),
            "tenure_months": 6,
            "plan_name": "Basic",
            "usage_data_status": "complete",
        })

    frame = pd.DataFrame(rows)

    X = frame[FEATURES]
    y = np.array([i % 2 for i in range(60)])

    model = build_model()
    model.fit(X, y)

    probabilities = model.predict_proba(X)[:, 1]

    assert len(probabilities) == 60
    assert np.all(probabilities >= 0)
    assert np.all(probabilities <= 1)


def test_temporal_split():
    rows = []

    for month in pd.date_range(
        "2025-01-01",
        periods=12,
        freq="MS",
    ):
        for customer_id in range(1, 4):
            rows.append({
                "customer_id": customer_id,
                "month_start": month,
                "has_future_label": True,
                "churn_next_month": customer_id % 2,
            })

    df = pd.DataFrame(rows)

    train, validation, test = temporal_split(df)

    assert (
        train["month_start"].max()
        < validation["month_start"].min()
    )

    assert (
        validation["month_start"].max()
        < test["month_start"].min()
    )
