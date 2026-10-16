
CREATE OR REPLACE VIEW stg_usage AS

WITH reporting_month AS (
    SELECT MAX(month_start) AS current_month
    FROM monthly_usage
),

monthly_comparison AS (
    SELECT
        c.customer_id,

        previous.usage_hours AS previous_month_hours,
        current_usage.usage_hours AS current_month_hours,
        current_usage.session_count AS current_month_sessions,

        CASE
            WHEN previous.usage_hours IS NULL THEN NULL
            WHEN current_usage.usage_hours IS NULL THEN NULL
            WHEN previous.usage_hours = 0 THEN NULL
            ELSE ROUND(
                100.0 * (
                    previous.usage_hours
                    - current_usage.usage_hours
                ) / previous.usage_hours,
                2
            )
        END AS usage_decline_percent

    FROM stg_customers c

    CROSS JOIN reporting_month r

    LEFT JOIN monthly_usage previous
        ON c.customer_id = previous.customer_id
        AND previous.month_start = (
            r.current_month - INTERVAL '1 month'
        )::date

    LEFT JOIN monthly_usage current_usage
        ON c.customer_id = current_usage.customer_id
        AND current_usage.month_start = r.current_month
)

SELECT
    *,
    CASE
        WHEN previous_month_hours IS NULL
          OR current_month_hours IS NULL
            THEN 'missing_usage'
        WHEN previous_month_hours = 0
            THEN 'no_previous_activity'
        ELSE 'complete'
    END AS usage_data_status

FROM monthly_comparison;
