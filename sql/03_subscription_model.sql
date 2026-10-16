
CREATE OR REPLACE VIEW stg_subscriptions AS
SELECT
    sm.customer_id,
    sm.month_start,
    s.plan_name,
    s.monthly_price,
    sm.active_at_start,
    sm.cancelled_during_month,
    sm.active_at_end,
    sm.payment_failures
FROM subscription_monthly sm
JOIN subscriptions s
    ON sm.customer_id = s.customer_id;
