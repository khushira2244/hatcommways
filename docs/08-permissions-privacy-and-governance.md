# Hatcommways — Permissions, Privacy, and Governance

## 1. Purpose

This document defines who may:

- view projects
- view exact locations
- join projects
- accept responsibilities
- act for organizations
- see funding state
- see payment instructions
- enable public maps
- expose demographic analytics
- publish sponsor attribution
- change project scope
- approve agent proposals
- cancel or archive projects

Hatcommways contains:

- people
- communities
- organizations
- companies
- responsibilities
- locations
- events
- financial-support information
- demographic aggregations
- autonomous agents

Therefore permissions cannot be an afterthought.

Core principle:

> Agents may coordinate execution, but authority always comes from explicit permissions.

---

# 2. Governance Philosophy

Hatcommways should follow five primary governance principles.

## 2.1 Least Privilege

Every human, organization, service, and agent receives only the access required for its job.

## 2.2 Human Commitment Authority

Agents may suggest commitments.

Agents may not silently commit:

- a person
- a group
- a community
- an organization
- a company

Core rule:

> Agents coordinate commitments.
> Humans make commitments.

## 2.3 Contextual Visibility

A project being public does not mean every field inside it is public.

## 2.4 Sensitive Data Separation

Sensitive data such as:

- payment instructions
- exact private locations
- personal contact information
- private funding totals
- organization-private information

must remain separated from normal public project data.

## 2.5 Auditable Consequential Actions

Major actions should record:

- who performed them
- under what authority
- when
- what changed
- previous state
- resulting state

---

# 3. Identity Types

Hatcommways recognizes several principal identity types.

## 3.1 Participant

An individual Hatcommways user.

## 3.2 Group

A Temporary Group.

## 3.3 Community

A Permanent Community.

## 3.4 Organization

Examples:

- NGO
- welfare group
- school
- nonprofit
- resident organization

## 3.5 Company

A commercial or sponsoring organization.

## 3.6 Organization Representative

A participant authorized to act for an Organization or Company.

## 3.7 Platform Operator

Administrative identity responsible for platform-level operations.

## 3.8 Agent

A governed AI reasoning worker.

## 3.9 Deterministic Service

System software performing explicit, rule-based operations.

---

# 4. Permission Layers

Hatcommways should separate permission decisions into several layers.

## Layer 1 — Platform Permission

Can this identity use this platform capability?

Example:

Can this account create projects?

## Layer 2 — Project Permission

Can this identity perform this action inside this project?

Example:

Can this participant edit project scope?

## Layer 3 — Object Permission

Can this identity access this specific:

- task
- event
- responsibility
- payment instruction
- map
- organization record

## Layer 4 — Field Permission

Can this identity see a specific sensitive field?

Example:

Project is visible.

Funding mode is visible.

Exact achieved amount is not visible.

## Layer 5 — Agent Permission

Can this agent:

- read this data
- use this tool
- produce this proposal
- trigger this safe action

---

# 5. Project Visibility

Initial project visibility modes:

- public
- community_only
- controlled
- invite_only
- private

---

# 6. Public Project

A Public Project may be discoverable through:

- maps
- search
- public project links
- category browsing

Possible public fields:

- project title
- approved description
- category
- approximate location
- approved timeline summary
- open responsibilities
- selected events
- approved maps
- approved organization/sponsor attribution
- public project updates
- completed outcome

Public does not mean all project data is visible.

---

# 7. Community-Only Project

Visible only to:

- members of one or more attached communities
- explicitly authorized project participants
- selected organizations where allowed

Use cases:

- resident community projects
- school communities
- recurring local groups

---

# 8. Controlled Project

The existence of the project may be public, but access or participation is controlled.

Example:

Public can see:

- project title
- purpose
- broad location

But:

- joining requires approval
- detailed tasks require membership
- exact location is hidden

This mode may be common for real-world projects.

---

# 9. Invite-Only Project

Only invited identities may:

- discover
- view
- participate

Public discovery is disabled.

---

# 10. Private Project

Only explicitly authorized users/groups/organizations may access the project.

Private projects still remain subject to platform governance and safety policies.

Private does not mean ungoverned.

---

# 11. Field-Level Visibility

Different project fields require different visibility controls.

Potential fields include:

- title
- description
- approximate location
- exact location
- task graph
- detailed timeline
- actor identities
- open responsibilities
- internal responsibilities
- event locations
- funding mode
- target amount
- achieved amount
- payment instructions
- sponsor information
- participant demographics
- project evidence
- internal communication

Each may inherit project defaults or use more restrictive rules.

---

# 12. Location Privacy

Location must support precision levels.

Possible levels:

- country
- state/region
- city
- neighborhood
- approximate area
- exact location

Example:

Public:

Indiranagar, Bengaluru

Accepted event participants:

Exact event location

The platform must never infer:

public project
=
exact location public

---

# 13. Participant Location

Participant location should be treated carefully.

Action Maps may use:

- approximate area
- aggregated geography
- voluntarily shared project location

They should not expose:

- home address
- continuous location
- precise historical movement
- private coordinates

---

# 14. Responsibility Permissions

Responsibilities involve commitments.

Possible actors allowed to interact:

- project owner
- relevant project admin
- participant
- authorized organization representative
- group/community administrator where appropriate

A responsibility may support:

- view
- request
- offer
- accept
- decline
- withdraw
- transfer
- fulfill

Each action requires authorization.

---

# 15. Accepting Responsibility

Only the identity carrying the responsibility, or an explicitly authorized representative acting within valid authority, may finalize acceptance.

Agents may:

- recommend
- invite
- draft
- explain
- surface the opportunity

Agents may not:

- accept for a user
- promise their time
- claim they agreed when they did not

---

# 16. Responsibility Transfer

Transfer should require:

- current actor authorization where appropriate
- new actor acceptance
- project policy authorization where necessary

Agents may propose a transfer.

They cannot silently move accountability between humans.

---

# 17. Project Owner Permissions

Project Owner may generally:

- review initial AI plan
- approve project plan
- publish project
- control visibility
- manage admins
- approve significant replanning
- approve optional public maps
- approve public sponsor/organization attribution
- pause project
- request project closure
- cancel project where permitted

Project Owner power should still respect:

- organization ownership
- group/community governance
- platform rules
- privacy rights of other participants

---

# 18. Project Admin

Project Owner may delegate administrative capability.

Possible Project Admin actions:

- manage tasks
- manage responsibilities
- coordinate events
- update project status
- manage map visibility
- manage funding-state records
- manage participant access

Certain actions may remain owner-only.

Examples:

- transfer ownership
- delete/archive project
- expose particularly sensitive analytics

---

# 19. Task Owner Permissions

Task Owner may be allowed to:

- update task progress
- report blocker
- coordinate related actors
- submit completion
- request additional actors
- participate in task scheduling

Task Owner should not automatically gain:

- full project admin access
- payment-instruction access
- unrelated private task data

---

# 20. Event Organizer Permissions

Event organizer may access:

- event participants
- event readiness
- relevant task prerequisites
- schedule
- approved event location
- event communication

They should not automatically access:

- project-wide financial details
- unrelated private project data

---

# 21. Group Permissions

Temporary Groups may have roles such as:

- group_owner
- group_admin
- group_member

Group Owner/Admin may:

- invite members
- remove members according to policy
- attach group to projects
- manage group visibility
- approve group-level participation

Group membership must not automatically grant full project admin rights.

---

# 22. Community Permissions

Permanent communities may have:

- community_owner
- community_admin
- community_member

A community may:

- create projects
- attach projects
- participate in projects
- create temporary project groups

Community administrators manage community membership and community-level configuration.

Project permissions remain separate.

---

# 23. Organization Permissions

Organization accounts require internal roles.

Possible organization roles:

- organization_owner
- organization_admin
- organization_representative
- organization_member

Different organization actions require different authority.

---

# 24. Organization Representative Authority

A representative should have explicit scope.

Possible scopes:

- view projects
- join project discussions
- schedule meetings
- propose support
- accept organization responsibility
- approve sponsor attribution
- assign internal participants

Do not assume:

employee_of_company
=
authorized_to_commit_company

---

# 25. Organization Commitment

Consequential organization actions may require:

- representative with appropriate authority
- organization approval workflow
- explicit acceptance

Examples:

- organization accepts project responsibility
- company commits sponsorship
- school agrees to host an event

Agents may coordinate these processes.

They cannot fabricate institutional authority.

---

# 26. Sponsor Permissions

Sponsor/company account may control:

- project support offers
- representatives
- attribution preferences
- private impact dashboard
- meeting requests
- public visibility of selected support

Sponsor should not automatically access private project data merely because it contributes financially.

Project-specific access remains governed.

---

# 27. Sponsor History Privacy

A sponsor's private dashboard may contain:

- all projects it supported
- amounts
- locations
- outcomes
- participation statistics

This should not automatically become public.

Public users may see sponsor information only:

- on projects where attribution is allowed
- through specifically published impact stories
- through explicitly public sponsor data

Core rule:

> Project attribution does not imply public sponsor-history access.

---

# 28. Funding State Permissions

Funding-related information may include:

- funding mode
- target
- achieved amount
- remaining amount
- contribution records
- payment instructions

These should not all share the same visibility.

---

# 29. Funding Mode Visibility

Funding mode may often be safe to expose publicly.

Examples:

- self-funded
- community-funded
- sponsor-supported
- mixed

But project creator may restrict it if desired.

---

# 30. Target and Achieved Amount Permissions

Possible visibility:

- project owner only
- project admins
- members
- attached community
- approved organizations
- public

Default should be conservative.

Do not assume money totals are public.

---

# 31. Payment Instruction Permissions

Payment instructions are sensitive.

Default access:

- project owner
- authorized project admins

Additional access may be granted to:

- approved contributors
- selected community members
- selected organization representatives

Payment instructions must never automatically appear:

- on public project page
- on map
- in public search
- in public API
- in public memory retrieval

---

# 32. Payment Information Audit

Viewing or changing especially sensitive payment information may be audited.

Possible events:

- payment_instruction.created
- payment_instruction.updated
- payment_instruction.viewed_sensitive
- payment_instruction.revoked

The exact audit granularity can be decided during implementation.

---

# 33. Contribution Visibility

A contributor may choose attribution preferences where supported.

Possible options:

- private
- anonymous_public
- group_attributed
- named_on_project

The platform must not expose donor identity merely because a contribution was recorded.

---

# 34. Map Permissions

Each map has independent visibility.

Initial map types:

- Action Map
- Money / Support Map
- Sponsor / Organization Map
- optional analytics maps

Map permission includes:

- whether map is enabled
- who can view it
- what data granularity is used

---

# 35. Action Map Governance

Action Map is foundational but still privacy governed.

It may expose:

- aggregated actor counts
- role types
- project-area participation
- open responsibilities
- community participation

It should not expose:

- exact participant home location
- private participant identity without permission
- sensitive role information unnecessarily

---

# 36. Money Map Governance

Money Map may show:

- area-level support strength
- community-level support
- organization/company participation
- contributor-category distribution

It must not show:

- payment instructions
- account details
- private transaction IDs
- private donor identities
- precise financial location trails

---

# 37. Sponsor / Organization Map Governance

This map may show an organization only when:

- organization/project visibility allows it
- project attribution allows it
- relevant relationship is public

Private organization involvement must remain private.

---

# 38. Optional Analytics Maps

Analytics maps require stronger governance.

Examples:

- age bands
- contributor categories
- community demographics

These should be:

- disabled by default
- creator/admin enabled
- aggregated
- threshold protected

Agents cannot enable them automatically.

---

# 39. Demographic Minimum Thresholds

Do not show a demographic segment when the population is too small.

Example:

Age 60+:
2 participants

Public display should not reveal this as a highly identifiable segment.

Possible strategies:

- hide
- merge
- aggregate
- suppress map

Privacy service should enforce thresholds deterministically.

---

# 40. Public Map Approval

Creator/admin may choose:

- Action Map public
- Support Map community-only
- Sponsor Map public
- Age Map disabled

Each map layer should support independent governance.

---

# 41. Agent Permission Model

Every agent should have an explicit permission profile.

Agent permission profile defines:

- data domains readable
- memory types readable
- tools callable
- proposal types writable
- safe actions allowed
- forbidden actions

Do not give every agent project-admin capability.

---

# 42. Agent Least Privilege

Example:

Actor Theme Agent requires:

- canonical role names
- project theme preference

It does not require:

- funding totals
- payment instructions
- private organization data

Example:

Support State Reasoning Agent requires:

- funding mode
- funding state
- task dependencies on funding

It does not require:

- payment credentials

---

# 43. Agent Read vs Write

Agent read permission and write permission must be separated.

Example:

Replanning Agent may read:

- task graph
- actor graph
- timeline
- blockers

It may write:

- replanning proposal

It should not directly overwrite:

- authoritative task graph
- accepted responsibility
- organization commitment

---

# 44. Proposal Authority

Agents generally create proposals.

Examples:

- task_plan.proposed
- actor_structure.proposed
- replanning.proposed
- scheduling.proposed
- acceleration.proposed

A deterministic service or human approval workflow validates whether the proposal becomes authoritative.

---

# 45. Safe Agent Actions

Some low-risk actions may be autonomous.

Examples:

- generate summary
- detect blocker
- identify parallelization opportunity
- recompute recommendation
- generate memory compaction
- produce Action Map narrative
- prepare notification draft

These actions do not commit humans or expose private data.

---

# 46. Consequential Agent Actions

Examples requiring human or policy approval:

- accepting responsibility
- assigning organization commitment
- publishing project
- changing visibility
- exposing demographic map
- cancelling project
- publishing sponsor attribution
- significantly changing project scope
- sending some external messages on behalf of organization

---

# 47. Scheduling Authority

Scheduling Agent may:

- identify candidate times
- compare availability
- propose a schedule

It may autonomously schedule only where all relevant actors have pre-authorized that behavior.

Otherwise:

propose
→ humans accept
→ schedule persists

---

# 48. Messaging and Email

Hatcommways may coordinate communication.

Possible levels:

## Draft Only

Agent drafts message.

Human sends.

## Approved Template Automation

Agent may send routine messages based on previously approved rules.

## Consequential Communication

Examples:

- sponsor commitment
- organization acceptance
- public statement

requires explicit authorized approval.

---

# 49. External Tool Permissions

Hatcommways distinguishes two tool classes.

## Internal Hatcommways Tools

Examples:

- get_project
- get_task_graph
- get_open_responsibilities
- get_actor_capacity
- get_current_timeline
- propose_replanning

These call governed Hatcommways domain services. They do not require AgentCore Gateway merely because they are agent tools.

## External Tools

Examples include:

- email
- calendar
- organization APIs
- external scheduling systems
- future partner integrations

These are routed through Amazon Bedrock AgentCore Identity and AgentCore Gateway where adopted.

Conceptually:

Strands Agent
→ Hatcommways Agent Permission Check
→ Hatcommways User / Organization Authorization Check
→ AgentCore Identity
→ AgentCore Gateway
→ External Tool / API

Each tool call should enforce:

- agent permission
- user authorization
- project permission
- tool-specific scope

Agent access to a tool does not automatically grant access to all data within that tool.

Core principle:

> Internal authorization is owned by Hatcommways.
> Delegated external access is mediated through AgentCore Identity and Gateway.

AgentCore Identity helps establish:

- which agent/workload is making the request
- which user or organization delegated access
- which external system is being accessed
- what credential/authorization scope is available

Possession of an external credential is not project authorization.

Conceptually:

Hatcommways Permission
+
Delegated External Identity
=
Eligible External Action

Both are required where applicable.

Strands agents must not receive raw third-party credentials in prompts, memory, or unrestricted tool context, including:

- OAuth tokens
- API secrets
- calendar credentials
- email credentials
- organization API keys

Credential handling remains inside the governed identity/integration layer. Agents receive capabilities, not raw secrets.

AgentCore Gateway exposes only selected external capabilities. An agent should see only the tools it requires.

Examples:

Scheduling Agent may receive:

- get_available_calendar_slots
- propose_calendar_event
- create_calendar_event where pre-authorized

Organization Coordination Agent may receive:

- send_approved_email
- read_relevant_reply
- request_meeting

Permission is evaluated at the tool/action level. Tool availability is part of agent least privilege.

External access may occur on behalf of a participant, project owner, organization representative, or company representative. Delegation must be explicit and scoped. Organization membership alone does not imply authority to delegate company email, calendar, or external-system access.

Some external actions may run autonomously only when a human has explicitly granted bounded permission beforehand. Consequential external actions still require explicit human approval, including:

- contacting a new sponsor with a commitment request
- committing an organization
- accepting a contractual or financial obligation
- sending a sensitive public statement
- scheduling an event that participants have not authorized
- changing another person's external calendar without prior authorization

External access revocation must stop future agent access, expire cached authorization appropriately, and prevent pending unsafe actions. The affected agent may continue reasoning from Hatcommways project state without the revoked external capability.

---

# 50. Project Publication

Publishing changes information visibility.

Before publication:

- creator reviews plan
- visibility selected
- public fields determined
- map settings checked
- exact location policy checked
- organization attribution checked

Publication should be explicit.

---

# 51. Scope Change Governance

Minor scope changes may be safe.

Major scope changes require explicit approval.

Examples:

Minor:
rename task

Major:
project expands from 20 participants to 200

Major change may affect:

- timeline
- actors
- funding
- visibility
- events

The Replanning Agent may propose changes.

Authorized human approves.

---

# 52. Project Cancellation

Project cancellation is consequential.

Only authorized roles may cancel.

Potential rules:

- project owner
- authorized organization owner
- platform operator under exceptional policy

Cancellation must:

- preserve history
- notify affected actors
- close/open responsibilities appropriately
- preserve completed outcomes

---

# 53. Participant Removal

Removing another participant may affect:

- responsibilities
- timeline
- groups
- events

It requires appropriate authorization.

A removal should not erase prior execution history.

---

# 54. Blocking and Reporting

Participants may need to:

- block another user
- report abuse
- report harmful project
- report fraudulent support information

These are platform safety capabilities.

They are separate from project execution permissions.

---

# 55. Platform Governance

Platform operators may need capabilities for:

- abuse review
- project restriction
- account restriction
- privacy incidents
- policy enforcement
- security response

Platform admin access should itself be:

- scoped
- audited
- limited

Do not design universal silent superuser access without audit.

---

# 56. Safety Policy Boundary

Hatcommways supports legitimate community execution.

Projects should not be supported when they require prohibited or clearly harmful activity.

Project privacy cannot override platform safety rules.

Possible responses:

- refuse project creation
- restrict public discovery
- require review
- suspend execution
- escalate platform safety review

Detailed safety taxonomy may be documented separately.

---

# 57. Data Classification

Hatcommways should classify data.

## Public

Examples:

- public project title
- approved public map aggregation

## Internal Project

Examples:

- detailed task state
- internal timeline

## Restricted

Examples:

- private funding totals
- participant availability
- internal organization participation

## Sensitive

Examples:

- payment instructions
- exact private location
- contact details

## System Internal

Examples:

- agent traces
- security logs
- permission decisions

Classification should influence storage and API behavior.

---

# 58. Public API Filtering

Public endpoints must never return an object and rely on frontend hiding.

Backend must filter restricted fields.

Example:

Public project API should not include:

payment_instruction

even if frontend does not display it.

Authorization belongs server-side.

---

# 59. Object-Level Authorization

Every object access should be evaluated against:

- identity
- project
- role
- organization
- visibility
- object type
- requested action

Avoid authorization based purely on frontend route.

---

# 60. Multi-Party Projects

Projects may involve:

- creator
- community
- NGO
- sponsor
- school
- temporary group

No single organization should automatically gain ownership of all participant information.

Access is relationship-specific.

---

# 61. Cross-Organization Isolation

Organization A should not automatically see Organization B's:

- internal representatives
- private contribution data
- private communication
- private impact history

Even when both participate in the same project.

Only project-shared information becomes mutually visible.

---

# 62. Community Isolation

Private community information should not leak to unrelated communities merely because they participate in similar projects.

Cross-community memory reuse must use governed abstractions.

---

# 63. Memory Permissions

Memory retrieval must respect current authorization.

An agent should not retrieve:

> sponsor's private history

for a public visitor request.

Semantic search does not bypass authorization.

---

# 64. Historical Access

A participant who leaves a project may lose access to current private data.

However:

- their historical contribution remains
- appropriate public history may remain
- audit history remains

Past membership does not imply indefinite access.

---

# 65. Revocation

Permissions must support revocation.

Examples:

- organization representative removed
- participant removed
- community membership revoked
- payment access revoked
- map visibility disabled

Revocation should take effect promptly.

Cached authorization must not remain indefinitely valid.

---

# 66. Authorization Versioning

Important authorization relationships may have versions or timestamps.

Example:

Representative authorization:

valid_from
valid_until
revoked_at

Agents and tools should verify current authority before consequential execution.

---

# 67. Privacy and Replanning

Replanning Agent may need actor availability.

It should receive:

- availability state necessary for planning

not necessarily:

- full personal calendar
- unrelated personal schedule

Use minimum necessary data.

---

# 68. Privacy and Actor Matching

Actor Fit Agent may use:

- voluntarily shared skills
- allowed location precision
- availability
- prior contribution categories
- community memberships

It should not use hidden sensitive characteristics for matching.

---

# 69. Privacy and Money Maps

Money Map should operate on aggregation.

Pipeline:

Raw contribution records
→ privacy filter
→ aggregation
→ threshold enforcement
→ public map projection

Agents should consume the approved aggregated projection whenever possible.

---

# 70. Privacy and Action Maps

Action Map pipeline:

Responsibility/activity state
→ allowed location precision
→ aggregation
→ identity filtering
→ public/member projection

Exact actor location must not be embedded into public map points unless explicitly appropriate and consented.

---

# 71. Age Analytics Governance

If age-band analytics exist:

- use broad ranges
- require appropriate source/consent
- creator explicitly enables public display
- privacy threshold applies
- no exact ages
- no tiny-group exposure

Do not infer age.

---

# 72. Audit Logging

Consequential actions should emit audit records.

Examples:

- project visibility changed
- responsibility accepted
- organization committed
- sponsor attribution changed
- payment instruction updated
- demographic map enabled
- project cancelled
- agent proposal approved
- permission denied

Audit events should be immutable where practical.

Every consequential external tool operation should record at minimum:

- project id
- initiating agent
- initiating user/organization where applicable
- requested external capability
- authorization result
- tool/action
- timestamp
- correlation id
- success/failure state

Raw secrets must not be persisted in audit logs.

Hatcommways uses AgentCore Observability for infrastructure-level visibility into Strands agent runs, model activity, tool invocations, Gateway operations, errors, latency, and execution paths. This complements, but does not replace, Hatcommways audit records.

Core principle:

> Observability explains how execution occurred.
> Audit explains what product authority/state changed.

Correlation identifiers should propagate across:

Domain Event
→ Agent Orchestrator
→ Strands Agent Run
→ AgentCore Gateway Tool Call
→ External System
→ Result
→ Domain Event

Observability data must not become a secondary source of sensitive-data leakage. Trace attributes should prefer identifiers and safe metadata and must not unnecessarily contain OAuth tokens, payment instructions, private contact credentials, exact sensitive personal data, or full private message bodies.

---

# 73. Audit Actor

Audit record should identify:

- participant
- organization representative
- agent
- deterministic service
- platform operator

Do not record only "system."

---

# 74. Permission Denials

Permission denials should be explicit.

Example:

permission.denied

with:

- requested action
- identity
- resource
- reason code

Avoid leaking sensitive existence details in the error response.

---

# 75. Human Approval Queue

Hatcommways should have an Agent Inbox / Decision Inbox.

Examples:

- accept responsibility?
- approve revised timeline?
- approve organization participation?
- expose Support Map publicly?
- publish sponsor attribution?
- approve event schedule?

The agent handles coordination noise.

Humans receive decisions.

---

# 76. Approval Expiration

Some approval requests may expire.

Example:

Meeting candidate valid until tomorrow.

The approval record may include:

- created_at
- expires_at
- requested action
- current state version

Expired approval must not apply to stale state.

---

# 77. Stale Approval Protection

Example:

User approved Plan v3.

Current project is now Plan v5.

The system must not blindly apply an approval intended for an older plan.

Approvals should reference state versions.

---

# 78. Governance of Themed Roles

Themed names such as:

Captain
Hero
Guardian

must never determine permission.

Authorization uses:

canonical_role

Example:

display:
Captain

canonical:
project_owner

All backend checks use canonical role.

---

# 79. Governance of Groups

A group being responsible for a task does not mean every group member has the same project permission.

Group-level responsibility and individual member authority are separate.

---

# 80. Governance of Organizations

An organization accepting responsibility does not mean every employee/member can act on it.

The organization chooses/authorizes representatives.

---

# 81. Autonomous Agent Boundaries

Agents must never autonomously:

- disclose payment information
- expose exact private locations
- publish demographic maps
- accept human responsibility
- commit organizations
- reveal private sponsor history
- change project privacy
- remove humans from projects
- send consequential financial commitments

without the required authorized workflow.

---

# 82. Deterministic Policy Engine

Hatcommways should have a deterministic authorization/policy layer.

Conceptual input:

- subject
- action
- resource
- project context
- organization context
- visibility
- state

Output:

- allow
- deny
- require_approval

Agents may ask the policy engine.

Agents do not decide final authorization themselves.

---

# 83. Permission Example — Public Visitor

Public visitor opens a project.

Allowed:

- public title
- approved description
- approximate location
- public Action Map
- approved Support Map
- public responsibilities
- public events

Denied:

- private task notes
- exact private location
- payment instructions
- private donor identity
- private sponsor history
- internal project communication

---

# 84. Permission Example — Project Participant

Participant with accepted responsibility may access:

- relevant task details
- required event information
- relevant actor coordination
- member-level project timeline

They do not automatically gain:

- payment instructions
- all sponsor records
- project-admin permissions

---

# 85. Permission Example — Project Admin

Project Admin may:

- manage tasks
- manage maps
- manage participant access
- manage support state

Depending on owner policy they may or may not:

- view payment instructions
- change project ownership
- cancel project

---

# 86. Permission Example — Company Sponsor

Company Representative may see:

- project information granted to sponsor
- its own commitments
- its own meetings
- its own private impact record
- project-approved outcome information

It should not automatically see:

- private participant financial information
- contributions from other sponsors
- unrelated organization communication
- private project-member data

---

# 87. Permission Example — Agent

Replanning Agent may read:

- affected task graph
- actor availability state
- blockers
- timeline
- relevant project conditions

It may write:

- replanning proposal

It may not:

- accept responsibilities
- expose maps
- publish project
- read unrelated payment instructions

---

# 88. Privacy by Projection

Frontend should consume role-specific projections.

Examples:

PublicProjectView

MemberProjectView

AdminProjectView

SponsorProjectView

AgentPlanningView

Do not expose giant internal project objects and rely on clients to interpret permissions.

---

# 89. Privacy Defaults

Hatcommways should use conservative defaults.

Examples:

- exact location hidden
- payment instructions private
- exact contribution amounts restricted
- demographic maps disabled
- sponsor history private
- private organization details restricted

Creators may selectively expand visibility.

---

# 90. Security Principle

Never trade permission correctness for agent convenience.

If an agent lacks enough authorized information:

- it should reason with limited context
- request appropriate access
- ask a human
- or decline the operation

It should not retrieve data merely because it may improve an answer.

---

# 91. Governance Invariants

## Invariant 1

Public project != public everything.

## Invariant 2

Agent recommendation != human authorization.

## Invariant 3

Organization membership != organization commitment authority.

## Invariant 4

Group membership != project-admin permission.

## Invariant 5

Sponsor contribution != access to private project information.

## Invariant 6

Project attribution != public sponsor-history access.

## Invariant 7

Themed role names never determine authorization.

## Invariant 8

Payment instructions are private by default.

## Invariant 9

Optional demographic maps require explicit enablement and safe aggregation.

## Invariant 10

Semantic memory/search must obey the same permissions as transactional reads.

## Invariant 11

Revoked authority must stop future consequential actions.

## Invariant 12

Consequential agent proposals must be checked against current state and authority before application.

## Invariant 13

Agents never receive raw external credentials when governed capability access can be used instead.

## Invariant 14

AgentCore Identity does not replace Hatcommways project authorization.

## Invariant 15

AgentCore Gateway tool availability must follow least privilege.

## Invariant 16

External delegated access must be scoped to the user/organization authority that granted it.

## Invariant 17

AgentCore Observability does not replace application-level audit history.

## Invariant 18

Trace data must not expose sensitive secrets or private project information unnecessarily.

---

# 92. Core Authorization Model

Conceptually:

Identity
+
Canonical Role
+
Project Relationship
+
Organization Authority
+
Object
+
Requested Action
+
Visibility Policy
+
Current State

→

ALLOW
DENY
REQUIRE HUMAN APPROVAL

This decision should be deterministic and auditable.

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

---

# 93. Final Principle

Hatcommways coordinates people, communities, organizations, companies, money-state information, events, and autonomous agents.

That power requires strong boundaries.

The system should always be able to answer:

> Who is asking?
> What are they trying to do?
> On whose behalf?
> What project/object is affected?
> What authority do they currently hold?
> What information is actually necessary?
> Is this safe to perform automatically?
> Does a human need to decide?
> What must be recorded afterward?

Hatcommways should feel effortless to users while remaining strict underneath.

Convenient coordination must never mean invisible loss of control.
