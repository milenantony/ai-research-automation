from agent_framework import Agent
from agent_framework.gemini import GeminiChatClient

from app.services.llm_exceptions import LLMProviderError
from app.services.providers.gemini import GeminiProvider


class PaperDiscoveryAgent:
    def __init__(self):
        provider = GeminiProvider()
        client = GeminiChatClient(client=provider.client, model=provider.model)
        self.agent = Agent(
            client=client,
            name="PaperDiscoveryAgent",
            instructions=(
                "Turn the user's research topic into one concise academic search "
                "query suitable for both arXiv and Semantic Scholar. Preserve "
                "the topic's meaning, named entities, and explicit constraints. "
                "If the topic already works as a search query, return it as given. "
                "Return only the query on a single line, in plain text."
            ),
        )

    async def build_search_query(self, topic: str) -> str:
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Research topic cannot be empty.")

        try:
            response = await self.agent.run(topic.strip())
        except Exception as exc:
            raise LLMProviderError("Paper discovery query generation failed.") from exc

        query = (response.text or "").strip()
        if not query or len(query.splitlines()) != 1:
            raise LLMProviderError("Paper discovery expected a single-line query.")

        return query