# ADR-004: Modular Monolith Architecture

## Status

Proposed

## Context

The AI Research Automation System consists of five specialized agents, a workflow coordinator, a FastAPI backend, database services, and external AI APIs.

The system must support sequential workflow stages, parallel processing of independent research papers, persistent task state, error recovery, and human review.

A microservices architecture could separate these components into independently deployed services. However, it would also introduce additional deployment, communication, monitoring, and operational complexity.

The project is being developed incrementally, with a focus on learning and completing an initial working system within approximately six weeks.

## Decision Drivers

The initial architecture should prioritize:

- Clear separation of responsibilities.
- Straightforward development and testing.
- Manageable deployment complexity.
- Reliable workflow execution.
- Maintainability.
- The ability to introduce independent workers or services later if required.

## Options Considered

### Option 1: Modular Monolith

Implement the application as one deployable system with separate internal modules for the API, agents, orchestration, research processing, storage, and retrieval.

Advantages:
- Easier initial development and deployment.
- Lower infrastructure overhead.
- Straightforward local debugging.
- Modules can be tested independently.
- Supports incremental development.

Limitations:
- Independent components do not automatically scale separately.
- Poor module boundaries can create tight coupling.
- Long-running tasks still require appropriate execution and recovery mechanisms.

### Option 2: Microservices

Deploy the API, orchestration components, and selected workers as separate services.

Advantages:
- Independent deployment and scaling.
- Stronger runtime isolation between selected components.
- Individual services can evolve independently.

Limitations:
- Requires inter-service communication.
- Introduces distributed failure scenarios.
- Increases deployment and monitoring complexity.
- Requires additional work for tracing and operational management.

## Decision

Use a modular monolith for the initial implementation.

Organize the Python application into separate modules with clearly defined responsibilities and interfaces.

Allow paper-processing tasks to run concurrently when appropriate, without requiring every agent to be deployed as an independent service.

## Consequences

The project can begin with a manageable development environment and evolve incrementally.

Module boundaries must be maintained so that components can be tested independently.

The application must still implement persistent task state, appropriate retries, timeouts, and recovery. A modular monolith does not automatically provide these reliability properties.

## Review Conditions

Reconsider the architecture if:

- Specific workers require independent scaling.
- Workloads create unacceptable resource contention.
- Strong runtime isolation becomes necessary.
- Deployment requirements demand independent releases.
- Measurements demonstrate that the current architecture cannot meet operational requirements.

Any future transition should be justified by actual requirements and performance evidence.