
import os

from google import genai


class GeminiProvider:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash"
        )

        self.client = genai.Client(api_key=api_key)

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return response.text
