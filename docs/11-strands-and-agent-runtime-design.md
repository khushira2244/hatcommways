# Hatcommways — Strands and Agent Runtime Design

## 1. Purpose

This document defines how Hatcommways' reasoning agents are implemented and executed using the Strands Agents SDK.

It explains:

- how agents are registered
- how events activate agents
- how agent dependencies are represented
- how independent agents run concurrently
- how agents receive context
- how tools are exposed
- how structured outputs are validated
- how stale results are rejected
- how retries work
- how human decisions are surfaced
- what belongs to Strands
- what remains Hatcommways infrastructure
- where Amazon Bedrock AgentCore may fit

Core principle:

> Strands provides agent execution.
> Hatcommways provides orchestration policy, business truth, permissions, and execution governance.

---

# 2. Runtime Philosophy

Hatcommways must not implement its agents as one giant conversational agent.

It also must not implement:

Agent 1
→ Agent 2
→ Agent 3
→ ...
→ Agent 24

as a permanent sequential chain.

The agent system is:

> event-driven
> dependency-driven
> state-aware
> concurrent where safe

Agents should run only when:

- a relevant event occurs
- required inputs exist
- policy allows execution
- the resulting reasoning is still useful

---

# 3. Strands Role in Hatcommways

Strands Agents SDK should provide the base capabilities for:

- agent definitions
- model interaction
- tool calling
- structured agent behavior
- workflow / graph patterns where useful
- multi-agent execution
- instrumentation
- agent runtime abstractions

Hatcommways-specific behavior remains outside the framework.

Strands does not become the source of truth for:

- projects
- tasks
- responsibilities
- permissions
- organization authority
- timelines
- funding state
- project lifecycle

---

# 4. Agent Runtime Deployment

The initial agent runtime should be implemented in Python using Strands.

Conceptually:

Application Backend
→ domain event
→ agent orchestration request
→ Python Strands Runtime
→ agent(s)
→ structured proposal(s)
→ validation
→ domain state transition

The runtime may initially run as one deployable service containing all registered agents.

Do not deploy 24 independent services on Day 1.

---

# 5. Agent Registry

Every agent must be defined in a machine-readable registry.

Conceptual record:

agent_id:
parallelization

name:
Parallelization Agent

version:
1

description:
Identifies task branches that may safely run concurrently.

trigger_events:
- responsibility.accepted
- actor.available
- actor.capacity_changed
- task.completed
- blocker.resolved
- dependency.updated

reads:
- task_graph
- dependencies
- responsibilities
- actor_capacity
- timeline

tools:
- task_graph_reader
- actor_capacity_reader
- timeline_reader
- execution_pattern_reader

output_contract:
ParallelizationProposal

write_scope:
proposal_only

requires_human_approval:
conditional

memory_profile:
parallelization_memory

---

# 6. Agent Identity

Every agent run should have explicit identity.

Example:

agent_type:
parallelization

agent_version:
1

run_id:
unique identifier

This identity should be included in:

- logs
- audit
- tool calls
- proposal provenance
- observability traces

Do not use anonymous generic "AI" operations.

---

# 7. Agent Versions

Agent definitions will evolve.

Example:

parallelization:v1

later:

parallelization:v2

Historical agent runs should preserve which version produced a proposal.

This helps:

- debugging
- evaluation
- rollback
- comparing behavior

---

# 8. Trigger-Based Activation

Agents are activated by relevant domain events.

Example:

responsibility.accepted

may activate:

- Responsibility Intelligence Agent
- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

But only if each agent's trigger conditions are satisfied.

---

# 9. Trigger Filtering

An event match alone is not enough.

Example:

responsibility.accepted

Project Memory Agent may always record it.

Parallelization Agent should run only if:

- responsibility affects executable work
- affected tasks may have concurrency implications

This prevents unnecessary model calls.

---

# 10. Activation Contract

Before invoking an agent, the orchestrator should evaluate:

1. Did a relevant event occur?
2. Is this agent enabled?
3. Does affected state satisfy prerequisites?
4. Has equivalent reasoning already been completed for this state version?
5. Is the relevant project still active?
6. Is required context accessible?
7. Would deterministic logic alone resolve this?
8. Is there already an active run for the same affected region?

Only then invoke the agent.

---

# 11. Agent Dependency Graph

Some agent runs depend on other reasoning results.

Example during initial planning:

Goal Understanding
→ Task Decomposition

Task Decomposition
→ Dependency Reasoning
→ Actor Requirement

Dependency Graph
+
Task Graph
→ Timeline Planning

Actor Requirements
→ Actor Capacity

This should be represented as execution dependencies.

It should not become a hard-coded giant function chain.

---

# 12. Parallel Agent Execution

If dependencies allow:

agents should execute concurrently.

Example:

Once task decomposition is available:

Dependency Reasoning Agent
and
Actor Requirement Agent

may run at the same time.

Likewise after responsibility acceptance:

Participation Intelligence Agent
and
Project Memory Agent

may operate independently of timeline reasoning.

---

# 13. Fan-Out

One event may produce several independent agent jobs.

Example:

task.completed

Fan-out:

- Parallelization analysis
- Acceleration analysis
- Project memory update
- participation interpretation

The orchestrator should enqueue these independently.

---

# 14. Fan-In

Some planning decisions require outputs from multiple agents.

Example:

Initial plan may require:

- Task Decomposition Proposal
- Dependency Proposal
- Actor Requirement Proposal
- Timeline Proposal

A plan assembly step combines validated outputs.

Fan-in should occur through structured state/proposals.

Agents should not need to converse freely with each other.

---

# 15. Agent-to-Agent Communication

Preferred pattern:

Agent A
→ typed proposal
→ validated/persisted intermediate state
→ event
→ Agent B

Avoid:

Agent A directly starts a free-form conversation with Agent B.

Direct agent-to-agent calls should be rare.

Reasons:

- auditability
- determinism
- version control
- debugging
- concurrency
- permission enforcement

---

# 16. Strands Graph / Workflow Usage

Strands graph/workflow capabilities may be useful for bounded reasoning workflows.

Examples:

## Initial Planning Workflow

Goal Understanding
→ Task Decomposition

then parallel:

Dependency Reasoning
Actor Requirement

then:

Timeline Planning
Actor Capacity
Parallelization

This can be represented as a bounded graph.

---

# 17. Do Not Use One Permanent Global Workflow

Hatcommways lifecycle lasts:

- hours
- days
- weeks
- months

Therefore one giant Strands workflow should not remain alive for the entire project.

Instead:

domain events
→ create bounded reasoning runs

Each run handles one reasoning objective.

Long-lived continuity belongs in:

- database
- event history
- memory
- project state

not an in-memory workflow.

---

# 18. Bounded Reasoning Runs

Examples of bounded runs:

- initial project planning
- actor-role recalculation
- blocker analysis
- timeline acceleration
- event scheduling
- outcome analysis

Each run should:

- have clear inputs
- produce typed outputs
- have maximum stages
- stop deterministically
- record result

## Bounded Strands Graph Run Contract

When a reasoning objective requires multiple agents, the runtime constructs or selects a bounded Strands Graph containing only the relevant specialized agents.

Each graph run should contain:

- graph_run_id
- source_event_id
- correlation_id
- project_id
- affected_execution_region
- source_project_version
- source_task_graph_version
- source_actor_graph_version
- source_timeline_version
- participating_agents
- graph nodes and dependencies
- allowed parallel branches
- completion and failure conditions

Agents execute concurrently where graph dependencies permit. Fan-out and fan-in are bounded to the current reasoning objective.

The graph may use bounded cyclic refinement only when justified by an explicit review or repair need. Cycles require a maximum attempt count, no-progress detection, and deterministic termination.

The 24 Hatcommways agents remain specialized reasoning workers. A Strands Graph is not a new agent and is not a permanent project workflow.

Core principle:

> Strands Graph executes bounded multi-agent reasoning episodes; Hatcommways owns long-lived orchestration.

---

# 19. Agent Context Builder

Before invoking an agent, Hatcommways should build a scoped context package.

Example:

ParallelizationAgentContext:

- project_id
- source_event
- affected_task_ids
- dependency region
- current responsibilities
- actor availability
- actor capacity
- current timeline
- relevant execution patterns
- project state version

Do not pass unnecessary project data.

The context builder should produce two distinct context categories.

## Reasoning Context

Examples:

- tasks
- dependencies
- responsibilities
- timeline
- blockers
- approved memory

## Capability Context

Examples:

- which internal tools are enabled
- which external tools are available
- delegated identity references
- approval state
- capability restrictions

Do not place secrets in either context. External capability availability is resolved at runtime and may change when delegated access is revoked or expires.

---

# 20. Context Construction Pipeline

Conceptually:

Trigger Event
→ Determine affected region
→ Determine agent
→ Read agent permission profile
→ Load authoritative state
→ Retrieve allowed memory
→ Filter sensitive fields
→ Attach state versions
→ Build typed context
→ Invoke Strands agent

This pipeline should be reusable.

---

# 21. Current State Before Memory

Agents should receive authoritative current state before historical memory.

Priority:

1. current transactional state
2. relevant project history
3. relevant reusable patterns
4. agent working context

Historical memory must never override current state.

---

# 22. Tool-Driven Retrieval

Do not put the entire database into the agent prompt.

Provide governed tools.

Example tools:

- get_project_summary
- get_task
- get_affected_task_graph
- get_dependencies
- get_open_responsibilities
- get_actor_capacity
- get_current_timeline
- get_event_constraints
- retrieve_similar_blueprints
- get_blocker_history

Agents query only what they need.

---

# 23. Tool Permissions

Every agent tool invocation should include:

- agent identity
- project identity
- run identity
- requested operation

The tool layer evaluates permissions.

Example:

Actor Theme Agent:

allowed:
get_actor_roles

denied:
get_payment_instruction

Even if the model requests it.

---

# 24. Read Tools vs Write Tools

Prefer read-only tools for most reasoning agents.

Write-like capabilities should usually create proposals.

Example:

Allowed:

propose_replan(...)

Not:

update_task_dependency_directly(...)

The proposal is validated by deterministic services.

## Internal Hatcommways Tools

Internal tools provide access to Hatcommways execution state.

Examples:

- get_project_context
- get_task_graph
- get_dependencies
- get_actor_capacity
- get_open_responsibilities
- get_current_timeline
- get_blockers
- retrieve_project_memory
- retrieve_similar_blueprints
- propose_replan

Execution path:

Strands Agent
→ Hatcommways Tool Router
→ Hatcommways Authorization / Agent Permission Check
→ Domain Service
→ Structured Result

Internal tools remain inside the Hatcommways trust boundary and do not require AgentCore Gateway merely because agents use them.

## External Tools

External tools interact with third-party systems such as calendars, email, meeting systems, organization APIs, external scheduling systems, and future partner integrations.

Execution path:

Strands Agent
→ Hatcommways Tool Permission Check
→ Hatcommways User / Organization Authorization
→ AgentCore Identity
→ AgentCore Gateway
→ External Tool / API
→ Result

Core principle:

> Strands chooses among the tools it has been permitted to use.
> Hatcommways decides whether that capability is actually authorized.
> AgentCore governs the external identity and execution boundary.

Every agent definition should explicitly declare its allowed internal and external tools. Agents must not dynamically acquire unrestricted tools.

Strands agent prompts, memory, context, and normal tool arguments must not contain raw OAuth tokens, refresh tokens, API secrets, email credentials, calendar credentials, or organization integration secrets. Agents receive a capability, not the credential implementing that capability.

When an external tool is requested, the runtime should know:

- agent identity
- agent version
- agent run id
- project id
- initiating user
- represented organization where applicable
- delegated identity reference
- requested capability
- authorization scope
- correlation id

Before external access, Hatcommways checks:

1. Is this agent permitted to use this tool type?
2. Is the action relevant to this project?
3. Is the initiating user authorized?
4. If acting for an organization, is representative authority valid?
5. Does the human delegation cover this action?
6. Does the action require fresh human approval?
7. Is the request based on current project state?

Only after these pass should external execution continue.

Conceptually, `ExternalToolRequest` contains:

- request_id
- project_id
- agent_id
- agent_run_id
- tool_name
- action
- delegated_identity_reference
- input
- source_state_version
- correlation_id

It must not contain secrets.

Conceptually, `ExternalToolResult` contains:

- request_id
- tool_name
- status
- external_resource_reference
- safe_result
- occurred_at
- correlation_id
- error_code if failed

The result returns only information necessary for Hatcommways. External system state does not replace Hatcommways truth.

AgentCore Gateway capabilities should be task-oriented and narrow. Prefer `create_project_calendar_event(project_id, event_id, approved_time)` over unrestricted calendar mutation or arbitrary HTTP access.

---

# 25. Structured Output

System-relevant agent outputs must be structured.

Do not parse arbitrary prose to mutate project state.

Example:

ParallelizationProposal

fields:

- proposal_id
- source_project_version
- source_task_graph_version
- affected_task_ids
- currently_serialized_groups
- proposed_parallel_groups
- required_actor_capacity
- predicted_timeline_effect
- explanation
- confidence

## Typed Agent Proposal Contract

Every consequential reasoning agent should return a schema-defined proposal rather than unstructured prose.

Example:

ReplanningProposal

- proposal_id
- project_id
- agent_id
- agent_run_id
- source_project_version
- source_task_graph_version
- source_actor_graph_version
- source_timeline_version
- affected_task_ids
- affected_responsibility_ids
- proposed_dependency_changes
- proposed_timeline_changes
- proposed_responsibility_changes
- reason_codes
- evidence_references
- memory_references
- confidence

Exact contracts may differ by agent, but every proposal must identify its source state, affected scope, proposed changes, provenance, and confidence.

Agent-facing narrative may accompany a proposal for explanation. It must not be parsed as the source of authoritative mutations.

---

# 26. Output Validation

After a Strands agent returns:

1. validate schema
2. validate referenced objects
3. validate current state version
4. validate business invariants
5. validate permissions
6. determine approval requirement
7. persist proposal or reject

LLM output is untrusted input until validation succeeds.

The full deterministic validation pipeline is:

Strands reasoning
→ typed proposal
→ schema validation
→ object/reference validation
→ state-version validation
→ domain-invariant validation
→ permission validation
→ conflict/merge validation
→ human approval where required
→ authoritative transaction

Deterministic validators decide whether a proposal is eligible to become state. Agents never directly perform the authoritative mutation.

---

# 27. Invalid Output

If output is malformed:

Possible behavior:

- structured-output retry
- narrower repair request
- bounded second attempt
- mark agent run failed

Do not endlessly retry malformed reasoning.

---

# 28. Stale Output

Example:

Replanning Agent starts with:

timeline_version = 8

Before it finishes:

timeline_version = 10

Result references old execution conditions.

System should determine whether the result is materially stale.

Possible actions:

- reject
- rerun
- preserve as historical proposal
- merge only if explicitly safe

Example:

A Timeline or Replanning Agent begins against `timeline_version = 12`.

Before application, the authoritative timeline becomes version 13.

The proposal must not silently overwrite version 13. The runtime marks it stale, records the source and current versions, and rejects it. It reruns only when the underlying reasoning is still necessary for the current affected region.

Stale proposals remain available for operational trace and proposal history where policy permits, but they never become current truth.

## Proposal Merging

When concurrent graph nodes return proposals, the Proposal Merger / Conflict Resolver should:

- merge compatible changes against the same source versions
- preserve each agent's provenance, reason codes, evidence, and memory references
- detect overlapping writes and contradictory graph or timeline changes
- reject ambiguous conflicting changes
- rerun only the affected reasoning nodes when repair is safe
- escalate to human review when the conflict represents a consequential choice

Merged output is a new typed proposal and must pass the complete validation pipeline.

---

# 29. State Fingerprints

For some agents it may be useful to calculate a fingerprint of relevant state.

Example:

parallelization fingerprint:

hash(
affected task ids
+
dependencies
+
responsibility owners
+
actor availability
)

If fingerprint has not changed:

do not rerun identical reasoning.

This can reduce cost.

---

# 30. Agent Run State

Conceptual run states:

- queued
- context_building
- running
- awaiting_tool
- validating_output
- awaiting_human_approval
- completed
- stale
- failed
- cancelled
- exhausted

These states belong to the runtime/orchestration layer.

---

# 31. Retry Strategy

Retry only when failure is recoverable.

Retryable:

- transient model failure
- timeout
- temporary tool failure
- structured output syntax failure

Usually not retryable without new state:

- permission denied
- missing required human decision
- project cancelled
- no suitable planning alternative
- repeated same invalid result

---

# 32. Bounded Retries

Every agent should have:

- max attempts
- max tool calls
- max runtime
- max reasoning stages where relevant

No unbounded autonomous loops.

---

# 33. No-Progress Detection

The orchestrator should recognize repeated identical outputs.

Example:

Replanning Agent repeatedly proposes:

"Move event to Sunday"

but Sunday was rejected twice.

No-progress protection should stop further repeats until relevant state changes.

---

# 34. Human Decision Boundary

Agent may produce:

HumanDecisionProposal

Example:

type:
replanning_approval

summary:
Move installation event from Saturday to Sunday.

reason:
Transport responsibility remains vacant.

impact:
Expected project completion +1 day.

The Decision Service creates an inbox item.

---

# 35. Decision Inbox Integration

Agent does not sit waiting inside an active LLM session.

Instead:

Agent creates proposal
→ workflow pauses persistently
→ human sees Decision Inbox
→ human approves later
→ decision event emitted
→ new bounded agent/domain work continues

This is essential for long-running projects.

---

# 36. Resume Without Replay

After human approval:

Hatcommways should resume from persisted project state.

Do not replay all previous agents unnecessarily.

Example:

Initial plan already completed.

Creator approves.

System should not rerun:

Goal Understanding
Task Decomposition

unless relevant state changed.

---

# 37. Event-Driven Resume

Human action produces a normal domain event.

Example:

human_approval.granted

or:

project.plan_approved

The event activates only the next relevant work.

This keeps project execution resumable across days/weeks.

---

# 38. Agent Memory

Strands agents may use memory, but Hatcommways controls memory scope.

Types available:

- current project memory
- historical execution patterns
- blueprint memory
- short-lived working memory

The runtime should retrieve memory through governed interfaces.

## Memory Context Contract

The Context Builder retrieves only memory relevant to the affected execution region and reasoning objective.

Every reusable memory reference supplied to an agent should include:

- memory id and type
- provenance
- source scope
- source project type
- context signature
- project scale
- actor structure where relevant
- dependency or failure pattern where relevant
- outcome quality
- recency
- reuse count where relevant
- confidence
- applicability score
- reason for retrieval

Agents must distinguish:

current state facts

from:

historical/reusable memory

Current authoritative state always wins. A semantically similar memory must be ignored or qualified when its scale, topology, actor structure, outcome quality, permissions, or context make it inapplicable.

---

# 39. Agent Working Memory

Working memory exists only for one bounded reasoning run.

It may include:

- intermediate comparisons
- tool results
- candidate plans

It should not automatically become durable project memory.

---

# 40. Durable Memory Promotion

Only validated meaningful outputs may become durable memory.

Examples:

- approved plan revision
- confirmed blocker explanation
- final outcome summary
- reusable execution lesson

Promotion should occur after validation.

---

# 41. Model Selection

Not every Hatcommways agent necessarily requires the same model.

Potential future strategy:

High-reasoning model:

- task decomposition
- dependency planning
- replanning
- outcome synthesis

Lower-cost model:

- summaries
- theme generation
- simple classification

However, initial implementation may use one well-performing Bedrock model to reduce complexity.

Model abstraction should allow later per-agent configuration.

---

# 42. Model Configuration in Registry

Example:

agent:
replanning

model_profile:
high_reasoning

temperature:
low

structured_output:
ReplanningProposal

max_iterations:
5

Agent registry should reference logical model profiles rather than scattering model IDs throughout code.

---

# 43. System Prompts

Every agent should have:

- role definition
- domain invariants
- allowed reasoning scope
- forbidden behaviors
- expected output contract
- tool-use guidance

Shared product laws should be reusable.

Do not duplicate 100% of Hatcommways product documentation inside every system prompt.

---

# 44. Shared Agent Laws

All agents should inherit common rules such as:

- do not fabricate commitments
- do not override current authoritative state
- respect task vs responsibility distinction
- respect privacy
- do not expose sensitive data
- reference current versions
- produce only allowed outputs

Agent-specific instructions add domain rules.

---

# 45. Agent Evaluation Hooks

Each agent should eventually support evaluation.

Possible dimensions:

- schema validity
- correct referenced objects
- proposal quality
- unnecessary tool calls
- state-staleness rate
- human acceptance rate
- reasoning cost
- latency

Do not rely only on whether the model returned successfully.

## Evaluation Harness and Scenario Corpus

Hatcommways should maintain a conceptual scenario corpus of approximately 20–30 deterministic cases. The harness runs these fixtures against the same agent contracts, bounded graph runtime, governed tools, validators, permission rules, and stale-result checks used in production.

Example scenario:

Venue becomes unavailable 12 hours before an event.

Expected behavior:

- blocker detected
- affected execution region calculated
- unrelated branches preserved
- relevant replanning agents activated
- stale state not overwritten
- external commitment requires authorization and approval
- resulting proposal is schema valid

Potential metrics:

- correct agent activation rate
- proposal schema validity rate
- stale proposal rejection rate
- unnecessary task mutation rate
- dependency preservation rate
- approval-boundary violation rate
- scenario completion rate
- external tool failure recovery rate
- irrelevant memory reuse rate
- useful memory reuse rate

Evaluation must measure agent-system behavior, not only whether an LLM produced plausible text.

---

# 46. Agent Observability

Each run should produce traces for:

- trigger
- context build
- memory retrieval
- model invocation
- tool calls
- output validation
- final result
- retry
- failure

This is particularly important with concurrent agents.

AgentCore Observability should trace:

domain event
→ affected execution region
→ bounded Strands Graph run
→ participating agents
→ model calls
→ memory retrieval
→ internal tool calls
→ external Gateway calls where applicable
→ typed proposal
→ merge/conflict result
→ validation result
→ resulting domain event

Trace metadata should include graph run id, agent run ids, correlation and causation ids, source state versions, affected region, safe memory references, tool names, latency, retries, failures, and stale-result outcomes.

Do not log secrets, raw hidden reasoning, unnecessary private memory content, or raw third-party credentials.

---

# 47. OpenTelemetry

Where Strands supports observability/instrumentation, Hatcommways should integrate with standard tracing.

Useful trace relationships:

Domain Event
→ Orchestration Run
→ Agent Run
→ Model Call
→ Tool Call
→ Proposal
→ Domain State Change

Correlation IDs should connect them.

---

# 48. Cost Tracking

Agent runs should record:

- model
- input tokens
- output tokens
- estimated cost
- latency
- tool count

Cost can later be analyzed by:

- agent
- project
- project type
- user plan

This is important for eventual Hatcommways pricing.

---

# 49. AgentCore Runtime

Amazon Bedrock AgentCore Runtime may later host the Strands runtime.

This is a deployment/infrastructure choice.

It should not alter:

- agent contracts
- domain boundaries
- event taxonomy
- project state model

The runtime interface should remain portable enough that local development works without AgentCore.

---

# 50. AgentCore Memory

AgentCore Memory may be used for appropriate agent-oriented memory.

Potential uses:

- long-running contextual memory
- cross-run agent context

But:

PostgreSQL remains authoritative for execution truth.

AgentCore Memory should never become the only record of:

- responsibility acceptance
- tasks
- project state
- permissions
- financial state

---

# 51. AgentCore Gateway

AgentCore Gateway exposes selected external operations as governed capabilities such as:

- calendar
- email
- organization systems
- external APIs

This fits Hatcommways because agents should use governed tool boundaries instead of raw credentials.

It does not replace Hatcommways' internal tool router. Internal domain tools remain inside Hatcommways.

---

# 52. AgentCore Identity

AgentCore Identity manages delegated credentials and governed external access where adopted.

Example:

Scheduling Agent needs calendar access granted by user.

This can complement Hatcommways application authorization.

It does not replace Hatcommways' project permission model.

Tool availability must be resolved dynamically for each run. If delegated access is revoked or expires, the integration layer rejects the call. The agent may continue internal reasoning, propose a manual alternative, request renewed access, or surface a human decision. The entire project must not fail.

---

# 53. AgentCore Observability

Hatcommways uses AgentCore Observability for agent-infrastructure tracing across:

Domain Event
→ Hatcommways Orchestrator
→ Agent Context Build
→ Strands Agent Run
→ Model Call
→ Tool Selection
→ Internal Tool or Gateway Tool
→ Structured Output
→ Validation
→ Domain Result

The following identifiers should be propagated where possible:

- correlation_id
- causation_id
- project_id
- agent_run_id
- agent_id
- source_event_id
- state_version

Each concurrent agent run has its own run id and independent trace while sharing the parent correlation. Retries should preserve prior attempts, and stale-result rejection should show the source and current versions.

External-tool traces should contain safe metadata such as agent id, tool name, operation type, latency, success/failure, and correlation id. They must not include secrets.

Hatcommways should still preserve its own:

- domain audit
- project history
- proposal history
- agent-run metadata

Infrastructure traces and product audit are different layers.

Runtime traces answer which model or tool ran, how long it took, and where it failed. Product audit answers who approved an action and what became authoritative.

---

# 54. Local Development

Agent runtime should run locally without requiring the complete production environment.

Developer should be able to:

- start backend
- start agent runtime
- use test database
- emit test domain event
- invoke one Strands agent
- inspect structured output

This is important for fast Codex-driven development.

---

# 55. Agent Simulation

Testing may simulate events.

Example:

Given:

responsibility.accepted

for Task B

with Actor 2

Expected:

Parallelization Agent invoked

Expected proposal:

Task A and B may run concurrently

No real user/organization commitments should be fabricated during testing.

---

# 56. Unit Tests

Test agent infrastructure for:

- trigger filtering
- context builder
- tool permissions
- output validation
- stale-result rejection
- retry bounds
- no-progress detection
- human approval routing

Agent reasoning quality evaluation is separate.

---

# 57. Contract Tests

Every agent output schema should have contract tests.

Example:

Replanning Agent must always produce:

- source version
- affected scope
- proposal
- rationale
- confidence

Invalid referenced task IDs must be rejected.

---

# 58. Agent Integration Tests

Example test:

1. Create project.
2. Create independent Tasks A and B.
3. Give one actor both responsibilities.
4. Generate timeline.
5. Add second actor.
6. Emit responsibility.accepted.
7. Parallelization Agent activates.
8. Proposal passes validation.
9. Timeline recalculates.
10. Project completion time improves.

This is a high-value Hatcommways integration test.

---

# 59. Failure Test

Example:

Parallelization Agent proposes concurrent tasks that actually have a dependency.

Validator must reject proposal.

This proves:

> Agent reasoning does not override graph truth.

---

# 60. Permission Test

Example:

Support Intelligence Agent requests payment instructions.

Tool layer should deny access.

Agent should still reason using:

- funding mode
- funding state
- aggregated support data

---

# 61. Concurrency Test

Example:

task.completed
and
responsibility.accepted

arrive close together.

Multiple agents run concurrently.

One proposal becomes stale.

Expected:

stale proposal rejected or rerun.

No execution truth is corrupted.

---

# 62. Initial Agent Runtime Modules

Conceptually:

agents/
  registry
  definitions
  prompts
  contracts
  model_profiles

runtime/
  executor
  context_builder
  internal_tool_router
  external_tool_router
  output_validator
  retry_policy
  run_state
  stale_state_checker
  observability

orchestration/
  trigger_router
  dependency_resolver
  concurrency_manager
  stale_state_checker
  approval_router

memory/
  retriever
  policy
  project_memory
  blueprint_memory

tools/
  internal
  external

integrations/
  agentcore_identity
  agentcore_gateway
  external_capabilities

The final code layout may differ, but these boundaries should remain recognizable.

---

# 63. Do Not Create 24 Copies of Runtime Infrastructure

All agents should reuse common infrastructure for:

- model invocation
- schema validation
- context building
- memory
- tools
- logging
- retries
- permissions

Agent definitions should mostly specify:

- reasoning role
- triggers
- required context
- tools
- output contract
- model profile

---

# 64. Agent Definition Example

Conceptually:

Parallelization Agent

Purpose:
Detect safe concurrency opportunities.

Triggers:
- responsibility.accepted
- actor.capacity_changed
- task.completed

Required context:
- affected task graph
- dependencies
- actor capacity
- timeline

Allowed tools:
- graph read
- actor capacity read
- historical execution pattern read

Output:
ParallelizationProposal

Write authority:
proposal only

Human approval:
only if proposal materially restructures approved plan

---

# 65. Deterministic Prechecks Before Agent Use

Before calling a reasoning agent, run cheap deterministic checks.

Example:

Parallelization:

If there is only one affected task:

do not call agent.

If tasks have explicit direct dependency:

basic parallelization may already be impossible.

If no actor capacity changed:

skip actor-driven acceleration reasoning.

This reduces model use.

---

# 66. Deterministic Postchecks

After reasoning:

validate against:

- graph invariants
- current state
- permissions
- cardinality
- dependency consistency
- approved project constraints

Agent output becomes authoritative only after passing postchecks.

---

# 67. Background Agents

"Background agent" does not mean permanently running an LLM loop.

For Hatcommways it means:

> Relevant reasoning activates automatically when project state changes, without the user manually invoking AI.

Example:

Actor joins.

Hatcommways automatically checks whether project execution can accelerate.

That is meaningful background autonomy.

---

# 68. Surface Only Real Decisions

Most agent operations should remain invisible.

Do not notify user:

> Parallelization Agent finished.

Instead notify only when useful:

> Two tasks can now run in parallel. Expected completion moved 2 days earlier.

Or:

> Transport responsibility is vacant. Installation may be delayed unless someone takes it.

This is the intended human-agent relationship.

---

# 69. Agent Failure Isolation

If one agent fails:

- unrelated agents continue
- authoritative state remains valid
- relevant proposal simply remains unavailable
- retry according to policy

Examples:

Actor Theme Agent fails:
use canonical names.

Participation Intelligence Agent fails:
Action Map raw aggregation still works.

Memory summary fails:
event history remains available.

---

# 70. Runtime Invariants

## Invariant 1

Strands agents never become transactional truth stores.

## Invariant 2

Every state-changing agent result is validated.

## Invariant 3

Every consequential proposal references current state versions.

## Invariant 4

Independent agents may run concurrently.

## Invariant 5

Long-running project continuity lives in persisted state, not a live model session.

## Invariant 6

Human waits persist as decision state rather than open agent sessions.

## Invariant 7

Agents access data only through governed context/tools.

## Invariant 8

Agent outputs use typed contracts.

## Invariant 9

Repeated no-progress reasoning is bounded.

## Invariant 10

Optional AgentCore services complement rather than redefine Hatcommways architecture.

## Invariant 11

Internal Hatcommways tools and external third-party tools remain separate capability classes.

## Invariant 12

Agents never receive raw third-party credentials.

## Invariant 13

External tool access requires both Hatcommways authorization and valid delegated external identity where applicable.

## Invariant 14

AgentCore Gateway does not grant project authority by itself.

## Invariant 15

External tool availability is resolved dynamically and can be revoked.

## Invariant 16

AgentCore Observability traces runtime execution but does not replace product audit.

## Invariant 17

Sensitive data must not be inserted unnecessarily into traces.

## Invariant 18

External system state never silently replaces Hatcommways authoritative domain state.

## Invariant 19

Only agents relevant to the affected execution region participate in a bounded graph run.

## Invariant 20

Concurrent proposals are merged only when compatible and must retain provenance.

## Invariant 21

Current authoritative state overrides historical or reusable memory.

## Invariant 22

Evaluation measures governed system behavior, including validation, permissions, selective mutation, memory applicability, and failure recovery.

---

# 71. Core Runtime Flow

Domain Event

↓

Trigger Router

↓

Deterministic Precheck

↓

Agent Eligibility Check

↓

Agent Context Builder

↓

Authorization / Memory Filtering

↓

Strands Agent Run

↓

Governed Tool Calls

↓

Structured Output

↓

Schema Validation

↓

State-Version Validation

↓

Domain-Invariant Validation

↓

Human Approval if Required

↓

Domain Service Applies Change

↓

New Domain Event

This is the core Hatcommways agent execution loop.

For internal reasoning:

Domain Event
→ Trigger Router
→ Context Builder
→ Strands Agent
→ Hatcommways Internal Tool
→ Structured Proposal
→ Validation
→ Domain Service

For external action:

Domain Event / Approved Human Action
→ Trigger Router
→ Strands Agent
→ External Tool Request
→ Hatcommways Permission Check
→ Delegation Check
→ AgentCore Identity
→ AgentCore Gateway
→ External System
→ Safe Result
→ Hatcommways Audit / State Update

Across both paths, AgentCore Observability, Hatcommways Application Observability, and Hatcommways Product Audit provide complementary visibility.

---

# 72. Final Principle

The user should never feel that Hatcommways contains 24 independent bots.

They should experience one coordinated system that quietly keeps work moving.

Internally:

> Events wake specialized agents.
> Agents reason only about their bounded responsibilities.
> Independent reasoning runs concurrently.
> Typed proposals cross into deterministic application services.
> Human authority is requested only when genuinely necessary.
> Persisted state allows the system to stop, wait, and resume for days or months without replaying completed work.

Strands is the reasoning runtime beneath that experience.

Hatcommways remains the execution system above it.
