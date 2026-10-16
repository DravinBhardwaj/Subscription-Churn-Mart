
import csv
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.config import BASE_DIR
from app.database import (
    engine,
    check_connection,
    read_sql_file,
)
from app.generate_data import generate_data
from app.validation import validate_data


SQL_FILES = [
    "02_customer_model.sql",
    "03_subscription_model.sql",
    "04_usage_model.sql",
    "05_churn_mart.sql",
]


def read_csv(filename):
    """Read generated sample data."""

    path = BASE_DIR / "data" / filename

    with path.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def create_tables():
    """Create database tables if necessary."""

    sql = read_sql_file("01_schema.sql")

    # Our schema file contains simple SQL statements.
    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print("Database tables are ready.")


def load_data(customers, subscriptions, usage):
    """Insert or update source records atomically."""

    customer_sql = text("""
        INSERT INTO customers (
            customer_id, customer_name, join_date
        )
        VALUES (
            :customer_id, :customer_name, :join_date
        )
        ON CONFLICT (customer_id)
        DO UPDATE SET
            customer_name = EXCLUDED.customer_name,
            join_date = EXCLUDED.join_date
    """)

    subscription_sql = text("""
        INSERT INTO subscriptions (
            subscription_id, customer_id,
            plan_name, monthly_price,
            status, payment_failures
        )
        VALUES (
            :subscription_id, :customer_id,
            :plan_name, :monthly_price,
            :status, :payment_failures
        )
        ON CONFLICT (subscription_id)
        DO UPDATE SET
            customer_id = EXCLUDED.customer_id,
            plan_name = EXCLUDED.plan_name,
            monthly_price = EXCLUDED.monthly_price,
            status = EXCLUDED.status,
            payment_failures = EXCLUDED.payment_failures
    """)

    usage_sql = text("""
        INSERT INTO monthly_usage (
            customer_id, month_start,
            usage_hours, session_count
        )
        VALUES (
            :customer_id, :month_start,
            :usage_hours, :session_count
        )
        ON CONFLICT (customer_id, month_start)
        DO UPDATE SET
            usage_hours = EXCLUDED.usage_hours,
            session_count = EXCLUDED.session_count
    """)

    customer_records = [
        {
            "customer_id": int(row["customer_id"]),
            "customer_name": row["customer_name"],
            "join_date": date.fromisoformat(
                row["join_date"]
            ),
        }
        for row in customers
    ]

    subscription_records = [
        {
            "subscription_id": int(row["subscription_id"]),
            "customer_id": int(row["customer_id"]),
            "plan_name": row["plan_name"],
            "monthly_price": Decimal(
                str(row["monthly_price"])
            ),
            "status": row["status"],
            "payment_failures": int(
                row["payment_failures"]
            ),
        }
        for row in subscriptions
    ]

    usage_records = [
        {
            "customer_id": int(row["customer_id"]),
            "month_start": date.fromisoformat(
                row["month_start"]
            ),
            "usage_hours": Decimal(
                str(row["usage_hours"])
            ),
            "session_count": int(
                row["session_count"]
            ),
        }
        for row in usage
    ]

    # A single transaction commits all inserts together.
    # If one fails, PostgreSQL rolls back this load.
    with engine.begin() as connection:
        connection.execute(
            customer_sql, customer_records
        )
        connection.execute(
            subscription_sql, subscription_records
        )
        connection.execute(
            usage_sql, usage_records
        )

    print("Sample data loaded successfully.")


def create_models():
    """Build SQL analytical views in dependency order."""

    with engine.begin() as connection:
        for filename in SQL_FILES:
            sql = read_sql_file(filename)
            connection.execute(text(sql))

            print(f"Created SQL model: {filename}")


def validate_mart():
    """Check important properties of the final mart."""

    with engine.connect() as connection:
        source_count = connection.execute(
            text("SELECT COUNT(*) FROM customers")
        ).scalar_one()

        mart_count = connection.execute(
            text(
                "SELECT COUNT(*) "
                "FROM customer_churn_mart"
            )
        ).scalar_one()

        duplicate_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM customer_churn_mart
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                ) duplicates
            """)
        ).scalar_one()

        invalid_risk_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM customer_churn_mart
                WHERE risk_level NOT IN (
                    'LOW', 'MEDIUM', 'HIGH',
                    'CHURNED', 'INSUFFICIENT DATA'
                )
            """)
        ).scalar_one()

        incorrect_churn_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM customer_churn_mart
                WHERE (
                    subscription_status = 'cancelled'
                    AND risk_level <> 'CHURNED'
                )
                OR (
                    subscription_status = 'active'
                    AND risk_level = 'CHURNED'
                )
            """)
        ).scalar_one()

    assert source_count > 0, "No customers loaded"
    assert mart_count == source_count, (
        "Mart must contain one row per customer"
    )
    assert duplicate_count == 0, (
        "Duplicate customers found in mart"
    )
    assert invalid_risk_count == 0, (
        "Invalid risk labels found"
    )
    assert incorrect_churn_count == 0, (
        "Churn status and risk label disagree"
    )

    print(f"Mart validation passed: {mart_count} customers")


def main():
    print("Starting Subscription Churn Mart pipeline...")

    if not check_connection():
        raise ConnectionError(
            "Unable to connect to PostgreSQL"
        )

    print("PostgreSQL connection successful.")

    # Generate sample CSV files.
    generate_data()

    # Read generated files.
    customers = read_csv("customers.csv")
    subscriptions = read_csv("subscriptions.csv")
    usage = read_csv("monthly_usage.csv")

    # Validate before inserting anything.
    validate_data(customers, subscriptions, usage)
    print("Source data validation passed.")

    create_tables()
    load_data(customers, subscriptions, usage)
    create_models()
    validate_mart()

    print("Pipeline completed successfully!")


if __name__ == "__main__":
    main()
