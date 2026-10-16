
# Subscription Churn Mart

An analytics engineering project using Python,
PostgreSQL, SQLAlchemy and raw SQL transformations.

## Problem Statement

Subscription companies need reliable customer
analytics to understand cancellations and identify
possible churn-risk indicators.

This project builds an analytical customer mart
and provides explanations based on engineered
features.

## Features

- Synthetic dataset generation
- PostgreSQL relational database
- SQL staging and analytical views
- Customer usage trend calculation
- Subscription churn indicators
- Rule-based churn-risk scoring
- Optional AI-generated explanations
- Streamlit analytics dashboard
- Automated validation tests
- Repeatable loading using database upserts

## Technology Stack

- Python
- PostgreSQL
- SQLAlchemy
- Pandas
- Streamlit
- Pytest
- OpenAI API (optional)

## Architecture

See [Architecture](docs/architecture.md).

## Data Model

The database contains:

1. customers
2. subscriptions
3. monthly_usage

These feed SQL views:

1. stg_customers
2. stg_subscriptions
3. stg_usage
4. customer_churn_mart

The final mart contains one row per customer.

## Setup Instructions

### 1. Prerequisites

Install Python 3.11+ and PostgreSQL.

Create a PostgreSQL database named:

    subscription_churn_db

### 2. Clone Repository

    git clone YOUR_REPOSITORY_URL

    cd Subscription-Churn-Mart

### 3. Create Environment

Windows PowerShell:

    python -m venv .venv

    .\.venv\Scripts\Activate.ps1

### 4. Install Dependencies

    python -m pip install -r requirements.txt

### 5. Configure Environment

Copy .env.example to .env.

PowerShell:

    Copy-Item .env.example .env

Set the PostgreSQL connection values.

Optional: Set OPENAI_API_KEY to enable live
AI-generated explanations.

Do not commit .env to GitHub.

### 6. Run Pipeline

    python -m app.pipeline

This creates tables, generates synthetic data,
loads the database and builds SQL views.

### 7. Run Tests

    python -m pytest tests/ -v

### 8. Start Dashboard

    python -m streamlit run app/dashboard.py

Open the local URL shown by Streamlit.

## Analytical Logic

Usage decline:

    (Previous Usage - Current Usage)
    / Previous Usage * 100

Risk score:

- Usage decline >= 60%: +2
- Failed payments >= 1: +1
- Sessions <= 2: +1

Risk categories:

- LOW: 0
- MEDIUM: 1-2
- HIGH: 3-4
- CHURNED: Cancelled subscription
- INSUFFICIENT DATA: Incomplete usage history

The thresholds are illustrative heuristics.

## Sample Results

The synthetic dataset contains:

- 12 customers
- 10 active subscriptions
- 2 cancelled subscriptions
- 23 monthly usage records

Snapshot cancellation proportion: 16.67%.

## Tests

The project includes automated tests for:

- Valid input data
- Duplicate customer IDs
- Negative usage values
- Invalid subscription status
- Missing monthly data
- High-risk explanations
- Missing-data explanations
- Restricting personal information from AI input

The pipeline also validates the final SQL mart.

## Edge Case

Customer 12 has no current-month usage record.

The system marks usage as incomplete instead of
assuming zero usage or inventing a churn probability.

## AI Approach

The AI component receives only engineered
analytical features.

The final risk label is calculated using SQL.

The AI explains the label but does not change it.

When the API is unavailable, the system provides
a clearly labeled deterministic explanation.

## Security

Credentials are stored in .env.

The .env file is excluded by .gitignore.

No real customer information is required.

## Technical Decisions

See [Design Note](docs/design_note.md).

## Known Limitations

- Small synthetic dataset
- Rule-based, non-calibrated risk scores
- Snapshot-level cancellation metrics
- Single subscription per customer
- Limited historical activity
- No prediction model trained on observed churn

## Future Improvements

- Add historical cancellation events
- Validate risk thresholds using real labeled data
- Add incremental processing
- Add data freshness checks
- Deploy using Docker
- Add CI and integration tests

## Demo

Add the 5-8 minute video URL here after recording.

## Author

Add your name and repository details here.
