"""Authenticated account adapters over frozen deterministic planning services."""

from __future__ import annotations

from uuid import UUID, uuid4

from services.planning_foundation.database import Database
from services.planning_foundation.errors import AuthorizationError
from services.planning_foundation.models import EventCreate, EventSnapshot
from services.planning_foundation.services import PlanningService


class AccountAuthorizationService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_event_for_account(
        self,
        command: EventCreate,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> EventSnapshot:
        event_id = uuid4()
        correlation_id = correlation_id or uuid4()
        with self.database.connect() as connection:
            account = connection.execute(
                "SELECT id,status FROM accounts WHERE id=%s FOR SHARE",
                (command.organizer_id,),
            ).fetchone()
            if account is None or account["status"] != "ACTIVE":
                raise AuthorizationError("authenticated account is not active")
            row = connection.execute(
                """
                INSERT INTO events (
                    id, organizer_id, name, purpose, event_type, starts_at,
                    ends_at, timezone, location_description
                ) VALUES (
                    %(id)s, %(organizer_id)s, %(name)s, %(purpose)s,
                    %(event_type)s, %(starts_at)s, %(ends_at)s, %(timezone)s,
                    %(location_description)s
                ) RETURNING *
                """,
                {"id": event_id, **command.model_dump()},
            ).fetchone()
            connection.execute(
                """
                INSERT INTO event_memberships (event_id,account_id,role,status)
                VALUES (%s,%s,'ORGANIZER','ACTIVE')
                """,
                (event_id, command.organizer_id),
            )
            PlanningService._enqueue_outbox(
                connection,
                event_type="event.created",
                aggregate_type="EVENT",
                aggregate_id=event_id,
                aggregate_version=1,
                payload={
                    "event_id": str(event_id),
                    "organizer_id": str(command.organizer_id),
                    "idempotency_key": idempotency_key,
                },
                correlation_id=correlation_id,
            )
        return EventSnapshot.model_validate(row)

    def require_active_organizer(self, event_id: UUID, account_id: UUID) -> None:
        with self.database.connect() as connection:
            event = PlanningService._lock_event(connection, event_id)
            membership = connection.execute(
                """
                SELECT 1 FROM event_memberships
                WHERE event_id=%s AND account_id=%s
                  AND role='ORGANIZER' AND status='ACTIVE'
                """,
                (event_id, account_id),
            ).fetchone()
        if membership is None:
            raise AuthorizationError("active organizer membership is required")
        PlanningService._require_organizer(event, account_id)

