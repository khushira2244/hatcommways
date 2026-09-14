# Asynchronous runtime

[Documentation index](README.md)

The deployed worker starts `services.agent_runtime.sqs_worker`; its production process also starts the outbox publisher. Transactions produce `domain_outbox` records. The publisher sends events through EventBridge (`hatcommways.runtime`) to SQS. Envelopes dispatch through `production_router` in `runtime_handlers.py`.

| Domain event | Handler |
| --- | --- |
| `blocker.affected_work_resolved` | `hatcommways-coordination-agent` |
| `support_offer.submitted` | `hatcommways-sponsor-fit-agent` |

Both registrations specify three maximum runtime attempts. Other reasoning capabilities are not all routed through SQS.

`runtime_agent_runs` records message/handler execution, status and attempts. Duplicate delivery is expected: runtime claims/reuse and domain persistence guards prevent duplicated effects. Transport retries and SQS redrive/DLQ handling preserve failure evidence. This is idempotent processing over delivery that may repeat, not exactly-once delivery.

Typed output still passes deterministic domain validation. Events do not authorize arbitrary actors, and advisory runs do not directly apply revised plans. See [observability](observability.md) and [execution](execution-and-replanning.md).
