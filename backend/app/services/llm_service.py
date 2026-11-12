
import os

from app.services.providers.gemini import GeminiProvider


class LLMService:
    def __init__(self):
        provider_name = os.getenv(
            "LLM_PROVIDER",
            "gemini"
        ).lower()

        if provider_name == "gemini":
            self.provider = GeminiProvider()
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_name}"
            )

    def generate(self, prompt: str) -> str:
        return self.provider.generate_response(prompt)
