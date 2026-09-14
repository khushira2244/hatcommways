# Deployment and configuration

[Documentation index](README.md)

Vercel static frontend; CloudFront → ALB → ECS/Fargate `hatcommways-api`; RDS PostgreSQL; `hatcommways-worker`, EventBridge and SQS/DLQ. Images use existing ECR. No separate dashboard service/schema is required.

Last verified 14 September 2026: API revision 5 and worker revision 5. API tag `sponsor-dashboard-20260914-073807`; worker retains `sponsor-20260914-014749`. The dashboard release layered two source changes over unchanged runtime/dependencies; no migration or worker deployment was required. These are dated observations, not a promise of future current state.

API base: `https://d2zg0c0ne74fcr.cloudfront.net`. Frontend: `https://hatcommways.vercel.app`. Owner/non-owner API and production browser access were verified after deployment.

## Static configuration

With Vercel Root Directory `apps/web`, Build Command is `node generate-runtime-config.mjs`; serve that directory's static files, with no separate generated output folder. For repository-root builds, run `node apps/web/generate-runtime-config.mjs` and serve `apps/web`.

Environment names: `HATCOMMWAYS_API_BASE`, `HATCOMMWAYS_GOOGLE_MAPS_API_KEY`, `HATCOMMWAYS_GOOGLE_MAPS_MAP_ID`.

The generator writes ignored `runtime-config.js`, loaded before auth/maps. Static JavaScript cannot directly read Vercel environment variables. Redeploy after changes. See `apps/web/runtime-config.example.js`. Browser keys are client-visible and need restrictions; never include backend credentials.

Local auth defaults to `http://127.0.0.1:8000`. The API reads `HATCOMMWAYS_DATABASE_URL` and optional comma-separated `HATCOMMWAYS_CORS_ORIGINS`. Retain local origins and explicitly allow the Vercel origin. Preview URLs are distinct origins. HTTPS frontend requires HTTPS API.

## Operations

Startup applies `schema.sql`; inspect changes before deployment. Preserve secrets/IAM/networking. Update workers for runtime compatibility, not every API read addition. Wait for task draining; verify health and authenticated behavior. See [earlier deployment evidence](sponsor-deployment-20260914.md).

Quantity-input safeguards added after the dashboard release require frontend deployment; this documentation pass does not certify their release or perform deployments.
