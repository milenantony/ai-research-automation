import os
from google import genai
from app.services.llm_exceptions import (
    LLMConfigurationError,
    LLMProviderError,
)
class GeminiProvider:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is missing"
            )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash"
        )

        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as exc:
            raise LLMConfigurationError(
                "Failed to initialize Gemini client"
            ) from exc

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            if not response.text or not response.text.strip():
                raise LLMProviderError(
                    "Gemini returned an empty response"
                )

            return response.text

        except LLMProviderError:
            raise

        except Exception as exc:
            raise LLMProviderError(
                "Gemini API request failed"
            ) from exc
