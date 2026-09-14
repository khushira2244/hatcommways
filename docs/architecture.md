# Implemented architecture

[Documentation index](README.md)

The [architecture image](assets/hatcommways-architecture.png) is the supplied diagram, unmodified. It summarizes system boundaries; workflow boxes do not imply every agent is queue-dispatched.

Vercel static frontend → CloudFront HTTPS → public ALB → ECS/Fargate FastAPI → RDS PostgreSQL. The frontend uses generated `window.HATCOMMWAYS_API_BASE` and bearer sessions. Explicit CORS origins are required. Google Maps is a separate browser integration.

PostgreSQL holds confirmed plans, dependencies, requirements, participation decisions, reports, blocker/proposal state, support offers and runtime evidence. Services own transactions and validation. Models do not write authoritative state directly.

The current worker routes are `blocker.affected_work_resolved` and `support_offer.submitted`. Other reasoning steps use API/application workflows. See [agents](agents.md) and [runtime](runtime.md).

No Bedrock AgentCore deployment is asserted. Existing AWS components are ECR, ECS/Fargate API and worker, RDS, CloudFront, ALB, EventBridge, SQS/DLQ and observability. Older designs discuss broader possibilities separately.
