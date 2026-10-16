
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    join_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL UNIQUE
        REFERENCES customers(customer_id),
    plan_name VARCHAR(30) NOT NULL,
    monthly_price NUMERIC(10, 2) NOT NULL
        CHECK (monthly_price > 0),
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('active', 'cancelled')),
    payment_failures INTEGER NOT NULL DEFAULT 0
        CHECK (payment_failures >= 0)
);

CREATE TABLE IF NOT EXISTS monthly_usage (
    usage_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INTEGER NOT NULL
        REFERENCES customers(customer_id),
    month_start DATE NOT NULL,
    usage_hours NUMERIC(10, 2) NOT NULL
        CHECK (usage_hours >= 0),
    session_count INTEGER NOT NULL
        CHECK (session_count >= 0),

    CONSTRAINT unique_customer_month
        UNIQUE (customer_id, month_start)
);
