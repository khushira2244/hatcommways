# Human updates and blockers

This backend foundation separates human-reported truth, AI-derived meaning, AI-derived execution-impact judgment, and authoritative organizer-visible blocker state. Both AI steps run only through explicit actions; neither changes schedules, work, dependencies, or assignments.

## API

All endpoints require the existing bearer session. Actor and organizer identities come from that session, never from request fields.

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/events/{event_id}/human-updates` | Active organizer or actor with an ACCEPTED participation in this event |
| GET | `/events/{event_id}/human-updates` | Active organizer; includes the interpretation when available |
| POST | `/events/{event_id}/human-updates/{update_id}/interpret` | Active organizer; explicit AI execution |
| GET | `/events/{event_id}/human-updates/{update_id}/interpretation` | Active organizer |
| POST | `/events/{event_id}/human-updates/{update_id}/assess-blocker` | Active organizer; requires persisted successful interpretation |
| GET | `/events/{event_id}/human-updates/{update_id}/blocker-assessment` | Active organizer |
| POST | `/events/{event_id}/blockers` | Active organizer |
| GET | `/events/{event_id}/blockers` | Active organizer |
| PATCH | `/events/{event_id}/blockers/{blocker_id}` | Active organizer, matching `expected_version` |
| POST | `/events/{event_id}/blockers/{blocker_id}/resolve-affected-work` | Active organizer; deterministic confirmed-graph resolution |
| GET | `/events/{event_id}/blockers/{blocker_id}/affected-work` | Active organizer; persisted resolution or null |
| POST | `/events/{event_id}/blockers/{blocker_id}/coordinate` | Active organizer; explicit bounded Strands/Nova execution |
| GET | `/events/{event_id}/blockers/{blocker_id}/coordination` | Active organizer; persisted proposal or null |

POST human updates accepts `text`, optional `stage_id`, `work_id`, `actor_requirement_id`, `participation_id`, and `idempotency_key`. Blank text and text over 10,000 characters are rejected. Whitespace, Unicode, and line endings are otherwise preserved exactly. A work link infers its stage; a role/participation link infers its ancestors. Conflicting or cross-event links are rejected. An actor's references must all match one of their accepted assignments. Event-level reports need at least one accepted assignment. A pending request, an unrelated membership, or a withdrawn/removed participation does not grant access. Partial approvals qualify through their accepted assignments only.

Organizers may report against any valid context in their own event. Only ACTOR and ORGANIZER source types are implemented and are derived server-side. There is no system-import endpoint or impersonation field.

POST blockers accepts `human_update_id`, `title`, `summary`, optional `category`, `stage_id`, `work_id`, and `idempotency_key`. The source must belong to this event. If stage/work are omitted, they inherit the source's scope; an organizer can explicitly assess a different valid context in the same event. The original reporter remains `reported_by_account_id`; the organizer is separately recorded as `created_by_account_id`. No downstream affected work is inferred.

GET blockers includes the immutable source snapshot, source reporter's display name, linked stage/work names, and both lifecycle states. No participant list endpoint or AI reasoning is exposed.

## Persistence and lifecycle

`human_updates` is separate from the existing organizer announcements in `actor_updates`. Reports start at `NOT_REQUESTED`, with `interpreted_at=null` and version 1. Report submission never starts interpretation. The explicit interpretation lifecycle is `NOT_REQUESTED → RUNNING → INTERPRETED`; runtime or validation errors produce `FAILED`. A failed update records only a bounded exception-class code and failure timestamp. `retry: true` starts another attempt; a failed request without that flag returns 409. A PostgreSQL trigger rejects changes to original text, attribution, context, creation time, or request key. There is no edit or delete API.

`human_update_interpretations` stores one active, AI-derived structured result per update. Its bounded taxonomy is `AVAILABILITY_CHANGE`, `ACCESS_PROBLEM`, `RESOURCE_PROBLEM`, `EQUIPMENT_PROBLEM`, `SCHEDULE_DELAY`, `SAFETY_CONCERN`, `COMPLETION_UPDATE`, `GENERAL_UPDATE`, or `UNKNOWN`. It stores a concise summary, reported condition, optional temporal/location signals, scoped references, possible-blocker signal, confidence, clarification signal, provider/model/agent/version, stop reason, usage, and creation time. The runtime controls provenance fields; model output cannot claim its own provenance.

The Human Update Interpretation Agent uses the existing Strands `Agent` and Amazon Bedrock Nova configuration (`us.amazon.nova-2-lite-v1:0`, temperature 0). Its single bound read tool exposes only the immutable report, reporter relationship/name, event time/location, explicitly linked stage/work, and one matching accepted participation. It never receives unrelated stages, work, participants, blockers, or the full event database. Structured output is validated by Pydantic and then by the service: source IDs must match, references may only use IDs in that scoped context, confidence is 0–1, and blocker/clarification explanations must match their booleans. Malformed output is not persisted.

Interpretation request and completion/failure emit `human_update.interpretation_requested`, `human_update.interpreted`, and `human_update.interpretation_failed` audit records through the existing domain outbox. These records contain IDs, bounded failure codes, and successful runtime provenance; they do not copy the report text. Existing interpretations are returned without another model call. A transactionally locked `RUNNING` state prevents concurrent calls from invoking the model twice.

`blocker_assessments` stores one active assessment per persisted interpretation. The bounded blocker kinds are `AVAILABILITY`, `ACCESS`, `RESOURCE`, `EQUIPMENT`, `SCHEDULE`, `SAFETY`, `DEPENDENCY`, `OTHER`, and `NONE`; severity and urgency use internal `LOW`, `MEDIUM`, or `HIGH` metadata. The result also records a concise reason, direct scoped references, coordination/replanning signals, clarification state, confidence, provider/model/agent provenance, stop reason, usage, and the authoritative blocker ID when one was created or reused. Assessment lifecycle metadata on the interpretation is `NOT_REQUESTED → RUNNING → ASSESSED`; runtime or validation errors produce `FAILED`, retain only a bounded exception-class code, and require an explicit `retry: true`.

The Blocker Assessment Agent uses the same synchronous Strands/Nova pattern and model as interpretation. Its single bound tool receives only the exact report, persisted interpretation, reporter relationship/name, directly linked stage/work schedules, one matching accepted participation, and meetings explicitly linked to that work or stage. It receives no event dependency graph or unrelated stages, work, meetings, participants, or blockers. Pydantic and service validation enforce IDs, direct scope, confidence, enum and semantic consistency. A non-blocker must use `NONE` with coordination and replanning false. An unresolved interpretation must remain clarification-only. Invalid output is not persisted.

Assessment is never triggered by report submission or interpretation completion. Existing results are reused without a model call, and a transactionally locked `RUNNING` state prevents concurrent execution. Request, success, and failure emit `blocker_assessment.requested`, `blocker_assessment.assessed`, and `blocker_assessment.failed` audit records without copying report text.

The model cannot write blocker rows or choose blocker lifecycle. After a valid `is_execution_blocker=true` result with no clarification, the assessment service calls the existing deterministic blocker boundary in the same transaction. That boundary creates or reuses one blocker for the source update, derives title/summary/category and direct references from the validated assessment, and always leaves a newly created blocker at `ACKNOWLEDGED + OPEN`. Non-blocker and clarification results create no blocker.

`blockers` starts at `ACKNOWLEDGED + OPEN`, version 1. Handling states ACKNOWLEDGED, WORKING, and STALLED are independent of condition states OPEN and CLEARED. Changing handling never clears the condition. Clearing sets `cleared_at`; handling changes retain it; reopening clears it. Lifecycle changes increment version and updated_at. An unchanged state returns the current snapshot without a version bump. Even no-op requests require the current version. Stale versions return HTTP 409. Clearing never deletes a blocker.

Every mutation checks permissions within its transaction. Writes serialize on the event row without changing it; blocker updates also lock the blocker. The service can be used by a future validated internal adapter with an authorized organizer principal; no unchecked agent path exists today.

## Deduplication

Human updates optionally deduplicate by `(event_id, reporter_account_id, idempotency_key)`. Matching replays return the same report; changed content under the same key returns 409. Without a key, separate submissions are separate reports.

A unique `(event_id, source_human_update_id)` constraint prevents accidental duplicate blockers even without a key. An optional event-scoped blocker key is also unique. Matching replays preserve the blocker ID and its current lifecycle, including a cleared state. A changed payload, a different supplied key for an existing source, or a key reused for another source returns 409. Source-only retries can omit the key. A composite foreign key also enforces that blocker and source belong to the same event.

## Deterministic affected work

An open blocker created by a persisted blocking assessment can be resolved after assessment. The resolver reads only authoritative stages whose source `STAGE_PLAN` proposal is approved and authoritative work whose source `WORK_DECOMPOSITION` proposal is approved. Pending, rejected, stale, missing, and cross-event graph data never enters traversal. A row `(work_id, depends_on_work_id)` means the first work item depends on the second; downstream traversal therefore follows each prerequisite to its dependents. The directly assessed work is retained separately, reachable dependents are deduplicated, and output order is stable by stage order then work order. Independent and upstream branches stay outside the result.

Stage-only assessments remain stage-level. They return the confirmed stage and no work IDs because the service does not infer that every work item in a stage is affected. Both work and stage dependency graphs are cycle-checked. Cycles, cross-event edges, unconfirmed direct references, missing direct scope, and graph changes after assessment fail safely. No LLM, Strands runtime, Nova call, coordination action, or replanning action participates in this calculation.

Each assessment records the event and direct stage/work versions present when assessment completed. Resolution records those source versions and a SHA-256 fingerprint of confirmed stage/work IDs, versions, source proposals, and dependency edges. A first resolution requires the assessed event version still to be current. Matching retries return the same immutable row and emit no second outbox event. A different current fingerprint or version returns HTTP 409 rather than silently overwriting history. A cleared blocker cannot receive its first resolution; an already persisted resolution remains readable and replayable as historical evidence after clearance.

Resolution inserts only `affected_work_resolutions` and one `blocker.affected_work_resolved` outbox record. It does not change the blocker condition, event/stage/work versions, schedules, dependency edges, meetings, actor requirements, accounts, or participations.

## Coordination proposals

Coordination is an explicit reasoning step after a persisted affected-work resolution. The Coordination Agent asks whether bounded operational actions can preserve the confirmed plan. Its scoped tool exposes only the authoritative blocker and assessment, affected stages/work, accepted actors assigned within that scope and their approved availability, relevant non-cancelled meetings, and existing event setup resources. It does not receive unrelated work, actors, meetings, pending proposals, email addresses, or a database-wide read tool.

The typed proposal records `coordination_possible`, `requires_replanning`, rationale, confidence, runtime provenance, source versions, and up to twelve bounded actions. Supported actions are `NOTIFY_ACTOR`, `REQUEST_CLARIFICATION`, `USE_EXISTING_RESOURCE`, `MOVE_EXISTING_RESOURCE`, `RESCHEDULE_MEETING`, `REASSIGNMENT_SUGGESTION`, `TEMPORARY_WORKAROUND`, `WAIT_FOR_CONDITION`, and `OTHER`. Every referenced actor, work item, meeting, and resource must exist in the supplied context. Resource actions require an existing resource, meeting rescheduling requires a relevant meeting, and reassignment suggestions always require human approval.

Actions are advisory records only. `NOTIFY_ACTOR` sends no notification, `RESCHEDULE_MEETING` changes no meeting, and `REASSIGNMENT_SUGGESTION` changes no assignment. Coordination never changes stage/work schedules, dependencies, work definitions, participations, blocker lifecycle, or plan versions. A `requires_replanning=true` result records only that conclusion; no replan is created.

`coordination_requests` provides `RUNNING`, `SUCCEEDED`, and `FAILED` lifecycle state. Runtime or validation failure persists only a bounded failure code and requires `retry: true`. The source fingerprint covers the event, blocker, confirmed affected graph, affected stage/work versions, relevant participation windows, meeting versions, and event setup version. Same-state retries reuse the proposal without another model call. Changed relevant state returns HTTP 409. Event locking ensures concurrent calls produce one effective model execution.

## Notifications and deferred work

No notifications are emitted yet. `event_notifications` requires a non-null `participation_request_id`, restricts its type to PARTICIPATION_REQUEST, and its reader hydrates that request. `actor_updates` supports actor-facing announcements and meeting/decision messages, not organizer human-report notifications. Reusing either for these reports would require changing its contract. This foundation does not create a second notification system.

Replanning, organizer replan approval, participant blocker visibility, frontend UI, notifications redesign, and EventBridge/SQS/AgentCore integration remain deferred. Assessment stores direct impact metadata; the deterministic resolver expands confirmed work dependencies; coordination stores bounded proposals. None writes schedules, dependencies, meetings, actor assignments, accounts, participation records, or plan versions.

## Verification

`tests/planning_foundation/test_human_updates_blockers.py` uses real PostgreSQL and the existing authenticated participation approval flow. It covers Gachibowli Lake Cleanup, Priya's exact late-arrival report, Shoreline Cleanup, independent states, reopen/clear timestamps, concurrent deduplication and stale updates, immutable text, scope and authorization failures, and unchanged schedules/accounts/assignments/agent-request records.

`tests/planning_foundation/test_human_update_interpretation.py` covers explicit-only execution, scoped context, typed persistence, provenance, read-model exposure, duplicate reuse, concurrent-run exclusion, failure and explicit retry, invalid output/IDs, completion and clarification semantics, unchanged authoritative planning/participation state, and absence of automatic blockers. Its separately marked real-Bedrock case checks the three semantic scenarios without matching exact model prose.

`tests/planning_foundation/test_blocker_assessment.py` covers explicit eligibility, tightly scoped context, typed persistence and provenance, semantic and ID validation, failure/retry, concurrent-run exclusion, assessment and blocker deduplication, immutable report/interpretation content, unchanged schedules/meetings/participations/assignments, deterministic initial blocker state, non-blocker and clarification behavior, and the separately marked three-case real-Nova proof.

`tests/planning_foundation/test_affected_work_resolver.py` covers precise branch traversal, upstream and independent exclusion, stage-only scope, persisted replay, no-agent execution, stale versions and fingerprints, cycles, cross-event edges, cleared-blocker history, duplicate-edge deduplication, concurrency, one outbox event, and unchanged authoritative planning and blocker state.

`tests/planning_foundation/test_coordination_agent.py` covers explicit-only execution, scoped context, non-replan and replan-needed outcomes, typed persistence, invalid-ID rejection, failed lifecycle and explicit retry, source staleness, concurrent single execution, no notifications, and unchanged schedules, dependencies, assignments, participations, meetings, and blocker state. Its marked real-Bedrock case exercises the same contract through Strands and Nova.

Use an isolated test database: the existing pytest fixture truncates test data. Never point the tests at the application database.

```powershell
$env:HATCOMMWAYS_TEST_DATABASE_URL = '<isolated PostgreSQL DSN>'
.venv/Scripts/python.exe -m pytest tests/planning_foundation/test_human_updates_blockers.py -q
.venv/Scripts/python.exe -m pytest tests/planning_foundation -m 'not real_bedrock' -q
```

Schema changes follow the existing `Database.apply_schema()` convention and are safe to apply repeatedly. Application startup applies this schema; a running API must be restarted to load the new routes. Test verification does not migrate the existing application database.
