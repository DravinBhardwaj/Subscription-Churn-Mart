
import copy

import pytest

import app.generate_data as generator
from app.validation import validate_data


@pytest.fixture
def sample_data(tmp_path, monkeypatch):
    monkeypatch.setattr(
        generator, "DATA_DIR", tmp_path
    )
    return generator.generate_data(customer_count=50)


def test_valid_data(sample_data):
    assert validate_data(sample_data) is True


def test_duplicate_customer(sample_data):
    broken = copy.deepcopy(sample_data)

    broken["customers"].append(
        broken["customers"][0].copy()
    )

    with pytest.raises(ValueError, match="Duplicate"):
        validate_data(broken)


def test_negative_usage(sample_data):
    broken = copy.deepcopy(sample_data)

    broken["monthly_usage"][0]["usage_hours"] = -10

    with pytest.raises(
        ValueError, match="Invalid usage hours"
    ):
        validate_data(broken)


def test_invalid_cancellation(sample_data):
    broken = copy.deepcopy(sample_data)

    row = broken["subscription_monthly"][0]
    row["cancelled_during_month"] = True
    row["active_at_end"] = True

    with pytest.raises(
        ValueError, match="Invalid cancellation state"
    ):
        validate_data(broken)


def test_unknown_usage_customer(sample_data):
    broken = copy.deepcopy(sample_data)

    broken["monthly_usage"][0]["customer_id"] = 999999

    with pytest.raises(
        ValueError, match="no matching subscription"
    ):
        validate_data(broken)
