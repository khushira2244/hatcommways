import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.agent_runtime.aws_transport import (
    EVENT_SOURCE,
    EventBridgeOutboxPublisher,
    eventbridge_entry,
    runtime_event_from_sqs_body,
)
from services.agent_runtime.runtime_events import RuntimeEventEnvelope
from services.agent_runtime.runtime_worker import (
    InMemoryRuntimeRunRegistry,
    RetryableRuntimeError,
    RuntimeHandler,
    RuntimeRouter,
    RuntimeRunStatus,
)
from services.agent_runtime.sqs_worker import consume_sqs_message


def runtime_event():
    message_id = uuid4()
    return RuntimeEventEnvelope(
        message_id=message_id,
        event_type="blocker.affected_work_resolved",
        aggregate_type="AFFECTED_WORK_RESOLUTION",
        aggregate_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        correlation_id=uuid4(),
        causation_id=uuid4(),
        idempotency_key=f"runtime-message:{message_id}",
        payload={"event_id": str(uuid4()), "blocker_id": str(uuid4())},
    )


def sqs_body(event):
    return json.dumps({"source": EVENT_SOURCE, "detail-type": event.event_type, "detail": event.model_dump(mode="json")})


def test_eventbridge_serialization_and_sqs_adapter_round_trip():
    event = runtime_event()
    entry = eventbridge_entry(event, "hatcommways-runtime-events")
    assert entry["Source"] == EVENT_SOURCE
    assert entry["DetailType"] == event.event_type
    assert RuntimeEventEnvelope.model_validate_json(entry["Detail"]) == event
    assert runtime_event_from_sqs_body(sqs_body(event)) == event
    with pytest.raises(ValueError, match="malformed|not a Hatcommways"):
        runtime_event_from_sqs_body('{"source":"someone.else","detail":{}}')


class FakeCursor:
    def __init__(self, *, rows=None):
        self.rows = rows or []
    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.updated = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def execute(self, sql, params=()):
        if "SELECT * FROM domain_outbox" in sql:
            return FakeCursor(rows=self.rows)
        if "UPDATE domain_outbox" in sql:
            self.updated.extend(params[0])
            return FakeCursor()
        raise AssertionError(sql)


class FakeDatabase:
    def __init__(self, rows):
        self.connection = FakeConnection(rows)
    def connect(self):
        return self.connection


def outbox_row(event):
    return {
        "id": event.message_id, "event_type": event.event_type,
        "aggregate_type": event.aggregate_type, "aggregate_id": event.aggregate_id,
        "occurred_at": event.occurred_at, "correlation_id": event.correlation_id,
        "causation_id": event.causation_id, "payload": event.payload,
    }


def test_outbox_marks_only_successful_eventbridge_entries():
    first, second = runtime_event(), runtime_event()
    database = FakeDatabase([outbox_row(first), outbox_row(second)])
    client = type("Client", (), {"put_events": lambda self, **_: {"Entries": [
        {"EventId": "aws-event-1"}, {"ErrorCode": "InternalFailure"}
    ]}})()
    result = EventBridgeOutboxPublisher(database, client, "hatcommways-runtime-events").publish_batch()
    assert (result.selected, result.published, result.failed) == (2, 1, 1)
    assert database.connection.updated == [first.message_id]


class FakeSqs:
    def __init__(self):
        self.deleted = []
        self.visibility = []
    def delete_message(self, **kwargs):
        self.deleted.append(kwargs)
    def change_message_visibility(self, **kwargs):
        self.visibility.append(kwargs)


def test_sqs_worker_deletes_success_and_retains_retryable_failure():
    event = runtime_event()
    message = {"MessageId": "sqs-1", "ReceiptHandle": "receipt", "Body": sqs_body(event)}
    sqs = FakeSqs()
    success_router = RuntimeRouter({event.event_type: RuntimeHandler("proof", lambda _: {"ok": "yes"})})
    result = consume_sqs_message(
        message, sqs=sqs, queue_url="queue", router=success_router,
        registry=InMemoryRuntimeRunRegistry(),
    )
    assert result.status == RuntimeRunStatus.SUCCEEDED
    assert len(sqs.deleted) == 1

    sqs.deleted.clear()
    retry_router = RuntimeRouter({event.event_type: RuntimeHandler("retry-proof", lambda _: (_ for _ in ()).throw(RetryableRuntimeError("retry")))})
    result = consume_sqs_message(
        message, sqs=sqs, queue_url="queue", router=retry_router,
        registry=InMemoryRuntimeRunRegistry(),
    )
    assert result.retryable_failure is True
    assert sqs.deleted == []
    assert sqs.visibility[-1]["VisibilityTimeout"] == 0
