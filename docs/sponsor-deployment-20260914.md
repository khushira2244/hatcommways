# Sponsor production deployment — 14 September 2026

> Historical release snapshot. See [deployment](deployment.md) for the later sponsor-dashboard API release and frontend status. Pending-deployment statements below describe the time of this earlier test.

- Image: `446103799369.dkr.ecr.us-east-1.amazonaws.com/hatcommways:sponsor-20260914-014749`
- Deployed digest: `sha256:70fab57f4311cd0a20c2882ac140b266c392246e534709e6e16114433595924d`
- API task: `hatcommways-api:4`
- Worker task: `hatcommways-worker:5`
- Both services: PRIMARY COMPLETED, desired/running 1, pending 0.
- HTTPS health: `https://d2zg0c0ne74fcr.cloudfront.net/health` returned 200 and `{"status":"ok"}`.
- Task roles, environment, secrets, network and logging configuration preserved; only image changed.

## Schema

Applied only the sponsor migration: `support_offers`, `sponsor_fit_results`, their
indexes, `event_notifications.support_offer_id`, nullable participation request
reference, and the type-specific notification constraint/index. All five existing
events remained. No existing production data was deleted.

## Production runtime proof

One clearly labeled deployment-test offer was submitted through the HTTPS API
for Community Lake Cleanup — Kokar (Demo), selecting Collection vehicle, quantity
1 with the event execution window. It was deliberately rejected after review.

- Event: `eb1ccfbb-0aa2-5ed5-9427-f9dcfc0b839d`
- Offer: `b7fc794e-c42a-4968-a657-c1258be81bbb`
- Outbox/message: `0933cca5-ebc8-4555-af83-5e13447cca49`
- Correlation: `65bdc688-e42d-4402-a6ad-4782111e060c`
- Run: `f5f37a54-1b2a-4eb4-99c8-eb16f3ea696f`
- Handler: `hatcommways-sponsor-fit-agent`
- Event type: `support_offer.submitted`
- Runtime status: `SUCCEEDED`, attempt 1
- Outbox published: 2026-09-14 02:03:50.121351+00:00
- Run start: 2026-09-14 02:03:50.263034+00:00; complete: 2026-09-14 02:03:51.782035+00:00
- SQS message: `d92e5e8e-4816-49b9-b738-f83f389af522`
- Trace: `6aa7560459fdb5c9876f6e2eaeaf52c5`
- Model: `us.amazon.nova-2-lite-v1:0`
- Fit: `WEAK`. The model correctly identified the explicitly
  labeled deployment test as not a real pledge. Timing fit was true; need and
  remaining-gap fit were false. The typed result and model provenance persisted.

The outbox publisher log confirmed published=1, failed=0. The ECS worker log
confirmed the same message, correlation and run IDs with SUCCEEDED. CloudWatch
Logs Insights found the runtime span in `aws/spans`, the existing active
CloudWatchLogs/X-Ray Transaction Search destination. Existing telemetry service
name remains `hatcommways-coordination-agent`; the handler attribute identifies
the Sponsor Fit Agent. No observability settings changed.

## Organizer review

The organizer-authenticated API returned the exact notification, offer and persisted
fit. Its deep link is:

https://hatcommways.vercel.app/event.html?event=eb1ccfbb-0aa2-5ed5-9427-f9dcfc0b839d&tab=resources&offer=b7fc794e-c42a-4968-a657-c1258be81bbb

The REJECT decision returned REJECTED, marked the notification read, and left
approved support and every resource pledged/remaining value unchanged. This was
the only production decision path exercised. Production ACCEPT was not exercised;
its transaction was covered by the previously completed focused local test.
Temporary verification sessions were revoked. The labeled test account and rejected
offer remain as the audit record.

## Frontend and cleanup

Vercel needs redeployment after the frontend changes are pushed. No Git commit or
push was made. The new production browser review page is therefore not claimed as
verified on Vercel; organizer review was verified through the production API.

Temporary CodeBuild project, source bucket, build IAM role/policy and temporary
build log group were deleted after success. The versioned ECR image remains.
No new persistent infrastructure, full regression, dashboard or product work.
