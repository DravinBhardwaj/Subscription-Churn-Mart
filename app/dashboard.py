
import pandas as pd
import streamlit as st
from sqlalchemy import text

from app.database import engine
from app.explanations import ai_explanation


st.set_page_config(
    page_title="Subscription Churn Mart",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=60)
def load_mart():
    """Read the final analytics mart from PostgreSQL."""

    query = text("""
        SELECT
            customer_id,
            customer_name,
            plan_name,
            monthly_price,
            subscription_status,
            payment_failures,
            previous_month_hours,
            current_month_hours,
            current_month_sessions,
            usage_decline_percent,
            usage_data_status,
            decline_points,
            payment_points,
            low_activity_points,
            risk_score,
            risk_level
        FROM customer_churn_mart
        ORDER BY customer_id
    """)

    with engine.connect() as connection:
        return pd.read_sql_query(query, connection)


def prepare_customer(row):
    """Convert a Pandas record into a normal dictionary."""

    customer = row.to_dict()

    for key, value in customer.items():
        if pd.isna(value):
            customer[key] = None

    return customer


def main():
    st.title("📊 Subscription Churn Mart")

    st.write(
        "A SQL-driven customer analytics system with "
        "explainable churn-risk indicators."
    )

    st.caption(
        "Demonstration using synthetic customer data. "
        "Risk levels are heuristic indicators, "
        "not machine-learning probabilities."
    )

    if st.button("Refresh analytics"):
        load_mart.clear()
        st.rerun()

    try:
        df = load_mart()

    except Exception as error:
        st.error(
            "Unable to load the analytics mart. "
            "Check PostgreSQL and run the data pipeline."
        )
        st.code(str(error))
        st.stop()

    if df.empty:
        st.warning(
            "No data found. Run: python -m app.pipeline"
        )
        st.stop()

    # ---------------------------------------
    # KPI METRICS
    # ---------------------------------------

    total_customers = len(df)

    churned_customers = int(
        (df["subscription_status"] == "cancelled").sum()
    )

    active_customers = int(
        (df["subscription_status"] == "active").sum()
    )

    churn_rate = (
        churned_customers / total_customers * 100
        if total_customers > 0 else 0
    )

    st.subheader("Customer Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Customers", total_customers)
    col2.metric("Active Customers", active_customers)
    col3.metric("Churned Customers", churned_customers)
    col4.metric("Churn Rate", f"{churn_rate:.2f}%")

    st.caption(
        "Churn rate = cancelled customers / all "
        "customers in this synthetic snapshot. "
        "It is not a monthly churn rate."
    )

    st.divider()

    # ---------------------------------------
    # RISK DISTRIBUTION
    # ---------------------------------------

    st.subheader("Customer Risk Distribution")

    active_df = df[
        df["subscription_status"] == "active"
    ].copy()

    risk_order = [
        "LOW",
        "MEDIUM",
        "HIGH",
        "INSUFFICIENT DATA",
    ]

    risk_counts = (
        active_df["risk_level"]
        .value_counts()
        .reindex(risk_order, fill_value=0)
    )

    left, right = st.columns(2)

    with left:
        st.write("Active Customers by Risk Level")
        st.bar_chart(risk_counts)

    with right:
        st.write("Usage Comparison")

        usage_chart = active_df[
            [
                "customer_name",
                "previous_month_hours",
                "current_month_hours",
            ]
        ].copy()

        usage_chart = usage_chart.set_index(
            "customer_name"
        )

        st.bar_chart(usage_chart)

    st.divider()

    # ---------------------------------------
    # CUSTOMER TABLE
    # ---------------------------------------

    st.subheader("Customer Analytics Table")

    risk_filter = st.selectbox(
        "Filter by risk level",
        [
            "All",
            "LOW",
            "MEDIUM",
            "HIGH",
            "INSUFFICIENT DATA",
            "CHURNED",
        ],
    )

    filtered_df = df.copy()

    if risk_filter != "All":
        filtered_df = filtered_df[
            filtered_df["risk_level"] == risk_filter
        ]

    display_columns = [
        "customer_id",
        "customer_name",
        "plan_name",
        "subscription_status",
        "usage_decline_percent",
        "payment_failures",
        "risk_score",
        "risk_level",
    ]

    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ---------------------------------------
    # CUSTOMER EXPLANATIONS
    # ---------------------------------------

    st.subheader("Explain Customer Risk")

    customer_options = {
        f"{row['customer_id']} - {row['customer_name']}":
            row["customer_id"]
        for _, row in df.iterrows()
    }

    selected_label = st.selectbox(
        "Select a customer",
        list(customer_options.keys()),
    )

    selected_id = customer_options[selected_label]

    selected_row = df[
        df["customer_id"] == selected_id
    ].iloc[0]

    customer = prepare_customer(selected_row)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Risk Classification",
        customer["risk_level"],
    )

    col2.metric(
        "Risk Score",
        str(customer["risk_score"]),
    )

    decline = customer["usage_decline_percent"]

    col3.metric(
        "Usage Decline",
        (
            f"{float(decline):.1f}%"
            if decline is not None
            else "Unavailable"
        ),
    )

    st.write("Engineered Customer Features")

    feature_table = pd.DataFrame({
        "Feature": [
            "Subscription Status",
            "Usage Data Status",
            "Previous Month Hours",
            "Current Month Hours",
            "Current Month Sessions",
            "Payment Failures",
            "Decline Points",
            "Payment Points",
            "Activity Points",
        ],
        "Value": [
            customer["subscription_status"],
            customer["usage_data_status"],
            customer["previous_month_hours"],
            customer["current_month_hours"],
            customer["current_month_sessions"],
            customer["payment_failures"],
            customer["decline_points"],
            customer["payment_points"],
            customer["low_activity_points"],
        ],
    })

    st.dataframe(
        feature_table,
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Generate Risk Explanation"):
        with st.spinner("Preparing explanation..."):
            explanation, source = ai_explanation(
                customer
            )

        st.info(explanation)
        st.caption(f"Explanation source: {source}")

    st.divider()

    st.subheader("Methodology and Limitations")

    st.write(
        "The system uses predefined SQL rules to "
        "identify churn indicators. These risk scores "
        "are not calibrated probabilities. Missing "
        "usage is treated as insufficient evidence. "
        "The demonstration dataset is synthetic, "
        "and the risk thresholds require validation "
        "before any real business use."
    )


if __name__ == "__main__":
    main()
