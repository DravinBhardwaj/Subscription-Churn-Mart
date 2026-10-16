
from app.explanations import (
    explanation_features,
    rule_based_explanation,
    valid_explanation,
)


def test_private_fields_not_sent_to_gemini():
    """Ensure personal information is excluded."""

    customer = {
        "customer_name": "Private Customer",
        "email": "private@example.com",
        "payment_failures": 1,
        "risk_level": "HIGH",
        "churn_probability": 0.30,
    }

    result = explanation_features(customer)

    assert "customer_name" not in result
    assert "email" not in result
    assert result["risk_level"] == "HIGH"
    assert result["churn_probability"] == 0.30


def test_rule_based_explanation():
    """Verify the correct probability and usage values."""

    customer = {
        "churn_probability": 0.25,
        "risk_level": "HIGH",
        "previous_month_hours": 50,
        "current_month_hours": 10,
        "usage_decline_percent": 80,
        "payment_failures": 1,
        "current_month_sessions": 2,
        "usage_data_status": "complete",
    }

    explanation = rule_based_explanation(customer)

    assert "25.00%" in explanation
    assert "HIGH" in explanation
    assert "80.00%" in explanation
    assert "50.00 hours" in explanation
    assert "10.00 hours" in explanation
    assert "failed payment" in explanation


def test_complete_explanation():
    """Accept a complete four-sentence explanation."""

    explanation = (
        "The model estimates a 12.50% chance of "
        "cancellation during the next month. "
        "Customer usage declined significantly "
        "compared with the previous reporting month. "
        "The customer recorded fewer sessions and "
        "one failed subscription payment this month. "
        "This customer belongs to the HIGH relative "
        "priority group based on their ranking "
        "among active customers."
    )

    assert valid_explanation(explanation) is True


def test_truncated_explanation():
    """Reject an incomplete Gemini response."""

    explanation = (
        "This subscriber has an estimated cancellation "
        "risk of LOW, with a churn"
    )

    assert valid_explanation(explanation) is False


def test_missing_usage_explanation():
    """Missing usage must be explained accurately."""

    customer = {
        "churn_probability": 0.04,
        "risk_level": "LOW",
        "previous_month_hours": None,
        "current_month_hours": None,
        "usage_decline_percent": None,
        "payment_failures": 0,
        "current_month_sessions": None,
        "usage_data_status": "missing_usage",
    }

    explanation = rule_based_explanation(customer)

    assert "4.00%" in explanation
    assert "incomplete" in explanation.lower()
    assert "LOW" in explanation
