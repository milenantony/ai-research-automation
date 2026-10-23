# AI Research Automation System

## 1. Project Overview

The AI Research Automation System aims to automate repetitive academic research tasks using Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and AI agents.

The system will help researchers discover relevant academic papers, extract important insights, compare research findings, identify potential research gaps, and generate structured research reports.

## 2. Problem Statement

Academic research often requires researchers to search for papers across multiple sources, read lengthy documents, compare methodologies and findings, and identify areas that need further investigation.

Performing these tasks manually can be time-consuming.

This project aims to streamline the process through an AI-assisted research workflow.

## 3. Proposed Technology Stack

- Programming Language: Python
- Backend Framework: FastAPI
- Frontend Framework: React
- Language Models: An LLM accessed through a provider API
- Research Sources: Academic research APIs such as arXiv and OpenAlex
- Relational Database: PostgreSQL
- Vector Search: To be selected between Qdrant and PostgreSQL with pgvector
- AI Workflow: Agent-based orchestration
- Version Control: Git and GitHub

Redis and Docker may be introduced later if the system's requirements justify them.

## 4. High-Level Architecture

1. The user enters a research topic through the React frontend.
2. FastAPI validates the request and passes it to the research orchestrator.
3. The orchestrator manages the research workflow and invokes the appropriate agents.
4. Research agents discover papers through academic research APIs.
5. The system retrieves available paper content and extracts text.
6. The documents are divided into chunks and converted into embeddings.
7. The vector-search component stores embeddings and supports semantic retrieval.
8. RAG retrieves relevant evidence for the research task.
9. The LLM analyzes the evidence and helps generate report sections.
10. The application validates the output and its supporting citations.
11. PostgreSQL stores structured application data, processing statuses, and report metadata.
12. FastAPI returns the result to the React frontend.

## 5. Main Components

### React Frontend
Collects research topics and report preferences and displays processing status and generated reports.

### FastAPI Backend
Provides API endpoints, validates requests, enforces authorization, and connects the frontend to application services.

### Research Orchestrator
Coordinates the workflow and manages task execution, agent selection, retries, and completion status.

### AI Agents
Perform tasks such as topic refinement, paper discovery, insight extraction, comparison, and research-gap analysis.

### Research APIs
Provide access to academic paper metadata and, where available, paper content.

### RAG Pipeline
Retrieves relevant research evidence and supplies it to the LLM as context.

### Vector Search
Stores or indexes embeddings and associated metadata to support semantic retrieval.

### LLM
Analyzes provided research evidence and generates summaries, comparisons, and report sections.

### PostgreSQL
Stores structured application records, processing statuses, report metadata, and other relational data.

## 6. Reliability and Evidence Validation

The system should handle API failures through timeouts, limited retries, and appropriate fallback mechanisms.

Generated claims should be checked against retrieved source material wherever possible. Unsupported claims should be revised or flagged for human review.

The system should treat retrieved documents as untrusted content and should not allow document instructions to override application security rules.

## 7. Initial Development Strategy

Development will proceed in stages:

1. Understand and document the complete architecture.
2. Learn the required technologies.
3. Build small, connected learning projects.
4. Implement the main system in separate modules.
5. Integrate and test the complete workflow.
6. Document design decisions and maintain meaningful Git commits.

The initial implementation will favor a modular monolith over microservices to reduce complexity.