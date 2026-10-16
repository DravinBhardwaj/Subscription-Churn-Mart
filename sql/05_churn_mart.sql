
CREATE OR REPLACE VIEW customer_churn_mart AS

WITH customer_features AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.join_date,

        s.plan_name,
        s.monthly_price,
        s.subscription_status,
        s.payment_failures,
        s.is_churned,

        u.previous_month_hours,
        u.current_month_hours,
        u.current_month_sessions,
        u.usage_decline_percent,
        u.usage_data_status,

        CASE
            WHEN u.usage_data_status <> 'complete'
                THEN 0
            WHEN u.usage_decline_percent >= 60
                THEN 2
            ELSE 0
        END AS decline_points,

        CASE
            WHEN s.payment_failures >= 1 THEN 1
            ELSE 0
        END AS payment_points,

        CASE
            WHEN u.usage_data_status = 'complete'
             AND u.current_month_sessions <= 2
                THEN 1
            ELSE 0
        END AS low_activity_points

    FROM stg_customers c

    INNER JOIN stg_subscriptions s
        ON c.customer_id = s.customer_id

    LEFT JOIN stg_usage u
        ON c.customer_id = u.customer_id
),

risk_scores AS (
    SELECT
        *,
        (
            decline_points
            + payment_points
            + low_activity_points
        ) AS risk_score

    FROM customer_features
)

SELECT
    *,

    CASE
        WHEN subscription_status = 'cancelled'
            THEN 'CHURNED'

        WHEN usage_data_status <> 'complete'
            THEN 'INSUFFICIENT DATA'

        WHEN risk_score >= 3
            THEN 'HIGH'

        WHEN risk_score >= 1
            THEN 'MEDIUM'

        ELSE 'LOW'
    END AS risk_level

FROM risk_scores;
