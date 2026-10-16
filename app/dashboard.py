
import pandas as pd
import streamlit as st
from sqlalchemy import text

from app.database import engine
from app.explanations import ai_explanation


st.set_page_config(
    page_title="Subscription Churn Intelligence",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=60)
def load_metrics():
    with engine.connect() as connection:
        return pd.read_sql_query(
            text("""
                SELECT *
                FROM monthly_churn_metrics
                ORDER BY month_start
            """),
            connection,
        )


@st.cache_data(ttl=60)
def load_predictions():
    with engine.connect() as connection:
        return pd.read_sql_query(
            text("""
                SELECT
                    p.customer_id,
                    c.customer_name,
                    p.prediction_month,
                    p.target_month,
                    p.churn_probability,
                    p.risk_level,
                    p.model_name,
                    f.plan_name,
                    f.monthly_price,
                    f.payment_failures,
                    f.current_month_hours,
                    f.current_month_sessions,
                    f.previous_month_hours,
                    f.usage_decline_percent,
                    f.avg_usage_3_months,
                    f.usage_data_status,
                    f.tenure_months

                FROM customer_risk_predictions p

                JOIN customers c
                  ON c.customer_id = p.customer_id

                JOIN customer_churn_mart f
                  ON f.customer_id = p.customer_id
                 AND f.month_start = p.prediction_month

                WHERE p.prediction_month = (
                    SELECT MAX(prediction_month)
                    FROM customer_risk_predictions
                )

                ORDER BY
                    p.churn_probability DESC,
                    p.customer_id
            """),
            connection,
        )


def format_customer(row):
    customer = row.to_dict()

    for key, value in customer.items():
        if pd.isna(value):
            customer[key] = None
        elif hasattr(value, "item"):
            customer[key] = value.item()

    return customer


def main():
    st.title("📊 Subscription Churn Intelligence")

    st.write(
        "Historical churn analytics using PostgreSQL, "
        "SQL feature engineering, Machine Learning "
        "and Google Gemini."
    )

    st.info(
        "The estimated probabilities come from a model "
        "trained on synthetic data. HIGH, MEDIUM and LOW "
        "are relative customer-review priorities, "
        "not absolute probabilities."
    )

    if st.button("Refresh Dashboard"):
        load_metrics.clear()
        load_predictions.clear()
        st.rerun()

    try:
        metrics = load_metrics()
        predictions = load_predictions()

    except Exception as error:
        st.error(
            "Could not load analytics. Run the SQL "
            "pipeline and ML training first."
        )
        st.code(str(error))
        st.stop()

    if metrics.empty or predictions.empty:
        st.warning("No analytics results available.")
        st.stop()

    # Historical churn metrics
    latest = metrics.iloc[-1]

    st.subheader("Historical Churn Analytics")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Customers at Start",
        f"{int(latest['customers_at_start']):,}",
    )

    c2.metric(
        "Monthly Cancellations",
        f"{int(latest['churned_customers']):,}",
    )

    c3.metric(
        "Monthly Churn Rate",
        f"{float(latest['churn_rate_percent']):.2f}%",
    )

    c4.metric(
        "Retention Rate",
        f"{float(latest['retention_rate_percent']):.2f}%",
    )

    st.metric(
        "Lost Monthly Recurring Revenue",
        f"₹{float(latest['lost_monthly_recurring_revenue']):,.2f}",
    )

    trend = metrics.copy()

    trend["month_start"] = pd.to_datetime(
        trend["month_start"]
    )

    trend = trend.set_index("month_start")

    left, right = st.columns(2)

    with left:
        st.write("Monthly Churn Rate (%)")
        st.line_chart(trend["churn_rate_percent"])

    with right:
        st.write("Monthly Cancellations")
        st.bar_chart(trend["churned_customers"])

    st.divider()

    # Relative risk distribution
    st.subheader("Next-Month Customer Review Priorities")

    st.write(
        f"Prediction snapshot: "
        f"{predictions['prediction_month'].iloc[0]}"
    )

    st.write(
        f"Target month: "
        f"{predictions['target_month'].iloc[0]}"
    )

    counts = predictions["risk_level"].value_counts()

    high = int(counts.get("HIGH", 0))
    medium = int(counts.get("MEDIUM", 0))
    low = int(counts.get("LOW", 0))

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Customers Scored", f"{len(predictions):,}")
    c2.metric("HIGH Priority", f"{high:,}")
    c3.metric("MEDIUM Priority", f"{medium:,}")
    c4.metric("LOW Priority", f"{low:,}")

    priority_counts = (
        counts.reindex(
            ["HIGH", "MEDIUM", "LOW"],
            fill_value=0,
        )
    )

    st.bar_chart(priority_counts)

    st.caption(
        "HIGH = top 10% of predicted probabilities; "
        "MEDIUM = next 20%; LOW = remaining 70%. "
        "This is a customer-ranking policy rather "
        "than a validated probability threshold."
    )

    st.divider()

    # Customer risk table
    st.subheader("Customer Predictions")

    priority_filter = st.selectbox(
        "Filter by review priority",
        ["All", "HIGH", "MEDIUM", "LOW"],
    )

    filtered = predictions.copy()

    if priority_filter != "All":
        filtered = filtered[
            filtered["risk_level"] == priority_filter
        ]

    filtered["probability_percent"] = (
        filtered["churn_probability"] * 100
    ).round(2)

    st.dataframe(
        filtered[
            [
                "customer_id",
                "customer_name",
                "plan_name",
                "usage_decline_percent",
                "payment_failures",
                "probability_percent",
                "risk_level",
            ]
        ].rename(columns={
            "probability_percent":
                "Estimated Cancellation %",
            "risk_level": "Review Priority",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Customer detail and Gemini
    st.subheader("Customer Risk Explanation")

    customer_choices = {
        f"{row.customer_id} - {row.customer_name}":
            int(row.customer_id)
        for row in predictions.itertuples()
    }

    selected_label = st.selectbox(
        "Select customer",
        list(customer_choices.keys()),
    )

    customer_id = customer_choices[selected_label]

    row = predictions[
        predictions["customer_id"] == customer_id
    ].iloc[0]

    customer = format_customer(row)

    probability = float(
        customer["churn_probability"]
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Estimated Next-Month Cancellation",
        f"{probability * 100:.2f}%",
    )

    c2.metric(
        "Relative Review Priority",
        customer["risk_level"],
    )

    st.progress(
        min(1.0, max(0.0, probability))
    )

    feature_names = [
        "plan_name",
        "monthly_price",
        "payment_failures",
        "current_month_hours",
        "current_month_sessions",
        "previous_month_hours",
        "usage_decline_percent",
        "avg_usage_3_months",
        "usage_data_status",
        "tenure_months",
    ]

    feature_table = pd.DataFrame([
        {
            "Feature": field,
            "Value": customer.get(field),
        }
        for field in feature_names
    ])

    st.write("SQL-Engineered Customer Features")

    st.dataframe(
        feature_table,
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Generate Gemini Explanation"):
        with st.spinner("Generating explanation..."):
            explanation, source = ai_explanation(
                customer
            )

        st.info(explanation)
        st.caption(f"Explanation source: {source}")

    st.divider()

    st.subheader("Methodology and Limitations")

    st.write(
        "SQL calculates the historical churn rate "
        "and customer behavioral features. Logistic "
        "Regression estimates future cancellation "
        "probabilities using those features. "
        "Relative priority bands rank customers for "
        "review. Gemini provides narrative explanations "
        "without changing the stored ML results."
    )

    st.warning(
        "This demonstration uses synthetic data. "
        "It is not a validated real-world churn "
        "prediction or continuous live-monitoring system."
    )


if __name__ == "__main__":
    main()
