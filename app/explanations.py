
import json
import logging
import os
import re

from google import genai
from google.genai import types

from app.config import BASE_DIR


logger = logging.getLogger(__name__)

# Loading config also loads the .env file.
_ = BASE_DIR


ALLOWED_FIELDS = [
    "plan_name",
    "monthly_price",
    "payment_failures",
    "current_month_hours",
    "current_month_sessions",
    "previous_month_hours",
    "usage_decline_percent",
    "avg_usage_3_months",
    "usage_data_status",
    "tenure_months",
    "churn_probability",
    "risk_level",
]


def explanation_features(customer):
    """Select approved SQL and ML features."""

    features = {}

    for field in ALLOWED_FIELDS:
        value = customer.get(field)

        if value is None:
            features[field] = None
        elif isinstance(value, (str, int, float, bool)):
            features[field] = value
        else:
            features[field] = str(value)

    return features


def rule_based_explanation(customer):
    """Provide four sentences if Gemini is unavailable."""

    probability = customer.get("churn_probability")
    risk = customer.get("risk_level", "UNKNOWN")

    probability_text = (
        f"{float(probability) * 100:.2f}%"
        if probability is not None
        else "an unavailable probability"
    )

    sentence1 = (
        f"The ML model estimates a {probability_text} "
        "chance of cancellation during the next month."
    )

    previous = customer.get("previous_month_hours")
    current = customer.get("current_month_hours")
    decline = customer.get("usage_decline_percent")

    if (
        previous is not None
        and current is not None
        and decline is not None
    ):
        sentence2 = (
            f"Customer usage changed from "
            f"{float(previous):.2f} hours to "
            f"{float(current):.2f} hours, "
            f"representing a {float(decline):.2f}% decline."
        )
    else:
        sentence2 = (
            "The available usage history is incomplete, "
            "so a reliable month-over-month usage "
            "decline cannot be calculated."
        )

    failures = int(customer.get("payment_failures") or 0)
    sessions = customer.get("current_month_sessions")

    if failures > 0:
        sentence3 = (
            f"The customer recorded {failures} failed "
            "payment(s), which is an additional "
            "feature considered by the model."
        )
    elif sessions is not None:
        sentence3 = (
            f"The customer recorded {int(sessions)} "
            "sessions during the current reporting month."
        )
    else:
        sentence3 = (
            "Available payment and engagement features "
            "provide additional context for the estimate."
        )

    sentence4 = (
        f"The customer belongs to the {risk} relative-priority "
        "group based on their ranking among active customers; "
        "the model was trained on synthetic data, so its "
        "probabilities are not validated for real-world use."
    )

    return " ".join([
        sentence1,
        sentence2,
        sentence3,
        sentence4,
    ])


def valid_explanation(answer):
    """Reject empty, incomplete or truncated responses."""

    if not isinstance(answer, str):
        return False

    answer = answer.strip()

    if not 140 <= len(answer) <= 2500:
        return False

    if not answer.endswith((".", "!", "?")):
        return False

    sentences = [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            answer,
        )
        if sentence.strip()
    ]

    return (
        3 <= len(sentences) <= 4
        and all(
            len(sentence.split()) >= 6
            for sentence in sentences
        )
    )


def ai_explanation(customer):
    """Generate a Gemini explanation using engineered features."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return (
            rule_based_explanation(customer),
            "Rule-based fallback: API key missing",
        )

    features = explanation_features(customer)

    probability = customer.get("churn_probability")

    if probability is None:
        return (
            rule_based_explanation(customer),
            "Rule-based fallback: probability unavailable",
        )

    prompt = f"""
Explain this subscription churn prediction.

Engineered SQL and ML features:
{json.dumps(features, indent=2)}

The HIGH/MEDIUM/LOW labels represent relative priority,
not absolute cancellation probability.

HIGH = top 10% by predicted probability.
MEDIUM = next 20%.
LOW = remaining 70%.

Write EXACTLY FOUR complete sentences:

1. State the estimated cancellation probability
   and relative priority.
2. Explain the change in usage hours and percentage.
3. Explain sessions and payment failures.
4. Discuss the interpretation and limitations.

Rules:
- Use only provided values.
- Do not invent information.
- Do not change the risk category or probability.
- Do not make unsupported causal claims.
- Mention that the model uses synthetic training data.
- Do not use bullet points or headings.
"""

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-2.5-flash",
            ),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=800,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0
                ),
                system_instruction=(
                    "You are an analytics assistant. "
                    "Explain only the supplied evidence "
                    "using complete and simple sentences."
                ),
            ),
        )

        answer = response.text

        if not valid_explanation(answer):
            logger.warning(
                "Gemini returned an incomplete explanation"
            )
            return (
                rule_based_explanation(customer),
                "Rule-based fallback: incomplete response",
            )

        return answer.strip(), "Google Gemini AI"

    except Exception as error:
        logger.warning(
            "Gemini failed: %s",
            type(error).__name__,
        )
        return (
            rule_based_explanation(customer),
            "Rule-based fallback: Gemini unavailable",
        )
