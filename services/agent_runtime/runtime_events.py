"""Typed runtime envelopes built from the existing PostgreSQL domain outbox."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RuntimeEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    event_type: str = Field(min_length=1, max_length=200)
    aggregate_type: str = Field(min_length=1, max_length=100)
    aggregate_id: UUID
    tenant_id: UUID | None = None
    occurred_at: datetime
    correlation_id: UUID
    causation_id: UUID | None = None
    idempotency_key: str = Field(min_length=1, max_length=300)
    payload: dict[str, Any]
    schema_version: int = Field(default=1, ge=1)

    @classmethod
    def from_outbox(cls, row: dict[str, Any]) -> "RuntimeEventEnvelope":
        message_id = UUID(str(row["id"]))
        return cls(
            message_id=message_id,
            event_type=row["event_type"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            occurred_at=row["occurred_at"],
            correlation_id=row["correlation_id"],
            causation_id=row.get("causation_id"),
            idempotency_key=f"runtime-message:{message_id}",
            payload=dict(row["payload"]),
        )

    def followup(
        self,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> "RuntimeEventEnvelope":
        return RuntimeEventEnvelope(
            message_id=uuid4(),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(timezone.utc),
            correlation_id=self.correlation_id,
            causation_id=self.message_id,
            idempotency_key=idempotency_key,
            payload=payload,
            schema_version=self.schema_version,
        )
