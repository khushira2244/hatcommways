"""Transactional deterministic services for Level 1 Task 1."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .database import Database
from .errors import (
    AuthorizationError,
    NotFoundError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
)
from .models import (
    EventCreate,
    EventSnapshot,
    ProposalCreate,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalDecisionResult,
    ProposalSnapshot,
    ProposalStatus,
    StageSnapshot,
    WorkSnapshot,
)
from .validation import ProposalValidator


class PlanningService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.validator = ProposalValidator()

    def create_event(
        self,
        command: EventCreate,
        *,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> EventSnapshot:
        event_id = uuid4()
        correlation_id = correlation_id or uuid4()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO events (
                    id, organizer_id, name, purpose, event_type, starts_at,
                    ends_at, timezone, location_description
                ) VALUES (
                    %(id)s, %(organizer_id)s, %(name)s, %(purpose)s,
                    %(event_type)s, %(starts_at)s, %(ends_at)s, %(timezone)s,
                    %(location_description)s
                )
                RETURNING *
                """,
                {"id": event_id, **command.model_dump()},
            ).fetchone()
            self._enqueue_outbox(
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

    def get_event(self, event_id: UUID) -> EventSnapshot:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE id = %s", (event_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("event not found")
        return EventSnapshot.model_validate(row)

    def update_event_direct(
        self,
        *,
        event_id: UUID,
        organizer_id: UUID,
        expected_version: int,
        changes: dict[str, Any],
    ) -> EventSnapshot:
        changes = self.validator.validate_payload(changes)
        with self.database.connect() as connection:
            event = self._lock_event(connection, event_id)
            self._require_organizer(event, organizer_id)
            if event["version"] != expected_version:
                raise StaleProposalError("event version does not match")
            self.validator.validate_effective_time_range(event, changes)
            updated = self._apply_event_changes(connection, event, changes)
            self._enqueue_outbox(
                connection,
                event_type="event.updated",
                aggregate_type="EVENT",
                aggregate_id=event_id,
                aggregate_version=updated["version"],
                payload={"event_id": str(event_id), "changed_fields": sorted(changes)},
                correlation_id=uuid4(),
            )
        return EventSnapshot.model_validate(updated)

    def store_proposal(self, command: ProposalCreate) -> ProposalSnapshot:
        with self.database.connect() as connection:
            stage = None
            work = None
            if command.target_type == "WORK":
                work = self._lock_work(connection, command.target_id)
                stage = self._lock_stage(connection, work["stage_id"])
                event = self._lock_event(connection, work["event_id"])
            elif command.target_type == "STAGE":
                stage = self._lock_stage(connection, command.target_id)
                event = self._lock_event(connection, stage["event_id"])
            else:
                event = self._lock_event(connection, command.target_id)
            if event["version"] != command.base_versions["event"]:
                raise StaleProposalError("proposal base event version is stale")
            if stage is not None and stage["version"] != command.base_versions["stage"]:
                raise StaleProposalError("proposal base stage version is stale")
            if work is not None and work["version"] != command.base_versions["work"]:
                raise StaleProposalError("proposal base work version is stale")
            normalized_payload = self.validator.validate_for_storage(
                command,
                EventSnapshot.model_validate(event),
                StageSnapshot.model_validate({**stage, "dependency_stage_ids": []})
                if stage is not None
                else None,
                WorkSnapshot.model_validate({**work, "dependency_work_ids": []})
                if work is not None
                else None,
            )
            proposal_id = (
                UUID(normalized_payload["proposal_id"])
                if command.proposal_type in {
                    "STAGE_PLAN", "WORK_DECOMPOSITION", "ACTOR_REQUIREMENT"
                }
                else uuid4()
            )
            try:
                row = connection.execute(
                    """
                    INSERT INTO proposals (
                        id, proposal_type, target_type, target_id, created_by,
                        base_versions, payload, idempotency_key, correlation_id
                    ) VALUES (
                        %(id)s, %(proposal_type)s, %(target_type)s, %(target_id)s,
                        %(created_by)s, %(base_versions)s, %(payload)s,
                        %(idempotency_key)s, %(correlation_id)s
                    )
                    RETURNING *
                    """,
                    {
                        **command.model_dump(exclude={"payload", "base_versions"}),
                        "id": proposal_id,
                        "base_versions": Jsonb(command.base_versions),
                        "payload": Jsonb(normalized_payload),
                    },
                ).fetchone()
            except UniqueViolation:
                connection.rollback()
                with self.database.connect() as lookup:
                    existing = lookup.execute(
                        "SELECT * FROM proposals WHERE idempotency_key = %s",
                        (command.idempotency_key,),
                    ).fetchone()
                return ProposalSnapshot.model_validate(existing)
            self._enqueue_outbox(
                connection,
                event_type="proposal.stored",
                aggregate_type="PROPOSAL",
                aggregate_id=proposal_id,
                aggregate_version=1,
                payload={
                    "proposal_id": str(proposal_id),
                    "proposal_type": command.proposal_type,
                    "target_id": str(command.target_id),
                },
                correlation_id=command.correlation_id,
            )
        return ProposalSnapshot.model_validate(row)

    def decide_proposal(
        self, command: ProposalDecisionCommand
    ) -> ProposalDecisionResult:
        with self.database.connect() as connection:
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE id = %s FOR UPDATE",
                (command.proposal_id,),
            ).fetchone()
            if proposal is None:
                raise NotFoundError("proposal not found")

            existing = connection.execute(
                "SELECT * FROM proposal_decisions WHERE proposal_id = %s",
                (command.proposal_id,),
            ).fetchone()
            if existing is not None:
                if existing["decision_idempotency_key"] != command.decision_idempotency_key:
                    raise ProposalAlreadyDecidedError("proposal already decided")
                applied = (
                    self._lock_event(connection, existing["applied_event_id"])
                    if existing["applied_event_id"] is not None
                    else None
                )
                return ProposalDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus(proposal["status"]),
                    applied_event=EventSnapshot.model_validate(applied) if applied else None,
                    duplicate=True,
                )

            if proposal["status"] != ProposalStatus.PENDING:
                raise ProposalAlreadyDecidedError("proposal is not pending")

            event = self._lock_event(connection, proposal["target_id"])
            self._require_organizer(event, command.organizer_id)

            if command.decision == ProposalDecision.REJECT:
                connection.execute(
                    "UPDATE proposals SET status = 'REJECTED', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                self._record_decision(connection, command, applied_event=None)
                self._enqueue_outbox(
                    connection,
                    event_type="proposal.rejected",
                    aggregate_type="PROPOSAL",
                    aggregate_id=command.proposal_id,
                    aggregate_version=1,
                    payload={"proposal_id": str(command.proposal_id)},
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return ProposalDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.REJECTED,
                )

            if event["version"] != proposal["base_versions"]["event"]:
                connection.execute(
                    "UPDATE proposals SET status = 'STALE', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                self._enqueue_outbox(
                    connection,
                    event_type="proposal.stale",
                    aggregate_type="PROPOSAL",
                    aggregate_id=command.proposal_id,
                    aggregate_version=1,
                    payload={
                        "proposal_id": str(command.proposal_id),
                        "expected_event_version": proposal["base_versions"]["event"],
                        "current_event_version": event["version"],
                    },
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return ProposalDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.STALE,
                )

            effective_payload = (
                command.edited_payload
                if command.edited_payload is not None
                else proposal["payload"]
            )
            changes = self.validator.validate_payload(effective_payload)
            self.validator.validate_effective_time_range(event, changes)
            updated = self._apply_event_changes(connection, event, changes)
            self._before_approval_outbox(connection)
            connection.execute(
                "UPDATE proposals SET status = 'APPROVED', payload = %s, decided_at = now() WHERE id = %s",
                (Jsonb(changes), command.proposal_id),
            )
            self._record_decision(connection, command, applied_event=updated)
            self._enqueue_outbox(
                connection,
                event_type="proposal.approved",
                aggregate_type="PROPOSAL",
                aggregate_id=command.proposal_id,
                aggregate_version=1,
                payload={
                    "proposal_id": str(command.proposal_id),
                    "applied_event_id": str(updated["id"]),
                    "applied_event_version": updated["version"],
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
            self._enqueue_outbox(
                connection,
                event_type="event.updated",
                aggregate_type="EVENT",
                aggregate_id=updated["id"],
                aggregate_version=updated["version"],
                payload={
                    "event_id": str(updated["id"]),
                    "source_proposal_id": str(command.proposal_id),
                    "changed_fields": sorted(changes),
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
        return ProposalDecisionResult(
            proposal_id=command.proposal_id,
            status=ProposalStatus.APPROVED,
            applied_event=EventSnapshot.model_validate(updated),
        )

    def get_proposal(self, proposal_id: UUID) -> ProposalSnapshot:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM proposals WHERE id = %s", (proposal_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("proposal not found")
        return ProposalSnapshot.model_validate(row)

    @staticmethod
    def _lock_event(connection: Connection, event_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM events WHERE id = %s FOR UPDATE", (event_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("event not found")
        return row

    @staticmethod
    def _lock_stage(connection: Connection, stage_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM stages WHERE id = %s FOR UPDATE", (stage_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("stage not found")
        return row

    @staticmethod
    def _lock_work(connection: Connection, work_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM work_items WHERE id = %s FOR UPDATE", (work_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("work item not found")
        return row

    @staticmethod
    def _require_organizer(event: dict[str, Any], actor_id: UUID) -> None:
        if event["organizer_id"] != actor_id:
            raise AuthorizationError("only the event organizer may perform this action")

    @staticmethod
    def _apply_event_changes(
        connection: Connection,
        event: dict[str, Any],
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = {
            "name", "purpose", "event_type", "starts_at", "ends_at",
            "timezone", "location_description",
        }
        if not set(changes).issubset(allowed):
            raise ValueError("event update contains forbidden fields")
        assignments = ", ".join(f"{field} = %({field})s" for field in changes)
        return connection.execute(
            f"""
            UPDATE events
            SET {assignments}, version = version + 1, updated_at = now()
            WHERE id = %(event_id)s
            RETURNING *
            """,
            {**changes, "event_id": event["id"]},
        ).fetchone()

    @staticmethod
    def _record_decision(
        connection: Connection,
        command: ProposalDecisionCommand,
        *,
        applied_event: dict[str, Any] | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO proposal_decisions (
                id, proposal_id, organizer_id, decision,
                decision_idempotency_key, applied_event_id, applied_event_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(), command.proposal_id, command.organizer_id,
                command.decision.value, command.decision_idempotency_key,
                applied_event["id"] if applied_event else None,
                applied_event["version"] if applied_event else None,
            ),
        )

    @staticmethod
    def _enqueue_outbox(
        connection: Connection,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        aggregate_version: int,
        payload: dict[str, Any],
        correlation_id: UUID,
        causation_id: UUID | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO domain_outbox (
                id, event_type, aggregate_type, aggregate_id, aggregate_version,
                payload, correlation_id, causation_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(), event_type, aggregate_type, aggregate_id,
                aggregate_version, Jsonb(payload), correlation_id, causation_id,
            ),
        )

    def _before_approval_outbox(self, connection: Connection) -> None:
        """Test seam used to prove rollback across application and outbox."""
