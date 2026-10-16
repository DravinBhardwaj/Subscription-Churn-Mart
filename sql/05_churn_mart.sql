
CREATE OR REPLACE VIEW customer_churn_mart AS

WITH features AS (
    SELECT
        c.customer_id,
        c.customer_name,
        s.month_start,
        s.plan_name,
        s.monthly_price,
        s.active_at_start,
        s.active_at_end,
        s.cancelled_during_month,
        s.payment_failures,

        u.current_month_hours,
        u.current_month_sessions,
        u.previous_month_hours,
        u.two_months_ago_hours,
        u.usage_decline_percent,
        u.avg_usage_3_months,
        u.usage_data_status,

        (
            (EXTRACT(YEAR FROM AGE(
                s.month_start, c.join_date
            )) * 12)
            + EXTRACT(MONTH FROM AGE(
                s.month_start, c.join_date
            ))
        )::INTEGER AS tenure_months

    FROM stg_subscriptions s
    JOIN stg_customers c
        ON c.customer_id = s.customer_id
    JOIN stg_usage u
        ON u.customer_id = s.customer_id
       AND u.month_start = s.month_start
)

SELECT
    f.*,

    -- This label belongs to the NEXT month.
    -- It must never be used as an input feature.
    next_s.cancelled_during_month::INTEGER
        AS churn_next_month,

    CASE
        WHEN next_s.customer_id IS NULL
        THEN FALSE
        ELSE TRUE
    END AS has_future_label

FROM features f

LEFT JOIN stg_subscriptions next_s
    ON next_s.customer_id = f.customer_id
   AND next_s.month_start =
       (f.month_start + INTERVAL '1 month')::date

WHERE f.active_at_end = TRUE;
