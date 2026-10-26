# ADR-003: Database and Vector Storage

## Status

Proposed

## Context

The AI Research Automation System must manage structured application data while supporting semantic retrieval over academic research papers.

Structured data includes research jobs, paper metadata, workflow task statuses, extracted insights, and generated report metadata.

Semantic retrieval requires representing document chunks as numerical embeddings and finding passages relevant to a user's query.

The architecture must support both requirements without introducing unnecessary infrastructure during the initial development phase.

## Options Considered

### Option 1: PostgreSQL with pgvector

Use PostgreSQL for structured records and pgvector for storing embeddings and performing vector similarity searches.

Advantages:
- One primary database service.
- Supports relational queries and vector retrieval.
- Simplifies development and deployment.
- Allows source metadata and vector references to be managed within the same database environment.

Limitations:
- Performance depends on the dataset, indexing, query patterns, and configuration.
- Larger or specialized workloads may require further evaluation.

### Option 2: PostgreSQL with a Separate Vector Database

Use PostgreSQL for structured records and a dedicated vector database for semantic retrieval.

Advantages:
- Separates structured data management from vector retrieval.
- May provide operational or performance advantages for particular workloads.
- Allows retrieval infrastructure to scale independently when required.

Limitations:
- Introduces an additional service.
- Increases integration and operational complexity.
- Requires careful management of source identifiers and metadata consistency.

## Decision

Propose PostgreSQL with pgvector for the initial implementation.

Use PostgreSQL for authoritative structured records and workflow state.

Use pgvector for storing document embeddings and supporting semantic similarity search.

## Rationale

The initial project prioritizes simplicity, maintainability, and learning.

PostgreSQL with pgvector supports the required structured storage and retrieval capabilities without requiring a separate vector database service.

This decision allows the project to validate its research workflow and retrieval requirements before introducing additional infrastructure.

## Data Ownership

PostgreSQL will own the authoritative records for:

- Research jobs.
- Paper metadata.
- Task statuses and retry information.
- Extracted insights.
- Report metadata.
- Review and approval records.

Vector records will contain embeddings, chunk identifiers, source references, and selected retrieval metadata.

Stable identifiers will connect retrieved passages to their original papers.

## Consequences

The initial deployment requires one primary database service with pgvector enabled.

Retrieval quality and performance must be evaluated using representative research questions and document collections.

The architecture should avoid tightly coupling agent logic to a particular vector-storage implementation.

## Review Conditions

Reevaluate the decision if:

- Retrieval latency becomes unacceptable.
- Dataset size or query volume changes significantly.
- Indexing and query optimization are insufficient.
- Independent vector infrastructure provides a measurable benefit.
- Operational requirements justify the added complexity.