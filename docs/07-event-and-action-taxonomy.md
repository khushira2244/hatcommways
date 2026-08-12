# Hatcommways — Event and Action Taxonomy

## 1. Purpose

This document defines the authoritative event and action vocabulary for Hatcommways.

Hatcommways is event-driven.

Projects change because something happens:

- a goal is created
- a plan is approved
- a task becomes ready
- an actor joins
- a responsibility is accepted
- an event is scheduled
- support changes
- a blocker appears
- a project is replanned
- an outcome is completed

These changes must be represented explicitly.

Core principle:

> Events describe what happened.
> Actions describe what someone or something attempted to do.

Events are historical facts.

Actions may succeed, fail, require approval, or create one or more events.

---

# 2. Why Event Taxonomy Matters

The event system powers:

- agent activation
- deterministic state transitions
- timeline recalculation
- task readiness
- actor readiness
- maps
- notifications
- project memory
- auditability
- retries
- replanning
- analytics

Agents should not wake up because of vague polling.

They should react to relevant events.

---

# 3. Event Naming Convention

Use:

domain.event_name

Examples:

project.created

task.completed

responsibility.accepted

actor.unavailable

support.updated

event.rescheduled

blocker.created

timeline.recalculated

Names should:

- describe completed facts
- use past-tense or settled-state semantics
- remain stable
- not embed UI wording
- not depend on actor themes

Example:

Correct:

responsibility.accepted

Wrong:

hero_joined_mission

The UI may call the actor "Hero", but the internal event remains canonical.

---

# 4. Event Envelope

Every event should conceptually contain:

- event_id
- event_type
- project_id
- occurred_at
- actor_reference where applicable
- organization_reference where applicable
- source_type
- source_id
- correlation_id
- causation_id
- project_version
- payload
- visibility_scope
- audit_metadata

Optional:

- task_id
- responsibility_id
- event_id_reference
- community_id
- group_id
- organization_id

Events should be append-only.

---

# 5. Event Source Types

Possible event sources:

- human
- organization
- agent
- deterministic_service
- external_integration
- scheduled_system_job

Source must be explicit.

Example:

task.completed

source_type:
human

or:

timeline.recalculated

source_type:
deterministic_service

---

# 6. Correlation and Causation

Events should support causal tracking.

Example:

responsibility.accepted

causes:

actor_readiness.recalculated

which causes:

task.execution_ready

which causes:

timeline.recalculated

All of these may share a correlation id.

This allows Hatcommways to explain:

> Why did this timeline change?

---

# 7. Action Model

Actions represent requested operations.

Examples:

- create project
- approve plan
- accept responsibility
- update availability
- create event
- update support
- withdraw from responsibility
- revise project scope

Conceptually:

Action Request
→ validation
→ authorization
→ execution
→ Event(s)

Actions may originate from:

- humans
- organizations
- agents
- system workflows

---

# 8. Human Commitment Actions

The following actions always require an authorized human or organization representative:

- accept responsibility
- withdraw responsibility
- publish project
- commit organization participation
- approve major scope change
- cancel project
- expose optional public maps
- approve public sponsor attribution

Agents may propose them.

Agents may not silently perform them for humans.

---

# 9. Project Lifecycle Events

Core project events:

- project.created
- project.context_updated
- project.plan_requested
- project.plan_created
- project.plan_revised
- project.plan_approved
- project.published
- project.activated
- project.paused
- project.resumed
- project.scope_changed
- project.completing
- project.completed
- project.cancelled
- project.archived

---

# 10. project.created

Meaning:

A new project container has been created from a user/community/organization goal.

Potential producers:

- project service

Potential agent triggers:

- Goal Understanding Agent
- Project Scope Agent

State effects:

- create project record
- create initial version
- persist creation context

---

# 11. project.context_updated

Meaning:

Creator-added planning context changed.

Examples:

- location updated
- timeframe updated
- funding mode updated
- known context added

Potential triggers:

- Goal Understanding Agent
- Project Scope Agent
- Task Decomposition Agent where material

Do not replan every time trivial text changes.

---

# 12. project.plan_created

Meaning:

An initial structured project plan exists.

May include:

- tasks
- dependencies
- actor structure
- initial timeline

Potential triggers:

- creator review workflow
- Project Memory Agent

---

# 13. project.plan_approved

Meaning:

Authorized creator/admin accepted the current project plan for execution.

Potential triggers:

- publication readiness
- responsibility opening
- timeline activation
- map initialization
- Project Memory Agent

---

# 14. project.published

Meaning:

Project became discoverable according to visibility rules.

Potential triggers:

- project discovery indexing
- Action Map initialization
- open responsibility publication
- notification workflows

---

# 15. project.scope_changed

Meaning:

The intended execution scope materially changed.

Examples:

20 shelters → 35 shelters

one-day event → three-day event

Potential triggers:

- Task Decomposition Agent
- Dependency Reasoning Agent
- Actor Requirement Agent
- Actor Capacity Agent
- Timeline Planning Agent
- Replanning Agent
- Project Memory Agent

This is a major event.

---

# 16. Goal Events

Goal events:

- goal.created
- goal.clarified
- goal.updated
- goal.reframed
- goal.completed
- goal.partially_completed

Goal changes should preserve previous goal versions.

---

# 17. Task Events

Core task events:

- task.proposed
- task.created
- task.updated
- task.split
- task.merged
- task.removed
- task.ready
- task.execution_ready
- task.started
- task.progress_updated
- task.blocked
- task.unblocked
- task.completed
- task.reopened
- task.cancelled
- task.superseded

---

# 18. task.created

Meaning:

A new authoritative task exists.

Potential triggers:

- Dependency Reasoning Agent
- Actor Requirement Agent
- Timeline Planning Agent

Potential deterministic reactions:

- task graph version increment
- readiness recomputation

---

# 19. task.ready

Meaning:

Task dependencies are satisfied.

This means:

logical_ready = true

It does not necessarily mean execution can start.

Potential triggers:

- Responsibility Intelligence Agent
- Scheduling Agent
- Acceleration Agent

---

# 20. task.execution_ready

Meaning:

Required execution conditions are satisfied.

Possible conditions:

- logical readiness
- responsibility coverage
- actor availability
- required approval
- support state where applicable
- event prerequisites

Potential triggers:

- Scheduling Agent
- Coordination workflows
- notifications

---

# 21. task.started

Meaning:

Task execution has begun.

State effects:

- actual_start_at
- active responsibility association
- execution history

Potential triggers:

- Participation and Action Intelligence Agent
- Project Memory Agent

---

# 22. task.progress_updated

Meaning:

Material progress changed.

Do not emit for every tiny UI interaction.

Potential payload:

- previous_progress
- current_progress
- note
- evidence_reference

Potential triggers:

- blocker analysis if progress stalls
- map/activity updates

---

# 23. task.blocked

Meaning:

Task cannot continue under current conditions.

Potential triggers:

- Blocker Detection Agent
- Replanning Agent
- Project Memory Agent

The whole project must not automatically pause.

---

# 24. task.completed

Meaning:

Required work for the task has completed.

Potential deterministic reactions:

- satisfy downstream dependencies
- recalculate readiness
- update timeline

Potential agent triggers:

- Parallelization Agent
- Acceleration Agent
- Participation Intelligence Agent
- Project Memory Agent

Multiple downstream tasks may become ready simultaneously.

---

# 25. Dependency Events

Core dependency events:

- dependency.proposed
- dependency.created
- dependency.updated
- dependency.satisfied
- dependency.invalidated
- dependency.removed
- dependency.conflict_detected

---

# 26. dependency.satisfied

Meaning:

A dependency condition is now satisfied.

Potential deterministic reactions:

- recalculate affected task readiness

Potential outcome:

one or many task.ready events

This should usually be deterministic.

---

# 27. dependency.invalidated

Meaning:

A previously satisfied or valid prerequisite is no longer valid.

Example:

required event cancelled

approval revoked

Potential triggers:

- Blocker Detection Agent
- Replanning Agent

---

# 28. Actor Events

Actor-related events:

- actor.joined_project
- actor.left_project
- actor.available
- actor.partially_available
- actor.unavailable
- actor.capacity_changed
- actor.role_interest_added
- actor.role_interest_removed

Actor does not necessarily mean responsibility owner.

---

# 29. actor.joined_project

Meaning:

A participant/organization has joined the project context.

This alone does not assign responsibility.

Potential triggers:

- Actor Fit Agent
- Participation Intelligence Agent

---

# 30. actor.available

Meaning:

Actor availability relevant to execution became available.

Potential triggers:

- Parallelization Agent
- Acceleration Agent
- Scheduling Agent
- Responsibility Intelligence Agent

Availability must include appropriate validity/time scope.

---

# 31. actor.unavailable

Meaning:

Actor cannot currently execute expected responsibilities.

Potential triggers:

- Blocker Detection Agent
- Replanning Agent
- Scheduling Agent

Accepted responsibility may remain accepted.

---

# 32. actor.capacity_changed

Meaning:

Execution capacity materially changed.

Examples:

- available hours increased
- team size changed
- organization provides additional people

Potential triggers:

- Actor Capacity Agent
- Parallelization Agent
- Acceleration Agent

---

# 33. Actor Role Events

Role-definition events:

- actor_role.proposed
- actor_role.created
- actor_role.updated
- actor_role.specialized
- actor_role.capacity_changed
- actor_role.removed
- actor_role.theme_changed

Role events affect project structure, not commitments.

---

# 34. actor_role.created

Meaning:

Project now requires a particular canonical role.

Example:

canonical_role:
coordinator

required_count:
2

Potential triggers:

- Responsibility generation
- Actor Fit Agent

---

# 35. actor_role.capacity_changed

Meaning:

The number of required actors for a role changed.

Example:

1 coordinator → 3 coordinators

Potential triggers:

- Responsibility Intelligence Agent
- Actor Fit Agent
- Timeline reasoning

---

# 36. Responsibility Events

Core responsibility events:

- responsibility.opened
- responsibility.offered
- responsibility.requested
- responsibility.accepted
- responsibility.activated
- responsibility.paused
- responsibility.fulfilled
- responsibility.declined
- responsibility.withdrawn
- responsibility.handoff_requested
- responsibility.transferred
- responsibility.reopened
- responsibility.cancelled

---

# 37. responsibility.opened

Meaning:

A project requires an actor to carry this responsibility and it is currently vacant.

Potential triggers:

- Actor Fit Agent
- public responsibility discovery
- project notifications

---

# 38. responsibility.requested

Meaning:

A participant asks to take an open responsibility.

This is not yet acceptance when project approval is required.

Possible next events:

- responsibility.accepted
- responsibility.declined

---

# 39. responsibility.accepted

Meaning:

An authorized human/organization has accepted accountability.

Potential deterministic reactions:

- update responsibility counts
- actor readiness recomputation
- task execution-readiness recomputation

Potential agent triggers:

- Parallelization Agent
- Acceleration Agent
- Responsibility Intelligence Agent
- Participation Intelligence Agent
- Project Memory Agent

This is one of the most important Hatcommways events.

---

# 40. responsibility.withdrawn

Meaning:

Actor voluntarily leaves a responsibility.

Potential reactions:

- create vacancy
- actor readiness changes
- affected task may lose execution readiness

Potential triggers:

- Blocker Detection Agent
- Replanning Agent
- Actor Fit Agent
- Project Memory Agent

History must remain.

---

# 41. responsibility.transferred

Meaning:

Responsibility moved from one actor to another through an authorized handoff.

Payload should preserve:

- previous_actor
- new_actor
- transfer_time
- reason where supplied

Potential triggers:

- timeline recalculation
- memory update

---

# 42. Group Events

Temporary/permanent group events:

- group.created
- group.member_joined
- group.member_left
- group.attached_to_project
- group.detached_from_project
- group.archived
- group.conversion_proposed
- group.converted_to_community

Conversion requires human approval.

---

# 43. Community Events

Permanent community events:

- community.created
- community.member_joined
- community.member_left
- community.project_attached
- community.project_completed
- community.visibility_changed

Potential triggers:

- Community and Group Structure Agent
- participation/map updates

---

# 44. Organization Events

Organization events:

- organization.joined_project
- organization.left_project
- organization.representative_added
- organization.representative_removed
- organization.role_accepted
- organization.support_offered
- organization.support_withdrawn
- organization.event_hosting_confirmed

---

# 45. organization.joined_project

Meaning:

An organization formally joins project participation.

Potential triggers:

- Organization Participation Agent
- Actor Requirement Agent where role topology changes
- Sponsor/Organization Map update
- Project Memory Agent

---

# 46. organization.support_offered

Meaning:

Organization has stated an offer of support.

This does not necessarily mean money.

Possible support:

- people
- venue
- expertise
- equipment
- sponsorship
- service

The offer must be interpreted before execution state changes.

Potential trigger:

- Organization Participation Agent

---

# 47. Support / Funding Events

Core support events:

- support.mode_selected
- support.target_set
- support.target_updated
- support.contribution_reported
- support.contribution_confirmed_by_project
- support.contribution_cancelled
- support.state_changed
- support.sufficient
- support.insufficient
- support.completed

Hatcommways does not process payment itself.

---

# 48. support.contribution_reported

Meaning:

A contribution was entered/reported.

It is not independently verified by Hatcommways.

Potential state:

reported

Potential next event:

support.contribution_confirmed_by_project

---

# 49. support.contribution_confirmed_by_project

Meaning:

Authorized project actor manually confirmed the contribution for project purposes.

Important:

This must never be described as externally verified payment.

Potential triggers:

- Support State Reasoning Agent
- Money Map aggregation
- Project Memory Agent

---

# 50. support.state_changed

Meaning:

Project financial-support execution state materially changed.

Potential states:

- not_required
- being_arranged
- partially_ready
- sufficient
- insufficient
- blocked
- completed

Potential triggers:

- Support State Reasoning Agent
- affected task readiness recomputation
- Replanning Agent if execution changes

---

# 51. Event/Meeting Events

Because "Event" is also a product entity, use execution_event.* or scheduled_event.* if implementation naming becomes ambiguous.

Conceptually:

- scheduled_event.proposed
- scheduled_event.created
- scheduled_event.scheduling_started
- scheduled_event.scheduled
- scheduled_event.participant_confirmed
- scheduled_event.ready
- scheduled_event.started
- scheduled_event.completed
- scheduled_event.postponed
- scheduled_event.rescheduled
- scheduled_event.cancelled

---

# 52. scheduled_event.proposed

Meaning:

A time-bound activity has been proposed.

Potential triggers:

- Event Planning Agent
- Scheduling Agent

---

# 53. scheduled_event.scheduled

Meaning:

An approved date/time exists.

This does not guarantee execution readiness.

Potential deterministic reactions:

- update timeline

Potential triggers:

- Scheduling Agent
- notifications

---

# 54. scheduled_event.ready

Meaning:

Required event prerequisites are satisfied.

Potential prerequisites:

- organizer
- minimum participants
- required tasks
- location
- organization confirmation

---

# 55. scheduled_event.rescheduled

Meaning:

Event date/time materially changed.

Potential triggers:

- Scheduling Agent
- Replanning Agent
- Project Memory Agent

Potential effects:

- participant availability invalidated
- downstream tasks shifted
- notifications emitted

---

# 56. scheduled_event.cancelled

Meaning:

Event will not occur under current plan.

Potential triggers:

- Blocker Detection Agent
- Replanning Agent
- Project Memory Agent

Cancellation should not automatically cancel the project.

---

# 57. Blocker Events

Core blocker events:

- blocker.detected
- blocker.created
- blocker.updated
- blocker.escalated
- blocker.resolution_proposed
- blocker.resolved
- blocker.dismissed

---

# 58. blocker.created

Meaning:

A validated execution blocker exists.

Payload may contain:

- affected scope
- blocker type
- severity
- impacted tasks
- impacted responsibilities
- detected source

Potential triggers:

- Replanning Agent
- Project Memory Agent

---

# 59. blocker.resolved

Meaning:

The blocker condition no longer prevents execution.

Potential reactions:

- task readiness recomputation
- timeline recalculation
- previously blocked branch restart

Potential triggers:

- Acceleration Agent
- Project Memory Agent

---

# 60. Timeline Events

Timeline events:

- timeline.initialized
- timeline.recalculation_requested
- timeline.recalculated
- timeline.compressed
- timeline.expanded
- timeline.branch_shifted
- timeline.stale_detected

---

# 61. timeline.recalculated

Meaning:

Authoritative expected execution timeline changed.

Payload should include:

- prior_timeline_version
- new_timeline_version
- affected_tasks
- expected_completion_before
- expected_completion_after
- reason
- source_event_ids

Potential triggers:

- Project Memory Agent
- relevant notifications
- project UI refresh

---

# 62. timeline.compressed

Meaning:

Expected completion moved earlier because execution improved.

Example reasons:

- new actors
- parallelization
- early task completion

Potential trigger:

- Acceleration Agent narrative
- project update

---

# 63. timeline.expanded

Meaning:

Expected completion moved later.

Potential reasons:

- actor withdrawal
- task delay
- event reschedule
- blocker

This is not necessarily project failure.

---

# 64. Parallelization Events

Potential events:

- parallelization.opportunity_detected
- parallelization.proposed
- parallelization.applied
- parallelization.removed
- actor_contention.detected
- actor_contention.resolved

---

# 65. parallelization.opportunity_detected

Meaning:

Current project state may allow additional concurrent work.

Producer:

- Parallelization Agent
- Acceleration Agent

Potential next step:

- deterministic validation
- plan update
- timeline recalculation

---

# 66. actor_contention.detected

Meaning:

Multiple independent tasks depend on the same execution actor/capacity.

Potential triggers:

- Actor Capacity Agent
- Parallelization Agent
- Replanning Agent

---

# 67. Replanning Events

Core events:

- replanning.requested
- replanning.started
- replanning.proposed
- replanning.approved
- replanning.applied
- replanning.rejected
- replanning.failed

Affected execution-region events:

- execution_region.calculated
- execution_region.expanded
- execution_region.invalidated

`execution_region.calculated` means the deterministic affected-subgraph calculation completed for a source change.

`execution_region.expanded` means validation discovered a broader dependency, shared capacity constraint, or project-wide consequence requiring more of the graph to be included.

`execution_region.invalidated` means a previously calculated region is no longer safe to use because relevant state changed.

---

# 68. replanning.requested

Possible producers:

- blocker
- project scope change
- actor withdrawal
- event cancellation
- support-state change
- timeline risk

Potential trigger:

- Replanning Agent

---

# 69. replanning.proposed

Meaning:

Agent generated a structured alternative plan.

Payload should reference:

- source plan version
- affected region
- proposed changes
- expected timeline impact
- actor changes
- reason
- confidence

Proposal is not authoritative state yet.

---

# 70. replanning.applied

Meaning:

Validated/authorized plan revision became authoritative.

Potential effects:

- new plan version
- new timeline
- new responsibilities
- changed dependencies

Potential triggers:

- Project Memory Agent
- relevant execution agents

---

# 71. Acceleration Events

Potential events:

- acceleration.opportunity_detected
- acceleration.proposed
- acceleration.applied
- acceleration.dismissed

Acceleration differs from disruption-driven replanning.

---

# 72. Map Events

Maps are derived views, but events may describe meaningful updates.

Examples:

- action_map.updated
- support_map.updated
- organization_map.updated
- map.visibility_changed
- analytics_map.enabled
- analytics_map.disabled

These should generally be emitted by deterministic map services.

---

# 73. map.visibility_changed

Meaning:

Authorized creator/admin changed who can see a map.

Potential payload:

- map_type
- previous_visibility
- new_visibility

Potential trigger:

- public cache invalidation
- Project Memory Agent if material

---

# 74. analytics_map.enabled

Examples:

- age distribution enabled
- community distribution enabled

Human approval is required.

Agents must not enable demographic maps automatically.

---

# 75. Participation Intelligence Events

Possible agent-generated events:

- participation.weak_area_detected
- participation.role_gap_detected
- participation.strong_area_detected
- participation.summary_generated

These are interpretations.

They must not be treated as deterministic execution truth.

---

# 76. Support Intelligence Events

Possible interpretation events:

- support.pattern_detected
- support.community_strength_detected
- organization.participation_summary_generated

Again:

interpretation != authoritative financial state

---

# 77. Memory Events

Memory events:

- memory.project_entry_created
- memory.project_summary_created
- memory.compacted
- memory.pattern_created
- memory.pattern_updated
- memory.failure_recorded
- memory.lesson_recorded
- memory.blueprint_created
- execution_memory.recorded
- failure_memory.recorded
- blueprint_memory.created
- memory.reuse_evaluated
- memory.reuse_applied
- memory.reuse_rejected

`memory.reuse_evaluated` records that historical memory was assessed for the current context. It does not mean that the memory was applied.

`memory.reuse_applied` records that an applicable memory reference influenced a validated proposal or decision.

`memory.reuse_rejected` records that a candidate memory was not used because it was inapplicable, unauthorized, stale, low-confidence, or contradicted by current state.

---

# 78. memory.project_entry_created

Meaning:

A new durable structured memory entry was created with provenance.

Potential producer:

- Project Memory Agent

The raw source events remain authoritative.

---

# 79. memory.compacted

Meaning:

Many low-level historical events were summarized into a structured memory object.

Raw events must remain intact.

---

# 80. Outcome Events

Outcome events:

- outcome.recording_started
- outcome.recorded
- outcome.partially_achieved
- outcome.verified
- blueprint.generated
- appreciation.generated
- appreciation.approved
- appreciation.sent

---

# 81. outcome.recorded

Meaning:

Project's actual outcome has been structurally captured.

Potential triggers:

- Outcome and Blueprint Agent
- private/public impact computation
- project completion workflow

---

# 82. blueprint.generated

Meaning:

A privacy-safe reusable execution blueprint has been produced.

Blueprint generation must not expose:

- private participant data
- private payment information
- private organization data

---

# 83. Appreciation Events

Possible events:

- appreciation.draft_generated
- appreciation.approved
- appreciation.sent

AI may generate drafts.

Authorized humans approve outbound communication where needed.

---

# 84. Notification Events

Notification infrastructure may consume many events.

Examples:

responsibility.opened
→ notify suitable interested users

responsibility.accepted
→ notify task owner

scheduled_event.rescheduled
→ notify affected participants

blocker.created
→ notify responsible actors

Notifications should not themselves drive authoritative execution state unless an explicit user action follows.

---

# 85. Audit Events

Every consequential action should be auditable.

Examples:

- permission.denied
- action.rejected
- stale_result.rejected
- agent_run.started
- agent_run.completed
- agent_run.failed
- agent_run.retried
- human_approval.requested
- human_approval.granted
- human_approval.denied

---

# 86. stale_result.rejected

Meaning:

An agent result was not applied because it was based on obsolete state.

Payload:

- agent_run_id
- expected_version
- current_version
- affected_domain

Potential next action:

rerun relevant agent

---

# 87. Agent Run Events

Operational events:

- agent_run.requested
- agent_run.started
- agent_run.completed
- agent_run.failed
- agent_run.retry_scheduled
- agent_run.exhausted
- agent_run.cancelled

Bounded agent-graph events:

- agent_graph.requested
- agent_graph.started
- agent_graph.completed
- agent_graph.failed

These events describe one bounded Strands Graph reasoning episode. They should reference the graph run id, source event, affected execution region, participating agents, and source state versions.

Evaluation events:

- evaluation.started
- evaluation.completed
- evaluation.failed

Evaluation events are operational and belong to the evaluation harness. They do not represent project-domain changes.

These are operational, not public project events.

---

# 88. External Tool and AgentCore Operational Events

External tool events describe the lifecycle of governed third-party capability execution requested by a Strands agent.

Core events:

- external_tool.requested
- external_tool.authorized
- external_tool.denied
- external_tool.started
- external_tool.completed
- external_tool.failed
- external_tool.cancelled

## external_tool.requested

Meaning:

A Strands agent requested use of an external capability. This does not mean the action is authorized or executed.

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

## external_tool.authorized

Meaning:

Hatcommways authorization and required delegated identity checks succeeded. The request is eligible to continue to AgentCore Gateway.

Authorization may include:

- agent tool permission
- project permission
- user delegation
- organization authority
- current-state validation
- approval state

## external_tool.denied

Meaning:

The requested external capability was not authorized.

Possible reasons include an unauthorized agent, insufficient participant or representative authority, missing/revoked delegation, missing human approval, changed project state, or unavailable capability. The event should contain a safe reason code without exposing sensitive security details.

## external_tool.started

Meaning:

The authorized external operation began through AgentCore Gateway or the governed external integration layer. This is operational state, not domain truth.

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

A successful external operation does not automatically mean Hatcommways domain state changed. Relevant domain services must process the result.

## external_tool.failed

Meaning:

The external operation failed because of conditions such as provider unavailability, expired delegated access, Gateway failure, external API rejection, timeout, or tool validation failure.

Potential reactions include bounded retry, human decision, manual fallback, or continuing unaffected project branches. External-tool failure must not automatically stop the project.

## external_tool.cancelled

Meaning:

A pending or in-progress external operation was intentionally cancelled because of human cancellation, changed project state, staleness, pause, or project cancellation.

## External Identity Events

Core events:

- external_identity.connected
- external_identity.updated
- external_identity.revoked
- external_identity.expired

These events describe delegated external-access availability and never expose credentials.

`external_identity.connected` means a participant or authorized organization representative established delegated access. Tool availability must still be checked at runtime.

`external_identity.revoked` means delegated access was revoked. Future capabilities must be removed, cached authorization invalidated, and pending unsafe operations stopped. The project continues.

`external_identity.expired` is handled similarly for future calls and may surface a reconnection request.

## Gateway Events

Optional internal operational events:

- gateway.request_started
- gateway.request_completed
- gateway.request_failed

These support observability, debugging, retries, and latency analysis. They do not normally appear in public or project feeds.

## Trace Correlation Event

`agent_trace.correlated` means a Hatcommways domain/action record has been associated with an agent/runtime trace.

Possible payload:

- project_id
- source_event_id
- agent_run_id
- correlation_id
- trace_reference

It must not contain raw model reasoning or sensitive tool data.

## Updated Agent Run Metadata

Agent-run events may include:

- correlation_id
- trace_reference
- external_tool_count
- gateway_call_count

## External Action Flow

Agent decides an external capability may be useful
→ external_tool.requested
→ Hatcommways authorization
→ external_tool.denied

or, if approved:

external_tool.authorized
→ AgentCore Identity
→ AgentCore Gateway
→ external_tool.started
→ External System
→ external_tool.completed / external_tool.failed
→ Hatcommways Domain Service
→ relevant domain event

The external-tool event and product-domain event remain separate.

External tool and AgentCore events are system-internal by default. Users should see meaningful product outcomes rather than raw Gateway or runtime events.

## Operational vs Domain Events

Operational events such as `agent_run.started`, `external_tool.started`, `gateway.request_failed`, and `agent_trace.correlated` explain how the system executed.

Domain events such as `responsibility.accepted`, `task.completed`, `scheduled_event.scheduled`, `organization.joined_project`, and `timeline.recalculated` describe Hatcommways product reality.

Operational events must not be mistaken for domain state.

---

# 89. Agent Trigger Matrix

Initial high-level mapping:

## Goal Understanding Agent

Triggers:

- project.created
- goal.created
- goal.updated
- project.context_updated

## Project Scope Agent

Triggers:

- goal.clarified
- project.scope_changed

## Task Decomposition Agent

Triggers:

- goal.structured
- project.scope_changed

## Dependency Reasoning Agent

Triggers:

- task batch created
- task split
- task merged
- scope change

## Timeline Planning Agent

Triggers:

- dependency graph created
- project plan requested
- significant scope change

## Parallelization Agent

Triggers:

- dependency graph changed
- responsibility.accepted
- actor.available
- actor.capacity_changed
- task.completed
- actor_contention.resolved

## Actor Requirement Agent

Triggers:

- task graph created
- project scope changed
- event added

## Actor Capacity Agent

Triggers:

- actor roles created
- project scale changed
- participation scale changed

## Role Specialization Agent

Triggers:

- actor requirements created
- niche execution requirement discovered

## Actor Theme Agent

Triggers:

- creator requests theme
- theme changed

## Actor Fit Agent

Triggers:

- responsibility.opened
- actor availability changed
- organization joined

## Responsibility Intelligence Agent

Triggers:

- responsibility.opened
- responsibility.accepted
- responsibility.withdrawn
- actor capacity changed

## Community and Group Structure Agent

Triggers:

- project created
- group created
- project participation grows
- project completes

## Organization Participation Agent

Triggers:

- organization joined
- organization support offered
- organization role requested

## Scheduling Agent

Triggers:

- task.execution_ready
- scheduled_event.proposed
- availability changed
- event rescheduled

## Event Planning Agent

Triggers:

- project plan created
- event requested
- task converted to event

## Blocker Detection Agent

Triggers:

- task blocked
- actor unavailable
- responsibility withdrawn
- support insufficient
- event cancelled
- timeline risk detected

## Replanning Agent

Triggers:

- blocker.created
- project.scope_changed
- actor.withdrawn
- scheduled_event.cancelled
- support state materially changed

## Acceleration Agent

Triggers:

- actor joined
- responsibility accepted
- task completed early
- blocker resolved
- actor contention resolved

## Support State Reasoning Agent

Triggers:

- support.state_changed
- support contribution confirmed
- project support mode changed

## Participation and Action Intelligence Agent

Triggers:

- responsibility accepted
- responsibility fulfilled
- actor joined
- group/community participation changed

## Support and Organization Intelligence Agent

Triggers:

- support contribution confirmed
- organization joined
- sponsor visibility changed

## Project Memory Agent

Triggers:

- major project transitions
- plan revisions
- blockers/resolutions
- important responsibility changes
- event completion

## Outcome and Blueprint Agent

Triggers:

- project.completing
- project.completed
- outcome.recorded

---

# 90. Events That Should Stay Deterministic

These should generally be produced from deterministic services rather than LLM reasoning:

- dependency.satisfied
- responsibility count changed
- task readiness changed
- actor vacancy count changed
- map aggregation updated
- funding totals changed
- authorization result
- state version increment
- timeline persisted
- duplicate event rejected

Agents may reason about implications.

They should not invent these facts.

---

# 91. Agent Proposal Events

When an agent proposes something but has not changed system truth, use proposal semantics.

Examples:

- task_plan.proposed
- dependency_plan.proposed
- actor_structure.proposed
- replanning.proposed
- acceleration.proposed
- event_schedule.proposed

The bounded proposal lifecycle may use:

- proposal.generated
- proposal.merged
- proposal.accepted
- proposal.rejected
- proposal.stale

`proposal.generated` records a schema-defined agent result.

`proposal.merged` records that compatible proposals were combined while preserving provenance.

`proposal.accepted` means the proposal passed the applicable validation and approval boundary. Authoritative state changes only when the domain service completes its transaction.

`proposal.rejected` means validation, permission, conflict resolution, or human review rejected it.

`proposal.stale` means its source state versions no longer match current authoritative state and it cannot silently apply.

Never emit:

task.created

when an agent merely suggested a task that has not been accepted/persisted.

---

# 92. Human Approval Events

Potential lifecycle:

human_approval.requested
→ human_approval.granted
or
→ human_approval.denied

Approval payload should identify:

- requested action
- requesting agent/workflow
- affected project object
- summary
- expiration where relevant

---

# 93. Public vs Internal Events

Events should have visibility.

Examples:

Public-safe:

- project.published
- scheduled_event.scheduled
- project.completed

Project-internal:

- responsibility.accepted
- task.blocked

System-internal:

- stale_result.rejected
- agent_run.failed
- memory.compacted

Do not expose internal orchestration events directly in public feeds.

---

# 94. Event Replay

Because execution history is event-driven, the architecture should eventually support replay where practical.

Replay can help:

- rebuild derived projections
- reconstruct map state
- debug timeline changes
- audit project history

However, current transactional state remains authoritative for normal runtime reads.

---

# 95. Duplicate Event Handling

Every event should have stable event id.

Consumers should protect against duplicate processing.

Example:

responsibility.accepted

processed twice

must not produce:

two responsibility owners
two map increments
two notifications representing separate commitments

Idempotency is mandatory.

---

# 96. Event Ordering

Events may arrive close together.

The system should not assume globally perfect ordering.

Use:

- entity versions
- occurred_at
- processed_at
- causation id
- project version

where needed.

Example:

actor.unavailable

may arrive while a timeline agent is running.

Version checks prevent stale application.

---

# 97. Concurrency Example

Current state:

Task A and B independent.

Actor 1 owns A.

Responsibility for B is open.

Events:

responsibility.accepted for Actor 2
task.completed for Task A

arrive almost together.

Independent reactions may include:

- downstream dependency update from A
- B actor readiness update
- Parallelization Agent
- Acceleration Agent
- timeline recalculation

The system should allow these reactions to converge safely through state versioning.

---

# 98. Event Fan-Out

One event may produce many reactions.

Example:

responsibility.accepted

Potential fan-out:

- responsibility projection update
- task readiness update
- Action Map update
- timeline check
- Acceleration Agent
- Project Memory Agent
- notifications

This is expected.

Do not serialize all consumers unnecessarily.

---

# 99. Event Storm Protection

Large projects may generate many events.

The system should support:

- debounce where appropriate
- event aggregation
- affected-region recalculation
- bounded agent invocation
- deduplication

Example:

20 participants update availability within one minute.

Do not necessarily run the full Timeline Agent 20 times.

A short aggregation window may produce one affected scheduling update.

---

# 100. Event Privacy

Event payloads may contain sensitive references.

Public projections must filter them.

Example:

support.contribution_confirmed_by_project

may contain private contributor reference internally.

Money Map receives only privacy-safe aggregation.

Do not expose raw event payload publicly.

---

# 101. Event Retention

Important execution events should be durable.

Examples:

- responsibility acceptance
- project plan versions
- blockers
- timeline revisions
- project outcomes

Operational events may use separate retention.

Examples:

- retry details
- low-level worker events

Retention policy will be defined separately.

---

# 102. Core Event Flow

Conceptually:

Human / Organization / Agent / System Action
→ Authorization
→ Validation
→ State Change
→ Event
→ Event Bus
→ Deterministic Consumers
→ Relevant Agents
→ Structured Proposals
→ Validation
→ New State Change
→ New Event

This loop continues until the project reaches an outcome.

---

# 103. Example End-to-End Event Flow

Goal:

Run a community build event.

Creator submits goal.

project.created

Triggers:

Goal Understanding Agent
Project Scope Agent

They generate structured proposals.

Plan service persists approved plan.

project.plan_created

Creator approves.

project.plan_approved

Responsibilities become open.

responsibility.opened

Users begin joining.

responsibility.accepted

Deterministic service recalculates actor readiness.

task.execution_ready

Scheduling Agent proposes event time.

scheduled_event.proposed

Creator/participants approve.

scheduled_event.scheduled

One actor withdraws.

responsibility.withdrawn

Affected task loses actor readiness.

task.blocked

Blocker created.

blocker.created

Replanning Agent proposes alternative.

replanning.proposed

New actor accepts responsibility.

responsibility.accepted

Blocker resolves.

blocker.resolved

Timeline recalculated.

timeline.recalculated

Event executes.

scheduled_event.completed

Tasks finish.

task.completed

Project reaches outcome.

project.completed

Outcome and Blueprint Agent runs.

outcome.recorded
blueprint.generated

Project Memory receives the complete execution history.

---

# 104. Event Taxonomy Invariants

## Invariant 1

Events describe facts that happened.

## Invariant 2

Agent proposals are not authoritative events until validated/applied.

## Invariant 3

Human commitments require explicit human/authorized organization actions.

## Invariant 4

Events are append-only.

## Invariant 5

Event processing must be idempotent.

## Invariant 6

Public projections must not expose private event payloads.

## Invariant 7

One event may safely activate multiple independent consumers.

## Invariant 8

Agents should activate from relevant events/state, not arbitrary global sequencing.

## Invariant 9

Historical events remain even after current state changes.

## Invariant 10

System truth is produced through validated state changes, not agent narration.

## Invariant 11

An external tool request does not imply authorization.

## Invariant 12

External authorization does not imply a Hatcommways domain state change.

## Invariant 13

Raw external credentials must never appear in event payloads.

## Invariant 14

External identity revocation must prevent future governed external access.

## Invariant 15

AgentCore operational events remain distinct from Hatcommways domain events.

## Invariant 16

External tool failure must not automatically block unrelated project execution.

## Invariant 17

Product audit and runtime traces should be correlatable without exposing sensitive data.

## Invariant 18

An agent proposal event does not mean the proposal became authoritative state.

## Invariant 19

Affected-region, bounded-graph, evaluation, and memory-reuse events remain internal unless a separate public-safe product event is produced.

---

# 105. Initial Event Families

The initial event families are:

1. Project
2. Goal
3. Task
4. Dependency
5. Actor
6. Actor Role
7. Responsibility
8. Group
9. Community
10. Organization
11. Support / Funding
12. Scheduled Event / Meeting
13. Blocker
14. Timeline
15. Parallelization / Contention
16. Replanning
17. Acceleration
18. Maps
19. Participation Intelligence
20. Support Intelligence
21. Memory
22. Outcome / Blueprint
23. Appreciation
24. Notifications
25. Audit / Agent Runtime
26. External Tools
27. External Identity
28. Gateway / External Integration Operations
29. Trace Correlation
30. Affected Execution Region
31. Bounded Agent Graph
32. Proposal Lifecycle
33. Evaluation
34. Execution / Failure / Blueprint Memory

These categories are broad enough to support the current product without inventing domain-specific event systems.

---

# 106. Final Principle

Hatcommways should be understood as a continuously evolving execution state driven by meaningful events.

The system does not ask:

> Which agent comes next?

It asks:

> What just changed?
> Which parts of project state are affected?
> Which deterministic calculations must rerun?
> Which reasoning agents now have enough information to work?
> Which work can proceed independently?
> Does a human decision need to surface?

That event-driven model is the foundation for autonomous, parallel, auditable community execution.
