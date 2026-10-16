
CREATE OR REPLACE VIEW stg_subscriptions AS

SELECT
    subscription_id,
    customer_id,
    plan_name,
    monthly_price,
    status AS subscription_status,
    payment_failures,

    CASE
        WHEN status = 'cancelled' THEN 1
        ELSE 0
    END AS is_churned

FROM subscriptions;
