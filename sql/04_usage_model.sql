
CREATE OR REPLACE VIEW stg_usage AS

SELECT
    sm.customer_id,
    sm.month_start,

    current_u.usage_hours AS current_month_hours,
    current_u.session_count AS current_month_sessions,
    previous_u.usage_hours AS previous_month_hours,
    previous_2.usage_hours AS two_months_ago_hours,

    CASE
        WHEN previous_u.usage_hours > 0
         AND current_u.usage_hours IS NOT NULL
        THEN ROUND(
            100.0 *
            (
                previous_u.usage_hours
                - current_u.usage_hours
            ) / previous_u.usage_hours,
            2
        )
        ELSE NULL
    END AS usage_decline_percent,

    CASE
        WHEN current_u.usage_hours IS NOT NULL
         AND previous_u.usage_hours IS NOT NULL
         AND previous_2.usage_hours IS NOT NULL
        THEN ROUND(
            (
                current_u.usage_hours
                + previous_u.usage_hours
                + previous_2.usage_hours
            ) / 3.0,
            2
        )
        ELSE NULL
    END AS avg_usage_3_months,

    CASE
        WHEN current_u.usage_hours IS NULL
          OR previous_u.usage_hours IS NULL
        THEN 'missing_usage'
        WHEN previous_u.usage_hours = 0
        THEN 'zero_baseline'
        ELSE 'complete'
    END AS usage_data_status

FROM subscription_monthly sm

LEFT JOIN monthly_usage current_u
    ON current_u.customer_id = sm.customer_id
   AND current_u.month_start = sm.month_start

LEFT JOIN monthly_usage previous_u
    ON previous_u.customer_id = sm.customer_id
   AND previous_u.month_start =
       (sm.month_start - INTERVAL '1 month')::date

LEFT JOIN monthly_usage previous_2
    ON previous_2.customer_id = sm.customer_id
   AND previous_2.month_start =
       (sm.month_start - INTERVAL '2 months')::date;
