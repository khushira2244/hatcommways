# PATCH — AgentCore Identity, Gateway, and Observability

## Updated External Tool Boundary

Hatcommways distinguishes between:

- internal Hatcommways tools
- external tools and third-party systems

Internal Hatcommways tools remain behind Hatcommways domain services and permission checks.

External tools are routed through AgentCore Identity + AgentCore Gateway.

Conceptually:

Strands Agent
→ Hatcommways Agent Permission Check
→ Hatcommways User / Organization Authorization
→ AgentCore Identity
→ AgentCore Gateway
→ External Tool / API

Examples of external systems:

- calendar
- email
- organization APIs
- external scheduling systems
- future partner integrations

Core principle:

> Hatcommways decides whether an external action is allowed.
> AgentCore provides the governed identity and gateway through which that action is executed.

---

## Updated Agent Tool Boundary

Agents must not receive unrestricted access to backend services or external systems.

There are two tool classes.

### Internal Tools

Examples:

- get_project_context
- get_affected_tasks
- get_dependency_region
- get_actor_capacity
- get_current_timeline
- get_open_responsibilities
- retrieve_similar_blueprints
- propose_replan

These tools call Hatcommways domain services directly through governed internal interfaces.

They enforce:

- project scope
- agent permissions
- field-level filtering
- state versions
- audit

### External Tools

Examples:

- get_calendar_availability
- create_approved_calendar_event
- send_approved_email
- request_external_meeting
- call_partner_api

These tools should be exposed through:

AgentCore Identity
+
AgentCore Gateway

where the integration is managed through AgentCore.

---

## AgentCore Identity Boundary

AgentCore Identity is used to manage governed external access for agents.

It may support:

- agent/workload identity
- delegated user access
- delegated organization access
- third-party credentials
- access tokens
- scoped authorization to external systems

Hatcommways domain authorization remains authoritative for project-level permission.

Example:

Scheduling Agent may have delegated access to a user's calendar.

That does not mean the Scheduling Agent may create arbitrary events.

Hatcommways must first determine:

- whether this project permits the action
- whether the user authorized it
- whether the agent has the required tool permission
- whether human approval is required

Only then may AgentCore Identity be used to access the external capability.

---

## AgentCore Gateway Boundary

AgentCore Gateway is the controlled execution boundary for selected external tools.

Conceptually:

Agent
→ approved capability
→ Gateway
→ external system

Gateway should help prevent agents from directly handling raw integration credentials.

Examples:

Scheduling Agent
→ calendar tools

Organization Coordination Agent
→ email / meeting tools

Future organization integration agents
→ partner APIs

The Gateway does not replace Hatcommways' internal tool router.

Internal domain tools remain inside Hatcommways.

---

## No Direct Agent Credentials

Agents must not contain:

- API keys
- OAuth tokens
- email passwords
- calendar credentials
- partner-system secrets

in:

- prompts
- agent memory
- source code
- normal tool arguments

Credential handling belongs to the governed identity/integration layer.

---

## Updated Integration Layer

The Integration Layer now contains two explicit boundaries.

### Internal Integration Boundary

Connects agents to Hatcommways domain capabilities.

Examples:

- project lookup
- task graph
- responsibilities
- timeline
- maps
- memory

### External Integration Boundary

Connects agents to third-party systems through AgentCore Identity + Gateway.

Examples:

- email
- calendars
- organization systems
- partner APIs

This prevents external credentials and internal domain truth from being mixed.

---

## Updated Agent Runtime Architecture

The agent runtime remains:

Python
+
Strands Agents SDK

The runtime contains:

- agent registry
- context builder
- trigger router
- tool router
- output validation
- retries
- run state
- stale-result protection

When a Strands agent requests an internal tool:

Strands Agent
→ Hatcommways Tool Router
→ Domain Service

When it requests an external tool:

Strands Agent
→ Hatcommways Tool Permission Check
→ AgentCore Identity
→ AgentCore Gateway
→ External System

---

## Updated Agent Write Path

Agent reasoning path:

Domain Event

↓

Agent Orchestrator

↓

Load Authorized Context

↓

Strands Agent

↓

Internal Tools
or
AgentCore-Governed External Tools

↓

Structured Proposal / Tool Result

↓

Proposal Validation

↓

State-Version Validation

↓

Human Approval if Required

↓

Domain Service

↓

Transactional State Change

↓

New Domain Event

Agents still do not write arbitrary database state.

---

## External Action Path

For a consequential external action:

Domain Event / Human Request

↓

Agent Orchestrator

↓

Strands Agent

↓

Hatcommways Permission Check

↓

Human / Organization Delegation Check

↓

AgentCore Identity

↓

AgentCore Gateway

↓

External Tool

↓

External Result

↓

Hatcommways Domain Event / Audit

This path should be traceable end to end.

---

## Example — Calendar Scheduling

Scheduling Agent proposes:

Saturday 10 AM

Creator approves.

Hatcommways verifies:

- project authorization
- participant authorization
- current event version
- calendar delegation

Then:

Scheduling Agent
→ AgentCore Identity
→ AgentCore Gateway
→ Calendar Tool
→ external calendar event created

Hatcommways records:

- external event reference
- project event reference
- correlation id
- result

The external calendar does not become the source of truth for Hatcommways project state.

---

## Example — Organization Email

Project owner requests:

Contact Organization X about hosting an event.

Organization Coordination Agent drafts the message.

If approval is required:

Decision Inbox
→ human approval

Then:

Agent
→ Hatcommways permission check
→ AgentCore Identity
→ AgentCore Gateway
→ Email capability

The sent-message result is recorded.

The agent does not receive raw email credentials.

---

## AgentCore Observability

Hatcommways should use AgentCore Observability for agent-infrastructure tracing.

This should provide visibility into execution paths such as:

Domain Event
→ Agent Run
→ Model Call
→ Tool Call
→ Gateway Action
→ External Result

Useful observability data includes:

- agent run
- model invocation
- tool invocation
- Gateway call
- latency
- errors
- retry
- execution path

---

## Product Audit vs AgentCore Observability

These are different systems.

### Hatcommways Audit

Answers:

- who accepted responsibility?
- who approved this plan?
- why did project visibility change?
- what organization committed?
- what timeline version became authoritative?

### AgentCore Observability

Answers:

- which agent ran?
- what tools did it invoke?
- where did latency occur?
- which external call failed?
- what execution path occurred?

Core principle:

> Audit explains authority and product state.
> Observability explains runtime execution.

Both should exist.

---

## Trace Correlation

A common correlation identifier should connect:

Domain Event
→ Orchestrator Run
→ Strands Agent Run
→ Model Invocation
→ Tool Invocation
→ AgentCore Gateway Call
→ External System Result
→ Resulting Domain Event

This makes Hatcommways agent execution explainable operationally.

Example:

Why was the project meeting created?

Trace:

human approval
→ Scheduling Agent
→ calendar tool
→ Gateway
→ external calendar
→ scheduled_event.created

---

## Sensitive Observability Data

Trace attributes should not contain sensitive values unnecessarily.

Never place raw:

- OAuth tokens
- API keys
- payment credentials
- private account details
- sensitive exact locations

into normal observability attributes.

Prefer:

- resource ids
- project ids
- tool names
- safe reason codes
- correlation ids

---

## Updated Observability Architecture

Hatcommways now has three observability layers.

### Application Observability

Tracks:

- API
- workers
- database
- queues
- application errors

### AgentCore / Agent Observability

Tracks:

- Strands runs
- model calls
- tool calls
- Gateway calls
- latency
- retries
- failures

### Product Execution Observability

Tracks:

- open responsibilities
- blockers
- timeline instability
- project progress
- execution health

These layers serve different purposes.

---

## Updated High-Level Architecture

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

- PostgreSQL
- Object Storage
- Cache
- Event / Audit History
- Map Projections
- Application Observability