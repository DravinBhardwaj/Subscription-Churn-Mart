
from datetime import date
from decimal import Decimal, InvalidOperation


def check_unique(rows, key_fields):
    """Reject duplicate business keys."""

    seen = set()

    for row in rows:
        key = tuple(row[field] for field in key_fields)

        if key in seen:
            raise ValueError(
                f"Duplicate record found for {key_fields}: {key}"
            )

        seen.add(key)


def validate_data(customers, subscriptions, usage):
    """Validate the CSV data before loading it."""

    check_unique(customers, ["customer_id"])
    check_unique(subscriptions, ["subscription_id"])
    check_unique(subscriptions, ["customer_id"])
    check_unique(usage, ["customer_id", "month_start"])

    customer_ids = set()

    for customer in customers:
        customer_id = int(customer["customer_id"])

        if customer_id <= 0:
            raise ValueError("Customer ID must be positive")

        if not customer["customer_name"].strip():
            raise ValueError("Customer name is missing")

        date.fromisoformat(customer["join_date"])
        customer_ids.add(customer_id)

    for subscription in subscriptions:
        customer_id = int(subscription["customer_id"])

        if customer_id not in customer_ids:
            raise ValueError(
                f"Subscription has unknown customer: {customer_id}"
            )

        if subscription["status"] not in (
            "active", "cancelled"
        ):
            raise ValueError("Invalid subscription status")

        if subscription["plan_name"] not in (
            "Basic", "Premium"
        ):
            raise ValueError("Invalid plan name")

        try:
            price = Decimal(
                str(subscription["monthly_price"])
            )
        except InvalidOperation as error:
            raise ValueError("Invalid monthly price") from error

        if not price.is_finite() or price <= 0:
            raise ValueError("Monthly price must be positive")

        if int(subscription["payment_failures"]) < 0:
            raise ValueError(
                "Payment failures cannot be negative"
            )

    for record in usage:
        customer_id = int(record["customer_id"])

        if customer_id not in customer_ids:
            raise ValueError(
                f"Usage has unknown customer: {customer_id}"
            )

        month = date.fromisoformat(record["month_start"])

        if month.day != 1:
            raise ValueError(
                "Monthly usage date must be the first day"
            )

        try:
            hours = Decimal(str(record["usage_hours"]))
        except InvalidOperation as error:
            raise ValueError("Invalid usage hours") from error

        if not hours.is_finite() or hours < 0:
            raise ValueError("Usage hours cannot be negative")

        if int(record["session_count"]) < 0:
            raise ValueError(
                "Session count cannot be negative"
            )

    return True
