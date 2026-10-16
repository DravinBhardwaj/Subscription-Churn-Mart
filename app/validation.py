
from datetime import date
from decimal import Decimal


def check_unique(rows, columns):
    seen = set()

    for row in rows:
        key = tuple(row[column] for column in columns)

        if key in seen:
            raise ValueError(f"Duplicate record: {key}")

        seen.add(key)


def validate_data(data):
    customers = data["customers"]
    subscriptions = data["subscriptions"]
    history = data["subscription_monthly"]
    usage = data["monthly_usage"]

    check_unique(customers, ["customer_id"])
    check_unique(subscriptions, ["subscription_id"])
    check_unique(subscriptions, ["customer_id"])
    check_unique(history, ["customer_id", "month_start"])
    check_unique(usage, ["customer_id", "month_start"])

    customer_ids = set()

    for row in customers:
        customer_id = int(row["customer_id"])

        if customer_id <= 0:
            raise ValueError("Invalid customer ID")

        if not row["customer_name"].strip():
            raise ValueError("Missing customer name")

        date.fromisoformat(row["join_date"])
        customer_ids.add(customer_id)

    for row in subscriptions:
        if int(row["customer_id"]) not in customer_ids:
            raise ValueError("Unknown subscription customer")

        if row["plan_name"] not in (
            "Basic", "Standard", "Premium"
        ):
            raise ValueError("Invalid plan")

        price = Decimal(str(row["monthly_price"]))

        if not price.is_finite() or price <= 0:
            raise ValueError("Invalid price")

    if len(subscriptions) != len(customers):
        raise ValueError("Subscription count mismatch")

    valid_history = set()
    by_customer = {}

    for row in history:
        customer_id = int(row["customer_id"])
        month = date.fromisoformat(row["month_start"])

        if customer_id not in customer_ids:
            raise ValueError("Unknown history customer")

        if month.day != 1:
            raise ValueError("Invalid reporting month")

        start = row["active_at_start"]
        cancelled = row["cancelled_during_month"]
        end = row["active_at_end"]

        if not all(
            isinstance(v, bool)
            for v in (start, cancelled, end)
        ):
            raise ValueError("Invalid boolean status")

        if not start or end == cancelled:
            raise ValueError("Invalid cancellation state")

        if int(row["payment_failures"]) < 0:
            raise ValueError("Negative payment failures")

        valid_history.add((customer_id, month))
        by_customer.setdefault(
            customer_id, []
        ).append((month, end))

    for customer_id in customer_ids:
        records = sorted(by_customer.get(customer_id, []))

        if not records:
            raise ValueError("Missing subscription history")

        for i in range(1, len(records)):
            previous_month, previous_active = records[i - 1]
            current_month, _ = records[i]

            expected_year = (
                previous_month.year
                + (previous_month.month == 12)
            )
            expected_month = previous_month.month % 12 + 1

            if not previous_active:
                raise ValueError(
                    "History continues after cancellation"
                )

            if (
                current_month.year != expected_year
                or current_month.month != expected_month
            ):
                raise ValueError("Missing history month")

    for row in usage:
        customer_id = int(row["customer_id"])
        month = date.fromisoformat(row["month_start"])

        if (customer_id, month) not in valid_history:
            raise ValueError(
                "Usage has no matching subscription month"
            )

        hours = Decimal(str(row["usage_hours"]))

        if not hours.is_finite() or hours < 0:
            raise ValueError("Invalid usage hours")

        if int(row["session_count"]) < 0:
            raise ValueError("Negative session count")

    return True
