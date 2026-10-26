# ADR-003: Database and Vector Storage

## Status
Proposed

## Context
The AI Research Automation System needs to store research jobs, paper metadata, extracted insights, workflow statuses, and document embeddings.

The system also needs semantic retrieval to support Retrieval-Augmented Generation (RAG).

## Options Considered

### Option 1: PostgreSQL with pgvector
Use PostgreSQL for structured records and pgvector for storing embeddings and performing vector similarity searches.

Advantages:
- One primary database to configure and maintain.
- Supports relational queries and vector retrieval.
- Simplifies development and deployment.

Limitations:
- Retrieval performance depends on workload, indexing, and configuration.
- Very large workloads may require further evaluation.

### Option 2: PostgreSQL and a Separate Vector Database
Use PostgreSQL for structured records and a dedicated vector database for semantic retrieval.

Advantages:
- Separates structured data management from vector retrieval.
- May offer operational or performance benefits for particular workloads.

Limitations:
- Introduces another service to configure, monitor, and maintain.
- Requires additional integration between storage systems.

## Decision
Propose PostgreSQL with pgvector for the initial implementation.

## Rationale
The initial project prioritizes simplicity, maintainability, and learning. PostgreSQL with pgvector can support structured storage and semantic retrieval without requiring a separate database service.

## Consequences
The architecture must keep document identifiers and metadata consistent between records and embeddings.

The decision should be reviewed if retrieval performance, dataset size, or operational requirements justify a dedicated vector database.