
import os

from google import genai

from app.config import BASE_DIR


def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        print("Error: GEMINI_API_KEY is missing.")
        return

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash"
            ),
            contents=(
                "In one sentence, explain what "
                "customer churn means."
            ),
        )

        print("Gemini API connected successfully!")
        print()
        print("Gemini Response:")
        print(response.text)

    except Exception as error:
        print("Gemini API connection failed.")
        print(f"Error type: {type(error).__name__}")
        print(str(error))


if __name__ == "__main__":
    main()
