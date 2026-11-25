# ADR-005 Research workflow orchestration

## Status

Accepted for PaperX through the end-to-end research workflow.

## Decision

Use explicit Python service calls inside the FastAPI modular monolith. The Day 29 endpoint ingests and ranks passages from the selected papers, commits reusable passage data, then extracts structured insights and verifies their citations. An extraction retry can reuse embeddings for unchanged abstracts. The response includes the retrieved paper IDs and each insight's verified quote and source metadata.

PostgreSQL already holds research jobs and reviewed gaps. Day 30 can pass the typed insight results into gap analysis and the existing review flow. Day 29 returns insights in the API response, with persistence decisions deferred to that integration.

Earlier architecture notes proposed AutoGen. Microsoft has since archived AutoGen, so PaperX will keep it as a historical reference. LangGraph remains a candidate if branching, durable execution, or interrupt and resume requirements exceed what explicit calls and existing database state can handle.

- [AutoGen project status](https://microsoft.github.io/autogen/stable/index.html)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)

## Try Insight Extraction

After applying Alembic, provision a pgvector-enabled database with `backend/sql/enable_passage_retrieval.sql` and configure `GEMINI_API_KEY`. Create a job, link papers through discovery, and send `POST /research-jobs/{job_id}/papers:extract-insights` with `paper_ids` and an optional `limit` (default 5). The job topic is the retrieval query. An empty retrieval returns empty arrays. A database without the optional passage table returns HTTP 503 for this endpoint. Existing research endpoints continue to work there.
