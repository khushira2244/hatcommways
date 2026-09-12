"""AWS transport adapters for runtime envelopes."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
from pydantic import ValidationError as PydanticValidationError

from services.planning_foundation.database import Database
from .runtime_events import RuntimeEventEnvelope

EVENT_SOURCE = "hatcommways.runtime"


@dataclass(frozen=True)
class AwsRuntimeConfig:
    region: str
    event_bus_name: str
    queue_url: str | None = None
    dlq_url: str | None = None
    profile: str | None = None

    @classmethod
    def from_env(cls, *, require_queue: bool = False) -> "AwsRuntimeConfig":
        config = cls(
            region=os.environ.get("HATCOMMWAYS_AWS_REGION", "us-east-1"),
            event_bus_name=os.environ["HATCOMMWAYS_EVENT_BUS_NAME"],
            queue_url=os.environ.get("HATCOMMWAYS_RUNTIME_QUEUE_URL"),
            dlq_url=os.environ.get("HATCOMMWAYS_RUNTIME_DLQ_URL"),
            profile=os.environ.get("AWS_PROFILE"),
        )
        if require_queue and not config.queue_url:
            raise RuntimeError("HATCOMMWAYS_RUNTIME_QUEUE_URL is required")
        return config

    def session(self):
        return boto3.Session(profile_name=self.profile, region_name=self.region)


def eventbridge_entry(event: RuntimeEventEnvelope, event_bus_name: str) -> dict[str, Any]:
    return {
        "Source": EVENT_SOURCE,
        "DetailType": event.event_type,
        "Detail": event.model_dump_json(),
        "EventBusName": event_bus_name,
        "Time": event.occurred_at,
    }


def runtime_event_from_sqs_body(body: str) -> RuntimeEventEnvelope:
    try:
        aws_event = json.loads(body)
        if aws_event.get("source") != EVENT_SOURCE or not isinstance(aws_event.get("detail"), dict):
            raise ValueError("not a Hatcommways runtime event")
        return RuntimeEventEnvelope.model_validate(aws_event["detail"])
    except (json.JSONDecodeError, PydanticValidationError, TypeError) as error:
        raise ValueError("malformed runtime transport message") from error


@dataclass(frozen=True)
class PublishBatchResult:
    selected: int
    published: int
    failed: int
    message_ids: tuple[str, ...]


class EventBridgeOutboxPublisher:
    def __init__(self, database: Database, client: Any, event_bus_name: str) -> None:
        self.database = database
        self.client = client
        self.event_bus_name = event_bus_name

    def publish_batch(self, *, limit: int = 10) -> PublishBatchResult:
        limit = max(1, min(limit, 10))
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM domain_outbox WHERE published_at IS NULL
                   ORDER BY occurred_at,id FOR UPDATE SKIP LOCKED LIMIT %s""",
                (limit,),
            ).fetchall()
            if not rows:
                return PublishBatchResult(0, 0, 0, ())
            envelopes = [RuntimeEventEnvelope.from_outbox(row) for row in rows]
            response = self.client.put_events(
                Entries=[eventbridge_entry(item, self.event_bus_name) for item in envelopes]
            )
            results = response.get("Entries", [])
            successful = [
                row["id"] for row, result in zip(rows, results, strict=False)
                if result.get("EventId") and not result.get("ErrorCode")
            ]
            if successful:
                connection.execute(
                    "UPDATE domain_outbox SET published_at=now() WHERE id=ANY(%s::uuid[])",
                    (successful,),
                )
            return PublishBatchResult(
                selected=len(rows),
                published=len(successful),
                failed=len(rows) - len(successful),
                message_ids=tuple(str(item) for item in successful),
            )
