from datetime import datetime, timezone
from uuid import uuid4

from services.agent_runtime.runtime_events import RuntimeEventEnvelope
from services.agent_runtime.runtime_worker import (
    InMemoryRuntimeRunRegistry,
    RetryableRuntimeError,
    RuntimeHandler,
    RuntimeRouter,
    RuntimeRunStatus,
    consume_runtime_event,
)


def event() -> RuntimeEventEnvelope:
    message_id, correlation_id = uuid4(), uuid4()
    return RuntimeEventEnvelope(
        message_id=message_id,
        event_type="blocker.affected_work_resolved",
        aggregate_type="AFFECTED_WORK_RESOLUTION",
        aggregate_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        correlation_id=correlation_id,
        idempotency_key=f"runtime-message:{message_id}",
        payload={"event_id": str(uuid4()), "blocker_id": str(uuid4())},
    )


def test_local_worker_routes_records_and_deduplicates_delivery():
    calls = []
    source = event()
    handler = RuntimeHandler(
        name="coordination-workflow",
        execute=lambda envelope: calls.append(envelope.message_id) or {"proposal_id": str(uuid4())},
    )
    registry = InMemoryRuntimeRunRegistry()
    router = RuntimeRouter({source.event_type: handler})

    first = consume_runtime_event(source, router=router, registry=registry)
    second = consume_runtime_event(source, router=router, registry=registry)

    assert first.status == RuntimeRunStatus.SUCCEEDED
    assert second.status == RuntimeRunStatus.SUCCEEDED
    assert second.reused is True
    assert second.run_id == first.run_id
    assert calls == [source.message_id]


def test_followup_preserves_correlation_and_sets_causation():
    source = event()
    followup = source.followup(
        event_type="coordination.requested",
        aggregate_type="COORDINATION_REQUEST",
        aggregate_id=uuid4(),
        payload={"blocker_id": str(source.aggregate_id)},
        idempotency_key="coordination:focused-proof",
    )
    assert followup.correlation_id == source.correlation_id
    assert followup.causation_id == source.message_id
    assert followup.message_id != source.message_id


def test_retryable_failure_waits_for_explicit_redelivery():
    calls = []
    source = event()

    def execute(envelope):
        calls.append(envelope.message_id)
        if len(calls) == 1:
            raise RetryableRuntimeError("temporary local failure")
        return {"proposal_id": str(uuid4())}

    registry = InMemoryRuntimeRunRegistry()
    router = RuntimeRouter({source.event_type: RuntimeHandler(name="coordination-workflow", execute=execute)})
    first = consume_runtime_event(source, router=router, registry=registry)
    assert first.status == RuntimeRunStatus.RETRYABLE
    assert calls == [source.message_id]

    second = consume_runtime_event(source, router=router, registry=registry)
    assert second.status == RuntimeRunStatus.SUCCEEDED
    assert second.attempt == 2
    assert calls == [source.message_id, source.message_id]
