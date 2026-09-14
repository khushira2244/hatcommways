# Sponsor support vertical slice

The existing Event Home owns submission and review. Notifications link to
`event.html?event={event_id}&tab=resources&offer={offer_id}`; no new page exists.

## Persistence and authority

`support_offers` stores the sponsor account, selected resource snapshot/reference,
quantity, availability, comment, decision/version, idempotency fingerprint and
correlation ID. Only APPROVED rows form the authoritative contribution ledger.
The support workspace projects these into Sponsors & Support and sums their
quantities into pledged/remaining values. Pending/rejected rows contribute zero.
Existing manually configured sponsors remain intact.

Existing resource needs are JSON value objects. References are deterministic
UUIDs scoped to the event and resource content (with an occurrence suffix for
identical entries). Editing/removing a need invalidates its old reference;
approval refuses to silently reattach an old offer to another need. All decisions
lock the event, verify organizer authority and the offer version/status, and
recheck the current remaining quantity in the same transaction. Privacy flags
still control public sponsor/resource visibility.

`sponsor_fit_results` stores one versioned typed advisory per offer, with model,
usage, message, correlation and causation provenance. Runtime replay cannot
duplicate the assessment or create a contribution. An unavailable/failed fit
does not grant or remove organizer authority.

## Runtime

Submission atomically writes the offer, SPONSOR_OFFER notification and
`support_offer.submitted` domain outbox event. Existing EventBridge source routing
already forwards `hatcommways.runtime` events to SQS. The new production router
handler uses the existing runtime registry, retries and worker instrumentation.
One tool-free Strands agent calls `us.amazon.nova-2-lite-v1:0` with only scoped
offer/event/need/approved-quantity/timing/profile data. It cannot mutate anything.
Deterministic validation rejects unsupported positive timing/gap assertions.

## Release order

Production API and worker deployment was verified on 14 September 2026; see
[sponsor deployment report](sponsor-deployment-20260914.md). Vercel frontend
redeployment is still required. The API startup applies
the additive schema in `schema.sql`. Ship the schema and updated API/worker
images before publishing the frontend feature; wait for old API tasks to drain
before creating sponsor notifications. Old workers do not know this event type.
No new EventBridge rule, queue, infrastructure, credentials or Google Maps change
is required. Existing participation and blocker workflows retain their owners.

## Focused verification

Run `tests/planning_foundation/test_support_offers.py` only against an isolated
PostgreSQL test database: it exercises authenticated submission, notifications,
scoped fit persistence/replay, decisions, isolation and overfill rejection.
Browser verification uses the real local API for submission, exact-offer bell
routing, accept/reject and return to the normal tab. A separate real Nova call
was verified through the production router using an isolated local database;
the later production EventBridge/SQS proof is recorded in the deployment report.

Sponsor dashboards, maps, profiles, payments, contracts and analytics are deferred.

## Changed files

- `apps/web/event.html`, `event-home.js`, `event-home.css`, `event-support.js`
- `services/api/app.py`
- `services/planning_foundation/schema.sql`, `support_offer_models.py`,
  `support_offer_service.py`, `participation_service.py`
- `services/agent_runtime/sponsor_fit.py`, `runtime_handlers.py`, `runtime_worker.py`
- `tests/planning_foundation/test_support_offers.py`
- `docs/sponsor-support.md`

Focused results: two PostgreSQL/API tests passed (sponsor and participation);
browser submission/notification/review/accept/reject checks passed without JS
exceptions; real Nova returned STRONG with all three fit checks true for the
Kokar transport example. The subsequent production deployment and live queue proof are recorded in the
deployment report.
