
import os
import json
import logging

from google import genai
from google.genai import types

from app.config import BASE_DIR


logger = logging.getLogger(__name__)


def explanation_features(customer):
    """
    Select only SQL-engineered features.

    Personal information such as customer name
    and email must not be sent to Gemini.
    """

    allowed_fields = [
        "subscription_status",
        "plan_name",
        "payment_failures",
        "previous_month_hours",
        "current_month_hours",
        "current_month_sessions",
        "usage_decline_percent",
        "usage_data_status",
        "decline_points",
        "payment_points",
        "low_activity_points",
        "risk_score",
        "risk_level",
    ]

    features = {}

    for field in allowed_fields:
        value = customer.get(field)

        if value is None:
            features[field] = None
        else:
            features[field] = str(value)

    return features


def rule_based_explanation(customer):
    """
    Generate an explanation using fixed business rules.

    This is used when Gemini is unavailable.
    """

    status = customer.get("subscription_status")
    usage_status = customer.get("usage_data_status")
    risk = customer.get("risk_level")

    if status == "cancelled":
        return (
            "This customer has already cancelled "
            "their subscription and is classified "
            "as CHURNED."
        )

    if usage_status != "complete":
        return (
            "The customer's usage history is incomplete. "
            "There is insufficient information to "
            "reliably evaluate usage-based churn risk."
        )

    reasons = []

    decline = customer.get("usage_decline_percent")

    if decline is not None and float(decline) >= 60:
        reasons.append(
            f"usage decreased by {float(decline):.1f}%"
        )

    if int(customer.get("payment_failures", 0)) >= 1:
        reasons.append(
            "one or more subscription payments failed"
        )

    if int(customer.get("current_month_sessions", 0)) <= 2:
        reasons.append(
            "the customer had at most two sessions "
            "during the current month"
        )

    if not reasons:
        return (
            "No configured risk indicators were triggered. "
            "The customer is classified as LOW risk "
            "under the current business rules."
        )

    return (
        f"The customer is classified as {risk} risk "
        f"because {'; '.join(reasons)}. "
        "This classification is based on predefined "
        "SQL indicators, not a predicted probability."
    )


def ai_explanation(customer):
    """
    Generate an explanation using Google Gemini.

    Returns:
        explanation: Generated or fallback text
        source: Origin of the explanation
    """

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # Step 1: Check whether an API key is provided.
    if not api_key:
        return (
            rule_based_explanation(customer),
            "Rule-based explanation (Gemini key missing)",
        )

    # Step 2: Handle cancelled or incomplete records
    # deterministically.
    if customer.get("risk_level") in (
        "CHURNED",
        "INSUFFICIENT DATA",
    ):
        return (
            rule_based_explanation(customer),
            "Rule-based explanation",
        )

    # Step 3: Extract approved engineered features.
    features = explanation_features(customer)

    # Step 4: Prepare the Gemini prompt.
    prompt = f"""
Explain the following subscription customer's churn risk.

The customer's engineered features are:

{json.dumps(features, indent=2)}

Instructions:

1. Explain the customer's risk in 2 to 4 simple sentences.
2. Use only the engineered features provided above.
3. Explain the role of usage decline, payment failures,
   and customer engagement when relevant.
4. Do not invent personal information or missing values.
5. Do not invent churn probabilities.
6. Do not change the provided risk classification.
7. Do not claim that the indicators prove causation.
8. Clearly explain why the customer was assigned
   the existing risk level.

Return only the explanation.
"""

    # Step 5: Send the prompt to Gemini.
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash"
            ),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=300,
                system_instruction=(
                    "You are a customer analytics assistant. "
                    "Explain subscription churn indicators "
                    "clearly and accurately. "
                    "Use only the supplied engineered "
                    "customer features."
                ),
            ),
        )

        explanation = response.text

        # Step 6: Check for an empty or invalid response.
        if not isinstance(explanation, str):
            raise ValueError("Invalid Gemini response")

        explanation = explanation.strip()

        if not explanation or len(explanation) > 1500:
            raise ValueError(
                "Gemini returned an empty or oversized response"
            )

        return (
            explanation,
            "Google Gemini AI explanation",
        )

    except Exception as error:
        # Log the error without exposing the API key.
        logger.warning(
            "Gemini explanation failed: %s",
            type(error).__name__,
        )

        return (
            rule_based_explanation(customer),
            "Rule-based fallback (Gemini unavailable)",
        )
