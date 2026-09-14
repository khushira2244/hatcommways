# Sponsor support and My Sponsorships

[Documentation index](README.md)

## Submission, reasoning and human decision

Explore → Event Home → Resources & Sponsors → Support This Event. Submission atomically writes a PENDING `support_offers` row, notification and `support_offer.submitted` outbox record. EventBridge → SQS → ECS worker → tool-free Strands Sponsor Fit → Bedrock Nova produces a typed persisted advisory in `sponsor_fit_results`. The organizer follows `event.html?event={event_id}&tab=resources&offer={offer_id}` to Accept/Reject. Fit failure does not grant or remove human authority.

## Quantity and persistence

APPROVED offers are the contribution ledger; no second counter is incremented. PostgreSQL numeric quantities and Decimal calculations derive pledged/remaining values. Pending/rejected offers count zero. Approval locks the event, validates organizer, offer version/status and capacity transactionally. Rejection changes no contribution totals.

Need IDs are deterministic event-scoped references to setup value objects, including duplicate occurrences. Edited/removed needs cannot silently acquire old offers. Manual sponsors remain separate. Fingerprints reject conflicting replay; runtime replay cannot duplicate assessments or approve support.

Required 1 and approved 1 yields pledged 1, remaining 0. Legitimate fractions remain fractional; display rounding cannot replace correct persistence. The investigated 0.992 offer matched its submission fingerprint: approval did not scale 1 down. A user-authorized correction retained fingerprint/reviewer information and logged before/after values. Wheel protection and decimal-text submission are input safeguards, not a new backend contract.

## Dashboard and privacy

`my-sponsorships.html` opens the current organization; `?sponsor={account_id}` opens another organization's public view for an authenticated user. Explore is unchanged.

`GET /sponsors/{sponsor_id}` resolves an active organization and explicitly projects approved contributions on PUBLIC events with `show_sponsors=true`: event metadata, coordinates, available cover, support type and approval time. It omits private comments and pending/rejected details for others. Only the owner receives detailed `offers`. No separate profile schema, upload system, verified badge or financial totals are implied.

The map fits approved event coordinates. Highlights prefer recent approved contributions and need not match the map's ordering. Pending offers appear only in the private list. Missing Maps/images have fallbacks.

Existing APIs: `GET/POST /events/{event_id}/support-offers`, `GET /events/{event_id}/support-notifications`, `POST /events/{event_id}/support-offers/{offer_id}/decision`.

## Evidence and limits

See [deployment](deployment.md) for dashboard release evidence and [earlier runtime proof](sponsor-deployment-20260914.md) for submission-to-model execution. Dashboard/maps are implemented; payments, contracts, delivery/completion lifecycle and richer profiles are not claimed.

Focused checks: `tests/planning_foundation/test_support_offers.py` (disposable database required) and `tests/test_sponsor_quantity_exact.py` (isolated rolled-back schema). No full regression is implied by this docs pass.
