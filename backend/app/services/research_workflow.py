
from app.services.llm_service import LLMService


class ResearchWorkflow:
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or LLMService()

    def generate_summary(
        self,
        topic: str,
        research_context: str,
    ) -> str:
        if not topic or not topic.strip():
            raise ValueError("Research topic cannot be empty")

        if not research_context or not research_context.strip():
            raise ValueError("Research context cannot be empty")

        prompt = f"""
You are an academic research assistant.

Research Topic:
{topic}

Research Material:
{research_context}

Instructions:
1. Analyze the supplied research material.
2. Generate a clear and structured academic summary.
3. Identify the key findings and important concepts.
4. Do not invent facts, statistics, or research findings.
5. If information is insufficient, explicitly mention the limitations.
6. Base your answer only on the supplied research material.

Provide a concise, well-organized research summary.
"""

        return self.llm_service.generate(prompt)
