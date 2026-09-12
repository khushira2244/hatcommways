"""Long-polling SQS entrypoint for the transport-neutral runtime worker."""

from __future__ import annotations

import logging
import os
import signal
from threading import Event, Thread
from time import monotonic

from opentelemetry import trace

from services.planning_foundation.database import Database

from .aws_transport import AwsRuntimeConfig, runtime_event_from_sqs_body
from .runtime_worker import (
    PostgresRuntimeRunRegistry,
    RuntimeHandler,
    RuntimeRouter,
    RuntimeRunStatus,
    consume_runtime_event,
)


LOGGER = logging.getLogger("hatcommways.runtime.worker")
STOP = Event()
TRACER = trace.get_tracer("hatcommways.runtime.worker")


def consume_sqs_message(message, *, sqs, queue_url, router, registry):
    started = monotonic()
    sqs.change_message_visibility(
        QueueUrl=queue_url,
        ReceiptHandle=message["ReceiptHandle"],
        VisibilityTimeout=int(os.environ.get("HATCOMMWAYS_RUNTIME_VISIBILITY_SECONDS", "300")),
    )
    try:
        event = runtime_event_from_sqs_body(message["Body"])
    except ValueError:
        LOGGER.warning("runtime_message_permanent_failure sqs_message_id=%s", message.get("MessageId"))
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
        return None
    with TRACER.start_as_current_span("hatcommways.runtime.consume") as span:
        span.set_attribute("hatcommways.message_id", str(event.message_id))
        span.set_attribute("hatcommways.correlation_id", str(event.correlation_id))
        span.set_attribute("hatcommways.event_type", event.event_type)
        span.set_attribute("messaging.message.id", message.get("MessageId", ""))
        try:
            result = consume_runtime_event(event, router=router, registry=registry)
        except ValueError as error:
            LOGGER.warning(
                "runtime_message_unsupported sqs_message_id=%s message_id=%s event_type=%s error=%s",
                message.get("MessageId"), event.message_id, event.event_type, error,
            )
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
            return None
        span.set_attribute("hatcommways.run_id", str(result.run_id))
        span.set_attribute("hatcommways.handler", result.handler_name)
        span.set_attribute("hatcommways.attempt", result.attempt)
        span.set_attribute("hatcommways.status", result.status.value)
    latency_ms = round((monotonic() - started) * 1000)
    LOGGER.info(
        "runtime_message_result sqs_message_id=%s message_id=%s run_id=%s event_type=%s handler=%s attempt=%s "
        "correlation_id=%s causation_id=%s status=%s reused=%s latency_ms=%s retryable=%s",
        message.get("MessageId"), event.message_id, result.run_id, event.event_type,
        result.handler_name, result.attempt,
        event.correlation_id, event.causation_id, result.status, result.reused, latency_ms,
        result.retryable_failure,
    )
    if result.status == RuntimeRunStatus.SUCCEEDED or (
        result.status == RuntimeRunStatus.FAILED and not result.retryable_failure
    ):
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    elif result.retryable_failure:
        sqs.change_message_visibility(
            QueueUrl=queue_url,
            ReceiptHandle=message["ReceiptHandle"],
            VisibilityTimeout=0,
        )
    return result


def run(router: RuntimeRouter, *, max_messages: int | None = None) -> None:
    config = AwsRuntimeConfig.from_env(require_queue=True)
    sqs = config.session().client("sqs")
    registry = PostgresRuntimeRunRegistry(Database(os.environ["HATCOMMWAYS_DATABASE_URL"]))
    consumed = 0
    while not STOP.is_set() and (max_messages is None or consumed < max_messages):
        response = sqs.receive_message(
            QueueUrl=config.queue_url, MaxNumberOfMessages=1,
            WaitTimeSeconds=20, AttributeNames=["ApproximateReceiveCount"],
        )
        for message in response.get("Messages", []):
            consume_sqs_message(message, sqs=sqs, queue_url=config.queue_url, router=router, registry=registry)
            consumed += 1


def proof_router() -> RuntimeRouter:
    """Side-effect-free handler used only for explicit transport verification."""
    return RuntimeRouter({
        "blocker.affected_work_resolved": RuntimeHandler(
            name="runtime-transport-proof",
            execute=lambda event: {"message_id": str(event.message_id), "proof": "received"},
        )
    })


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    if os.environ.get("HATCOMMWAYS_RUNTIME_PROOF_MODE") == "1":
        run(proof_router(), max_messages=int(os.environ.get("HATCOMMWAYS_RUNTIME_MAX_MESSAGES", "1")))
        return

    from .outbox_publisher import run as run_publisher
    from .runtime_handlers import production_router

    database = Database(os.environ["HATCOMMWAYS_DATABASE_URL"])
    publisher = Thread(
        target=run_publisher,
        kwargs={"stop": STOP},
        name="hatcommways-outbox-publisher",
        daemon=True,
    )
    publisher.start()
    try:
        run(production_router(database))
    finally:
        STOP.set()
        publisher.join(timeout=10)


if __name__ == "__main__":
    main()
