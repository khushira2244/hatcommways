"""Validated persistence and deterministic blocker boundary for impact assessments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .database import Database
from .errors import IdempotencyConflictError, NotFoundError, ValidationError
from .human_update_interpretation_service import HumanUpdateInterpretationService
from .human_update_models import (
    BlockerAssessment,
    BlockerAssessmentContext,
    BlockerAssessmentInterpretation,
    BlockerAssessmentSnapshot,
    BlockerCreate,
    HumanUpdateInterpretation,
    HumanUpdateInterpretationSnapshot,
)
from .human_update_service import HumanUpdateService
from .services import PlanningService


@dataclass(frozen=True)
class BlockerAssessmentStart:
    interpretation: HumanUpdateInterpretationSnapshot
    existing: BlockerAssessmentSnapshot | None


class BlockerAssessmentService:
    def __init__(self, database: Database):
        self.database = database
        self.human_updates = HumanUpdateService(database)
        self.interpretations = HumanUpdateInterpretationService(database)

    @staticmethod
    def _assessment(row: dict[str, Any]) -> BlockerAssessmentSnapshot:
        return BlockerAssessmentSnapshot.model_validate(row)

    def get_assessment(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> BlockerAssessmentSnapshot | None:
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
                """SELECT a.* FROM blocker_assessments a
                   JOIN human_update_interpretations i ON i.id=a.interpretation_id
                   WHERE a.event_id=%s AND a.human_update_id=%s""",
                (event_id, update_id),
            ).fetchone()
            return self._assessment(row) if row else None

    def begin(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID, *, retry: bool
    ) -> BlockerAssessmentStart:
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            update = connection.execute(
                "SELECT * FROM human_updates WHERE id=%s AND event_id=%s FOR UPDATE",
                (update_id, event_id),
            ).fetchone()
            if update is None:
                raise NotFoundError("human update not found in this event")
            interpretation = connection.execute(
                """SELECT * FROM human_update_interpretations
                   WHERE human_update_id=%s AND event_id=%s FOR UPDATE""",
                (update_id, event_id),
            ).fetchone()
            if update["interpretation_status"] != "INTERPRETED" or interpretation is None:
                raise ValidationError("a persisted successful interpretation is required")
            existing = connection.execute(
                "SELECT * FROM blocker_assessments WHERE interpretation_id=%s",
                (interpretation["id"],),
            ).fetchone()
            if existing:
                return BlockerAssessmentStart(
                    interpretation=self.interpretations._interpretation(interpretation),
                    existing=self._assessment(existing),
                )
            status = interpretation["blocker_assessment_status"]
            if status == "RUNNING":
                raise IdempotencyConflictError("blocker assessment is already running")
            if status == "FAILED" and not retry:
                raise IdempotencyConflictError(
                    "explicit retry is required after blocker assessment failure"
                )
            if status not in ("NOT_REQUESTED", "FAILED"):
                raise IdempotencyConflictError("blocker assessment is not eligible to run")
            interpretation = connection.execute(
                """UPDATE human_update_interpretations
                   SET blocker_assessment_status='RUNNING',
                       blocker_assessment_failed_at=NULL,
                       blocker_assessment_failure_code=NULL,
                       blocker_assessment_attempt_count=blocker_assessment_attempt_count+1
                   WHERE id=%s RETURNING *""",
                (interpretation["id"],),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="blocker_assessment.requested",
                aggregate_type="BLOCKER_ASSESSMENT",
                aggregate_id=interpretation["id"],
                aggregate_version=interpretation["blocker_assessment_attempt_count"],
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "interpretation_id": str(interpretation["id"]),
                    "attempt": interpretation["blocker_assessment_attempt_count"],
                },
                correlation_id=correlation_id,
            )
            return BlockerAssessmentStart(
                interpretation=self.interpretations._interpretation(interpretation),
                existing=None,
            )

    def context(
        self, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> BlockerAssessmentContext:
        source = self.interpretations.context(event_id, update_id, organizer_id)
        interpretation = self.interpretations.get_interpretation(
            event_id, update_id, organizer_id
        )
        if interpretation is None:
            raise ValidationError("a persisted successful interpretation is required")
        meetings: list[dict[str, Any]] = []
        if source.work or source.stage:
            with self.database.connect() as connection:
                rows = connection.execute(
                    """SELECT id,title,meeting_type,start_time,end_time,location,status,
                              stage_id,work_id
                       FROM event_meetings
                       WHERE event_id=%s AND status<>'CANCELLED'
                         AND ((%s::uuid IS NOT NULL AND work_id=%s)
                           OR (%s::uuid IS NOT NULL AND work_id IS NULL AND stage_id=%s))
                       ORDER BY start_time,id""",
                    (
                        event_id,
                        source.work["id"] if source.work else None,
                        source.work["id"] if source.work else None,
                        source.stage["id"] if source.stage else None,
                        source.stage["id"] if source.stage else None,
                    ),
                ).fetchall()
                meetings = [dict(row) for row in rows]
        return BlockerAssessmentContext(
            event_id=event_id,
            human_update_id=update_id,
            original_text=source.original_text,
            reporter_relationship=source.reporter_relationship,
            reporter_display_name=source.reporter_display_name,
            interpretation=BlockerAssessmentInterpretation.model_validate(
                {
                    "id": interpretation.id,
                    **{
                        key: getattr(interpretation, key)
                        for key in HumanUpdateInterpretation.model_fields
                    },
                }
            ),
            stage=source.stage,
            work=source.work,
            accepted_participation=source.accepted_participation,
            directly_relevant_meetings=meetings,
        )

    @staticmethod
    def validate(assessment: BlockerAssessment, context: BlockerAssessmentContext) -> None:
        if assessment.event_id != context.event_id:
            raise ValidationError("assessment targets the wrong event")
        if assessment.human_update_id != context.human_update_id:
            raise ValidationError("assessment targets the wrong human update")
        if assessment.interpretation_id != context.interpretation.id:
            raise ValidationError("assessment targets the wrong interpretation")
        allowed_stage = context.stage["id"] if context.stage else None
        allowed_work = context.work["id"] if context.work else None
        if assessment.directly_referenced_stage_id not in (None, allowed_stage):
            raise ValidationError("assessment referenced a stage outside its scoped context")
        if assessment.directly_referenced_work_id not in (None, allowed_work):
            raise ValidationError("assessment referenced work outside its scoped context")
        if (
            assessment.directly_referenced_work_id is not None
            and assessment.directly_referenced_stage_id is not None
            and context.work["stage_id"] != assessment.directly_referenced_stage_id
        ):
            raise ValidationError("assessment work and stage references do not agree")
        if context.interpretation.requires_clarification and (
            not assessment.requires_clarification or assessment.is_execution_blocker
        ):
            raise ValidationError(
                "an unresolved interpretation must remain clarification-only"
            )

    def complete(
        self,
        event_id: UUID,
        update_id: UUID,
        organizer_id: UUID,
        assessment: BlockerAssessment,
        *,
        provider_name: str,
        model_id: str,
        agent_name: str,
        agent_version: str,
        stop_reason: str,
        usage: dict[str, int],
    ) -> BlockerAssessmentSnapshot:
        context = self.context(event_id, update_id, organizer_id)
        self.validate(assessment, context)
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            update = connection.execute(
                "SELECT * FROM human_updates WHERE id=%s AND event_id=%s FOR UPDATE",
                (update_id, event_id),
            ).fetchone()
            interpretation = connection.execute(
                """SELECT * FROM human_update_interpretations
                   WHERE id=%s AND human_update_id=%s AND event_id=%s FOR UPDATE""",
                (assessment.interpretation_id, update_id, event_id),
            ).fetchone()
            existing = connection.execute(
                "SELECT * FROM blocker_assessments WHERE interpretation_id=%s",
                (assessment.interpretation_id,),
            ).fetchone()
            if existing:
                return self._assessment(existing)
            if (
                update is None
                or update["interpretation_status"] != "INTERPRETED"
                or interpretation is None
                or interpretation["blocker_assessment_status"] != "RUNNING"
            ):
                raise IdempotencyConflictError("blocker assessment is not running")

            blocker_id = None
            if assessment.is_execution_blocker and not assessment.requires_clarification:
                blocker = self.human_updates._create_blocker(
                    connection,
                    event_id,
                    organizer_id,
                    BlockerCreate(
                        human_update_id=update_id,
                        title=f"{assessment.blocker_kind.value.title()} execution blocker",
                        summary=assessment.concise_reason,
                        category=assessment.blocker_kind.value,
                        stage_id=assessment.directly_referenced_stage_id,
                        work_id=assessment.directly_referenced_work_id,
                        idempotency_key=f"blocker-assessment:{assessment.interpretation_id}",
                    ),
                    reuse_existing_source=True,
                )
                blocker_id = blocker.id

            assessed_stage_id = assessment.directly_referenced_stage_id
            if assessed_stage_id is None and assessment.directly_referenced_work_id is not None:
                assessed_stage_id = context.work["stage_id"]
            assessed_stage_version = None
            if assessed_stage_id is not None:
                assessed_stage_version = connection.execute(
                    "SELECT version FROM stages WHERE id=%s AND event_id=%s",
                    (assessed_stage_id, event_id),
                ).fetchone()["version"]
            assessed_work_version = None
            if assessment.directly_referenced_work_id is not None:
                assessed_work_version = connection.execute(
                    "SELECT version FROM work_items WHERE id=%s AND event_id=%s",
                    (assessment.directly_referenced_work_id, event_id),
                ).fetchone()["version"]

            values = assessment.model_dump(mode="python")
            row = connection.execute(
                """INSERT INTO blocker_assessments(
                       id,event_id,human_update_id,interpretation_id,is_execution_blocker,
                       blocker_kind,concise_reason,directly_referenced_stage_id,
                       directly_referenced_work_id,severity_internal,urgency_internal,
                       coordination_needed,replanning_may_be_needed,requires_clarification,
                       clarification_question,confidence,authoritative_blocker_id,
                       provider_name,model_id,agent_name,agent_version,stop_reason,usage,
                       assessed_event_version,assessed_stage_version,assessed_work_version)
                   VALUES(%(id)s,%(event_id)s,%(human_update_id)s,%(interpretation_id)s,
                       %(is_execution_blocker)s,%(blocker_kind)s,%(concise_reason)s,
                       %(directly_referenced_stage_id)s,%(directly_referenced_work_id)s,
                       %(severity_internal)s,%(urgency_internal)s,%(coordination_needed)s,
                       %(replanning_may_be_needed)s,%(requires_clarification)s,
                       %(clarification_question)s,%(confidence)s,%(authoritative_blocker_id)s,
                       %(provider_name)s,%(model_id)s,%(agent_name)s,%(agent_version)s,
                       %(stop_reason)s,%(usage)s,%(assessed_event_version)s,
                       %(assessed_stage_version)s,%(assessed_work_version)s)
                   RETURNING *""",
                {
                    "id": uuid4(),
                    **values,
                    "blocker_kind": assessment.blocker_kind.value,
                    "severity_internal": assessment.severity_internal.value,
                    "urgency_internal": assessment.urgency_internal.value,
                    "authoritative_blocker_id": blocker_id,
                    "provider_name": provider_name,
                    "model_id": model_id,
                    "agent_name": agent_name,
                    "agent_version": agent_version,
                    "stop_reason": stop_reason,
                    "usage": Jsonb(usage),
                    "assessed_event_version": event["version"],
                    "assessed_stage_version": assessed_stage_version,
                    "assessed_work_version": assessed_work_version,
                },
            ).fetchone()
            connection.execute(
                """UPDATE human_update_interpretations
                   SET blocker_assessment_status='ASSESSED',
                       blocker_assessment_failed_at=NULL,
                       blocker_assessment_failure_code=NULL
                   WHERE id=%s""",
                (assessment.interpretation_id,),
            )
            PlanningService._enqueue_outbox(
                connection,
                event_type="blocker_assessment.assessed",
                aggregate_type="BLOCKER_ASSESSMENT",
                aggregate_id=row["id"],
                aggregate_version=1,
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "interpretation_id": str(assessment.interpretation_id),
                    "assessment_id": str(row["id"]),
                    "authoritative_blocker_id": str(blocker_id) if blocker_id else None,
                    "provider_name": provider_name,
                    "model_id": model_id,
                    "agent_name": agent_name,
                    "agent_version": agent_version,
                },
                correlation_id=correlation_id,
            )
            return self._assessment(row)

    def fail(self, event_id: UUID, update_id: UUID, failure_code: str) -> None:
        correlation_id = uuid4()
        safe_code = failure_code[:100]
        with self.database.connect() as connection:
            interpretation = connection.execute(
                """SELECT i.* FROM human_update_interpretations i
                   JOIN human_updates h ON h.id=i.human_update_id AND h.event_id=i.event_id
                   WHERE i.human_update_id=%s AND i.event_id=%s FOR UPDATE OF i""",
                (update_id, event_id),
            ).fetchone()
            if interpretation is None:
                raise NotFoundError("successful interpretation not found in this event")
            if interpretation["blocker_assessment_status"] != "RUNNING":
                return
            connection.execute(
                """UPDATE human_update_interpretations
                   SET blocker_assessment_status='FAILED',
                       blocker_assessment_failed_at=now(),
                       blocker_assessment_failure_code=%s
                   WHERE id=%s""",
                (safe_code, interpretation["id"]),
            )
            PlanningService._enqueue_outbox(
                connection,
                event_type="blocker_assessment.failed",
                aggregate_type="BLOCKER_ASSESSMENT",
                aggregate_id=interpretation["id"],
                aggregate_version=interpretation["blocker_assessment_attempt_count"],
                payload={
                    "event_id": str(event_id),
                    "human_update_id": str(update_id),
                    "interpretation_id": str(interpretation["id"]),
                    "failure_code": safe_code,
                },
                correlation_id=correlation_id,
            )
