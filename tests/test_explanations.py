
from app.explanations import (
    rule_based_explanation,
    explanation_features,
)


def test_high_risk_explanation():
    customer = {
        "subscription_status": "active",
        "usage_data_status": "complete",
        "usage_decline_percent": 90,
        "payment_failures": 2,
        "current_month_sessions": 2,
        "risk_level": "HIGH",
    }

    explanation = rule_based_explanation(customer)

    assert "HIGH" in explanation
    assert "90.0%" in explanation
    assert "payments failed" in explanation


def test_missing_data_explanation():
    customer = {
        "subscription_status": "active",
        "usage_data_status": "missing_usage",
        "risk_level": "INSUFFICIENT DATA",
    }

    explanation = rule_based_explanation(customer)

    assert "incomplete" in explanation.lower()


def test_ai_input_excludes_personal_information():
    customer = {
        "customer_name": "Private Customer",
        "email": "private@example.com",
        "risk_level": "HIGH",
        "payment_failures": 2,
    }

    features = explanation_features(customer)

    assert "customer_name" not in features
    assert "email" not in features
    assert features["risk_level"] == "HIGH"
