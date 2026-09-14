# Observability and evidence

[Documentation index](README.md)

Use `runtime_agent_runs`, outbox records, ECS logs, CloudWatch, and X-Ray/Transaction Search. IDs are correlation aids, not permissions.

Start with an offer/blocker ID. Find its outbox message/correlation ID, then match handler, run ID, attempts, status and trace. Inspect the persisted result separately: transport success, model success, validated persistence and human approval are different facts.

The [dated sponsor proof](sponsor-deployment-20260914.md) records a complete EventBridge/SQS/Strands/Nova run. Its labeled test offer returned WEAK and was rejected: a successful safe runtime demonstration. Spans were in `aws/spans`. The inherited telemetry service name was `hatcommways-coordination-agent`; the handler attribute identifies Sponsor Fit. Do not infer capability from the service label alone.

Do not publish tokens, database URLs, passwords or private comments. A green trace does not establish physical delivery/completion.
