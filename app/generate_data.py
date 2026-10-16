
import csv
import os
import random
from datetime import date

from app.config import BASE_DIR

DATA_DIR = BASE_DIR / "data"
SEED = 42
MONTH_COUNT = 18


def reporting_month(offset):
    # April 2025 + 17 months = September 2026
    total = 3 + offset
    year = 2025 + total // 12
    month = total % 12 + 1
    return date(year, month, 1).isoformat()


def save_csv(name, rows):
    DATA_DIR.mkdir(exist_ok=True)

    path = DATA_DIR / name

    with path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"{name}: {len(rows):,} rows")


def generate_data(customer_count=None):
    if customer_count is None:
        customer_count = int(
            os.getenv("CUSTOMER_COUNT", "10000")
        )

    if customer_count < 1:
        raise ValueError("Customer count must be positive")

    rng = random.Random(SEED)

    data = {
        "customers": [],
        "subscriptions": [],
        "subscription_monthly": [],
        "monthly_usage": [],
    }

    plans = [
        ("Basic", 299),
        ("Standard", 499),
        ("Premium", 799),
    ]

    for customer_id in range(1, customer_count + 1):
        plan, price = rng.choice(plans)

        data["customers"].append({
            "customer_id": customer_id,
            "customer_name": f"Customer {customer_id:06d}",
            "join_date": "2025-03-01",
        })

        data["subscriptions"].append({
            "subscription_id": 1000000 + customer_id,
            "customer_id": customer_id,
            "plan_name": plan,
            "monthly_price": price,
        })

        baseline = rng.uniform(20, 80)
        previous_usage = baseline
        low_engagement = False

        for month_index in range(MONTH_COUNT):
            month = reporting_month(month_index)

            # Engagement is persistent, but can recover.
            if low_engagement:
                low_engagement = rng.random() < 0.82
            else:
                low_engagement = rng.random() < 0.09

            if low_engagement:
                usage = rng.uniform(0.05, 0.40) * baseline
            else:
                usage = rng.uniform(0.75, 1.20) * baseline

            usage = round(usage, 2)
            sessions = max(1, round(usage / 2.5))

            payment_failure = (
                1 if rng.random() < (
                    0.12 if low_engagement else 0.03
                ) else 0
            )

            # Synthetic cancellation mechanism.
            # These are assumptions, not real-world rates.
            cancellation_probability = 0.008

            if low_engagement:
                cancellation_probability += 0.045

            if payment_failure:
                cancellation_probability += 0.035

            if (
                previous_usage > 0
                and usage / previous_usage < 0.4
            ):
                cancellation_probability += 0.025

            cancelled = (
                rng.random() < cancellation_probability
            )

            data["subscription_monthly"].append({
                "customer_id": customer_id,
                "month_start": month,
                "active_at_start": True,
                "cancelled_during_month": cancelled,
                "active_at_end": not cancelled,
                "payment_failures": payment_failure,
            })

            # Approximately 1% missing usage observations.
            if rng.random() >= 0.01:
                data["monthly_usage"].append({
                    "customer_id": customer_id,
                    "month_start": month,
                    "usage_hours": usage,
                    "session_count": sessions,
                })

            previous_usage = usage

            if cancelled:
                break

    for name, rows in data.items():
        save_csv(f"{name}.csv", rows)

    return data


if __name__ == "__main__":
    generate_data()
