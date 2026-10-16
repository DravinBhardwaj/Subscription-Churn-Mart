
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    join_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL UNIQUE
        REFERENCES customers(customer_id),
    plan_name VARCHAR(20) NOT NULL,
    monthly_price NUMERIC(10,2) NOT NULL
        CHECK (monthly_price > 0)
);

CREATE TABLE IF NOT EXISTS subscription_monthly (
    customer_id INTEGER NOT NULL
        REFERENCES customers(customer_id),
    month_start DATE NOT NULL,
    active_at_start BOOLEAN NOT NULL,
    cancelled_during_month BOOLEAN NOT NULL,
    active_at_end BOOLEAN NOT NULL,
    payment_failures INTEGER NOT NULL DEFAULT 0
        CHECK (payment_failures >= 0),
    PRIMARY KEY (customer_id, month_start),
    CHECK (
        active_at_start = TRUE
        AND active_at_end <> cancelled_during_month
    )
);

CREATE TABLE IF NOT EXISTS monthly_usage (
    customer_id INTEGER NOT NULL
        REFERENCES customers(customer_id),
    month_start DATE NOT NULL,
    usage_hours NUMERIC(10,2) NOT NULL
        CHECK (usage_hours >= 0),
    session_count INTEGER NOT NULL
        CHECK (session_count >= 0),
    PRIMARY KEY (customer_id, month_start)
);

CREATE TABLE IF NOT EXISTS customer_risk_predictions (
    customer_id INTEGER NOT NULL
        REFERENCES customers(customer_id),
    prediction_month DATE NOT NULL,
    target_month DATE NOT NULL,
    churn_probability DOUBLE PRECISION NOT NULL
        CHECK (
            churn_probability >= 0
            AND churn_probability <= 1
        ),
    risk_level VARCHAR(20) NOT NULL
        CHECK (risk_level IN ('LOW','MEDIUM','HIGH')),
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (customer_id, prediction_month)
);

CREATE INDEX IF NOT EXISTS idx_subscription_month
    ON subscription_monthly(month_start);

CREATE INDEX IF NOT EXISTS idx_usage_month
    ON monthly_usage(month_start);

CREATE INDEX IF NOT EXISTS idx_prediction_risk
    ON customer_risk_predictions(prediction_month, risk_level);
