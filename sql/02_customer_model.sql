
CREATE OR REPLACE VIEW stg_customers AS
SELECT
    customer_id,
    customer_name,
    join_date
FROM customers;
