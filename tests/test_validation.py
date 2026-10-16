
import pytest

from app.generate_data import generate_data
from app.validation import validate_data


def sample_data():
    return generate_data()


def test_valid_data():
    """Valid generated data should pass."""

    customers, subscriptions, usage = sample_data()

    assert validate_data(
        customers, subscriptions, usage
    ) is True


def test_duplicate_customer():
    """Duplicate customer IDs must be rejected."""

    customers, subscriptions, usage = sample_data()

    customers.append(customers[0].copy())

    with pytest.raises(
        ValueError, match="Duplicate record"
    ):
        validate_data(
            customers, subscriptions, usage
        )


def test_negative_usage():
    """Negative usage hours must be rejected."""

    customers, subscriptions, usage = sample_data()

    usage[0]["usage_hours"] = -10

    with pytest.raises(
        ValueError, match="Usage hours"
    ):
        validate_data(
            customers, subscriptions, usage
        )


def test_invalid_subscription_status():
    """Unsupported subscription statuses must fail."""

    customers, subscriptions, usage = sample_data()

    subscriptions[0]["status"] = "unknown"

    with pytest.raises(
        ValueError, match="Invalid subscription status"
    ):
        validate_data(
            customers, subscriptions, usage
        )


def test_missing_usage_is_allowed():
    """A missing monthly record is not zero usage."""

    customers, subscriptions, usage = sample_data()

    customer_12_october = [
        row for row in usage
        if row["customer_id"] == 12
        and row["month_start"] == "2026-10-01"
    ]

    assert len(customer_12_october) == 0

    assert validate_data(
        customers, subscriptions, usage
    ) is True
