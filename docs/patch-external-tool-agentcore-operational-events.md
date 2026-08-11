# PATCH — External Tool and AgentCore Operational Events

## External Tool Event Family

Add a new event family for governed external capability execution.

Core events:

- external_tool.requested
- external_tool.authorized
- external_tool.denied
- external_tool.started
- external_tool.completed
- external_tool.failed
- external_tool.cancelled

These events describe the lifecycle of an external tool operation requested by a Strands agent.

Examples of external capabilities:

- calendar
- email
- meeting systems
- organization APIs
- external scheduling systems
- future partner integrations

---

## external_tool.requested

Meaning:

A Strands agent requested use of an external capability.

This event does not mean the action is authorized or executed.

Payload may include:

- request_id
- project_id
- agent_id
- agent_run_id
- tool_name
- action
- delegated_identity_reference
- source_event_id
- source_state_version
- correlation_id

Sensitive credentials must never be included.

---

## external_tool.authorized

Meaning:

Hatcommways authorization and required delegated identity checks succeeded.

This means the request is eligible to continue to AgentCore Gateway.

Authorization may include:

- agent tool permission
- project permission
- user delegation
- organization authority
- current-state validation
- approval state

Potential next event:

external_tool.started

---

## external_tool.denied

Meaning:

The requested external capability was not authorized.

Possible reasons:

- agent not allowed to use tool
- participant lacks authority
- organization representative authority invalid
- delegated identity missing
- delegation revoked
- human approval missing
- project state changed
- capability unavailable

The denial should include a safe reason code.

Do not expose sensitive security details unnecessarily.

---

## external_tool.started

Meaning:

The authorized external operation began through AgentCore Gateway or the governed external integration layer.

Potential metadata:

- gateway operation reference
- agent run id
- correlation id
- started_at

This is operational state, not domain truth.

---

## external_tool.completed

Meaning:

The external operation completed successfully.

Payload may include:

- request_id
- tool_name
- safe result reference
- external resource reference
- occurred_at
- correlation_id

Examples:

- calendar event created
- approved email sent
- meeting request submitted

A successful external tool operation does not automatically mean Hatcommways domain state changed.

Relevant domain services must process the result.

---

## external_tool.failed

Meaning:

The external operation failed.

Possible reasons:

- provider unavailable
- expired delegated access
- Gateway failure
- external API rejection
- timeout
- tool validation failure

Potential reactions:

- bounded retry
- surface human decision
- fall back to manual action
- continue unaffected project branches

Failure of an external tool must not automatically stop the project.

---

## external_tool.cancelled

Meaning:

A pending or in-progress external operation was intentionally cancelled.

Possible causes:

- human cancelled approval
- project state changed
- tool request became stale
- project paused/cancelled

---

## External Identity Events

Add:

- external_identity.connected
- external_identity.updated
- external_identity.revoked
- external_identity.expired

These events describe the availability of delegated external access.

They do not expose credentials.

---

## external_identity.connected

Meaning:

A participant or authorized organization representative established delegated access to an external system.

Examples:

- calendar connected
- organization email capability connected

Potential reactions:

- Scheduling Agent may gain calendar capability
- Organization Participation Agent may gain approved email capability

Tool availability should still be checked at run time.

---

## external_identity.revoked

Meaning:

Delegated external access was revoked.

Potential reactions:

- remove external capability from future agent runs
- invalidate cached authorization
- stop pending unsafe external operations
- notify affected workflow if necessary

The project itself continues.

Example:

Calendar access revoked.

Scheduling Agent may still reason internally but can no longer use the calendar tool.

---

## external_identity.expired

Meaning:

Delegated external access expired naturally.

This should be handled similarly to revocation for future calls.

The system may surface:

> Calendar access needs to be reconnected before Hatcommways can check availability automatically.

---

## Gateway Events

Optional internal operational events:

- gateway.request_started
- gateway.request_completed
- gateway.request_failed

These are infrastructure events.

They should not normally appear in public/project feeds.

They may be used for:

- observability
- debugging
- retries
- latency analysis

---

## Trace Correlation Event

Add:

- agent_trace.correlated

Meaning:

A Hatcommways domain/action record has been associated with an agent/runtime trace.

Possible payload:

- project_id
- source_event_id
- agent_run_id
- correlation_id
- trace_reference

This event/reference helps connect product audit with AgentCore Observability.

It should not contain raw model reasoning or sensitive tool data.

---

## Updated Agent Run Events

Existing:

- agent_run.requested
- agent_run.started
- agent_run.completed
- agent_run.failed
- agent_run.retry_scheduled
- agent_run.exhausted
- agent_run.cancelled

Add optional metadata:

- correlation_id
- trace_reference
- external_tool_count
- gateway_call_count

This connects Strands execution to AgentCore Observability.

---

## Updated External Action Flow

Conceptually:

Agent decides external capability may be useful

↓

external_tool.requested

↓

Hatcommways authorization

↓

If denied:

external_tool.denied

OR

If approved:

external_tool.authorized

↓

AgentCore Identity

↓

AgentCore Gateway

↓

external_tool.started

↓

External System

↓

external_tool.completed
or
external_tool.failed

↓

Hatcommways Domain Service

↓

Relevant domain event

Example:

external_tool.completed
(calendar event created)

↓

scheduled_event.external_reference_attached

The external-tool event and product-domain event remain separate.

---

## Example — Calendar Flow

Creator approves proposed event time.

human_approval.granted

↓

Scheduling Agent / workflow requests external calendar action.

external_tool.requested

tool:
calendar.create_event

↓

Hatcommways validates:

- project permission
- user delegation
- current event version
- agent capability

↓

external_tool.authorized

↓

AgentCore Identity
→ AgentCore Gateway
→ Calendar

↓

external_tool.completed

↓

Hatcommways attaches external event reference.

↓

scheduled_event.external_reference_attached

The calendar event does not replace the Hatcommways event entity.

---

## Example — Email Flow

Project owner approves contact with Organization X.

human_approval.granted

↓

Organization Participation Agent uses:

email.send_approved_message

↓

external_tool.requested

↓

organization authority checked

↓

external_tool.authorized

↓

AgentCore Gateway sends message

↓

external_tool.completed

↓

communication.sent

Product audit records who authorized the communication.

Runtime trace records how the tool executed.

---

## Example — Revoked Access

Scheduling Agent wants calendar availability.

external_tool.requested

↓

Delegated calendar identity has been revoked.

↓

external_tool.denied

reason:
delegation_revoked

↓

No calendar API call occurs.

↓

Scheduling Agent may return:

manual_availability_required

Project execution continues.

---

## Operational vs Domain Events

This distinction must remain explicit.

### Operational Events

Examples:

- agent_run.started
- external_tool.started
- gateway.request_failed
- agent_trace.correlated

These explain how the system executed.

### Domain Events

Examples:

- responsibility.accepted
- task.completed
- scheduled_event.scheduled
- organization.joined_project
- timeline.recalculated

These describe Hatcommways product reality.

Operational events must not be mistaken for domain state.

---

## Public Visibility

External tool and AgentCore events are system-internal by default.

Do not expose raw events such as:

- external_tool.authorized
- external_identity.connected
- gateway.request_failed

on public project pages.

Users should see meaningful product outcomes instead.

Example:

Instead of:

> Gateway request completed.

Show:

> Meeting added to your calendar.

---

## Updated Event Families

Add to the existing event-family list:

26. External Tools
27. External Identity
28. Gateway / External Integration Operations
29. Trace Correlation

These are operational families supporting the existing product event model.

---

## Updated Event Taxonomy Invariants

Add:

### Invariant 11

An external tool request does not imply authorization.

### Invariant 12

External authorization does not imply a Hatcommways domain state change.

### Invariant 13

Raw external credentials must never appear in event payloads.

### Invariant 14

External identity revocation must prevent future governed external access.

### Invariant 15

AgentCore operational events remain distinct from Hatcommways domain events.

### Invariant 16

External tool failure must not automatically block unrelated project execution.

### Invariant 17

Product audit and runtime traces should be correlatable without exposing sensitive data.

---

## Updated Core Event Loop

Human / Organization / Domain Event

↓

Hatcommways Validation / Authorization

↓

Agent Activation if reasoning is required

↓

Strands Agent

↓

Internal Tool

OR

External Tool Request

↓

For external tools:

Hatcommways Permission
→ AgentCore Identity
→ AgentCore Gateway
→ External System

↓

Result

↓

Validated Hatcommways Domain State Change

↓

New Domain Event

Across this entire path:

- Hatcommways Audit tracks product authority
- AgentCore Observability tracks runtime execution
- correlation ids connect the two

---

## Final Principle

External integrations are effects around Hatcommways execution, not independent sources of authority.

The event system should always distinguish:

> What did an agent request?

from:

> What was authorized?

from:

> What happened in an external system?

from:

> What became true inside Hatcommways?

That separation keeps Strands agents autonomous enough to be useful while preserving Hatcommways governance, auditability, and execution truth.