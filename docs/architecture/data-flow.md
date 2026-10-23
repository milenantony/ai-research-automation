# Data Flow

## Main Workflow

User
→ React Frontend
→ FastAPI Backend
→ Research Orchestrator
→ Appropriate Research Agent
→ Academic Research APIs
→ Paper Metadata and Available Content
→ Text Extraction and Chunking
→ Embedding Generation
→ Vector Search Storage
→ Relevant Evidence Retrieval
→ LLM Analysis
→ Report Generation
→ Evidence and Citation Validation
→ PostgreSQL Persistence
→ FastAPI Response
→ React Frontend
→ User Views the Report

## Important Design Notes

- PostgreSQL stores structured application records; it does not generate reports.
- The LLM generates report content using the information supplied to it.
- RAG retrieves relevant evidence to support generation.
- The vector-search component enables semantic retrieval.
- The orchestrator manages the workflow and may invoke agents multiple times.
- Processing status should be saved so failed tasks can be retried without unnecessarily repeating completed work.
- Human review may be required for important or insufficiently supported conclusions.