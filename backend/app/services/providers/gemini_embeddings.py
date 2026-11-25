import os

from google import genai
from google.genai import types

from app.services.llm_exceptions import LLMConfigurationError, LLMProviderError
from app.services.passage_retrieval import EMBEDDING_DIMENSIONS


class GeminiEmbeddingProvider:
    model = "gemini-embedding-001"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is missing")
        self.client = genai.Client(api_key=api_key)

    def embed(self, content: str, *, is_query: bool) -> list[float]:
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=content,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBEDDING_DIMENSIONS,
                ),
            )
        except Exception as exc:
            raise LLMProviderError("Gemini embedding request failed") from exc

        if not response.embeddings or not response.embeddings[0].values:
            raise LLMProviderError("Gemini returned an empty embedding")
        return response.embeddings[0].values
