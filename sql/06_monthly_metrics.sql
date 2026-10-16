
CREATE OR REPLACE VIEW monthly_churn_metrics AS

SELECT
    month_start,

    COUNT(*) AS customers_at_start,

    COUNT(*) FILTER (
        WHERE cancelled_during_month
    ) AS churned_customers,

    COUNT(*) FILTER (
        WHERE active_at_end
    ) AS customers_at_end,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE cancelled_during_month
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_percent,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE active_at_end
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS retention_rate_percent,

    COALESCE(
        SUM(monthly_price) FILTER (
            WHERE cancelled_during_month
        ),
        0
    ) AS lost_monthly_recurring_revenue

FROM stg_subscriptions
GROUP BY month_start;
