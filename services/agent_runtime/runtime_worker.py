"""Deterministic runtime routing and a transport-neutral worker boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from services.planning_foundation.database import Database

from .runtime_events import RuntimeEventEnvelope


CORE_RUNTIME_EVENTS = frozenset({
    "human_update.submitted",
    "human_update.interpreted",
    "blocker_assessment.assessed",
    "blocker.affected_work_resolved",
    "coordination.requested",
    "coordination.proposed",
    "replan.requested",
    "replan.proposed",
    "replan.approved",
    "replan.rejected",
    "blocker.cleared",
})


class RuntimeRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"
    DEAD_LETTERED = "DEAD_LETTERED"


class RetryableRuntimeError(RuntimeError):
    """A handler failure which a later transport may redeliver."""


@dataclass(frozen=True)
class RuntimeHandler:
    name: str
    execute: Callable[[RuntimeEventEnvelope], dict[str, Any] | None]
    max_attempts: int = 3
    policy_reference: str = "bounded-default-v1"


@dataclass(frozen=True)
class RuntimeConsumptionResult:
    run_id: UUID
    status: RuntimeRunStatus
    handler_name: str
    attempt: int
    reused: bool
    output_reference: dict[str, Any] | None = None


class RuntimeRouter:
    def __init__(self, handlers: dict[str, RuntimeHandler]) -> None:
        unsupported = set(handlers) - CORE_RUNTIME_EVENTS
        if unsupported:
            raise ValueError(f"unsupported runtime event routes: {sorted(unsupported)}")
        self._handlers = dict(handlers)

    def route(self, event: RuntimeEventEnvelope) -> RuntimeHandler:
        handler = self._handlers.get(event.event_type)
        if handler is None:
            raise ValueError(f"no runtime handler registered for {event.event_type}")
        return handler


class RuntimeRunRegistry(Protocol):
    def claim(self, event: RuntimeEventEnvelope, handler: RuntimeHandler, fingerprint: str) -> RuntimeConsumptionResult: ...
    def succeed(self, run_id: UUID, output_reference: dict[str, Any] | None) -> RuntimeConsumptionResult: ...
    def fail(self, run_id: UUID, error: Exception, *, retryable: bool) -> RuntimeConsumptionResult: ...


class PostgresRuntimeRunRegistry:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _result(row: dict[str, Any], *, reused: bool) -> RuntimeConsumptionResult:
        return RuntimeConsumptionResult(
            run_id=row["id"], status=RuntimeRunStatus(row["status"]),
            handler_name=row["handler_name"], attempt=row["attempt"], reused=reused,
            output_reference=row.get("output_reference"),
        )

    def claim(self, event: RuntimeEventEnvelope, handler: RuntimeHandler, fingerprint: str) -> RuntimeConsumptionResult:
        with self.database.connect() as connection:
            row = connection.execute(
                """INSERT INTO runtime_agent_runs(
                       id,message_id,event_type,handler_name,status,attempt,max_attempts,
                       policy_reference,started_at,correlation_id,causation_id,
                       idempotency_key,input_fingerprint)
                   VALUES(%s,%s,%s,%s,'RUNNING',1,%s,%s,now(),%s,%s,%s,%s)
                   ON CONFLICT (message_id,handler_name) DO NOTHING RETURNING *""",
                (uuid4(), event.message_id, event.event_type, handler.name,
                 handler.max_attempts, handler.policy_reference, event.correlation_id,
                 event.causation_id, event.idempotency_key, fingerprint),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM runtime_agent_runs WHERE message_id=%s AND handler_name=%s FOR UPDATE",
                    (event.message_id, handler.name),
                ).fetchone()
                if row["input_fingerprint"] != fingerprint:
                    raise ValueError("runtime message replay has different content")
                if row["status"] != RuntimeRunStatus.RETRYABLE or row["attempt"] >= row["max_attempts"]:
                    return self._result(row, reused=True)
                row = connection.execute(
                    """UPDATE runtime_agent_runs SET status='RUNNING',attempt=attempt+1,
                              started_at=now(),completed_at=NULL,last_error_code=NULL,
                              last_error_message=NULL,next_retry_at=NULL,updated_at=now()
                       WHERE id=%s RETURNING *""",
                    (row["id"],),
                ).fetchone()
                return self._result(row, reused=False)
            return self._result(row, reused=False)

    def succeed(self, run_id: UUID, output_reference: dict[str, Any] | None) -> RuntimeConsumptionResult:
        with self.database.connect() as connection:
            row = connection.execute(
                """UPDATE runtime_agent_runs SET status='SUCCEEDED',completed_at=now(),
                          output_reference=%s,updated_at=now() WHERE id=%s RETURNING *""",
                (Jsonb(output_reference) if output_reference is not None else None, run_id),
            ).fetchone()
            return self._result(row, reused=False)

    def fail(self, run_id: UUID, error: Exception, *, retryable: bool) -> RuntimeConsumptionResult:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM runtime_agent_runs WHERE id=%s FOR UPDATE", (run_id,)).fetchone()
            status = RuntimeRunStatus.RETRYABLE if retryable and row["attempt"] < row["max_attempts"] else RuntimeRunStatus.FAILED
            row = connection.execute(
                """UPDATE runtime_agent_runs SET status=%s,completed_at=now(),
                          last_error_code=%s,last_error_message=%s,updated_at=now()
                   WHERE id=%s RETURNING *""",
                (status.value, type(error).__name__[:100], str(error)[:1000], run_id),
            ).fetchone()
            return self._result(row, reused=False)


class InMemoryRuntimeRunRegistry:
    """Local transport proof with the same claim/outcome semantics as PostgreSQL."""

    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, str], dict[str, Any]] = {}

    def claim(self, event: RuntimeEventEnvelope, handler: RuntimeHandler, fingerprint: str) -> RuntimeConsumptionResult:
        key = (event.message_id, handler.name)
        row = self.rows.get(key)
        if row:
            if row["fingerprint"] != fingerprint:
                raise ValueError("runtime message replay has different content")
            if row["status"] == RuntimeRunStatus.RETRYABLE and row["attempt"] < row["max_attempts"]:
                row["attempt"] += 1
                row["status"] = RuntimeRunStatus.RUNNING
                return RuntimeConsumptionResult(row["id"], row["status"], handler.name, row["attempt"], False)
            return RuntimeConsumptionResult(row["id"], row["status"], handler.name, row["attempt"], True, row.get("output"))
        row = {"id": uuid4(), "status": RuntimeRunStatus.RUNNING, "attempt": 1,
               "max_attempts": handler.max_attempts, "fingerprint": fingerprint,
               "handler": handler.name, "correlation_id": event.correlation_id,
               "causation_id": event.causation_id, "idempotency_key": event.idempotency_key}
        self.rows[key] = row
        return RuntimeConsumptionResult(row["id"], row["status"], handler.name, 1, False)

    def succeed(self, run_id: UUID, output_reference: dict[str, Any] | None) -> RuntimeConsumptionResult:
        row = next(row for row in self.rows.values() if row["id"] == run_id)
        row.update(status=RuntimeRunStatus.SUCCEEDED, output=output_reference)
        return RuntimeConsumptionResult(run_id, row["status"], row["handler"], row["attempt"], False, output_reference)

    def fail(self, run_id: UUID, error: Exception, *, retryable: bool) -> RuntimeConsumptionResult:
        row = next(row for row in self.rows.values() if row["id"] == run_id)
        row["status"] = RuntimeRunStatus.RETRYABLE if retryable and row["attempt"] < row["max_attempts"] else RuntimeRunStatus.FAILED
        return RuntimeConsumptionResult(run_id, row["status"], row["handler"], row["attempt"], False)


def input_fingerprint(event: RuntimeEventEnvelope, handler_name: str) -> str:
    encoded = json.dumps(
        {"event": event.model_dump(mode="json"), "handler": handler_name},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def consume_runtime_event(
    event: RuntimeEventEnvelope | dict[str, Any],
    *,
    router: RuntimeRouter,
    registry: RuntimeRunRegistry,
) -> RuntimeConsumptionResult:
    envelope = event if isinstance(event, RuntimeEventEnvelope) else RuntimeEventEnvelope.model_validate(event)
    handler = router.route(envelope)
    claimed = registry.claim(envelope, handler, input_fingerprint(envelope, handler.name))
    if claimed.reused:
        return claimed
    try:
        output_reference = handler.execute(envelope)
    except Exception as error:
        return registry.fail(claimed.run_id, error, retryable=isinstance(error, RetryableRuntimeError))
    return registry.succeed(claimed.run_id, output_reference)
