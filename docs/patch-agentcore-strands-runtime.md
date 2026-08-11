# PATCH — AgentCore Identity, Gateway, and Observability in the Strands Runtime

## Updated Tool Architecture

Hatcommways Strands agents use two different classes of tools:

1. Internal Hatcommways tools
2. External tools

These must remain architecturally separate.

---

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

Internal tools do not need AgentCore Gateway simply because they are used by agents.

They remain inside the Hatcommways trust boundary.

---

## External Tools

External tools interact with third-party systems.

Examples:

- calendar availability
- calendar event creation
- email
- meeting systems
- organization APIs
- external scheduling systems
- future partner integrations

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

---

## Agent Tool Profiles

Every agent definition should explicitly declare its allowed tools.

Example:

Parallelization Agent

Internal tools:

- get_affected_task_graph
- get_dependencies
- get_actor_capacity
- get_current_timeline

External tools:

- none

Example:

Scheduling Agent

Internal tools:

- get_event
- get_task_readiness
- get_actor_availability
- get_current_timeline

External tools:

- calendar.read_availability
- calendar.create_event

Example:

Organization Participation Agent

Internal tools:

- get_organization_relationship
- get_project_context
- get_open_organization_roles

External tools:

- email.send_approved_message
- meeting.request

Agents must not dynamically acquire unrestricted tools.

---

## No Raw External Credentials

Strands agent prompts, memory, context, and tool arguments must not contain raw external credentials.

Examples that must not be exposed to agents:

- OAuth access tokens
- refresh tokens
- API secrets
- email credentials
- calendar credentials
- organization integration secrets

Agents receive:

> a capability

not:

> the credential implementing that capability

Credential management belongs to AgentCore Identity / governed integration infrastructure.

---

## Delegated Identity Context

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

This context should travel through the governed external-action path.

---

## Hatcommways Authorization Before AgentCore

AgentCore Identity does not decide Hatcommways business permission.

Before external access:

Hatcommways checks:

1. Is this agent permitted to use this tool type?
2. Is the action relevant to this project?
3. Is the initiating user authorized?
4. If acting for an organization, is representative authority valid?
5. Does the human delegation cover this action?
6. Does the action require fresh human approval?
7. Is the request based on current project state?

Only after these pass should external execution continue.

---

## External Tool Invocation Contract

Conceptually:

ExternalToolRequest

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

The runtime should avoid placing secrets inside this contract.

---

## External Tool Result Contract

Conceptually:

ExternalToolResult

- request_id
- tool_name
- status
- external_resource_reference
- safe_result
- occurred_at
- correlation_id
- error_code if failed

The result should return only information necessary for Hatcommways.

---

## Example — Scheduling Agent

Current project state:

Installation Event requires scheduling.

Scheduling Agent receives:

- event constraints
- task readiness
- relevant participant availability permissions
- timeline
- project version

Agent reasons:

> Saturday 10 AM is likely suitable.

If external calendar access is required:

Strands Scheduling Agent
→ calendar.read_availability

Runtime performs:

Hatcommways tool permission check
→ delegated user authorization check
→ AgentCore Identity
→ AgentCore Gateway
→ calendar system

The agent receives only the allowed availability result.

It does not receive calendar credentials.

---

## Example — Calendar Creation

Scheduling Agent proposes:

Saturday 10 AM.

If human approval is required:

SchedulingProposal
→ Decision Inbox
→ Human Approval

After approval:

approved external action
→ AgentCore Identity
→ AgentCore Gateway
→ calendar.create_event

The resulting external event id is stored as a reference.

Hatcommways Scheduled Event remains the product execution record.

External calendar state does not replace Hatcommways truth.

---

## Example — Organization Email

Organization Participation Agent determines that an approved message should be sent.

Agent may produce:

EmailDraft

Human approves when required.

Then:

Strands Agent / workflow
→ email.send_approved_message
→ Hatcommways permission check
→ organization authority check
→ AgentCore Identity
→ AgentCore Gateway
→ email provider

The runtime records:

- message reference
- success/failure
- project correlation
- agent run

---

## Internal Tools Do Not Automatically Need Identity Delegation

Example:

Parallelization Agent calls:

get_dependency_region

This is a Hatcommways internal read.

It requires:

- agent permission
- project scope

It does not require external user credential delegation.

Do not force AgentCore Identity into every internal data read.

---

## Updated Context Builder

The Agent Context Builder should now produce two distinct context categories.

### Reasoning Context

Examples:

- tasks
- dependencies
- responsibilities
- timeline
- blockers
- approved memory

### Capability Context

Examples:

- which internal tools are enabled
- which external tools are available
- delegated identity references
- approval state
- capability restrictions

Do not place secrets in either context.

---

## Capability Availability Is Dynamic

An external capability may be available for one run and unavailable for another.

Example:

Scheduling Agent:

Run 1:
calendar access available

Run 2:
user revoked calendar access

Therefore tool availability should be resolved at runtime.

Do not assume that because an agent historically had a tool, it still has access.

---

## Revoked External Access

If delegated identity access is revoked while a project remains active:

AgentCore / integration layer rejects the call.

Hatcommways should emit an appropriate operational/domain event.

The agent may then:

- continue with internal reasoning
- propose manual scheduling
- request renewed access
- surface a human decision

Do not fail the entire project.

---

## AgentCore Gateway as External Capability Boundary

AgentCore Gateway should expose selected external operations as governed capabilities.

Examples:

calendar:
- read_availability
- create_event

email:
- send_approved_message

meeting:
- request_meeting

organization API:
- retrieve_allowed_information
- submit_authorized_request

Avoid exposing overly broad capabilities such as:

- unrestricted HTTP request
- arbitrary mailbox access
- arbitrary calendar mutation

Tools should remain task-oriented and narrow.

---

## External Tool Least Privilege

Tool definitions should be narrow.

Better:

create_project_calendar_event(
    project_id,
    event_id,
    approved_time
)

Worse:

execute_arbitrary_calendar_operation(payload)

The narrower interface makes:

- permission checks
- auditing
- validation
- agent behavior

more reliable.

---

## AgentCore Observability Integration

Hatcommways should integrate agent runtime execution with AgentCore Observability.

The desired execution trace is:

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

Observability should make the agent execution path inspectable.

---

## Trace Context

The following identifiers should be propagated where possible:

- correlation_id
- causation_id
- project_id
- agent_run_id
- agent_id
- source_event_id
- state_version

This allows distributed operations to be connected.

---

## Example Trace

responsibility.accepted

correlation_id:
abc123

↓

Parallelization Agent Run

agent_run_id:
run789

↓

get_affected_task_graph

↓

get_actor_capacity

↓

model produces ParallelizationProposal

↓

proposal validated

↓

timeline v12 → v13

Using shared trace/correlation context, Hatcommways can explain the operational path behind this change.

---

## External Tool Trace

For external actions:

Scheduling Agent
→ AgentCore Gateway
→ Calendar

trace should include safe metadata such as:

- agent id
- tool name
- external operation type
- latency
- success/failure
- correlation id

Do not include secrets in trace attributes.

---

## Product Audit vs Runtime Trace

AgentCore Observability does not replace Hatcommways product audit.

Runtime trace answers:

- which model call occurred?
- which tool ran?
- how long did it take?
- where did it fail?

Product audit answers:

- who approved the meeting?
- which responsibility was accepted?
- why did timeline become authoritative?
- which organization committed?

Both remain necessary.

---

## Agent Run Observability Record

Each Strands run should retain safe operational metadata.

Example:

- run_id
- agent_id
- agent_version
- project_id
- trigger_event
- started_at
- finished_at
- model_profile
- tool_calls
- external_gateway_calls
- retry_count
- result_status
- source_state_version
- output_reference
- trace_reference

---

## Observability and Concurrent Agents

Concurrency is a core Hatcommways behavior.

Example:

responsibility.accepted

activates concurrently:

- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

Each run must have:

- its own run id
- shared parent correlation
- independent trace
- state-version context

This makes concurrency understandable during debugging.

---

## Observability and Stale Results

Example:

Timeline Agent starts against:

timeline_version = 12

During execution:

timeline_version becomes 13

Agent output is rejected as stale.

Observability should make visible:

- agent run
- source version
- current version
- stale-result rejection

This allows us to distinguish:

agent failure

from:

correct governance behavior

---

## Observability and Retry

When an agent retries:

do not hide prior attempts.

Trace should allow:

Run
→ Attempt 1 failed
→ Attempt 2 succeeded

Product users do not need to see this.

Developers/operators should.

---

## AgentCore Does Not Replace Hatcommways Runtime Governance

Even with AgentCore Identity, Gateway, and Observability:

Hatcommways still owns:

- Trigger Router
- Agent Registry
- Context Builder
- Tool permission profiles
- Output validation
- stale-result protection
- human approval routing
- domain invariant checking
- state mutation

AgentCore strengthens the external execution and observability boundaries.

It does not become Hatcommways' business orchestrator.

---

## Updated Runtime Modules

Conceptually:

agents/
  registry/
  definitions/
  prompts/
  contracts/
  model_profiles/

runtime/
  executor/
  context_builder/
  internal_tool_router/
  external_tool_router/
  output_validator/
  retry_policy/
  stale_state_checker/
  observability/

integrations/
  agentcore_identity/
  agentcore_gateway/
  external_capabilities/

orchestration/
  trigger_router/
  dependency_resolver/
  concurrency_manager/
  approval_router/

memory/
  retriever/
  policy/
  project_memory/
  blueprint_memory/

tools/
  internal/
  external/

The exact source tree may differ, but the boundary should remain.

---

## Updated Agent Definition Example

Parallelization Agent:

- Strands agent: yes
- internal tools:
  - task graph
  - dependency graph
  - actor capacity
  - timeline
- external tools:
  - none
- external delegated identity:
  - not required
- output:
  - ParallelizationProposal

Scheduling Agent:

- Strands agent: yes
- internal tools:
  - event state
  - task readiness
  - timeline
  - allowed availability state
- external tools:
  - calendar availability
  - calendar create event
- delegated identity:
  - required when accessing private external calendar
- output:
  - SchedulingProposal / approved external action

Organization Participation Agent:

- Strands agent: yes
- internal tools:
  - organization relationship
  - project context
- external tools:
  - approved email
  - meeting request
- delegated identity:
  - user / organization representative depending on action

---

## Updated Runtime Invariants

Add:

### Invariant 11

Internal Hatcommways tools and external third-party tools remain separate capability classes.

### Invariant 12

Agents never receive raw third-party credentials.

### Invariant 13

External tool access requires both Hatcommways authorization and valid delegated external identity where applicable.

### Invariant 14

AgentCore Gateway does not grant project authority by itself.

### Invariant 15

External tool availability is resolved dynamically and can be revoked.

### Invariant 16

AgentCore Observability traces runtime execution but does not replace product audit.

### Invariant 17

Sensitive data must not be inserted unnecessarily into traces.

### Invariant 18

External system state never silently replaces Hatcommways authoritative domain state.

---

## Updated Runtime Flow

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


Across both:

AgentCore Observability
+
Hatcommways Application Observability
+
Hatcommways Product Audit

provide complementary visibility.

---

## Updated Final Principle

Strands remains the framework that executes Hatcommways reasoning agents.

Hatcommways remains responsible for:

- why an agent runs
- what it can see
- what tools it can request
- whether its output is valid
- whether a human must decide
- what becomes authoritative state

AgentCore Identity + Gateway add a secure boundary when Strands agents need to act outside Hatcommways.

AgentCore Observability makes those agent runs and tool paths operationally visible.

The resulting architecture is:

> Hatcommways governs.
> Strands reasons.
> AgentCore secures external capability access and exposes runtime execution.
> Humans retain authority over commitments.