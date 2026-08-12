# Hatcommways — System Architecture and Service Boundaries

## 1. Purpose

This document defines the high-level system architecture for Hatcommways.

It establishes clear boundaries between:

- frontend
- application backend
- deterministic domain services
- event infrastructure
- Strands agent runtime
- memory
- data storage
- maps
- notifications
- external integrations
- optional Amazon Bedrock AgentCore infrastructure

The goal is to prevent agent reasoning, business truth, permissions, storage, and UI responsibilities from becoming mixed together.

Core principle:

> Agents reason.
> Deterministic services maintain truth.
> Events connect the system.
> Humans retain authority over commitments.

---

# 2. Architecture Goals

Hatcommways architecture must support:

- approximately 24 specialized reasoning agents
- event-driven execution
- parallel task and agent execution
- dynamic timelines
- project revisions
- task/dependency graphs
- actor/responsibility graphs
- human approval
- organizations and communities
- maps
- privacy-sensitive data
- project memory
- historical blueprints
- long-running projects
- failure recovery
- observability
- future scale

The architecture must not depend on a single synchronous request-response chain.

---

# 3. High-Level Architecture

Conceptually:

User
↓
Hatcommways Web / PWA
↓
Application API
↓
Domain / Execution Layer
↓
Event Infrastructure
↙                ↓                 ↘
Agent Runtime   Background Workers   Projection Services
(Strands)                            Maps / Read Models
↓
Model / Tools

Shared infrastructure:

- PostgreSQL
- cache
- object storage
- event/audit history
- notifications
- search
- observability

Optional production agent infrastructure:

Amazon Bedrock AgentCore

---

# 4. Major Architectural Layers

Initial layers:

1. Client Layer
2. Application API Layer
3. Identity and Authorization Layer
4. Domain Services
5. Execution Engine
6. Event Infrastructure
7. Agent Orchestration Layer
8. Strands Agent Runtime
9. Background Workers
10. Projection / Read Model Layer
11. Memory Layer
12. Integration Layer
13. Persistence Layer
14. Observability and Audit Layer

These boundaries are logical.

They do not necessarily mean fourteen separately deployed microservices.

---

# 5. Start as a Modular System

Hatcommways should not begin as dozens of independent microservices.

The product is already conceptually complex.

Initial architecture should favor:

> Strong internal boundaries before distributed-service boundaries.

For example:

- one main application backend
- one agent runtime
- worker processes
- PostgreSQL
- queue/event infrastructure
- object storage

Modules should still have explicit ownership.

Later, high-load or security-sensitive boundaries may become independent services.

---

# 6. Client Layer

Initial client:

> Mobile-first responsive web application / PWA

Primary responsibilities:

- authentication UX
- project creation
- natural-language goal entry
- plan review
- task/timeline visualization
- actor-role browsing
- responsibility acceptance
- project discovery
- maps
- events
- decision inbox
- project execution updates
- organization/community views

The frontend must not contain authoritative permission rules.

Backend determines what data/actions are allowed.

---

# 7. Client Views

Important product surfaces include:

## Creator / Project Owner

- project creation
- AI plan review
- task graph
- timeline
- actor structure
- open responsibilities
- blocker status
- decision inbox
- support state
- maps
- outcome

## Participant

- nearby projects
- suitable responsibilities
- active responsibilities
- events
- project updates
- decisions
- completed contributions

## Organization

- projects
- representatives
- commitments
- meetings/events
- responsibilities
- private impact history

## Public Visitor

- public projects
- discovery map
- public Action Map
- approved support/organization maps
- public events
- open opportunities
- outcomes

---

# 8. Application API Layer

The Application API is the primary trusted boundary for clients.

Responsibilities:

- validate client requests
- authenticate identities
- enforce permissions
- call domain services
- persist authorized actions
- expose role-specific projections
- create events
- return current system state

The API must never allow clients to write authoritative internal state directly.

Example:

Wrong:

PATCH /task
{
  "execution_ready": true
}

Correct:

User performs an allowed action.

Domain service recalculates readiness.

---

# 9. API Does Not Directly Depend on LLM Responses

The normal API architecture should not be:

Frontend
→ API
→ LLM
→ database mutation

Instead:

Frontend
→ API
→ domain command
→ persisted state/event

and when reasoning is required:

event
→ agent runtime
→ typed proposal
→ validation
→ state transition

This creates safer and more auditable execution.

---

# 10. Identity Service

Identity responsibilities include:

- participant accounts
- organization accounts
- organization representatives
- group/community membership
- authentication
- session/token handling
- account state

Identity should remain deterministic.

AI agents do not decide user identity.

---

# 11. Authorization / Policy Service

Authorization evaluates:

- who is acting
- on whose behalf
- requested action
- resource
- canonical role
- project relationship
- organization authority
- visibility
- current state

Conceptual result:

ALLOW
DENY
REQUIRE_APPROVAL

All important APIs and agent tool calls must pass through authorization.

Agents do not define permission truth.

---

# 12. Project Service

Owns authoritative Project state.

Responsibilities:

- project lifecycle
- goal relationship
- project visibility
- project owner/admin relationships
- plan version references
- current project state
- scope revisions
- completion/cancellation

It emits domain events when state changes.

---

# 13. Goal Service

Owns:

- original goal
- goal revisions
- creator-provided context
- location context
- timeframe
- funding mode
- planning assumptions approved as state

AI may interpret goals.

The service stores the authoritative structured representation.

---

# 14. Task Graph Service

Owns authoritative task graph state.

Responsibilities:

- tasks
- parent/child relationships
- task state
- task versions
- progress
- completion
- task graph revision

It should expose graph queries such as:

- downstream tasks
- upstream tasks
- current branch
- affected region

---

# 15. Dependency Service

Owns dependency relationships.

Responsibilities:

- dependency persistence
- dependency validation
- dependency satisfaction
- affected task readiness
- graph traversal

Dependency satisfaction should usually be deterministic.

Agent may propose dependencies.

Service decides authoritative graph state.

---

# 16. Responsibility Service

Owns:

- responsibility records
- open responsibility state
- offers
- requests
- acceptance
- withdrawal
- transfer
- fulfillment
- vacancy
- responsibility lineage

Human commitments are recorded here.

AI agents cannot directly fabricate accepted responsibility.

---

# 17. Actor / Role Service

Owns:

- canonical actor-role definitions
- project role requirements
- role cardinality
- specializations
- theme mappings
- actor capacity references

AI may propose:

- required roles
- capacities
- specializations

Service stores validated structure.

---

# 18. Community and Group Service

Owns:

- Temporary Groups
- Permanent Communities
- membership
- project attachment
- community roles
- group lifecycle
- group-to-community conversion workflow

It must keep:

group membership

separate from:

project authorization

---

# 19. Organization Service

Owns:

- organization identity
- organization type
- representatives
- representative authority
- project relationships
- support relationships
- organization responsibilities
- attribution preferences

Organization commitment must be authorized.

---

# 20. Event / Scheduling Service

This service owns product Events and Meetings.

Responsibilities:

- scheduled event records
- proposed schedule
- confirmed schedule
- location
- participant relationship
- event state
- prerequisites
- event readiness
- rescheduling

Scheduling Agent may propose times.

The service stores authoritative approved schedule.

---

# 21. Support State Service

Owns project-level support/funding execution state.

Responsibilities:

- funding mode
- funding target
- reported contribution
- project-confirmed contribution
- support state
- task support prerequisites
- visibility rules

It does not process money initially.

---

# 22. Sensitive Payment Instruction Service

Payment instructions should have a stricter data boundary.

Examples:

- UPI/payment address
- external payment link
- payment contact instructions

This service/module should enforce:

- field-level encryption where appropriate
- narrow access control
- audit
- exclusion from public projections
- exclusion from general agent context

Agents should almost never require access to this data.

---

# 23. Execution Engine

The Execution Engine connects:

- task readiness
- dependencies
- responsibilities
- actor availability
- event conditions
- project conditions
- support conditions

It determines deterministic execution state.

Conceptually:

Task logical readiness
+
actor readiness
+
required conditions
=
execution readiness

This is one of the most important non-agent parts of Hatcommways.

---

# 24. Execution Engine Responsibilities

The engine may calculate:

- logical task readiness
- responsibility sufficiency
- actor capacity sufficiency
- execution readiness
- blocked/unblocked transitions
- newly ready downstream work
- basic timeline constraints

AI may reason about ambiguous planning choices.

The engine decides current persisted execution truth.

---

# 25. Timeline Service

Timeline Service owns authoritative timeline versions.

It consumes:

- task graph
- dependency graph
- duration estimates
- actor capacity
- events
- blockers
- project conditions

It persists:

- timeline versions
- expected task windows
- expected completion
- revision reason
- source plan/state version

Agent reasoning may propose timeline changes.

Timeline Service validates and persists them.

---

# 26. Replanning Boundary

Replanning is divided between:

## Agent Reasoning

Replanning Agent determines:

- alternatives
- affected branch
- proposed sequencing
- possible actor changes
- expected implications

## Deterministic Application

Validates:

- current state version
- permissions
- graph validity
- accepted responsibilities
- immutable history
- human approval requirements

Then persists a new plan version.

---

# 27. Event Infrastructure

Hatcommways should use an asynchronous event layer.

Domain state changes emit events.

Example:

responsibility.accepted

Consumers may include:

- execution readiness worker
- timeline worker
- Action Map projection
- notification service
- agent orchestrator
- memory pipeline

This prevents tight coupling.

---

# 28. Event Infrastructure Requirements

The event layer should support:

- asynchronous consumption
- multiple consumers
- retry
- dead-letter handling
- correlation ids
- causation ids
- idempotency
- event metadata
- durable delivery where required

The exact AWS service will be selected in the tech-stack document.

---

# 29. Event Store vs Event Bus

These are conceptually separate.

## Event Bus

Moves events to consumers.

## Event / Audit History

Stores durable history.

We do not necessarily need full event sourcing.

Current transactional database remains authoritative.

But consequential domain events should remain durable for:

- audit
- debugging
- memory
- replay of projections

---

# 30. Agent Orchestrator

Hatcommways requires a governed agent orchestration layer.

This layer determines:

- which events need agent reasoning
- which agent should activate
- whether agents can run concurrently
- required input
- relevant memory
- version checks
- retries
- no-progress protection

The orchestrator is infrastructure.

It is not one of the 24 reasoning agents.

## Trigger Router

The Trigger Router maps a domain event and current project state to eligible deterministic reactions and reasoning work. It filters irrelevant triggers before model execution.

## Affected Subgraph Resolver

The Affected Subgraph Resolver deterministically calculates the smallest safe execution region influenced by the source event.

It considers:

- changed tasks, dependencies, responsibilities, actors, events, and project conditions
- upstream constraints
- downstream impact
- actor capacity and contention
- reasons the region must expand
- whether the change has project-wide consequences

Its output scopes context construction, bounded graph execution, selective invalidation, and timeline recalculation. It preserves unaffected branches.

Core principle:

> Hatcommways replans affected execution regions rather than blindly regenerating the entire project.

---

# 31. Strands Agents SDK

Strands Agents SDK is the primary agent framework for Hatcommways.

It should be used from the beginning rather than added as a thin hackathon integration later.

Strands provides the foundation for:

- specialized agents
- tools
- structured agent interactions
- workflows
- graphs
- multi-agent patterns
- model access
- observability integration

Hatcommways-specific execution rules remain outside Strands.

---

# 32. Strands Agent Runtime

Initial recommendation:

> Python-based Strands agent runtime

Responsibilities:

- instantiate agent definitions
- execute reasoning jobs
- call authorized tools
- produce structured outputs
- integrate agent memory retrieval
- expose run lifecycle
- emit agent runtime events

The agent runtime should not own core transactional business state.

For multi-agent reasoning, the runtime executes bounded Strands Graph runs selected or constructed for one reasoning objective. It does not host one permanent project-lifetime graph.

Each bounded graph contains only relevant specialized agents, explicit graph dependencies, permitted parallel branches, bounded fan-out/fan-in, and deterministic completion conditions.

---

# 33. Agent Registry

Each reasoning agent should be registered with metadata.

Example:

agent_id:
parallelization

version:
1

triggers:
- responsibility.accepted
- actor.capacity_changed
- task.completed

reads:
- affected task graph
- dependency graph
- actor capacity
- timeline

writes:
- ParallelizationProposal

tools:
- graph query tool
- execution pattern retrieval

permissions:
scoped

This registry should be machine-readable eventually.

---

# 34. Agent Tool Boundary

Agents should not receive unrestricted database access.

Instead they use two separate classes of governed tools.

## Internal Hatcommways Tools

Examples:

- get_project_context
- get_affected_tasks
- get_dependency_region
- get_actor_capacity
- get_open_responsibilities
- retrieve_similar_blueprints
- propose_replan
- propose_schedule

These tools call Hatcommways domain services through governed internal interfaces. They enforce:

- authorization
- project scope
- field filtering
- versioning
- audit

Internal tools do not require AgentCore Gateway merely because they are agent tools.

## External Tools

Examples:

- get_calendar_availability
- create_approved_calendar_event
- send_approved_email
- request_external_meeting
- call_partner_api

These tools interact with third-party systems and are exposed through AgentCore Identity and AgentCore Gateway where the integration is managed through AgentCore.

Conceptually:

Strands Agent
→ Hatcommways Agent Permission Check
→ Hatcommways User / Organization Authorization
→ AgentCore Identity
→ AgentCore Gateway
→ External Tool / API

Core principle:

> Hatcommways decides whether an external action is allowed.
> AgentCore provides the governed identity and gateway through which that action is executed.

Agents must not receive unrestricted access to backend services or external systems, and must not receive raw external credentials in prompts, memory, source code, or normal tool arguments.

---

# 35. Agent Output Boundary

Agent results should use structured contracts.

Example:

ReplanningProposal

{
  source_plan_version,
  trigger,
  affected_task_ids,
  proposed_dependency_changes,
  proposed_timing_changes,
  proposed_actor_requirements,
  explanation,
  confidence
}

The application must validate before state mutation.

## Typed Proposals

Every consequential reasoning result crosses the runtime boundary as a schema-defined proposal containing source state versions, affected objects, proposed changes, reason codes, evidence and memory references, confidence, and agent provenance.

## Proposal Merger / Conflict Resolver

Concurrent graph nodes may produce several proposals. The Proposal Merger / Conflict Resolver:

- merges compatible changes
- preserves contributing-agent provenance
- detects conflicting writes
- rejects ambiguous combinations
- routes repair, rerun, or human review when appropriate

Merged proposals remain untrusted until validation.

## Proposal Validation Pipeline

The deterministic validation boundary includes:

- schema validation
- object/reference validation
- state-version validation
- domain-invariant validation
- permission validation
- conflict/merge validation

Human approval is added where the proposal is consequential. Only an authorized domain service may perform the authoritative transaction.

---

# 36. Agent Concurrency

Hatcommways should allow independent agents to run in parallel.

Example:

responsibility.accepted

may activate:

- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

These need not form a fixed chain.

The orchestrator determines actual dependency relationships.

---

# 37. Stale Result Protection

Every agent run should reference relevant state versions.

Possible:

- project_version
- plan_version
- task_graph_version
- actor_graph_version
- timeline_version

Before applying result:

current version is compared.

If materially stale:

- reject
- rerun
- merge only where explicitly safe

---

# 38. Background Worker Layer

Not all asynchronous work belongs to an agent.

Workers should handle deterministic/background operations such as:

- notifications
- map projection rebuild
- event fan-out
- image/file processing
- search indexing
- aggregation
- cleanup
- scheduled reminders
- timeline recalculation
- cache updates

This keeps LLM use intentional.

---

# 39. Notification Service

Notification Service converts domain changes into user-facing communication.

Channels may later include:

- in-app
- email
- push
- organization messaging

Notification Service receives events such as:

- responsibility offered
- task ready
- event rescheduled
- decision required
- blocker created

Agents may draft text when useful.

Delivery remains deterministic.

---

# 40. Decision / Approval Service

Hatcommways should have a dedicated Decision Inbox abstraction.

Owns:

- approval request
- affected object
- proposed action
- originating agent/workflow
- state version
- deadline/expiration
- approval result

Examples:

- approve plan
- accept organization support
- approve replanning
- publish demographic map
- confirm event schedule

This gives agents a safe human-in-the-loop boundary.

---

# 41. Map Projection Service

Maps should not query every operational table live.

A map projection layer can maintain privacy-safe derived views.

Initial projections:

- Action Map
- Money / Support Map
- Sponsor / Organization Map
- optional analytics maps

The projection pipeline applies:

- visibility
- location precision
- aggregation
- privacy thresholds

---

# 42. Geospatial Service

Geospatial responsibilities include:

- project search by region
- project pin positioning
- broad location aggregation
- participant/support aggregation
- map clustering
- radius/geographic queries

Exact technology will be selected later.

PostgreSQL/PostGIS is one possible direction.

---

# 43. Search Service

Search may support:

- public project search
- community discovery
- organization lookup
- open responsibilities
- historical blueprint retrieval

Initially, relational and indexed search may be sufficient.

Do not add complex search infrastructure before justified.

---

# 44. Memory Layer

Memory architecture remains separate from transactional truth.

Memory categories:

- project memory
- participant memory
- organization memory
- community memory
- relationship memory
- execution pattern memory
- failure/revision memory
- blueprint memory
- temporary agent working memory

Memory is a first-class execution boundary, not a replacement for transactional state.

## Memory Retriever

The Memory Retriever supplies scoped project episodic, decision, execution-pattern, failure/revision, outcome, and blueprint memory to the Context Builder.

Reusable memories include provenance, confidence, source scope, context signature, structural and scale metadata, and applicability. Current authoritative state is loaded first and always wins.

## Memory Writer

After a validated outcome, failure, revision, or decision, the Memory Writer creates structured durable memory with source references and state versions.

It does not persist raw chain-of-thought or every agent message. Raw event/audit history remains separate and append-oriented.

---

# 45. Transactional Memory Storage

Structured current/historical memory should initially live close to transactional data where practical.

Examples:

- plan revisions
- decisions
- blocker history
- responsibility history
- project summaries
- structured lessons

PostgreSQL can handle much of this initially.

---

# 46. Semantic Retrieval

Semantic retrieval should be added only where useful.

Good uses:

- similar completed projects
- project blueprint retrieval
- lessons
- historical narrative search

Bad uses:

- who owns Task 4?
- is responsibility accepted?
- what is current funding state?
- is dependency satisfied?

Exact facts should use structured retrieval.

---

# 47. Model Provider Boundary

Strands should abstract model usage from product domain logic.

Hatcommways should not scatter direct model-provider calls across business services.

Agent definitions select/configure appropriate models.

Application services communicate with agent runtime through contracts.

This makes model/provider changes safer.

---

# 48. Amazon Bedrock

Amazon Bedrock is a natural model/runtime ecosystem for Strands on AWS.

Possible uses:

- foundation model access
- embeddings where later needed
- agent-related AWS integration

Exact models should be chosen in tech-stack planning based on:

- reasoning quality
- cost
- latency
- context size

Do not hard-code product architecture around one model.

---

# 49. Amazon Bedrock AgentCore

AgentCore is optional but strongly relevant to Hatcommways production architecture.

Potential components:

- AgentCore Runtime
- AgentCore Memory
- AgentCore Gateway
- AgentCore Identity
- AgentCore Observability

Use only where they strengthen a real product requirement.

Do not adopt every component solely for hackathon presentation.

---

# 50. AgentCore Runtime Boundary

Potential use:

Host/deploy the Strands agent runtime.

AgentCore Runtime would manage the operational environment for agent execution.

It should not replace:

- Hatcommways Project Service
- transactional state
- domain event history
- responsibility truth

---

# 51. AgentCore Memory Boundary

Potential use:

Support agent-oriented memory capabilities.

It may complement:

- long-term contextual agent memory
- execution-pattern retrieval

It must not replace:

- authoritative PostgreSQL project state
- responsibility history
- permissions
- task/dependency truth

Core rule:

> AgentCore Memory may enrich reasoning.
> Hatcommways data stores remain execution truth.

---

# 52. AgentCore Gateway Boundary

AgentCore Gateway is the controlled execution boundary for selected external tools.

Examples:

- email
- calendar
- organization APIs
- external scheduling tools
- future partner integrations

Conceptually:

Agent
→ approved capability
→ Gateway
→ external system

Gateway helps prevent agents from directly handling raw integration credentials. It does not replace Hatcommways' internal tool router. Internal domain tools remain inside Hatcommways.

This naturally fits Hatcommways' tool-governance model.

---

# 53. AgentCore Identity Boundary

AgentCore Identity manages governed external access for agents. It may support:

- agent/workload identity
- delegated user access
- delegated organization access
- third-party credentials
- access tokens
- scoped authorization to external systems

Hatcommways domain authorization remains authoritative for project-level permission. Before AgentCore Identity is used, Hatcommways determines whether the project permits the action, whether the user or organization authorized it, whether the agent has the required tool permission, and whether human approval is required.

External authorization requires:

Hatcommways Authorization
+
Human / Organization Delegation
+
Agent Tool Permission
+
AgentCore Identity
+
AgentCore Gateway

No single layer independently grants complete authority.

---

# 54. AgentCore Observability Boundary

Hatcommways uses AgentCore Observability for agent-infrastructure tracing. It complements but does not replace Hatcommways product audit.

AgentCore Observability provides visibility into:

- Strands agent runs
- model calls
- tool calls
- Gateway calls
- latency
- retries
- failures
- execution paths

Hatcommways Audit answers who accepted responsibility, who approved a plan, what organization committed, and what timeline version became authoritative.

AgentCore Observability answers which agent ran, which tools it invoked, where latency occurred, which external call failed, and what execution path occurred.

Core principle:

> Audit explains authority and product state.
> Observability explains runtime execution.

A common correlation identifier should connect:

Domain Event
→ Orchestrator Run
→ Strands Agent Run
→ Model Invocation
→ Tool Invocation
→ AgentCore Gateway Call
→ External System Result
→ Resulting Domain Event

Trace attributes must not contain sensitive values unnecessarily. Prefer resource ids, project ids, tool names, safe reason codes, and correlation ids.

Product-level audit data should still remain in Hatcommways.

---

# 55. Persistence Layer

Primary persistent data categories:

## Transactional

- users
- projects
- tasks
- dependencies
- responsibilities
- actors
- groups
- communities
- organizations
- events
- support state
- permissions

## Historical

- plan versions
- timeline versions
- domain events
- decisions
- blockers
- agent runs
- audit

## Files

- project images
- evidence
- organization documents
- attachments

## Derived

- map projections
- search indexes
- cached summaries

---

# 56. PostgreSQL as Primary System of Record

Initial recommendation:

> PostgreSQL as primary transactional system of record.

Reasons:

Hatcommways contains strongly relational data:

- projects
- tasks
- dependencies
- responsibilities
- actors
- groups
- organizations
- permissions
- plan versions

It also needs transactions and consistency.

The final AWS-hosted PostgreSQL option will be selected in the tech-stack document.

---

# 57. Graph Data

Hatcommways has many graph-shaped relationships.

Examples:

- task dependency graph
- actor/responsibility graph
- community relationships

This does not automatically require a graph database.

Initial graph queries may be represented using relational structures.

A graph database should only be introduced if real query/scale needs justify it.

---

# 58. Cache Layer

Potential uses:

- project read views
- session/cache data
- rate limiting
- temporary orchestration state
- frequently accessed map data

Cache must not become the only source of authoritative state.

---

# 59. Object Storage

Required for:

- project images
- outcome evidence
- organization files
- attachments
- exported artifacts

Object metadata and permissions should remain linked to transactional records.

---

# 60. Audit Layer

Audit system should capture consequential operations.

Examples:

- responsibility accepted
- organization committed
- project visibility changed
- plan approved
- payment instruction changed
- agent proposal applied
- platform moderation action

Audit data should be append-oriented and difficult to mutate accidentally.

---

# 61. Observability

Hatcommways needs three observability levels.

## Application Observability

- API latency
- errors
- worker status
- database
- event processing

## Agent Observability

- run counts
- latency
- model cost
- tool use
- structured-output failures
- retries
- stale results

## Product Execution Observability

- blocker counts
- open critical responsibilities
- timeline instability
- event failures

These should not be confused.

---

# 62. Failure Isolation

Architectural boundaries should prevent optional systems from stopping execution.

Examples:

If Map Service fails:

project tasks still execute.

If semantic retrieval fails:

current project state remains usable.

If Actor Theme Agent fails:

canonical role names display.

If Support Intelligence Agent fails:

support totals remain correct.

If notification delivery fails:

retry notification without corrupting project state.

---

# 63. External Integrations

Future integrations may include:

- email
- calendar
- messaging
- maps/geocoding
- organization APIs
- identity systems

Integrations should be placed behind explicit connector/tool interfaces.

Agents should never embed raw third-party credentials.

---

# 64. Email Boundary

Email may support:

- organization outreach
- responsibility invitations
- meeting coordination
- appreciation
- notifications

Agents may:

- draft
- classify reply
- suggest next action

Authorized workflow handles actual sending according to permissions.

---

# 65. Calendar Boundary

Calendar integration may support:

- meetings
- events
- actor availability
- organization scheduling

Scheduling Agent should receive minimum necessary availability rather than complete private calendar histories.

---

# 66. Maps Boundary

Map/geocoding providers support:

- project display
- discovery
- geocoding
- distance
- project areas

Map provider data should not define application privacy rules.

Hatcommways controls what precision is exposed.

---

# 67. Write Path

Typical human write path:

User Action

↓

Frontend

↓

Application API

↓

Authentication / Authorization

↓

Domain Service

↓

Transaction

↓

Domain Event

↓

Async Consumers

↓

Agents / Workers / Projections

This is the preferred pattern.

---

# 68. Agent Write Path

Typical reasoning path:

Domain Event

↓

Agent Orchestrator

↓

Load Authorized Agent Context

↓

Strands Agent

↓

Governed Tools / Memory

↓

Structured Proposal

↓

Proposal Validation

↓

Human Approval if Required

↓

Domain Service

↓

Transactional State Change

↓

New Domain Event

The agent does not write arbitrary database state.

The detailed bounded reasoning path is:

Domain Event
→ Trigger Router
→ Affected Subgraph Resolver
→ Context Builder
→ Current State + Memory Retriever
→ Bounded Strands Graph
→ Specialized Agents
→ Typed Proposals
→ Proposal Merger / Conflict Resolver
→ Schema Validation
→ State-Version Validation
→ Domain-Invariant Validation
→ Permission Validation
→ Decision Inbox where required
→ Domain Service
→ Transaction
→ New Domain Event
→ Validated Outcome / Failure
→ Memory Writer

This path preserves Hatcommways as the owner of long-lived orchestration and governance while Strands handles bounded reasoning/workflow execution.

---

# 69. Read Path

Typical project read:

Frontend

↓

Application API

↓

Authorization

↓

Role-specific projection

↓

Current authoritative state + derived view

Examples:

PublicProjectView

MemberProjectView

AdminProjectView

OrganizationProjectView

Avoid sending one enormous project object to every client.

---

# 70. Map Read Path

Public visitor requests Action Map.

↓

API

↓

permission check

↓

privacy-safe map projection

↓

map response

The response should not query raw private participant locations directly.

---

# 71. Agent Context Construction

Before an agent run:

1. Identify trigger.
2. Identify affected project region.
3. Determine required state.
4. Apply authorization/policy.
5. Retrieve relevant current state.
6. Retrieve relevant memory.
7. Exclude unnecessary sensitive fields.
8. attach state versions.
9. invoke Strands agent.

This should be a reusable infrastructure capability.

---

# 72. Agent Context Must Be Small and Relevant

Do not send:

- entire project history
- every conversation
- every participant
- all sponsor information

to every agent.

Example:

Parallelization Agent needs:

- affected tasks
- dependencies
- actor availability/capacity
- timeline

Nothing more unless justified.

This reduces:

- cost
- latency
- privacy exposure
- confusion

Memory included in context must be applicability-aware and carry provenance, confidence, and source scope. It must be clearly separated from current-state facts.

---

# 72.1 Evaluation Harness

The Evaluation Harness sits beside the production runtime rather than in the user request path.

It should run deterministic scenario fixtures against the same agent registry, graph execution, context, proposal contracts, validators, permission boundaries, and stale-result checks used by production.

Conceptually:

Scenario Corpus
→ Evaluation Harness
→ Bounded Strands Graph Runtime
→ Typed Proposals / Tool Results
→ Expected Invariants and Outcomes
→ Evaluation Report

Evaluation measures system behavior, including activation precision, schema validity, dependency preservation, unnecessary mutation, stale-result rejection, permission compliance, memory applicability, and external-tool failure recovery. It does not optimize solely for plausible model text.

---

# 73. Versioning Strategy

Important mutable structures should have versions.

Examples:

- project_version
- goal_version
- plan_version
- task_graph_version
- actor_graph_version
- timeline_version

This supports:

- concurrent reasoning
- stale-result detection
- audit
- replay
- conflict resolution

---

# 74. Optimistic Concurrency

When applying an agent/human change:

Expected version must match current relevant version.

If not:

- reject
- retry
- ask for refreshed approval
- rerun reasoning

This prevents older decisions from overwriting newer state.

---

# 75. Idempotency

Important write operations should support idempotency.

Examples:

- responsibility acceptance
- contribution confirmation
- project publication
- agent proposal application
- event processing

This protects against retries and duplicate event delivery.

---

# 76. Security Boundaries

Security-sensitive areas include:

- authentication
- authorization
- payment instructions
- exact locations
- organization authority
- agent tools
- external credentials
- public/private map projection

These areas should not rely on LLM judgment.

---

# 77. Deployment Boundaries

Initial deployment may conceptually contain:

## Web App

Hatcommways frontend.

## API Application

Core deterministic backend.

## Agent Runtime

Python + Strands.

## Worker Runtime

Event/background processing.

## Database

PostgreSQL.

## Queue/Event Infrastructure

Async event distribution.

## Object Storage

Files/evidence/images.

## Cache

Optional based on initial load.

This is sufficient for a serious first production architecture.

---

# 78. Avoid Premature Microservices

Do not initially create:

- Task microservice
- Actor microservice
- Timeline microservice
- Support microservice
- Community microservice

as independently deployed systems merely because logical boundaries exist.

Start modular.

Extract services when justified by:

- scale
- team ownership
- security
- failure isolation
- deployment independence

---

# 79. Potential Later Service Extraction

Likely future extraction candidates:

- Agent Runtime
- Notification Service
- Map Projection / Geospatial Service
- Search
- Integration Gateway
- Memory/Knowledge Retrieval

The core domain may remain a modular application longer.

---

# 80. Architecture Invariants

## Invariant 1

Agents do not own transactional truth.

## Invariant 2

Agents do not bypass authorization.

## Invariant 3

Human commitments are persisted only through authorized domain actions.

## Invariant 4

Frontend hiding is not security.

## Invariant 5

Event consumers are idempotent where required.

## Invariant 6

Agent outputs are structured proposals.

## Invariant 7

Stale agent results cannot silently overwrite current state.

## Invariant 8

Independent asynchronous work should be allowed to run concurrently.

## Invariant 9

Optional AI/map/memory failures must not corrupt core execution.

## Invariant 10

Structured facts use structured storage/retrieval.

## Invariant 11

Payment processing remains outside Hatcommways initially.

## Invariant 12

AgentCore complements Hatcommways architecture; it does not replace domain truth.

## Invariant 13

Internal Hatcommways tools and external third-party tools remain separate capability classes.

## Invariant 14

AgentCore Identity and Gateway do not replace Hatcommways project authorization.

## Invariant 15

Agents never receive raw third-party credentials.

## Invariant 16

External tool availability follows least privilege and valid user or organization delegation.

## Invariant 17

AgentCore Observability does not replace Hatcommways product audit.

## Invariant 18

External systems do not become the source of truth for Hatcommways project state.

## Invariant 19

Strands Graph executes bounded multi-agent reasoning episodes; Hatcommways owns long-lived orchestration.

## Invariant 20

Memory provides applicable historical context while PostgreSQL and current Hatcommways state remain execution truth.

## Invariant 21

Evaluation measures agent-system behavior using the same governed contracts and validators as production.

---

# 81. Initial Architecture Diagram

Conceptually:

                         ┌──────────────────────┐
                         │    Web / PWA         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Application API    │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┴─────────────────┐
                 │                                    │
                 ▼                                    ▼
        Identity / Policy                      Domain Services
                                                      │
                                                      ▼
                                             Execution Engine
                                                      │
                                                      ▼
                                                Domain Events
                                                      │
             ┌────────────────────────────────────────┼───────────────────────┐
             │                                        │                       │
             ▼                                        ▼                       ▼
   Background Workers                       Agent Orchestrator         Read / Map Models
                                                      │
                                                      ▼
                                               Context Builder
                                                      │
                                                      ▼
                                               Strands Runtime
                                                      │
                                             Specialized Agents
                                                      │
                          ┌───────────────────────────┴─────────────────────────┐
                          │                                                     │
                          ▼                                                     ▼
               Internal Hatcommways Tools                             External Tools
                          │                                                     │
                          ▼                                                     ▼
                    Domain Services                                  AgentCore Identity
                                                                                │
                                                                                ▼
                                                                      AgentCore Gateway
                                                                                │
                                                                    ┌───────────┼───────────┐
                                                                    ▼           ▼           ▼
                                                                  Email      Calendar   External APIs


                    Agent execution / tool activity
                                 │
                                 ▼
                     AgentCore Observability

Shared:
PostgreSQL
Object Storage
Cache
Event / Audit History
Map Projections
Application Observability

Detailed governed reasoning path:

                         Domain Event
                              ↓
                         Trigger Router
                              ↓
                 Affected Subgraph Resolver
                              ↓
                        Context Builder
                       /               \
              Current State       Memory Retriever
                       \               /
                              ↓
                   Bounded Strands Graph
                              ↓
                     Specialized Agents
                              ↓
                       Typed Proposals
                              ↓
              Proposal Merger / Conflict Resolver
                              ↓
                      Schema Validation
                   State-Version Validation
                  Domain-Invariant Validation
                     Permission Validation
                              ↓
                 Human Decision if required
                              ↓
                        Domain Service
                              ↓
                          Transaction
                              ↓
                     New Domain Event
                              ↓
                Validated Outcome / Failure
                              ↓
                         Memory Writer

External capability path remains:

Hatcommways Permission
→ Human / Organization Delegation
→ Agent Tool Permission
→ AgentCore Identity
→ AgentCore Gateway
→ External System

Beside the production runtime:

Scenario Corpus
→ Evaluation Harness
→ Same Bounded Graph Runtime and Contracts
→ Expected Invariants / Results
→ Evaluation Report

AgentCore Observability traces bounded graph runs, model calls, memory retrieval, tools, Gateway operations, latency, retries, and failures. Hatcommways product audit separately records authority and authoritative state changes.
