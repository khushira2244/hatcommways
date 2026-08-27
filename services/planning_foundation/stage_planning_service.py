"""Deterministic trigger, lifecycle, and application services for stage plans."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .database import Database
from .errors import (
    AuthorizationError,
    NotFoundError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
    ValidationError,
)
from .models import (
    EventPlanningRequest,
    EventSnapshot,
    PlanningRequestStatus,
    ProposalCreate,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
    StagePlanDecisionResult,
    StagePlanProposal,
    StageSnapshot,
)
from .services import PlanningService
from .stage_validation import StagePlanValidator


class StagePlanningService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.base = PlanningService(database)
        self.validator = StagePlanValidator()

    def request_event_planning(
        self,
        *,
        event_id: UUID,
        organizer_id: UUID,
        expected_event_version: int,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> EventPlanningRequest:
        correlation_id = correlation_id or uuid4()
        request_id = uuid4()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM event_planning_requests WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                return EventPlanningRequest.model_validate(existing)
            event = PlanningService._lock_event(connection, event_id)
            PlanningService._require_organizer(event, organizer_id)
            if event["version"] != expected_event_version:
                raise StaleProposalError("event planning request uses a stale event version")
            if connection.execute(
                "SELECT 1 FROM stages WHERE event_id = %s LIMIT 1", (event_id,)
            ).fetchone():
                raise ValidationError("event already has authoritative stages")
            if connection.execute(
                """
                SELECT 1 FROM event_planning_requests
                WHERE event_id = %s AND status IN ('REQUESTED', 'RUNNING')
                LIMIT 1
                """,
                (event_id,),
            ).fetchone():
                raise ValidationError("an event planning request is already active")
            if connection.execute(
                """
                SELECT 1 FROM proposals
                WHERE target_id = %s AND proposal_type = 'STAGE_PLAN'
                  AND status = 'PENDING'
                LIMIT 1
                """,
                (event_id,),
            ).fetchone():
                raise ValidationError("a stage plan is already pending approval")
            row = connection.execute(
                """
                INSERT INTO event_planning_requests (
                    id, event_id, organizer_id, base_event_version, status,
                    idempotency_key, correlation_id
                ) VALUES (%s, %s, %s, %s, 'REQUESTED', %s, %s)
                RETURNING *
                """,
                (
                    request_id, event_id, organizer_id, expected_event_version,
                    idempotency_key, correlation_id,
                ),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="event.planning_requested",
                aggregate_type="EVENT",
                aggregate_id=event_id,
                aggregate_version=event["version"],
                payload={
                    "planning_request_id": str(request_id),
                    "event_id": str(event_id),
                    "base_event_version": expected_event_version,
                },
                correlation_id=correlation_id,
            )
        return EventPlanningRequest.model_validate(row)

    def begin_request(self, request_id: UUID) -> EventPlanningRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            if request["status"] != PlanningRequestStatus.REQUESTED:
                raise ValidationError("planning request is not eligible to run")
            event = PlanningService._lock_event(connection, request["event_id"])
            if event["version"] != request["base_event_version"]:
                raise StaleProposalError("planning request became stale before execution")
            row = connection.execute(
                """
                UPDATE event_planning_requests
                SET status = 'RUNNING', updated_at = now()
                WHERE id = %s
                RETURNING *
                """,
                (request_id,),
            ).fetchone()
        return EventPlanningRequest.model_validate(row)

    def complete_request(
        self, request_id: UUID, proposal: StagePlanProposal
    ) -> EventPlanningRequest:
        request = self.get_request(request_id)
        if request.status != PlanningRequestStatus.RUNNING:
            raise ValidationError("planning request is not running")
        event = self.base.get_event(request.event_id)
        self.validator.validate(
            proposal, event, expected_proposal_id=proposal.proposal_id
        )
        stored = self.base.store_proposal(
            ProposalCreate(
                proposal_type="STAGE_PLAN",
                target_type="EVENT",
                target_id=request.event_id,
                created_by="event-planning-agent:v1",
                base_versions={"event": request.base_event_version},
                payload=proposal.model_dump(mode="json"),
                idempotency_key=f"stage-plan:{request.id}",
                correlation_id=request.correlation_id,
            )
        )
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE event_planning_requests
                SET status = 'SUCCEEDED', proposal_id = %s, updated_at = now()
                WHERE id = %s AND status = 'RUNNING'
                RETURNING *
                """,
                (stored.id, request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("planning request completion lost its state")
            PlanningService._enqueue_outbox(
                connection,
                event_type="event.stage_plan_proposed",
                aggregate_type="EVENT",
                aggregate_id=request.event_id,
                aggregate_version=request.base_event_version,
                payload={
                    "planning_request_id": str(request_id),
                    "proposal_id": str(stored.id),
                    "stage_count": len(proposal.proposed_stages),
                },
                correlation_id=request.correlation_id,
                causation_id=request_id,
            )
        return EventPlanningRequest.model_validate(row)

    def fail_request(self, request_id: UUID, failure_code: str) -> EventPlanningRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            row = connection.execute(
                """
                UPDATE event_planning_requests
                SET status = 'FAILED', failure_code = %s, updated_at = now()
                WHERE id = %s AND status IN ('REQUESTED', 'RUNNING')
                RETURNING *
                """,
                (failure_code[:100], request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("completed planning request cannot be failed")
            PlanningService._enqueue_outbox(
                connection,
                event_type="reasoning.execution_failed",
                aggregate_type="EVENT",
                aggregate_id=request["event_id"],
                aggregate_version=request["base_event_version"],
                payload={
                    "planning_request_id": str(request_id),
                    "failure_code": failure_code[:100],
                },
                correlation_id=request["correlation_id"],
                causation_id=request_id,
            )
        return EventPlanningRequest.model_validate(row)

    def decide_stage_plan(
        self, command: ProposalDecisionCommand
    ) -> StagePlanDecisionResult:
        with self.database.connect() as connection:
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE id = %s FOR UPDATE",
                (command.proposal_id,),
            ).fetchone()
            if proposal is None or proposal["proposal_type"] != "STAGE_PLAN":
                raise NotFoundError("stage plan proposal not found")
            event = PlanningService._lock_event(connection, proposal["target_id"])
            PlanningService._require_organizer(event, command.organizer_id)

            existing = connection.execute(
                "SELECT * FROM proposal_decisions WHERE proposal_id = %s",
                (command.proposal_id,),
            ).fetchone()
            if existing is not None:
                if existing["decision_idempotency_key"] != command.decision_idempotency_key:
                    raise ProposalAlreadyDecidedError("proposal already decided")
                return StagePlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus(proposal["status"]),
                    stages=self._list_stages(connection, event["id"], command.proposal_id),
                    event_version=existing["applied_event_version"],
                    duplicate=True,
                )
            if proposal["status"] != ProposalStatus.PENDING:
                raise ProposalAlreadyDecidedError("proposal is not pending")

            if command.decision == ProposalDecision.REJECT:
                connection.execute(
                    "UPDATE proposals SET status = 'REJECTED', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                self._record_decision(connection, command, event_version=None, stage_ids=[])
                PlanningService._enqueue_outbox(
                    connection,
                    event_type="event.stage_plan_rejected",
                    aggregate_type="EVENT",
                    aggregate_id=event["id"],
                    aggregate_version=event["version"],
                    payload={"proposal_id": str(command.proposal_id)},
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return StagePlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.REJECTED,
                    event_version=event["version"],
                )

            if event["version"] != proposal["base_versions"]["event"]:
                connection.execute(
                    "UPDATE proposals SET status = 'STALE', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                PlanningService._enqueue_outbox(
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
                return StagePlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.STALE,
                    event_version=event["version"],
                )

            payload = (
                command.edited_payload
                if command.edited_payload is not None
                else proposal["payload"]
            )
            stage_plan = self.validator.parse_and_validate(
                payload,
                EventSnapshot.model_validate(event),
                expected_proposal_id=command.proposal_id,
            )
            stage_ids = {
                stage.temporary_stage_ref: uuid4()
                for stage in stage_plan.proposed_stages
            }
            for stage in sorted(
                stage_plan.proposed_stages, key=lambda item: item.proposed_order
            ):
                connection.execute(
                    """
                    INSERT INTO stages (
                        id, event_id, canonical_name, purpose, stage_order,
                        starts_at, ends_at, source_proposal_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        stage_ids[stage.temporary_stage_ref], event["id"],
                        stage.canonical_name, stage.purpose, stage.proposed_order,
                        stage.proposed_start, stage.proposed_end, command.proposal_id,
                    ),
                )
            for stage in stage_plan.proposed_stages:
                for dependency in stage.dependencies:
                    connection.execute(
                        """
                        INSERT INTO stage_dependencies (stage_id, depends_on_stage_id)
                        VALUES (%s, %s)
                        """,
                        (stage_ids[stage.temporary_stage_ref], stage_ids[dependency]),
                    )
            updated_event = connection.execute(
                """
                UPDATE events SET version = version + 1, updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (event["id"],),
            ).fetchone()
            normalized = stage_plan.model_dump(mode="json")
            connection.execute(
                """
                UPDATE proposals
                SET status = 'APPROVED', payload = %s, decided_at = now()
                WHERE id = %s
                """,
                (Jsonb(normalized), command.proposal_id),
            )
            self._record_decision(
                connection,
                command,
                event_version=updated_event["version"],
                stage_ids=list(stage_ids.values()),
            )
            self._before_stage_approval_outbox(connection)
            PlanningService._enqueue_outbox(
                connection,
                event_type="event.stage_plan_approved",
                aggregate_type="EVENT",
                aggregate_id=event["id"],
                aggregate_version=updated_event["version"],
                payload={
                    "proposal_id": str(command.proposal_id),
                    "stage_ids": [str(value) for value in stage_ids.values()],
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
            PlanningService._enqueue_outbox(
                connection,
                event_type="stages.created",
                aggregate_type="EVENT",
                aggregate_id=event["id"],
                aggregate_version=updated_event["version"],
                payload={
                    "proposal_id": str(command.proposal_id),
                    "stage_count": len(stage_ids),
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
            stages = self._list_stages(connection, event["id"], command.proposal_id)
        return StagePlanDecisionResult(
            proposal_id=command.proposal_id,
            status=ProposalStatus.APPROVED,
            stages=stages,
            event_version=updated_event["version"],
        )

    def get_request(self, request_id: UUID) -> EventPlanningRequest:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM event_planning_requests WHERE id = %s", (request_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("planning request not found")
        return EventPlanningRequest.model_validate(row)

    def list_stages(self, event_id: UUID) -> list[StageSnapshot]:
        with self.database.connect() as connection:
            return self._list_stages(connection, event_id)

    @staticmethod
    def _lock_request(connection, request_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM event_planning_requests WHERE id = %s FOR UPDATE",
            (request_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("planning request not found")
        return row

    @staticmethod
    def _record_decision(
        connection,
        command: ProposalDecisionCommand,
        *,
        event_version: int | None,
        stage_ids: list[UUID],
    ) -> None:
        connection.execute(
            """
            INSERT INTO proposal_decisions (
                id, proposal_id, organizer_id, decision,
                decision_idempotency_key, applied_event_id,
                applied_event_version, application_result
            )
            SELECT %s, %s, %s, %s, %s, target_id, %s, %s
            FROM proposals WHERE id = %s
            """,
            (
                uuid4(), command.proposal_id, command.organizer_id,
                command.decision.value, command.decision_idempotency_key,
                event_version, Jsonb({"stage_ids": [str(value) for value in stage_ids]}),
                command.proposal_id,
            ),
        )

    @staticmethod
    def _list_stages(
        connection,
        event_id: UUID,
        source_proposal_id: UUID | None = None,
    ) -> list[StageSnapshot]:
        parameters: list[Any] = [event_id]
        source_clause = ""
        if source_proposal_id is not None:
            source_clause = "AND s.source_proposal_id = %s"
            parameters.append(source_proposal_id)
        rows = connection.execute(
            f"""
            SELECT s.*,
                   COALESCE(array_agg(d.depends_on_stage_id)
                     FILTER (WHERE d.depends_on_stage_id IS NOT NULL), ARRAY[]::uuid[])
                     AS dependency_stage_ids
            FROM stages s
            LEFT JOIN stage_dependencies d ON d.stage_id = s.id
            WHERE s.event_id = %s {source_clause}
            GROUP BY s.id
            ORDER BY s.stage_order
            """,
            parameters,
        ).fetchall()
        return [StageSnapshot.model_validate(row) for row in rows]

    def _before_stage_approval_outbox(self, connection) -> None:
        """Test seam proving stage application and outbox are one transaction."""
