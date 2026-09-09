# Human updates and blockers

This backend foundation stores real reports, bounded AI-derived interpretations, and organizer-managed blocker state. Interpretation runs only through an explicit action; it does not mark work blocked, change a schedule, or assign people.

## API

All endpoints require the existing bearer session. Actor and organizer identities come from that session, never from request fields.

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/events/{event_id}/human-updates` | Active organizer or actor with an ACCEPTED participation in this event |
| GET | `/events/{event_id}/human-updates` | Active organizer; includes the interpretation when available |
| POST | `/events/{event_id}/human-updates/{update_id}/interpret` | Active organizer; explicit AI execution |
| GET | `/events/{event_id}/human-updates/{update_id}/interpretation` | Active organizer |
| POST | `/events/{event_id}/blockers` | Active organizer |
| GET | `/events/{event_id}/blockers` | Active organizer |
| PATCH | `/events/{event_id}/blockers/{blocker_id}` | Active organizer, matching `expected_version` |

POST human updates accepts `text`, optional `stage_id`, `work_id`, `actor_requirement_id`, `participation_id`, and `idempotency_key`. Blank text and text over 10,000 characters are rejected. Whitespace, Unicode, and line endings are otherwise preserved exactly. A work link infers its stage; a role/participation link infers its ancestors. Conflicting or cross-event links are rejected. An actor's references must all match one of their accepted assignments. Event-level reports need at least one accepted assignment. A pending request, an unrelated membership, or a withdrawn/removed participation does not grant access. Partial approvals qualify through their accepted assignments only.

Organizers may report against any valid context in their own event. Only ACTOR and ORGANIZER source types are implemented and are derived server-side. There is no system-import endpoint or impersonation field.

POST blockers accepts `human_update_id`, `title`, `summary`, optional `category`, `stage_id`, `work_id`, and `idempotency_key`. The source must belong to this event. If stage/work are omitted, they inherit the source's scope; an organizer can explicitly assess a different valid context in the same event. The original reporter remains `reported_by_account_id`; the organizer is separately recorded as `created_by_account_id`. No downstream affected work is inferred.

GET blockers includes the immutable source snapshot, source reporter's display name, linked stage/work names, and both lifecycle states. No participant list endpoint or AI reasoning is exposed.

## Persistence and lifecycle

`human_updates` is separate from the existing organizer announcements in `actor_updates`. Reports start at `NOT_REQUESTED`, with `interpreted_at=null` and version 1. Report submission never starts interpretation. The explicit interpretation lifecycle is `NOT_REQUESTED → RUNNING → INTERPRETED`; runtime or validation errors produce `FAILED`. A failed update records only a bounded exception-class code and failure timestamp. `retry: true` starts another attempt; a failed request without that flag returns 409. A PostgreSQL trigger rejects changes to original text, attribution, context, creation time, or request key. There is no edit or delete API.

`human_update_interpretations` stores one active, AI-derived structured result per update. Its bounded taxonomy is `AVAILABILITY_CHANGE`, `ACCESS_PROBLEM`, `RESOURCE_PROBLEM`, `EQUIPMENT_PROBLEM`, `SCHEDULE_DELAY`, `SAFETY_CONCERN`, `COMPLETION_UPDATE`, `GENERAL_UPDATE`, or `UNKNOWN`. It stores a concise summary, reported condition, optional temporal/location signals, scoped references, possible-blocker signal, confidence, clarification signal, provider/model/agent/version, stop reason, usage, and creation time. The runtime controls provenance fields; model output cannot claim its own provenance.

The Human Update Interpretation Agent uses the existing Strands `Agent` and Amazon Bedrock Nova configuration (`us.amazon.nova-2-lite-v1:0`, temperature 0). Its single bound read tool exposes only the immutable report, reporter relationship/name, event time/location, explicitly linked stage/work, and one matching accepted participation. It never receives unrelated stages, work, participants, blockers, or the full event database. Structured output is validated by Pydantic and then by the service: source IDs must match, references may only use IDs in that scoped context, confidence is 0–1, and blocker/clarification explanations must match their booleans. Malformed output is not persisted.

Interpretation request and completion/failure emit `human_update.interpretation_requested`, `human_update.interpreted`, and `human_update.interpretation_failed` audit records through the existing domain outbox. These records contain IDs, bounded failure codes, and successful runtime provenance; they do not copy the report text. Existing interpretations are returned without another model call. A transactionally locked `RUNNING` state prevents concurrent calls from invoking the model twice.

`blockers` starts at `ACKNOWLEDGED + OPEN`, version 1. Handling states ACKNOWLEDGED, WORKING, and STALLED are independent of condition states OPEN and CLEARED. Changing handling never clears the condition. Clearing sets `cleared_at`; handling changes retain it; reopening clears it. Lifecycle changes increment version and updated_at. An unchanged state returns the current snapshot without a version bump. Even no-op requests require the current version. Stale versions return HTTP 409. Clearing never deletes a blocker.

Every mutation checks permissions within its transaction. Writes serialize on the event row without changing it; blocker updates also lock the blocker. The service can be used by a future validated internal adapter with an authorized organizer principal; no unchecked agent path exists today.

## Deduplication

Human updates optionally deduplicate by `(event_id, reporter_account_id, idempotency_key)`. Matching replays return the same report; changed content under the same key returns 409. Without a key, separate submissions are separate reports.

A unique `(event_id, source_human_update_id)` constraint prevents accidental duplicate blockers even without a key. An optional event-scoped blocker key is also unique. Matching replays preserve the blocker ID and its current lifecycle, including a cleared state. A changed payload, a different supplied key for an existing source, or a key reused for another source returns 409. Source-only retries can omit the key. A composite foreign key also enforces that blocker and source belong to the same event.

## Notifications and deferred work

No notifications are emitted yet. `event_notifications` requires a non-null `participation_request_id`, restricts its type to PARTICIPATION_REQUEST, and its reader hydrates that request. `actor_updates` supports actor-facing announcements and meeting/decision messages, not organizer human-report notifications. Reusing either for these reports would require changing its contract. This foundation does not create a second notification system.

Blocker assessment, affected-work resolution, coordination, replanning, participant blocker visibility, frontend UI, notifications redesign, and EventBridge/SQS/AgentCore integration remain deferred. Interpretation does not create blockers and never writes schedules, actor assignments, accounts, participation records, or plan versions.

## Verification

`tests/planning_foundation/test_human_updates_blockers.py` uses real PostgreSQL and the existing authenticated participation approval flow. It covers Gachibowli Lake Cleanup, Priya's exact late-arrival report, Shoreline Cleanup, independent states, reopen/clear timestamps, concurrent deduplication and stale updates, immutable text, scope and authorization failures, and unchanged schedules/accounts/assignments/agent-request records.

`tests/planning_foundation/test_human_update_interpretation.py` covers explicit-only execution, scoped context, typed persistence, provenance, read-model exposure, duplicate reuse, concurrent-run exclusion, failure and explicit retry, invalid output/IDs, completion and clarification semantics, unchanged authoritative planning/participation state, and absence of automatic blockers. Its separately marked real-Bedrock case checks the three semantic scenarios without matching exact model prose.

Use an isolated test database: the existing pytest fixture truncates test data. Never point the tests at the application database.

```powershell
$env:HATCOMMWAYS_TEST_DATABASE_URL = '<isolated PostgreSQL DSN>'
.venv/Scripts/python.exe -m pytest tests/planning_foundation/test_human_updates_blockers.py -q
.venv/Scripts/python.exe -m pytest tests/planning_foundation -m 'not real_bedrock' -q
```

Schema changes follow the existing `Database.apply_schema()` convention and are safe to apply repeatedly. Application startup applies this schema; a running API must be restarted to load the new routes. Test verification does not migrate the existing application database.
