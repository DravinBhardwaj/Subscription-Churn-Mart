
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.database import (
    engine,
    check_connection,
    read_sql_file,
)
from app.generate_data import generate_data
from app.validation import validate_data


MODEL_FILES = [
    "02_customer_model.sql",
    "03_subscription_model.sql",
    "04_usage_model.sql",
    "05_churn_mart.sql",
    "06_monthly_metrics.sql",
]

BATCH_SIZE = 5000


def prepare_rows(data):
    customers = [
        {
            **row,
            "join_date": date.fromisoformat(
                row["join_date"]
            ),
        }
        for row in data["customers"]
    ]

    subscriptions = [
        {
            **row,
            "monthly_price": Decimal(
                str(row["monthly_price"])
            ),
        }
        for row in data["subscriptions"]
    ]

    history = [
        {
            **row,
            "month_start": date.fromisoformat(
                row["month_start"]
            ),
        }
        for row in data["subscription_monthly"]
    ]

    usage = [
        {
            **row,
            "month_start": date.fromisoformat(
                row["month_start"]
            ),
            "usage_hours": Decimal(
                str(row["usage_hours"])
            ),
        }
        for row in data["monthly_usage"]
    ]

    return customers, subscriptions, history, usage


def insert_batches(connection, statement, rows):
    for index in range(0, len(rows), BATCH_SIZE):
        connection.execute(
            text(statement),
            rows[index:index + BATCH_SIZE],
        )


def create_schema():
    script = read_sql_file("01_schema.sql")

    with engine.begin() as connection:
        for command in script.split(";"):
            if command.strip():
                connection.execute(text(command.strip()))

    print("Database schema ready.")


def load_data(data):
    customers, subscriptions, history, usage = (
        prepare_rows(data)
    )

    queries = [
        """
        INSERT INTO customers
            (customer_id, customer_name, join_date)
        VALUES
            (:customer_id, :customer_name, :join_date)
        ON CONFLICT (customer_id) DO UPDATE SET
            customer_name = EXCLUDED.customer_name,
            join_date = EXCLUDED.join_date
        """,
        """
        INSERT INTO subscriptions
            (subscription_id, customer_id,
             plan_name, monthly_price)
        VALUES
            (:subscription_id, :customer_id,
             :plan_name, :monthly_price)
        ON CONFLICT (subscription_id) DO UPDATE SET
            plan_name = EXCLUDED.plan_name,
            monthly_price = EXCLUDED.monthly_price
        """,
        """
        INSERT INTO subscription_monthly
            (customer_id, month_start, active_at_start,
             cancelled_during_month, active_at_end,
             payment_failures)
        VALUES
            (:customer_id, :month_start, :active_at_start,
             :cancelled_during_month, :active_at_end,
             :payment_failures)
        ON CONFLICT (customer_id, month_start)
        DO UPDATE SET
            active_at_start = EXCLUDED.active_at_start,
            cancelled_during_month =
                EXCLUDED.cancelled_during_month,
            active_at_end = EXCLUDED.active_at_end,
            payment_failures = EXCLUDED.payment_failures
        """,
        """
        INSERT INTO monthly_usage
            (customer_id, month_start,
             usage_hours, session_count)
        VALUES
            (:customer_id, :month_start,
             :usage_hours, :session_count)
        ON CONFLICT (customer_id, month_start)
        DO UPDATE SET
            usage_hours = EXCLUDED.usage_hours,
            session_count = EXCLUDED.session_count
        """,
    ]

    # Commit the source load as one transaction.
    with engine.begin() as connection:
        for query, rows in zip(
            queries, [customers, subscriptions, history, usage]
        ):
            insert_batches(connection, query, rows)

    print("Source data loaded.")


def create_models():
    with engine.begin() as connection:
        for filename in MODEL_FILES:
            connection.execute(
                text(read_sql_file(filename))
            )
            print(f"Created: {filename}")


def validate_output():
    with engine.connect() as connection:
        monthly = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM monthly_churn_metrics
            """)
        ).scalar_one()

        bad_balance = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM monthly_churn_metrics
                WHERE customers_at_start <>
                    customers_at_end + churned_customers
            """)
        ).scalar_one()

        duplicate_features = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id, month_start
                    FROM customer_churn_mart
                    GROUP BY customer_id, month_start
                    HAVING COUNT(*) > 1
                ) d
            """)
        ).scalar_one()

    assert monthly == 18, "Expected 18 months"
    assert bad_balance == 0, "Customer totals do not balance"
    assert duplicate_features == 0, "Duplicate feature rows"

    print("SQL validation passed.")


def main():
    print("Starting Subscription Churn Mart V3...")

    if not check_connection():
        raise RuntimeError("PostgreSQL connection failed")

    print("PostgreSQL connected.")

    data = generate_data()
    validate_data(data)
    print("Source validation passed.")

    create_schema()
    load_data(data)
    create_models()
    validate_output()

    print("SQL pipeline completed successfully.")


if __name__ == "__main__":
    main()
