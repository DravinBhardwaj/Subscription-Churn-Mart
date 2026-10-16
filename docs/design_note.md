
# Design and Decision Note

## Project: Subscription Churn Mart

### 1. Problem

Subscription businesses need to understand which
customers have cancelled and which active customers
show possible warning signs of churn.

### 2. Approach

I implemented a customer-level analytical mart
using Python, PostgreSQL, SQLAlchemy and raw SQL.

The solution separates ingestion, validation,
transformation and presentation.

### 3. Main Technical Decisions

**PostgreSQL**

Used for relational storage and SQL analytical
transformations.

**SQLAlchemy**

Used as the Python database connection layer.
Business transformations remain visible in
separate SQL files.

**SQL Views**

Used for transparent and maintainable analytical
models. The small dataset does not require
materialized transformations.

**Synthetic Data**

Used to avoid exposing confidential or personal
information and to ensure reproducibility.

**Rule-Based Risk Scoring**

Used because no historical labeled training data
is provided. The project does not claim to
predict actual churn probabilities.

**AI Explanations**

The optional language model explains already
computed features. It does not assign or modify
customer risk levels.

### 4. Risk Assumptions

- Usage decline of 60% or more: 2 points
- At least one failed payment: 1 point
- Two or fewer monthly sessions: 1 point

Risk scores:

- 0: LOW
- 1-2: MEDIUM
- 3-4: HIGH

Cancelled customers are marked CHURNED.

Customers with missing or insufficient usage
history are marked INSUFFICIENT DATA.

These thresholds are demonstrative assumptions,
not validated business thresholds.

### 5. Edge Cases

The implementation handles:

- Duplicate customer IDs
- Invalid subscription states
- Negative usage
- Missing monthly records
- Division by zero when previous usage is zero
- Repeated pipeline execution
- Unavailable AI services

### 6. Trade-offs

SQL views simplify development and inspection
but may become inefficient with very large datasets.

The prototype uses one subscription record per
customer and two months of sample usage.

The project does not model historical subscription
changes or cancellations over time.

### 7. Known Limitations

- Very small synthetic dataset
- No validated predictive ML model
- Fixed example business thresholds
- No historical cancellation event dates
- Snapshot churn rate rather than period churn rate
- No automatic deletion of removed source records
- Basic AI response validation only
- Database setup requires a local PostgreSQL service

### 8. Future Improvements

For production, I would add:

- Historical subscription and cancellation events
- Incremental ingestion with source timestamps
- Automated data freshness checks
- Larger historical datasets
- Calibration of churn-risk thresholds
- Materialized reporting tables
- Stronger AI explanation verification
- Containerized deployment and CI

### 9. Conclusion

The solution prioritizes correctness,
reproducibility, explainability and simple
engineering decisions over unnecessary complexity.
