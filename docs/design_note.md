# Design and Decision Note

## Project: Subscription Churn Mart V3

### 1. Problem Statement

Subscription-based businesses need to identify customers who have already cancelled their subscriptions and active customers who may cancel in the future.

Customer engagement, payment behavior and subscription information are stored in different records. Analyzing these records separately makes it difficult to understand churn trends and identify potential cancellation risks.

This project addresses the problem by creating a SQL-driven analytical system that measures historical churn and estimates future cancellation risk using Machine Learning.

### 2. Proposed Solution and Approach

I developed an end-to-end analytics engineering project using **Python, PostgreSQL, SQLAlchemy, SQL transformations, Scikit-learn, Google Gemini AI and Streamlit**.

The system follows these stages:

1. **Data Generation:** Generates reproducible synthetic customer, subscription and monthly usage records.
2. **Data Validation:** Checks duplicate records, invalid values and inconsistent subscription history.
3. **Database Storage:** Stores validated records in PostgreSQL using SQLAlchemy.
4. **SQL Transformations:** Creates analytical models and engineered features such as usage decline, engagement trends and historical churn.
5. **Machine Learning:** Trains Logistic Regression to estimate next-month customer cancellation probability.
6. **Customer Prioritization:** Ranks active customers into HIGH, MEDIUM and LOW review-priority groups.
7. **Gemini AI Explanation:** Generates human-readable explanations from SQL-engineered features and ML predictions.
8. **Dashboard:** Displays historical churn, customer predictions and explanations using Streamlit.

The system initially processes **10,000 synthetic customers across 18 reporting months**, producing approximately 150,000 subscription-month records.

### 3. Main Technical Decisions

**PostgreSQL**

I selected PostgreSQL for relational data storage, historical subscription tracking, data integrity constraints and analytical SQL operations.

**SQLAlchemy**

I used SQLAlchemy to manage Python-to-PostgreSQL connectivity, database transactions and batched record loading.

I deliberately kept business transformations in separate SQL files so that the analytics logic remains readable and independently reviewable.

**SQL Transformation Models**

I organized SQL logic into customer, subscription, usage, churn-feature and monthly-metrics models.

SQL calculates metrics such as monthly churn rates, usage decline and three-month average usage. It also prepares historical customer-level features for Machine Learning.

This ensures SQL remains the analytical foundation of the project rather than delegating all data processing to Python.

**SQL Views**

I selected SQL views because they are easy to inspect, maintain and modify.

Views avoid storing redundant analytical copies of source records, although repeated computations may become expensive for larger datasets.

**Synthetic Data**

I used deterministic synthetic data to protect privacy, avoid dependency on confidential business records and allow reviewers to reproduce the solution.

The dataset simulates engagement changes, payment failures, cancellations and missing observations.

**Logistic Regression**

I selected Logistic Regression as the initial ML algorithm because it is relatively simple, computationally efficient and suitable as a baseline for binary classification.

The model estimates whether an active customer will cancel during the following month.

Numeric preprocessing, missing-value handling and categorical encoding are included in the Scikit-learn pipeline.

**Chronological Data Splitting**

I used earlier customer-month records for training and later records for validation and testing.

This better reflects real-world prediction, where future customer outcomes must not be available when predictions are made.

**Relative Customer-Risk Prioritization**

Because predicted cancellation probabilities are generally low in the synthetic dataset, I separated actual ML probabilities from customer-review priorities.

The system assigns:

- **HIGH:** Top 10% of active customers by predicted cancellation probability.
- **MEDIUM:** Next 20%.
- **LOW:** Remaining 70%.

These labels represent relative review priority, not absolute cancellation probabilities.

**Google Gemini AI**

Gemini is used to explain SQL-engineered features and stored ML predictions in understandable language.

Gemini does not calculate churn rates, train the model or modify predictions.

A deterministic fallback explanation is available if the AI service fails or produces an incomplete response.

**Streamlit**

I selected Streamlit to provide a lightweight interface for viewing historical business metrics, ML predictions, customer engagement and AI explanations without requiring a separate frontend/backend deployment.

### 4. Churn Calculation and ML Methodology

**Historical Churn Rate**

The historical churn rate is calculated in SQL:

\[
\text{Monthly Churn Rate} =
\frac{\text{Customers Cancelled During Month}}
{\text{Customers Active at Start of Month}}\times100
\]

Additional SQL metrics include monthly retention rate, cancellation count and lost monthly recurring revenue.

**SQL-Engineered ML Features**

The ML model receives features including:

- Previous and current monthly usage hours.
- Usage decline percentage.
- Three-month average usage.
- Current monthly session count.
- Payment failures.
- Subscription plan and monthly price.
- Customer tenure.
- Usage-data completeness status.

**Prediction Target**

The supervised learning target is `churn_next_month`, indicating whether an active customer cancelled during the following reporting month.

Only customer-month records with known future outcomes are used for supervised training and evaluation.

**Model Evaluation**

The project calculates ROC-AUC, PR-AUC, precision, recall and Brier score on later historical periods.

Predictions are stored in the PostgreSQL `customer_risk_predictions` table and accessed by the dashboard.

### 5. Edge Cases and Validation

The implementation includes checks for:

- Duplicate customer and subscription records.
- Invalid subscription plans.
- Negative usage hours.
- Invalid payment-failure counts.
- Unknown customer references.
- Inconsistent subscription and cancellation status.
- Subscription history continuing after cancellation.
- Missing monthly usage observations.
- Division by zero in usage-decline calculations.
- Repeated execution using PostgreSQL upserts.
- Invalid ML probability values.
- Incomplete or unavailable Gemini responses.

The test suite uses Pytest to validate source-data behavior, ML processing, priority ranking and explanation logic.

### 6. Important Trade-offs

**SQL Views vs Materialized Tables**

SQL views simplify analytical development but can require repeated computation. Materialized views or incremental reporting tables may be better for production-scale data.

**Logistic Regression vs Complex Models**

Logistic Regression provides a simpler baseline that is easier to train and debug. More complex models could improve predictive performance, but would require proper comparison and validation.

**Batch Processing vs Real-Time Monitoring**

The current system processes historical monthly records in batches. It does not yet consume live subscription events or continuously refreshed usage streams.

**Synthetic Data vs Real-World Data**

Synthetic data makes the project reproducible and privacy-conscious, but it does not represent the full complexity of real customer behavior.

**Relative Priorities vs Absolute Risk Thresholds**

Relative ranking guarantees a review order but does not indicate that HIGH-priority customers have a high absolute chance of cancelling.

The model probability and review priority are therefore presented separately.

### 7. Known Limitations

- The ML model is trained and evaluated on synthetic data.
- Synthetic cancellation behavior depends on assumptions in the data generator.
- Predicted probabilities are not validated against real-world outcomes.
- Probability calibration has not been comprehensively established.
- Customer prioritization uses fixed percentile bands.
- The historical model assumes a simplified subscription lifecycle without reactivation.
- The current system does not process real-time customer activity.
- Database upserts do not automatically remove deleted source records.
- The pipeline currently loads data in batches rather than using a complete incremental ingestion architecture.
- Gemini explanations are checked for completeness, but are not independently fact-verified in every detail.
- PostgreSQL must be configured for a clean local setup.

### 8. Future Improvements

For a production-oriented version, I would add:

- Real historical customer data with appropriate privacy controls.
- Renewal-date-aware customer monitoring.
- More comprehensive probability calibration.
- Random Forest and gradient-boosting model comparisons.
- Model explainability using coefficients or SHAP.
- Automated drift detection and monitoring.
- Incremental ingestion and data freshness checks.
- PostgreSQL integration tests and CI/CD.
- Docker-based reproducible deployment.
- Materialized analytical models for larger datasets.
- Stronger validation of Gemini-generated explanations.

### 9. Conclusion

Subscription Churn Mart V3 combines **analytics engineering, Machine Learning and generative AI**, with clear separation of responsibilities.

PostgreSQL and SQL transformations provide reliable analytical features and historical churn measurements. Logistic Regression estimates future cancellation probabilities, customer ranking supports review prioritization, and Google Gemini explains the available evidence.

The solution prioritizes **correctness, reproducibility, transparency, explainability and maintainable engineering decisions**, consistent with the objectives of the technical assessment.