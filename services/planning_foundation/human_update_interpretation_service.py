"""Validated persistence boundary for AI-derived human update interpretations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .database import Database
from .errors import IdempotencyConflictError, NotFoundError, ValidationError
from .human_update_models import (
    HumanUpdateInterpretation,
    HumanUpdateInterpretationContext,
    HumanUpdateInterpretationSnapshot,
    HumanUpdateSnapshot,
)
from .human_update_service import HumanUpdateService
from .services import PlanningService


@dataclass(frozen=True)
class InterpretationStart:
    update: HumanUpdateSnapshot
    existing: HumanUpdateInterpretationSnapshot | None


class HumanUpdateInterpretationService:
    def __init__(self, database: Database):
        self.database = database
        self.human_updates = HumanUpdateService(database)

    @staticmethod
    def _interpretation(row: dict[str, Any]) -> HumanUpdateInterpretationSnapshot:
        return HumanUpdateInterpretationSnapshot.model_validate(
            {
                "update_id": row["human_update_id"],
                **{
                    key: row[key]
                    for key in HumanUpdateInterpretationSnapshot.model_fields
                    if key != "update_id"
                },
            }
        )

    def get_interpretation(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> HumanUpdateInterpretationSnapshot | None:
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id)
            self.human_updates._require_organizer(connection, event, organizer_id)
            update = connection.execute(
                "SELECT 1 FROM human_updates WHERE id=%s AND event_id=%s",
                (update_id, event_id),
            ).fetchone()
            if update is None:
                raise NotFoundError("human update not found in this event")
            row = connection.execute(
                "SELECT * FROM human_update_interpretations WHERE human_update_id=%s",
                (update_id,),
            ).fetchone()
            return self._interpretation(row) if row else None

    def begin(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID, *, retry: bool
    ) -> InterpretationStart:
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            row = connection.execute(
                "SELECT * FROM human_updates WHERE id=%s AND event_id=%s FOR UPDATE",
                (update_id, event_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("human update not found in this event")
            existing = connection.execute(
                "SELECT * FROM human_update_interpretations WHERE human_update_id=%s",
                (update_id,),
            ).fetchone()
            if existing:
                return InterpretationStart(
                    update=self.human_updates._report(row),
                    existing=self._interpretation(existing),
                )
            if row["interpretation_status"] == "RUNNING":
                raise IdempotencyConflictError("human update interpretation is already running")
            if row["interpretation_status"] == "FAILED" and not retry:
                raise IdempotencyConflictError("explicit retry is required after interpretation failure")
            if row["interpretation_status"] not in ("NOT_REQUESTED", "FAILED"):
                raise IdempotencyConflictError("human update interpretation is not eligible to run")
            row = connection.execute(
                """UPDATE human_updates SET interpretation_status='RUNNING',
                       interpreted_at=NULL,interpretation_failed_at=NULL,
                       interpretation_failure_code=NULL,
                       interpretation_attempt_count=interpretation_attempt_count+1,
                       version=version+1
                   WHERE id=%s RETURNING *""",
                (update_id,),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="human_update.interpretation_requested",
                aggregate_type="HUMAN_UPDATE",
                aggregate_id=update_id,
                aggregate_version=row["version"],
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "attempt": row["interpretation_attempt_count"],
                },
                correlation_id=correlation_id,
            )
            return InterpretationStart(update=self.human_updates._report(row), existing=None)

    def context(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> HumanUpdateInterpretationContext:
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id)
            self.human_updates._require_organizer(connection, event, organizer_id)
            update = connection.execute(
                """SELECT h.*,a.display_name FROM human_updates h
                   JOIN accounts a ON a.id=h.reporter_account_id
                   WHERE h.id=%s AND h.event_id=%s""",
                (update_id, event_id),
            ).fetchone()
            if update is None:
                raise NotFoundError("human update not found in this event")
            stage = None
            if update["stage_id"]:
                row = connection.execute(
                    "SELECT id,canonical_name,starts_at,ends_at FROM stages WHERE id=%s AND event_id=%s",
                    (update["stage_id"], event_id),
                ).fetchone()
                stage = dict(row) if row else None
            work = None
            if update["work_id"]:
                row = connection.execute(
                    """SELECT id,stage_id,canonical_name,starts_at,ends_at
                       FROM work_items WHERE id=%s AND event_id=%s""",
                    (update["work_id"], event_id),
                ).fetchone()
                work = dict(row) if row else None
            participation = None
            if update["source_type"] == "ACTOR":
                row = connection.execute(
                    """SELECT id,stage_id,work_id,actor_requirement_id,approved_start,approved_end
                       FROM participations WHERE event_id=%s AND account_id=%s AND status='ACCEPTED'
                         AND (%s::uuid IS NULL OR id=%s)
                         AND (%s::uuid IS NULL OR work_id=%s)
                       ORDER BY created_at LIMIT 1""",
                    (
                        event_id,
                        update["reporter_account_id"],
                        update["participation_id"],
                        update["participation_id"],
                        update["work_id"],
                        update["work_id"],
                    ),
                ).fetchone()
                participation = dict(row) if row else None
            return HumanUpdateInterpretationContext(
                update_id=update_id,
                event_id=event_id,
                original_text=update["original_text"],
                reporter_relationship=update["source_type"],
                reporter_display_name=update["display_name"],
                event_name=event["name"],
                event_starts_at=event["starts_at"],
                event_ends_at=event["ends_at"],
                event_timezone=event["timezone"],
                event_location=event["location_description"],
                stage=stage,
                work=work,
                accepted_participation=participation,
            )

    @staticmethod
    def validate(
        interpretation: HumanUpdateInterpretation,
        context: HumanUpdateInterpretationContext,
    ) -> None:
        if interpretation.update_id != context.update_id or interpretation.event_id != context.event_id:
            raise ValidationError("interpretation targets the wrong human update or event")
        allowed_stage = context.stage["id"] if context.stage else None
        allowed_work = context.work["id"] if context.work else None
        if interpretation.referenced_stage_id not in (None, allowed_stage):
            raise ValidationError("interpretation referenced a stage outside its scoped context")
        if interpretation.referenced_work_id not in (None, allowed_work):
            raise ValidationError("interpretation referenced work outside its scoped context")
        if (
            interpretation.referenced_work_id is not None
            and interpretation.referenced_stage_id is not None
            and context.work["stage_id"] != interpretation.referenced_stage_id
        ):
            raise ValidationError("interpretation work and stage references do not agree")

    def complete(
        self,
        event_id: UUID,
        update_id: UUID,
        organizer_id: UUID,
        interpretation: HumanUpdateInterpretation,
        *,
        provider_name: str,
        model_id: str,
        agent_name: str,
        agent_version: str,
        stop_reason: str,
        usage: dict[str, int],
    ) -> HumanUpdateInterpretationSnapshot:
        context = self.context(event_id, update_id, organizer_id)
        self.validate(interpretation, context)
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            update = connection.execute(
                "SELECT * FROM human_updates WHERE id=%s AND event_id=%s FOR UPDATE",
                (update_id, event_id),
            ).fetchone()
            existing = connection.execute(
                "SELECT * FROM human_update_interpretations WHERE human_update_id=%s",
                (update_id,),
            ).fetchone()
            if existing:
                return self._interpretation(existing)
            if update is None or update["interpretation_status"] != "RUNNING":
                raise IdempotencyConflictError("human update interpretation is not running")
            values = interpretation.model_dump(mode="python")
            row = connection.execute(
                """INSERT INTO human_update_interpretations(
                       id,human_update_id,event_id,interpretation_type,concise_summary,
                       reported_condition,temporal_signal,location_signal,referenced_stage_id,
                       referenced_work_id,possible_blocker,blocker_reason,confidence,
                       requires_clarification,clarification_question,provider_name,model_id,
                       agent_name,agent_version,stop_reason,usage)
                   VALUES(%(id)s,%(update_id)s,%(event_id)s,%(interpretation_type)s,
                       %(concise_summary)s,%(reported_condition)s,%(temporal_signal)s,
                       %(location_signal)s,%(referenced_stage_id)s,%(referenced_work_id)s,
                       %(possible_blocker)s,%(blocker_reason)s,%(confidence)s,
                       %(requires_clarification)s,%(clarification_question)s,%(provider_name)s,
                       %(model_id)s,%(agent_name)s,%(agent_version)s,%(stop_reason)s,%(usage)s)
                   RETURNING *""",
                {
                    "id": uuid4(),
                    **values,
                    "interpretation_type": interpretation.interpretation_type.value,
                    "provider_name": provider_name,
                    "model_id": model_id,
                    "agent_name": agent_name,
                    "agent_version": agent_version,
                    "stop_reason": stop_reason,
                    "usage": Jsonb(usage),
                },
            ).fetchone()
            updated = connection.execute(
                """UPDATE human_updates SET interpretation_status='INTERPRETED',
                       interpreted_at=now(),interpretation_failed_at=NULL,
                       interpretation_failure_code=NULL,version=version+1
                   WHERE id=%s RETURNING version""",
                (update_id,),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="human_update.interpreted",
                aggregate_type="HUMAN_UPDATE",
                aggregate_id=update_id,
                aggregate_version=updated["version"],
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "interpretation_id": str(row["id"]),
                    "provider_name": provider_name,
                    "model_id": model_id,
                    "agent_name": agent_name,
                    "agent_version": agent_version,
                },
                correlation_id=correlation_id,
            )
            return self._interpretation(row)

    def fail(self, event_id: UUID, update_id: UUID, failure_code: str) -> None:
        correlation_id = uuid4()
        safe_code = failure_code[:100]
        with self.database.connect() as connection:
            update = connection.execute(
                "SELECT * FROM human_updates WHERE id=%s AND event_id=%s FOR UPDATE",
                (update_id, event_id),
            ).fetchone()
            if update is None:
                raise NotFoundError("human update not found in this event")
            if update["interpretation_status"] != "RUNNING":
                return
            updated = connection.execute(
                """UPDATE human_updates SET interpretation_status='FAILED',
                       interpreted_at=NULL,interpretation_failed_at=now(),
                       interpretation_failure_code=%s,version=version+1
                   WHERE id=%s RETURNING version""",
                (safe_code, update_id),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="human_update.interpretation_failed",
                aggregate_type="HUMAN_UPDATE",
                aggregate_id=update_id,
                aggregate_version=updated["version"],
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "failure_code": safe_code,
                },
                correlation_id=correlation_id,
            )
