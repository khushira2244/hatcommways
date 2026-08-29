"""Scoped read-only tools for future Level 1 reasoning agents."""

from __future__ import annotations

from uuid import UUID

from .errors import AuthorizationError, StaleProposalError
from .models import EventBrief, StageWorkContext, WorkActorContext
from .services import PlanningService


class ScopedPlanningReadTools:
    def __init__(self, service: PlanningService) -> None:
        self.service = service

    def get_event_brief(
        self,
        *,
        event_id: UUID,
        organizer_id: UUID,
        expected_version: int,
    ) -> EventBrief:
        event = self.service.get_event(event_id)
        if event.organizer_id != organizer_id:
            raise AuthorizationError("event brief scope is not authorized")
        if event.version != expected_version:
            raise StaleProposalError("event brief requested at a stale version")
        return EventBrief(
            event_id=event.id,
            name=event.name,
            purpose=event.purpose,
            event_type=event.event_type,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            timezone=event.timezone,
            location_description=event.location_description,
            version=event.version,
        )

    def get_stage_work_context(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        organizer_id: UUID,
        expected_event_version: int,
        expected_stage_version: int,
    ) -> StageWorkContext:
        with self.service.database.connect() as connection:
            row = connection.execute(
                """
                SELECT e.id AS event_id, e.organizer_id,
                       e.name AS event_name, e.purpose AS event_purpose,
                       e.event_type, e.version AS event_version,
                       s.id AS stage_id, s.canonical_name AS stage_name,
                       s.purpose AS stage_purpose, s.starts_at AS stage_start,
                       s.ends_at AS stage_end, s.version AS stage_version
                FROM stages s
                JOIN events e ON e.id = s.event_id
                WHERE e.id = %s AND s.id = %s
                """,
                (event_id, stage_id),
            ).fetchone()
        if row is None:
            raise AuthorizationError("targeted stage context is unavailable")
        if row["organizer_id"] != organizer_id:
            raise AuthorizationError("stage work context scope is not authorized")
        if row["event_version"] != expected_event_version:
            raise StaleProposalError("event context requested at a stale version")
        if row["stage_version"] != expected_stage_version:
            raise StaleProposalError("stage context requested at a stale version")
        row.pop("organizer_id")
        return StageWorkContext.model_validate(row)

    def get_work_actor_context(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        work_id: UUID,
        organizer_id: UUID,
        expected_event_version: int,
        expected_stage_version: int,
        expected_work_version: int,
    ) -> WorkActorContext:
        with self.service.database.connect() as connection:
            row = connection.execute(
                """
                SELECT e.id AS event_id, e.organizer_id,
                       e.name AS event_name, e.purpose AS event_purpose,
                       e.event_type, e.version AS event_version,
                       s.id AS stage_id, s.canonical_name AS stage_name,
                       s.purpose AS stage_purpose, s.version AS stage_version,
                       w.id AS work_id, w.canonical_name AS work_name,
                       w.purpose AS work_purpose,
                       w.estimated_person_hours, w.work_share,
                       w.starts_at AS work_start, w.ends_at AS work_end,
                       w.version AS work_version
                FROM work_items w
                JOIN stages s ON s.id = w.stage_id
                JOIN events e ON e.id = w.event_id
                WHERE e.id = %s AND s.id = %s AND w.id = %s
                """,
                (event_id, stage_id, work_id),
            ).fetchone()
        if row is None:
            raise AuthorizationError("targeted work context is unavailable")
        if row["organizer_id"] != organizer_id:
            raise AuthorizationError("work actor context scope is not authorized")
        if row["event_version"] != expected_event_version:
            raise StaleProposalError("event context requested at a stale version")
        if row["stage_version"] != expected_stage_version:
            raise StaleProposalError("stage context requested at a stale version")
        if row["work_version"] != expected_work_version:
            raise StaleProposalError("work context requested at a stale version")
        row.pop("organizer_id")
        return WorkActorContext.model_validate(row)
