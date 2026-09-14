# Hatcommways — Implementation Contract

> Design/planning reference, not a deployed feature inventory. For current behavior and boundaries, see the [implementation documentation index](README.md). Broader capabilities below remain proposals unless confirmed there.

## 1. Purpose

This document translates the canonical Hatcommways architecture into a concrete build contract.

It defines what implementation work may do, what it must not do, which boundaries own authoritative truth, and the dependency order for building the system.

This document does not select a final technology stack, AWS service topology, database schema, API shape, or deployment design.

Core principle:

> Hatcommways governs long-lived execution. Strands performs bounded reasoning. Deterministic services maintain truth. Humans retain authority over consequential commitments.

---

# 2. Core Invariants

Code must never violate these invariants.

1. Task is not Responsibility.
2. Actor Role is not Actor, Participant, or Organization.
3. Participant is not Organization; an organization representative has explicit, current authority scope.
4. Project is not Event.
5. Contribution/support is not Responsibility.
6. Joining or participating does not equal accepting responsibility.
7. AI suggestion, proposal, or invitation does not equal human or organization commitment.
8. Themed display names never alter canonical roles, permissions, or execution semantics.
9. PostgreSQL/current Hatcommways transactional state is authoritative execution truth.
10. Events are append-oriented historical facts; actions are requests that may fail, require approval, or produce events.
11. Agent output is untrusted until schema, reference, version, invariant, permission, conflict, and approval checks pass.
12. Agents produce typed proposals; they do not directly mutate authoritative domain state.
13. Stale proposals cannot overwrite newer project, task-graph, actor-graph, plan, or timeline versions.
14. Timeline is derived, versioned, and revisable—not immutable truth.
15. Readiness has four distinct layers: logical, responsibility, capacity, and execution readiness.
16. Independent work continues when unrelated work is blocked.
17. Hatcommways replans affected execution regions rather than regenerating the whole project by default.
18. Unaffected branches remain stable unless validated relationships require the affected region to expand.
19. The 24 specialized agents remain bounded reasoning workers; the orchestrator is not a 25th reasoning agent.
20. A bounded Strands Graph exists for one reasoning episode, not for the lifetime of a project.
21. Memory provides permission-aware, applicability-aware context and never overrides current state.
22. Raw events are not replaced by summaries, memory compaction, or blueprints.
23. Raw chain-of-thought, secrets, and unrestricted third-party credentials are not stored as product memory or trace data.
24. Human approval remains required for consequential commitments, publication, major scope changes, protected visibility changes, organization commitments, and cancellation.
25. Internal Hatcommways tools remain separate from external AgentCore-governed tools.
26. AgentCore Identity and Gateway do not replace Hatcommways authorization.
27. AgentCore Observability explains runtime execution; Hatcommways audit explains authority and product-state change.
28. External systems do not silently become Hatcommways execution truth.
29. Support is an execution condition that may include people, organizations, venue, materials, equipment, transport, expertise, and optional externally arranged funding.
30. Hatcommways is not a payment processor, fundraising platform, donor ledger, or popularity-ranking system.

---

# 3. Authoritative Domain Entities

The implementation must preserve these conceptual entities and their boundaries:

- Goal
- Project
- Task
- Dependency
- Timeline and Timeline Version
- Plan and Plan Revision
- Actor Role and Role Requirement
- Actor
- Responsibility and Responsibility Lineage
- Participant
- Organization and Organization Representative Authority
- Temporary Group
- Permanent Community
- Scheduled Event / Meeting
- Support Mode, Support Requirement, and Support State
- Contribution / Support Record where retained by the approved product model
- Blocker
- Decision / Approval Request
- Map Configuration and Map Projection
- Project State
- Outcome
- Domain Event and Audit Record
- Agent Run, Graph Run, and Proposal
- Project, Decision, Pattern, Failure/Revision, Outcome, Blueprint, and Working Memory

The exact persistence schema is deferred. Entity identifiers, version fields, visibility, provenance, and lifecycle state must remain explicit when schemas are later designed.

---

# 4. Deterministic Services and Modules

The initial codebase should expose strong modular boundaries without requiring independently deployed microservices.

Required deterministic modules are:

## Identity and Policy

- identity and account state
- group/community membership
- organization representatives and authority scope
- project/object/field/action authorization
- `ALLOW`, `DENY`, or `REQUIRE_APPROVAL`

## Project and Goal

- project lifecycle and visibility
- goal versions and creator context
- plan approval and scope revision references
- completion, cancellation, and archival rules

## Task Graph and Dependency

- task lifecycle and graph versions
- parent/child and branch relationships
- dependency validation and traversal
- deterministic dependency satisfaction
- upstream/downstream and affected-region queries

## Actor, Role, Responsibility, and Capacity

- canonical roles, cardinality, specialization, and themes
- responsibility lifecycle, vacancy, transfer, and lineage
- availability and capacity state
- deterministic coverage and contention inputs

## Execution Engine

- logical readiness
- responsibility readiness
- capacity readiness
- execution readiness
- blocked/unblocked and newly-ready transitions
- deterministic state effects from validated domain changes

## Timeline and Replanning Application

- authoritative timeline versions
- expected task windows and completion
- selective invalidation and selective recalculation
- persistence of validated replanning results
- revision reasons and source versions

## Event, Scheduling, Support, Community, and Organization

- scheduled-event state and prerequisites
- support requirements, availability, confirmations, and visibility
- group/community lifecycle and project attachment
- organization participation and commitment boundaries

## Decision and Approval

- version-bound approval requests
- expiration, grant, denial, and stale-approval protection
- persistent pause/resume across long-running workflows

## Memory, Projection, Notification, and Audit

- governed Memory Retriever and Memory Writer
- role-specific read models
- privacy-safe map projections
- deterministic notification delivery
- append-oriented domain history and product audit

---

# 5. The 24 Agent Boundaries

The approved agent registry remains:

1. Goal Understanding Agent — structures ambiguous creator goals and assumptions.
2. Project Scope Agent — estimates scale, complexity, branches, events, and participation boundaries.
3. Task Decomposition Agent — proposes task nodes and branches without assigning people.
4. Dependency Reasoning Agent — proposes dependency, branching, merging, conditional, event, and approval relationships.
5. Timeline Planning Agent — proposes estimates, phases, timing ranges, and initial or revised timeline implications.
6. Parallelization Agent — identifies structural concurrency, contention, and safe parallel groups.
7. Actor Requirement Agent — proposes project-specific canonical role requirements.
8. Actor Capacity Agent — proposes minimum, ideal, maximum-useful capacity and scale-based expansion.
9. Role Specialization Agent — proposes domain-relevant specializations mapped to canonical roles.
10. Actor Theme Agent — proposes display-only role naming.
11. Actor Fit Agent — recommends possible actors without assigning or committing them.
12. Responsibility Intelligence Agent — identifies vacancies, overload, handoff, and reassignment needs.
13. Community and Group Structure Agent — proposes temporary/permanent collaboration topology without automatic conversion.
14. Organization Participation Agent — interprets organization offers and proposes participation/responsibility mappings.
15. Scheduling Agent — proposes candidate times using approved constraints and allowed availability.
16. Event Planning Agent — proposes event structure, roles, prerequisites, and task-graph links.
17. Blocker Detection Agent — interprets meaningful blockers, severity, and affected scope.
18. Replanning Agent — proposes selective revisions for the affected execution region.
19. Acceleration Agent — proactively proposes safe timeline compression and unnecessary-wait removal.
20. Support State Reasoning Agent — interprets support conditions and identifies affected versus unaffected work.
21. Participation and Action Intelligence Agent — interprets execution participation and role coverage.
22. Support and Organization Intelligence Agent — interprets privacy-safe support and organization-participation patterns.
23. Project Memory Agent — proposes candidate memory entries, summaries, and execution-history interpretations.
24. Outcome and Blueprint Agent — proposes outcome analysis, lessons, appreciation, and privacy-safe reusable blueprints.

Agent definitions specify triggers, context, memory profile, tools, model profile, output contract, and proposal-only write scope. Durable truth and commitments remain outside agents.

---

# 6. Event-Driven Orchestration Responsibilities

The Hatcommways orchestrator is deterministic governance infrastructure. It must:

- consume and filter domain events
- propagate event, correlation, and causation identifiers
- run deterministic prechecks before model invocation
- calculate or request the affected execution region
- select eligible agents and determine whether a bounded graph is required
- resolve agent permission and capability profiles
- build scoped current-state and memory context
- enforce concurrency, deduplication, idempotency, retries, and no-progress limits
- track graph and agent run state
- route typed proposals through merge and validation
- create persistent Decision Inbox items when approval is required
- reject stale work and rerun only when still necessary
- emit operational events and preserve audit/trace correlation
- allow unrelated workers and reasoning branches to continue independently

The orchestrator does not perform specialized planning reasoning and does not directly invent domain truth.

---

# 7. Bounded Strands Graph Responsibilities

A bounded graph run is selected or constructed for one reasoning objective.

Each graph run carries:

- `graph_run_id`
- source event and correlation identifiers
- project identifier
- affected execution region
- source project, plan, task-graph, actor-graph, and timeline versions
- participating agents
- nodes and graph dependencies
- permitted parallel branches
- fan-out and fan-in points
- completion, failure, retry, and cancellation conditions

The Strands runtime may:

- execute eligible independent nodes concurrently
- use bounded cyclic refinement only with explicit limits and no-progress protection
- expose governed tools
- return schema-defined proposals and safe explanatory narratives

It may not:

- remain alive for the project lifetime
- bypass Hatcommways policy
- mutate authoritative state
- hold raw external credentials
- treat merged output as validated truth

---

# 8. Affected-Subgraph and Selective Replanning Responsibilities

The Affected Subgraph Resolver deterministically calculates an initial safe affected execution region and expands it when validated dependencies, shared capacity constraints, cross-branch relationships, or project-wide consequences require broader scope.

Inputs include:

- changed tasks, dependencies, responsibilities, actors, events, blockers, and support conditions
- upstream constraints and downstream dependents
- shared actors, specialists, organization capacity, and contention
- event prerequisites and project-wide approvals or states
- current graph and timeline versions

Outputs include:

- initially affected object identifiers
- upstream constraints
- downstream impact
- preserved unaffected branches
- expansion reasons
- invalidated readiness/timing assumptions
- source versions and calculation provenance

Selective replanning must update only the affected region unless validation proves broader impact. Project-wide pause, cancellation, major scope change, shared critical constraints, or completion-impact changes may require expansion.

---

# 9. Typed Proposal Contracts

Every consequential agent result uses a typed contract. A common proposal envelope should conceptually include:

- `proposal_id`
- proposal type and schema version
- `project_id`
- `agent_id`, agent version, and agent/graph run identifiers
- source event and correlation identifiers
- source project, plan, task-graph, actor-graph, and timeline versions
- affected execution region and affected object identifiers
- proposed changes
- reason codes
- evidence references
- memory references with applicability metadata
- confidence
- creation time and provenance

Agent-specific payloads may include:

- task and dependency changes
- timeline changes
- role/capacity requirements
- responsibility impacts
- blocker classifications
- schedules
- support impacts
- candidate memory or outcome entries

Narrative explanation is supplementary. Application state must never be mutated by parsing prose.

---

# 10. Proposal Validation, Merge, and Stale-Result Rules

The required pipeline is:

Typed Proposal
→ Schema Validation
→ Object / Reference Validation
→ State-Version Validation
→ Domain-Invariant Validation
→ Permission Validation
→ Conflict / Merge Validation
→ Human Approval where required
→ Authorized Domain Transaction

The Proposal Merger / Conflict Resolver may combine compatible proposals only when:

- their source versions are compatible
- their writes do not conflict
- merged changes preserve all domain invariants
- agent, evidence, and memory provenance remains intact

It must reject ambiguous conflicts rather than guess.

If authoritative state changes during reasoning:

- mark the proposal stale
- prevent it from overwriting newer state
- retain safe operational provenance
- recalculate the affected region if necessary
- rerun only eligible nodes whose reasoning remains necessary
- require refreshed human approval when an earlier approval references stale state

---

# 11. Memory Retriever and Memory Writer

## Memory Retriever

The Memory Retriever must:

- read current authoritative state before historical memory is considered
- enforce project, participant, community, organization, agent, and purpose scopes
- retrieve only memory relevant to the affected execution region and reasoning objective
- return provenance, source scope, confidence, context signature, structural similarity, scale, actor/dependency pattern, outcome quality, recency, and applicability
- distinguish current-project episodic/decision memory from cross-project patterns and blueprints
- reject or down-rank stale, unauthorized, low-confidence, or inapplicable memories
- return stable references for proposal provenance

Memory reuse is not generic nearest-neighbor retrieval. Current state always wins.

## Memory Writer

The Memory Writer must:

- accept only validated decisions, outcomes, failures, revisions, lessons, and approved candidate memory
- persist provenance and source state/event references
- control promotion, supersession, and compaction records
- keep raw append-oriented events intact
- generalize or remove private data from reusable blueprints
- avoid persisting raw chain-of-thought, every model message, secrets, and transient graph scratch state

AgentCore Memory is not an initial requirement. Hatcommways owns project, decision, pattern, failure/revision, outcome, and blueprint memory.

---

# 12. Human Approval Boundaries

Explicit authorized human or organization action is required for:

- accepting, withdrawing, or transferring responsibility where policy requires
- committing a person, group, community, organization, or company
- publishing a project
- approving major scope changes or consequential replanning
- changing project visibility or protected public fields
- enabling optional public demographic analytics
- publishing organization/support attribution
- consequential external messages or calendar actions without prior bounded authorization
- cancelling a project or removing another participant

Decision records must carry the requested action, affected object, source state version, initiator, authority context, expiry, result, and audit provenance.

Safe internal analysis, deterministic recalculation, proposal generation, summaries, and bounded pre-authorized routine communication may proceed according to policy.

---

# 13. Internal Tools and External AgentCore Tools

## Internal Hatcommways Tools

Internal tools call governed Hatcommways modules, for example:

- project and task-graph reads
- affected-region and dependency queries
- responsibility and capacity reads
- timeline and blocker reads
- permission-aware memory retrieval
- proposal submission

They require agent permission, project scope, field filtering, versions, and audit. They do not require AgentCore Gateway.

## External Tools

Selected third-party capabilities follow:

Strands Agent
→ Hatcommways Agent Tool Permission
→ Hatcommways User / Organization Authorization
→ Delegation Check
→ AgentCore Identity
→ AgentCore Gateway
→ Narrow External Capability

Examples include approved calendar, email, meeting, organization, and partner-system operations.

Capabilities must be narrow and dynamically resolved. Revocation immediately removes future access. Agents receive capability references, never OAuth tokens, API keys, passwords, or unrestricted HTTP access.

AgentCore Identity, Gateway, and Observability are the approved initial AgentCore boundaries. AgentCore Runtime remains an optional future deployment choice; AgentCore Memory remains an optional later evaluation for narrow agent-oriented cross-run context.

---

# 14. Background Workers

Deterministic/background workers should handle:

- event fan-out and consumer retries
- readiness and timeline recalculation
- projection rebuilds and privacy aggregation
- notification delivery
- search indexing
- file/evidence processing
- cache updates and invalidation
- scheduled reminders and approved routine workflows
- dead-letter handling and operational cleanup
- evaluation job execution

Workers must be idempotent where events or commands can be delivered more than once. Worker failure must not corrupt domain truth.

---

# 15. Read Models and Projections

Clients and agents consume purpose-specific projections rather than unrestricted aggregate objects.

Required projection classes include:

- public project view
- member/participant project view
- project-admin view
- organization/sponsor project view
- agent planning context
- Decision Inbox view
- Action Map
- Support Map
- Organization Map
- optional privacy-thresholded analytics

Projection services enforce field permissions, visibility, location precision, aggregation, threshold suppression, and freshness/version metadata. Public projections never depend on frontend hiding and never expose raw private event payloads.

---

# 16. Evaluation Harness Responsibilities

The Evaluation Harness sits beside production, not in the user request path.

It runs controlled scenario fixtures with deterministic assertions/invariants against the same:

- agent registry and contracts
- trigger and eligibility rules
- affected-region resolver
- bounded graph runtime
- governed tools
- proposal merger and validators
- permission and approval boundaries
- stale-result protection
- memory applicability rules

The model output may vary. Deterministic assertions cover permissions, schema validity, version protection, dependency preservation, unaffected branches, approval requirements, and forbidden state mutations.

Initial metrics include:

- correct agent activation rate
- proposal schema validity rate
- stale proposal rejection rate
- unnecessary task mutation rate
- dependency preservation rate
- approval-boundary violation rate
- scenario completion rate
- external-tool failure recovery rate
- irrelevant memory reuse rate
- useful memory reuse rate

Evaluation measures governed system behavior, not merely plausible model text.

---

# 17. Required Tests by Subsystem

## Domain and Invariants

- task/responsibility separation
- participant/organization/representative separation
- canonical-role versus theme behavior
- lifecycle and transition validity

## Graph, Readiness, and Timeline

- dependency satisfaction and invalidation
- logical/responsibility/capacity/execution readiness
- actor contention and capacity thresholds
- parallel and serialized timelines
- versioned timeline revisions

## Affected Region and Replanning

- local changes preserve unrelated branches
- upstream/downstream region calculation
- shared-capacity and cross-branch expansion
- project-wide consequence detection
- selective invalidation and recalculation

## Event and Orchestration

- event-envelope validation
- trigger precision and fan-out
- idempotent duplicate handling
- graph eligibility and completion
- retry, cancellation, dead-letter, and no-progress behavior

## Proposal Contracts

- schema and reference validation
- domain-invariant and permission rejection
- compatible merges and conflicting-write rejection
- stale proposal and stale approval rejection
- provenance preservation

## Memory

- current state outranks memory
- permission-scoped retrieval
- applicability ranking across scale/topology differences
- failure/mitigation reuse
- validated promotion and compaction
- raw events remain intact

## Human Authority and Policy

- responsibility acceptance cannot be fabricated
- organization authority scope and revocation
- protected visibility changes require authorization
- consequential actions route to Decision Inbox

## Internal and External Tools

- agent tool allow/deny profiles
- field filtering and project scope
- no raw credentials in context, arguments, events, or traces
- external delegation/revocation and safe result handling
- external result does not automatically mutate domain state

## Projections and Privacy

- public/member/admin/organization field isolation
- location precision
- aggregation thresholds
- Action versus passive-interest separation
- support and organization privacy

## Evaluation and Observability

- controlled fixtures use production contracts
- deterministic assertions detect invariant violations
- correlation across event, graph, agent, tool, proposal, and state change
- sensitive trace-data filtering
- product audit remains distinct from runtime trace

---

# 18. Smallest End-to-End Vertical Slice

The smallest real slice should prove Hatcommways' defining execution behavior without AWS or a user-facing application.

Scenario:

1. Create an in-memory project with independent Tasks A and B.
2. Give one actor accepted responsibility/capacity for both tasks.
3. Calculate a serialized initial timeline.
4. Record a second actor accepting responsibility for Task B.
5. Emit `responsibility.accepted` with versions and correlation metadata.
6. Resolve the affected execution region.
7. Run deterministic prechecks and invoke a bounded local graph using a fake Parallelization/Acceleration proposal producer.
8. Validate and merge the typed proposal.
9. Apply the authorized transaction through the domain boundary.
10. Produce a new timeline version where A and B may run concurrently.
11. Emit `timeline.recalculated` and write validated execution memory.
12. Assert unaffected state, provenance, idempotency, and stale-result rejection.

This slice proves events, graph scope, responsibility/capacity readiness, selective replanning, typed proposals, validation, versioning, timeline revision, and memory boundaries. It intentionally uses test doubles instead of AWS or live models.

---

# 19. Dependency-Ordered Implementation Sequence

## Phase 1 — Contracts and Pure Domain Logic

1. Canonical identifiers, versions, command/result types, event envelope, and error/result model.
2. Domain entity types and invariant checks.
3. Task/dependency graph primitives and traversal queries.
4. Responsibility, availability, capacity, and contention primitives.
5. Four-layer readiness calculator.
6. Timeline calculation and versioned revision primitives.
7. Affected Subgraph Resolver and selective invalidation rules.

## Phase 2 — Proposal and Orchestration Boundaries

8. Typed proposal envelope and first proposal contracts.
9. Schema, reference, version, invariant, permission, and merge/conflict validators.
10. Event dispatcher, trigger router, eligibility checks, run state, and idempotency.
11. Bounded graph abstraction with local fake agent nodes.
12. Decision/approval contract and stale-approval handling.

## Phase 3 — First Vertical Slice

13. Implement and test the responsibility-accepted timeline-compression slice.
14. Add audit/correlation and operational run records.
15. Add Memory Retriever/Writer interfaces with local structured storage adapters.
16. Record validated execution/failure memory from the slice.

## Phase 4 — Broader Deterministic Domain

17. Project/goal lifecycle, plan revisions, blocker, event/scheduling, support, organization, and community modules.
18. Role-specific read models and privacy projection rules.
19. Background worker contracts for events, timelines, notifications, projections, and indexing.
20. Expand scenario tests across failure, withdrawal, event, support, and scope-change cases.

## Phase 5 — Local Agent Runtime

21. Machine-readable 24-agent registry and permission/tool profiles.
22. Context Builder with current state, affected region, and applicability-aware memory.
23. Local Strands adapter and bounded graph execution using configured/test model access when available.
24. Proposal provenance, retries, no-progress protection, and observability hooks.

## Phase 6 — External and Production Integrations

25. Hatcommways authorization adapters for delegated external capabilities.
26. AgentCore Identity and Gateway integration for approved narrow tools.
27. AgentCore Observability integration and trace correlation.
28. Production persistence, queue/event infrastructure, object storage, cache, geospatial, and deployment choices only after separate approval.

---

# 20. Local-First and AWS-Dependent Work

## Build Locally Before AWS

- all domain types and invariants
- graph traversal, readiness, capacity, timeline, and affected-region logic
- event and proposal contracts
- validators, merger, stale-result protection, and approvals
- local orchestration and bounded graph interfaces
- fake/deterministic agent nodes
- Memory Retriever/Writer interfaces and local adapters
- projections and privacy filters
- background-worker interfaces
- vertical-slice and evaluation fixtures
- agent registry, context builder, tool router interfaces, and observability abstraction
- local Strands integration if model credentials/runtime are available, while keeping it replaceable in tests

## Must Wait for AWS/Bedrock/AgentCore Access or Explicit Infrastructure Choice

- live Bedrock model profiles and production model invocation
- AgentCore Identity delegated external credentials
- AgentCore Gateway external tools
- AgentCore Observability production traces
- any AgentCore Runtime evaluation or deployment
- any later AgentCore Memory experiment
- AWS-hosted persistence, queues/events, storage, cache, search, maps, and deployment topology

AWS is not required to prove the core Hatcommways execution model locally.

---

# 21. Proposed First 10 Implementation Tasks

1. Define shared IDs, version stamps, correlation/causation metadata, and result/error contracts. **Local-only.**
2. Define pure domain entity types and executable invariant tests. **Local-only.**
3. Implement task/dependency graph primitives and upstream/downstream traversal. **Local-only.**
4. Implement responsibility coverage, actor availability, capacity, and contention primitives. **Local-only.**
5. Implement logical, responsibility, capacity, and execution readiness calculation. **Local-only.**
6. Implement versioned deterministic timeline calculation for simple DAGs and actor contention. **Local-only.**
7. Implement the Affected Subgraph Resolver with expansion reasons and unaffected-branch preservation. **Local-only.**
8. Define typed proposal envelopes plus Parallelization and Timeline/Replanning proposal contracts. **Local-only.**
9. Implement schema/reference/version/invariant/permission validation and proposal merge/conflict rules. **Local-only.**
10. Build the local `responsibility.accepted` → affected region → bounded fake-agent graph → validated timeline revision vertical slice. **Local-only.**

None of the first 10 tasks requires AWS.

---

# 22. Known Documentation Contradictions and Alignment Items

The canonical documentation contains these unresolved alignment issues. This contract does not silently change them:

1. Some older product, event, map, governance, and flow sections still describe funding targets, contribution records, payment instructions, Money/Support Maps, and sponsor-centric behavior. The newer system architecture defines broad Support State and removes a dedicated payment subsystem. Before persistence contracts are finalized, the team must decide which legacy optional support records remain authoritative and which are historical wording only.
2. Some event and domain text still uses combined `actor readiness` or `actor_readiness.recalculated`, while the current execution model defines logical, responsibility, capacity, and execution readiness separately. Event names and projection fields require a canonical decision before schemas are created.
3. Canonical filenames are only partially numbered. This does not affect runtime architecture but should be normalized separately if ordering is intended to be machine-readable.
4. The documentation defines conceptual dependency types beyond simple finish-to-start and allows partial/conditional work, while explicitly deferring which types ship first. The first implementation scope must be approved before dependency persistence is designed.
5. The exact boundary between a safe automatically applied timeline recalculation and a consequential replanning change requiring approval remains policy-driven and is not fully enumerated.

---

# 23. Blockers Before Coding

No blocker prevents beginning the first local-only contract and pure-domain tasks.

Before database schemas, public APIs, or production workflows are implemented, the following decisions are required:

- resolve the legacy support/funding/payment scope contradiction
- choose canonical readiness event/field terminology
- approve the initial supported dependency types and partial-progress scope
- define the policy threshold for automatic versus approval-required replanning

AWS availability is not a blocker for the first vertical slice or the first 10 implementation tasks.

