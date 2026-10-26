# AI Research Automation System — System Architecture

## 1. Project Overview

The AI Research Automation System is an AI-powered application designed to help researchers discover academic papers, extract important insights, identify potential research gaps, and generate research reports.

The system uses specialized AI agents coordinated through a workflow orchestrator. It combines Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), structured data storage, and semantic search.

The initial implementation will use a modular monolith architecture to keep development and deployment manageable while maintaining clear separation between components.

## 2. Project Objectives

The system aims to:

- Refine broad research topics into focused research questions.
- Discover relevant academic papers.
- Extract structured insights from research papers.
- Identify potential research gaps based on available evidence.
- Generate research reports with traceable citations.
- Allow human review before a report is approved.
- Recover from temporary failures without unnecessarily repeating completed work.

## 3. Technology Stack

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React | Research submission, progress display, and report review |
| Backend API | FastAPI | HTTP endpoints, input validation, and request handling |
| Programming language | Python | Application logic and agent implementation |
| Agent orchestration | AutoGen | Agent collaboration and task execution |
| LLM | External LLM API | Research reasoning, insight extraction, and report generation |
| Embeddings | Embedding model/API | Convert text into numerical vectors |
| Primary database | PostgreSQL | Structured records and persistent workflow state |
| Vector search | pgvector | Store embeddings and perform semantic similarity search |
| Version control | Git | Track source code and documentation changes |
| Repository hosting | GitHub | Store the project and maintain its development history |

Technology choices will be reviewed if implementation requirements or performance measurements justify changes.

## 4. High-Level Architecture

The system consists of the following logical layers:

1. Presentation Layer
2. API Layer
3. Workflow Orchestration Layer
4. Agent Processing Layer
5. Storage and Retrieval Layer
6. External AI Services

### 4.1 Presentation Layer

React provides the user interface.

Responsibilities:
- Submit research topics.
- Display research job status.
- Display discovered papers and extracted insights.
- Present generated reports.
- Allow users to approve reports or request revisions.

The frontend communicates with the backend through HTTP APIs.

### 4.2 API Layer

FastAPI exposes endpoints for interacting with the system.

Responsibilities:
- Accept research requests.
- Validate request data.
- Create research jobs.
- Return job identifiers.
- Provide job status and report retrieval endpoints.
- Handle authentication and authorization when implemented.

Long-running research jobs should execute independently of the initial HTTP request. The API can return a job identifier that the frontend uses to retrieve progress.

### 4.3 Workflow Orchestration Layer

The workflow coordinator manages the overall research process.

Responsibilities:
- Track workflow progress.
- Enforce task dependencies.
- Select the next eligible task.
- Schedule independent paper-processing tasks.
- Handle retry policies and task failures.
- Determine when a stage is complete.
- Resume eligible work after interruption.

A custom selector function will help determine which agent or task should execute next based on the workflow state.

The selector, coordinator, and agents have distinct responsibilities.

### 4.4 Agent Processing Layer

The system contains five specialized agents.

#### Agent 1: Topic Refinement Agent

Input:
- User's research topic.

Output:
- Refined research question.
- Search keywords.
- Search phrases.
- Research scope.

#### Agent 2: Paper Discovery Agent

Input:
- Refined research question and search terms.

Output:
- Relevant paper metadata.
- Source identifiers.
- Abstracts and document links when available.

The initial implementation may use the arXiv API as a paper discovery source.

#### Agent 3: Insight Extraction Agent

Input:
- A discovered paper and its available text.

Output:
- Research problem.
- Methodology.
- Key findings.
- Limitations.
- Future research directions.

Each paper's extraction task will have its own status and result record.

#### Agent 4: Research Gap Analysis Agent

Input:
- Completed insight records from discovered papers.

Output:
- Potential research gaps.
- Supporting evidence.
- Related papers.
- Uncertainties and limitations.

The agent must distinguish a potential gap in the reviewed literature from a claim that no research exists anywhere.

#### Agent 5: Report Compilation Agent

Input:
- Research topic.
- Extracted insights.
- Research gap analysis.
- Source references.

Output:
- Structured research report.
- Literature review.
- Methodology comparison.
- Key findings.
- Potential research gaps.
- References and limitations.

## 5. Workflow and Data Flow

The initial workflow follows this order:

1. The user submits a research topic through React.
2. FastAPI validates the request and creates a research job.
3. The workflow coordinator schedules the Topic Refinement Agent.
4. The Paper Discovery Agent searches for relevant papers.
5. The system saves discovered paper metadata.
6. The Insight Extraction Agent processes papers.
7. Independent paper-processing tasks may execute in parallel, subject to resource and API limits.
8. The coordinator waits until the required extraction tasks finish or reach an explicitly handled failure state.
9. The Research Gap Analysis Agent analyzes the available evidence.
10. The Report Compilation Agent generates a draft report.
11. The system saves the report and marks it as pending review.
12. The user reviews the report and approves it or requests revisions.

The system should not automatically treat an incomplete collection of insights as a complete research analysis.

If some papers remain unprocessed, the system must either recover them or explicitly record the limitation before proceeding according to the configured completion policy.

## 6. Sequential and Parallel Execution

The following stages depend on earlier outputs:

- Topic refinement precedes paper discovery.
- Paper discovery precedes extraction for each discovered paper.
- Required insight extraction precedes research gap analysis.
- Research gap analysis precedes report compilation.

Paper extraction can run in parallel because the papers are independent inputs.

The initial implementation will use controlled parallelism rather than starting an unlimited number of requests simultaneously.

The workflow coordinator will enforce dependencies and determine when each stage can advance.

## 7. Data Storage

### PostgreSQL

PostgreSQL will store:

- Research jobs.
- Paper metadata.
- Task statuses.
- Retry counts and error information.
- Extracted insights.
- Report metadata.
- Review and approval records.

### pgvector

The pgvector extension will support vector storage and semantic similarity search.

It will store:
- Document chunk embeddings.
- Chunk identifiers.
- References to source papers.
- Selected metadata needed for retrieval.

The original paper metadata and authoritative task statuses will remain in PostgreSQL.

The application will connect chunks and embeddings to their source papers using stable identifiers.

## 8. RAG Architecture

Retrieval-Augmented Generation allows the system to retrieve relevant paper passages before generating an answer.

The pipeline is:

1. Obtain available paper text.
2. Split text into manageable chunks.
3. Generate embeddings for the chunks.
4. Store embeddings and source references using pgvector.
5. Convert the user's query into an embedding.
6. Retrieve relevant chunks through semantic search.
7. Provide the retrieved context to the LLM.
8. Generate an answer grounded in the retrieved evidence.
9. Preserve source references for citation and verification.

RAG supports evidence retrieval but does not guarantee that every generated claim is correct. Citation validation and evidence review remain necessary.

## 9. Workflow Reliability

The system will use persistent task state and bounded retries.

Initial task statuses:

- PENDING
- RUNNING
- RETRY_PENDING
- COMPLETED
- FAILED

The system will:

- Save task statuses and completed outputs.
- Classify errors before deciding whether to retry.
- Apply bounded retries with backoff for suitable transient errors.
- Use timeouts to prevent tasks from remaining stuck indefinitely.
- Recover interrupted tasks using persistent state and an appropriate recovery policy.
- Use idempotent result persistence to reduce duplicate records.
- Preserve completed work when another paper fails.
- Record unrecoverable errors for diagnosis.

The system will not assume that every external operation executes exactly once.

## 10. Human-in-the-Loop Review

Generated reports will require review before final approval.

Initial report statuses:

- GENERATING
- PENDING_REVIEW
- APPROVED
- REVISION_REQUESTED
- FAILED

The reviewer can approve the report or request revisions.

The system will preserve the report's source references so that reviewers can verify important claims.

## 11. Initial Deployment Architecture

The first implementation will use a modular monolith.

The API, orchestration logic, agent modules, and application services will reside in one Python application, organized into separate modules.

PostgreSQL with pgvector will provide the initial storage and retrieval capabilities.

This approach reduces infrastructure complexity while allowing the application to be tested and maintained in logical units.

Separate worker processes or services can be considered later if execution volume, reliability requirements, or scaling needs justify them.

## 12. Security and Configuration

- Store API keys in environment variables.
- Keep `.env` files out of Git.
- Provide a `.env.example` file containing variable names and placeholder values only.
- Validate incoming API requests.
- Add authentication and authorization before supporting private user research data.
- Avoid logging secrets or sensitive document contents unnecessarily.
- Preserve the provenance of research documents and generated findings.

## 13. Initial Implementation Priorities

Implementation will proceed in stages:

1. Finalize the architecture and data-flow documentation.
2. Define task, paper, insight, and report data models.
3. Build a small FastAPI application.
4. Integrate an LLM and validate structured outputs.
5. Implement paper discovery.
6. Build document processing and semantic retrieval.
7. Implement agent orchestration.
8. Add task recovery and retry behavior.
9. Implement report compilation and human review.
10. Integrate the frontend and test the complete workflow.

The system will be developed incrementally, with connected mini-projects before the complete application.