
import os

import requests

from app.config import BASE_DIR

# Importing config also loads environment variables.
_ = BASE_DIR


def explanation_features(customer):
    """Allow only engineered features into the AI prompt."""

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

        # Convert Pandas / Decimal values to plain text
        # before sending the structured prompt.
        if value is None:
            features[field] = "unknown"
        else:
            features[field] = str(value)

    return features


def rule_based_explanation(customer):
    """Provide a transparent explanation without an API."""

    status = customer.get("subscription_status")
    usage_status = customer.get("usage_data_status")
    risk = customer.get("risk_level")

    if status == "cancelled":
        return (
            "This customer has already cancelled the "
            "subscription. They are counted as churned, "
            "not as an active customer at risk."
        )

    if usage_status != "complete":
        return (
            "Usage history is incomplete, so the system "
            "cannot reliably assess usage decline. "
            "Review the missing usage records before "
            "assigning a behavioral churn-risk level."
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
            "in the current month"
        )

    if not reasons:
        return (
            "No configured risk indicators were triggered. "
            "The customer is classified as LOW risk under "
            "the current rules. This does not guarantee "
            "that the customer will remain subscribed."
        )

    return (
        f"The customer is classified as {risk} risk "
        f"because " + "; ".join(reasons) + ". "
        "This is an indicator-based assessment, "
        "not a statistically calibrated prediction."
    )


def ai_explanation(customer):
    """Use an LLM, with a safe local fallback."""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return (
            rule_based_explanation(customer),
            "Rule-based explanation",
        )

    features = explanation_features(customer)

    prompt = (
        "Explain this subscription customer's churn "
        "status or risk in 2 to 4 simple sentences.\n"
        "Use ONLY the provided engineered features.\n"
        "Do not invent facts, probabilities, causes, "
        "or customer personal details.\n"
        "Do not change the supplied risk label.\n"
        "A cancelled subscription is actual churn.\n"
        "Missing usage means insufficient evidence.\n"
        "The score is a heuristic, not a probability.\n\n"
        f"Engineered features:\n{features}"
    )

    payload = {
        "model": os.getenv(
            "OPENAI_MODEL", "gpt-4o-mini"
        ),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You explain analytics results clearly. "
                    "You must not invent unsupported facts."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 180,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )

        response.raise_for_status()

        answer = response.json()["choices"][0][
            "message"
        ]["content"]

        if not isinstance(answer, str):
            raise ValueError("AI returned invalid content")

        answer = answer.strip()

        if not answer or len(answer) > 1500:
            raise ValueError("AI response failed validation")

        # A local fallback is used for the most sensitive
        # classification states rather than asking the LLM
        # to reason about missing data or confirmed churn.
        if customer.get("risk_level") in (
            "CHURNED", "INSUFFICIENT DATA"
        ):
            return (
                rule_based_explanation(customer),
                "Rule-based explanation",
            )

        return answer, "AI-generated explanation"

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ):
        return (
            rule_based_explanation(customer),
            "Rule-based fallback (AI unavailable)",
        )
