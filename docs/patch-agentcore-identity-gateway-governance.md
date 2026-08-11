# PATCH — AgentCore Identity + Gateway Governance

## AgentCore Identity and Gateway Boundary

Hatcommways uses Amazon Bedrock AgentCore Identity and AgentCore Gateway for governed access to external tools and third-party systems.

Examples include:

- email
- calendars
- organization APIs
- external scheduling systems
- future partner integrations

This boundary applies only to external capabilities.

Internal Hatcommways data remains governed through Hatcommways domain services and permission checks.

Core principle:

> Internal authorization is owned by Hatcommways.
> Delegated external access is mediated through AgentCore Identity and Gateway.

---

## External Agent Access Flow

When a Strands agent needs to use an external capability, the execution path is:

Strands Agent
→ Hatcommways Agent Permission Check
→ Hatcommways User / Organization Authorization Check
→ AgentCore Identity
→ AgentCore Gateway
→ External Tool / API

An agent must not directly bypass this path when the external capability is managed through AgentCore.

---

## AgentCore Identity

AgentCore Identity is used to support governed external access for agents.

Its role in Hatcommways is to help establish:

- which agent/workload is making the request
- which user or organization delegated access
- which external system is being accessed
- what credential/authorization scope is available

Hatcommways must not treat possession of an external credential as project authorization.

Example:

A Scheduling Agent may technically have delegated calendar access.

It still requires Hatcommways policy to determine whether it is permitted to schedule something for this project.

Therefore:

Hatcommways Permission
+
Delegated External Identity
=
Eligible External Action

Both are required where applicable.

---

## No Raw Third-Party Credentials in Agents

Strands agents must not receive raw third-party credentials in prompts, memory, or unrestricted tool context.

Examples include:

- OAuth tokens
- API secrets
- calendar credentials
- email credentials
- organization API keys

Credential handling should remain inside the governed identity/integration layer.

Agents receive capabilities, not raw secrets.

Core rule:

> Agents use authorized tools.
> Agents do not possess credentials.

---

## AgentCore Gateway

AgentCore Gateway is the governed boundary through which selected external capabilities are exposed to Hatcommways agents.

Examples:

Scheduling Agent may receive:

- get_available_calendar_slots
- propose_calendar_event
- create_calendar_event where pre-authorized

Organization Coordination Agent may receive:

- send_approved_email
- read_relevant_reply
- request_meeting

An agent should only see the tools it requires.

---

## Internal Tools vs External Tools

Hatcommways distinguishes two tool classes.

### Internal Hatcommways Tools

Examples:

- get_project
- get_task_graph
- get_open_responsibilities
- get_actor_capacity
- get_current_timeline
- propose_replanning

These call governed Hatcommways domain services.

They do not require AgentCore Gateway merely because they are agent tools.

### External Tools

Examples:

- calendar
- email
- organization APIs
- external scheduling platform
- future third-party services

These should use AgentCore Identity + Gateway where adopted.

This separation prevents unnecessary routing of internal business data through external integration infrastructure.

---

## Delegated Authorization

External access may occur on behalf of:

- a participant
- project owner
- organization representative
- company representative

Delegation must be explicit and scoped.

Example:

A project owner may authorize Hatcommways to:

- read availability for a selected calendar
- create approved project meetings

That does not authorize Hatcommways to:

- inspect unrelated calendar history
- schedule arbitrary meetings
- share calendar contents with unrelated agents

---

## Organization Delegation

Organization integrations require particular care.

An organization representative must have authority to delegate the requested external capability.

Example:

Employee membership alone does not imply authority to grant:

- company email access
- organization calendar access
- external system access

Hatcommways organization authority checks occur before AgentCore delegated access is used.

---

## Tool-Level Authorization

Permission should be evaluated at the tool/action level.

Example:

Scheduling Agent:

Allowed:

- calendar.read_availability
- calendar.create_project_event if approved

Denied:

- email.send_sponsorship_commitment
- payments.read_instruction

Organization Coordination Agent:

Allowed:

- email.send_approved_message
- meeting.request

Denied:

- calendar.modify_unrelated_event
- payment_instruction.read

Tool availability itself becomes part of agent least privilege.

---

## Pre-Authorized Actions

Some external actions may be executed autonomously only if a human has explicitly granted bounded permission beforehand.

Example:

Project owner authorizes:

> Hatcommways may send routine reminders to accepted participants for this event.

Then the system may allow a notification/email workflow to execute automatically within that scope.

This must not be generalized into permission to send arbitrary messages.

---

## Consequential External Actions

Explicit human approval should remain required for consequential actions such as:

- contacting a new sponsor with a commitment request
- committing an organization
- accepting a contractual or financial obligation
- sending a sensitive public statement
- scheduling an event that participants have not authorized
- changing another person's external calendar without prior authorization

AgentCore Identity/Gateway enables secure access.

It does not eliminate human authority requirements.

---

## External Tool Audit

Every consequential external tool operation should be traceable.

Hatcommways should record at minimum:

- project id
- initiating agent
- initiating user/organization where applicable
- requested external capability
- authorization result
- tool/action
- timestamp
- correlation id
- success/failure state

Do not persist raw secrets in audit logs.

---

## AgentCore Observability

Hatcommways uses AgentCore Observability for infrastructure-level visibility into agent execution.

This complements, but does not replace, Hatcommways audit records.

AgentCore Observability may trace:

- Strands agent runs
- model activity
- tool invocations
- Gateway operations
- errors
- latency
- execution paths

Hatcommways audit remains responsible for product-level meaning such as:

- responsibility accepted
- project plan approved
- organization committed
- timeline changed

Core principle:

> Observability explains how execution occurred.
> Audit explains what product authority/state changed.

---

## Trace Correlation

Hatcommways should propagate correlation identifiers across:

Domain Event
→ Agent Orchestrator
→ Strands Agent Run
→ AgentCore Gateway Tool Call
→ External System
→ Result
→ Domain Event

This allows a project change to be traced back to the reasoning and tool execution that caused it.

Example:

scheduled_event.created
can be connected to:

- approval
- Scheduling Agent run
- calendar tool call
- resulting external calendar event

---

## Privacy in Observability

Observability data must not become a secondary source of sensitive-data leakage.

Avoid placing sensitive values into trace attributes.

Examples that should not be logged in plaintext merely for tracing:

- OAuth tokens
- payment instructions
- private contact credentials
- exact sensitive personal data
- full private message bodies unless explicitly required and protected

Prefer identifiers and safe metadata.

---

## External Access Revocation

If delegated access is revoked:

- future agent access must stop
- cached authorization must expire appropriately
- pending unsafe actions must not execute
- affected workflows should surface the loss of capability

Example:

User revokes calendar access.

Scheduling Agent may continue reasoning from Hatcommways project state but may no longer read or modify that calendar.

---

## Updated Agent Governance Invariants

Add the following invariants:

### Invariant 13

Agents never receive raw external credentials when governed capability access can be used instead.

### Invariant 14

AgentCore Identity does not replace Hatcommways project authorization.

### Invariant 15

AgentCore Gateway tool availability must follow least privilege.

### Invariant 16

External delegated access must be scoped to the user/organization authority that granted it.

### Invariant 17

AgentCore Observability does not replace application-level audit history.

### Invariant 18

Trace data must not expose sensitive secrets or private project information unnecessarily.

---

## Updated Authorization Model

For internal actions:

Identity
+
Canonical Role
+
Project Relationship
+
Organization Authority
+
Requested Action
+
Current State

→

ALLOW
DENY
REQUIRE HUMAN APPROVAL


For governed external actions:

Hatcommways Authorization
+
Human / Organization Delegation
+
Agent Tool Permission
+
AgentCore Identity
+
AgentCore Gateway

→

EXTERNAL ACTION ALLOWED / DENIED

No single layer independently grants complete authority.