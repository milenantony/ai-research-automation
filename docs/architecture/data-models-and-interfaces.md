# Data Models and Component Interfaces

## 1. Purpose

This document defines the main data entities and communication contracts for the AI Research Automation System.

The objective is to ensure that the agents, backend API, workflow coordinator, and storage components exchange predictable and consistent data.

## 2. Core Entities

### ResearchJob

Represents a research request.

Initial fields:
- id
- topic
- status
- created_at
- updated_at

### Paper

Represents a discovered academic paper.

Initial fields:
- id
- source
- source_id
- title
- authors
- abstract
- publication_year
- document_url

### AgentTask

Represents a unit of workflow execution.

Initial fields:
- id
- job_id
- paper_id, when applicable
- task_type
- status
- attempt_count
- last_error
- created_at
- updated_at

### PaperInsight

Stores structured information extracted from a paper.

Initial fields:
- id
- paper_id
- task_id
- research_problem
- methodology
- key_findings
- limitations
- future_research_directions
- evidence_references

### DocumentChunk

Represents a searchable section of a paper.

Initial fields:
- id
- paper_id
- chunk_index
- text
- embedding
- source_location

### ResearchReport

Represents a generated research report.

Initial fields:
- id
- job_id
- version
- status
- content
- created_at
- updated_at

## 3. Agent Contracts

### Topic Refinement Agent

Input:
- Original research topic.

Output:
- Refined research question.
- Search keywords.
- Search phrases.
- Research scope.

### Paper Discovery Agent

Input:
- Refined research question.
- Search keywords and phrases.

Output:
- A collection of paper records with source identifiers and metadata.

### Insight Extraction Agent

Input:
- Paper identifier.
- Paper metadata.
- Available paper text.

Output:
- Structured research problem.
- Methodology.
- Key findings.
- Limitations.
- Future research directions.
- Evidence references when available.

### Research Gap Analysis Agent

Input:
- Refined research question.
- Collection of extracted insights and supporting evidence.

Output:
- Potential research gaps.
- Supporting sources.
- Evidence limitations.
- Confidence or uncertainty information.

### Report Compilation Agent

Input:
- Research topic.
- Extracted insights.
- Research gap analysis.
- Source references.

Output:
- Draft report.
- Literature review.
- Methodology comparison.
- Key findings.
- Potential research gaps.
- References and limitations.

## 4. API Contracts

### Create Research Job

Method: POST

Endpoint: /research-jobs

Request:
- topic

Response:
- job_id
- status

### Get Research Job

Method: GET

Endpoint: /research-jobs/{job_id}

Response:
- job_id
- topic
- status
- progress information

### Get Discovered Papers

Method: GET

Endpoint: /research-jobs/{job_id}/papers

Response:
- List of discovered papers and their processing statuses.

### Get Research Report

Method: GET

Endpoint: /research-jobs/{job_id}/report

Response:
- Report metadata.
- Report content.
- Report status.
- Source references.

### Approve Report

Method: POST

Endpoint: /research-jobs/{job_id}/approve

Purpose:
- Record an authorized reviewer's approval of the report.

### Request Report Revision

Method: POST

Endpoint: /research-jobs/{job_id}/revision

Purpose:
- Record a revision request and initiate the appropriate revision workflow.

## 5. Data Ownership

PostgreSQL owns the authoritative records for research jobs, paper metadata, tasks, insights, reports, and review decisions.

pgvector supports semantic retrieval using document chunk embeddings and associated source identifiers.

Agent modules exchange validated data structures rather than relying exclusively on unstructured text.

## 6. Reliability Requirements

- Each research job has a stable identifier.
- Each task has a stable identifier.
- Completed task outputs are persisted.
- Retry attempts are bounded.
- Transient and permanent failures are handled differently.
- Result persistence is designed to prevent duplicate records.
- Interrupted tasks can be detected and recovered.
- Partial completion is reported explicitly.
- Generated claims preserve traceable source references.

## 7. Initial Implementation Scope

The initial implementation will prioritize:
1. Research job creation.
2. Paper discovery.
3. Structured insight extraction.
4. Persistent task and result storage.
5. Research gap analysis.
6. Report compilation.

Semantic retrieval, report review, and advanced recovery features will be integrated incrementally, with appropriate tests at each stage.