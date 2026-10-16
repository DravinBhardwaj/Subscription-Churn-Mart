
import csv
from pathlib import Path

from app.config import BASE_DIR

DATA_DIR = BASE_DIR / "data"


def save_csv(filename, rows):
    """Write a list of dictionaries to a CSV file."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = DATA_DIR / filename

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated: {path}")


def generate_data():
    """Generate reproducible fictional customer data."""

    customers = []
    subscriptions = []
    usage = []

    # Customer ID, previous hours, current hours,
    # current sessions, payment failures, status
    examples = [
        (1, 40, 38, 18, 0, "active"),
        (2, 50, 5, 2, 2, "active"),
        (3, 25, 23, 12, 0, "active"),
        (4, 60, 12, 3, 1, "active"),
        (5, 30, 0, 0, 0, "cancelled"),
        (6, 45, 40, 20, 0, "active"),
        (7, 20, 3, 1, 0, "active"),
        (8, 35, 33, 14, 0, "active"),
        (9, 28, 0, 0, 2, "cancelled"),
        (10, 42, 15, 5, 0, "active"),
        (11, 15, 18, 9, 0, "active"),
        (12, 40, None, None, 1, "active"),
    ]

    for (
        customer_id,
        previous_hours,
        current_hours,
        current_sessions,
        payment_failures,
        status,
    ) in examples:

        customers.append({
            "customer_id": customer_id,
            "customer_name": f"Customer {customer_id:03d}",
            "join_date": "2026-01-01",
        })

        subscriptions.append({
            "subscription_id": 1000 + customer_id,
            "customer_id": customer_id,
            "plan_name": (
                "Premium" if customer_id % 2 == 0
                else "Basic"
            ),
            "monthly_price": (
                499 if customer_id % 2 == 0 else 299
            ),
            "status": status,
            "payment_failures": payment_failures,
        })

        usage.append({
            "customer_id": customer_id,
            "month_start": "2026-09-01",
            "usage_hours": previous_hours,
            "session_count": max(
                1, round(previous_hours / 2)
            ),
        })

        # Customer 12 intentionally has no October record.
        # This allows us to test missing usage data.
        if current_hours is not None:
            usage.append({
                "customer_id": customer_id,
                "month_start": "2026-10-01",
                "usage_hours": current_hours,
                "session_count": current_sessions,
            })

    save_csv("customers.csv", customers)
    save_csv("subscriptions.csv", subscriptions)
    save_csv("monthly_usage.csv", usage)

    return customers, subscriptions, usage


if __name__ == "__main__":
    generate_data()
