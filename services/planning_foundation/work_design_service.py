"""Deterministic lifecycle and transactional application for work design."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .database import Database
from .errors import (
    NotFoundError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
    ValidationError,
)
from .models import (
    EventSnapshot,
    PlanningRequestStatus,
    ProposalCreate,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
    StageSnapshot,
    WorkDecompositionProposal,
    WorkDesignRequest,
    WorkPlanDecisionResult,
    WorkSnapshot,
)
from .services import PlanningService
from .work_validation import WorkDecompositionValidator


class WorkDesignService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.base = PlanningService(database)
        self.validator = WorkDecompositionValidator()

    def request_work_design(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        organizer_id: UUID,
        expected_event_version: int,
        expected_stage_version: int,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> WorkDesignRequest:
        request_id = uuid4()
        correlation_id = correlation_id or uuid4()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM work_design_requests WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                return WorkDesignRequest.model_validate(existing)
            event = PlanningService._lock_event(connection, event_id)
            PlanningService._require_organizer(event, organizer_id)
            stage = PlanningService._lock_stage(connection, stage_id)
            if stage["event_id"] != event_id:
                raise ValidationError("target stage does not belong to the event")
            if event["version"] != expected_event_version:
                raise StaleProposalError("work request uses a stale event version")
            if stage["version"] != expected_stage_version:
                raise StaleProposalError("work request uses a stale stage version")
            if connection.execute(
                "SELECT 1 FROM work_items WHERE stage_id = %s LIMIT 1", (stage_id,)
            ).fetchone():
                raise ValidationError("approved stage already has authoritative work")
            if connection.execute(
                """
                SELECT 1 FROM work_design_requests
                WHERE stage_id = %s AND status IN ('REQUESTED', 'RUNNING') LIMIT 1
                """,
                (stage_id,),
            ).fetchone():
                raise ValidationError("a work design request is already active")
            if connection.execute(
                """
                SELECT 1 FROM proposals
                WHERE target_id = %s AND proposal_type = 'WORK_DECOMPOSITION'
                  AND status = 'PENDING' LIMIT 1
                """,
                (stage_id,),
            ).fetchone():
                raise ValidationError("a work decomposition is already pending approval")
            row = connection.execute(
                """
                INSERT INTO work_design_requests (
                    id, event_id, stage_id, organizer_id, base_event_version,
                    base_stage_version, status, idempotency_key, correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, 'REQUESTED', %s, %s)
                RETURNING *
                """,
                (
                    request_id, event_id, stage_id, organizer_id,
                    expected_event_version, expected_stage_version,
                    idempotency_key, correlation_id,
                ),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="stage.work_design_requested",
                aggregate_type="STAGE",
                aggregate_id=stage_id,
                aggregate_version=stage["version"],
                payload={
                    "work_design_request_id": str(request_id),
                    "event_id": str(event_id),
                    "stage_id": str(stage_id),
                    "base_event_version": event["version"],
                    "base_stage_version": stage["version"],
                },
                correlation_id=correlation_id,
            )
        return WorkDesignRequest.model_validate(row)

    def begin_request(self, request_id: UUID) -> WorkDesignRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            if request["status"] != PlanningRequestStatus.REQUESTED:
                raise ValidationError("work design request is not eligible to run")
            event = PlanningService._lock_event(connection, request["event_id"])
            stage = PlanningService._lock_stage(connection, request["stage_id"])
            if event["version"] != request["base_event_version"]:
                raise StaleProposalError("event changed before work design execution")
            if stage["version"] != request["base_stage_version"]:
                raise StaleProposalError("stage changed before work design execution")
            row = connection.execute(
                """
                UPDATE work_design_requests
                SET status = 'RUNNING', updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (request_id,),
            ).fetchone()
        return WorkDesignRequest.model_validate(row)

    def complete_request(
        self, request_id: UUID, proposal: WorkDecompositionProposal
    ) -> WorkDesignRequest:
        request = self.get_request(request_id)
        if request.status != PlanningRequestStatus.RUNNING:
            raise ValidationError("work design request is not running")
        event = self.base.get_event(request.event_id)
        stage = self.get_stage(request.stage_id)
        self.validator.validate(proposal, event, stage)
        stored = self.base.store_proposal(
            ProposalCreate(
                proposal_type="WORK_DECOMPOSITION",
                target_type="STAGE",
                target_id=request.stage_id,
                created_by="work-design-agent:v1",
                base_versions={
                    "event": request.base_event_version,
                    "stage": request.base_stage_version,
                },
                payload=proposal.model_dump(mode="json"),
                idempotency_key=f"work-decomposition:{request.id}",
                correlation_id=request.correlation_id,
            )
        )
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE work_design_requests
                SET status = 'SUCCEEDED', proposal_id = %s, updated_at = now()
                WHERE id = %s AND status = 'RUNNING'
                RETURNING *
                """,
                (stored.id, request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("work design completion lost its state")
            PlanningService._enqueue_outbox(
                connection,
                event_type="stage.work_decomposition_proposed",
                aggregate_type="STAGE",
                aggregate_id=request.stage_id,
                aggregate_version=request.base_stage_version,
                payload={
                    "work_design_request_id": str(request_id),
                    "proposal_id": str(stored.id),
                    "work_count": len(proposal.proposed_work),
                },
                correlation_id=request.correlation_id,
                causation_id=request_id,
            )
        return WorkDesignRequest.model_validate(row)

    def fail_request(self, request_id: UUID, failure_code: str) -> WorkDesignRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            row = connection.execute(
                """
                UPDATE work_design_requests
                SET status = 'FAILED', failure_code = %s, updated_at = now()
                WHERE id = %s AND status IN ('REQUESTED', 'RUNNING')
                RETURNING *
                """,
                (failure_code[:100], request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("completed work design request cannot be failed")
            PlanningService._enqueue_outbox(
                connection,
                event_type="reasoning.execution_failed",
                aggregate_type="STAGE",
                aggregate_id=request["stage_id"],
                aggregate_version=request["base_stage_version"],
                payload={
                    "work_design_request_id": str(request_id),
                    "failure_code": failure_code[:100],
                },
                correlation_id=request["correlation_id"],
                causation_id=request_id,
            )
        return WorkDesignRequest.model_validate(row)

    def decide_work_decomposition(
        self, command: ProposalDecisionCommand
    ) -> WorkPlanDecisionResult:
        with self.database.connect() as connection:
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE id = %s FOR UPDATE",
                (command.proposal_id,),
            ).fetchone()
            if proposal is None or proposal["proposal_type"] != "WORK_DECOMPOSITION":
                raise NotFoundError("work decomposition proposal not found")
            stage = PlanningService._lock_stage(connection, proposal["target_id"])
            event = PlanningService._lock_event(connection, stage["event_id"])
            PlanningService._require_organizer(event, command.organizer_id)
            existing = connection.execute(
                "SELECT * FROM proposal_decisions WHERE proposal_id = %s",
                (command.proposal_id,),
            ).fetchone()
            if existing is not None:
                if existing["decision_idempotency_key"] != command.decision_idempotency_key:
                    raise ProposalAlreadyDecidedError("proposal already decided")
                return WorkPlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus(proposal["status"]),
                    work=self._list_work(connection, stage["id"], command.proposal_id),
                    event_version=existing["applied_event_version"],
                    stage_version=(existing["application_result"] or {}).get("stage_version"),
                    duplicate=True,
                )
            if proposal["status"] != ProposalStatus.PENDING:
                raise ProposalAlreadyDecidedError("proposal is not pending")

            if command.decision == ProposalDecision.REJECT:
                connection.execute(
                    "UPDATE proposals SET status = 'REJECTED', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                self._record_decision(
                    connection, command, event, stage_version=None, work_ids=[]
                )
                PlanningService._enqueue_outbox(
                    connection,
                    event_type="stage.work_decomposition_rejected",
                    aggregate_type="STAGE",
                    aggregate_id=stage["id"],
                    aggregate_version=stage["version"],
                    payload={"proposal_id": str(command.proposal_id)},
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return WorkPlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.REJECTED,
                    event_version=event["version"],
                    stage_version=stage["version"],
                )

            expected = proposal["base_versions"]
            if event["version"] != expected["event"] or stage["version"] != expected["stage"]:
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
                        "expected_event_version": expected["event"],
                        "current_event_version": event["version"],
                        "expected_stage_version": expected["stage"],
                        "current_stage_version": stage["version"],
                    },
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return WorkPlanDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.STALE,
                    event_version=event["version"],
                    stage_version=stage["version"],
                )

            payload = (
                command.edited_payload
                if command.edited_payload is not None
                else proposal["payload"]
            )
            work_plan = self.validator.parse_and_validate(
                payload,
                EventSnapshot.model_validate(event),
                self._stage_snapshot(stage),
                expected_proposal_id=command.proposal_id,
            )
            work_ids = {
                item.temporary_work_ref: uuid4() for item in work_plan.proposed_work
            }
            for work_order, item in enumerate(work_plan.proposed_work, start=1):
                connection.execute(
                    """
                    INSERT INTO work_items (
                        id, event_id, stage_id, canonical_name, purpose, work_order,
                        estimated_person_hours, work_share, starts_at, ends_at,
                        source_proposal_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        work_ids[item.temporary_work_ref], event["id"], stage["id"],
                        item.canonical_name, item.purpose, work_order,
                        item.estimated_person_hours, item.work_share,
                        item.proposed_start, item.proposed_end, command.proposal_id,
                    ),
                )
            for item in work_plan.proposed_work:
                for dependency in item.dependencies:
                    connection.execute(
                        """
                        INSERT INTO work_dependencies (work_id, depends_on_work_id)
                        VALUES (%s, %s)
                        """,
                        (work_ids[item.temporary_work_ref], work_ids[dependency]),
                    )
            updated_stage = connection.execute(
                """
                UPDATE stages SET version = version + 1, updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (stage["id"],),
            ).fetchone()
            updated_event = connection.execute(
                """
                UPDATE events SET version = version + 1, updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (event["id"],),
            ).fetchone()
            connection.execute(
                """
                UPDATE proposals SET status = 'APPROVED', payload = %s, decided_at = now()
                WHERE id = %s
                """,
                (Jsonb(work_plan.model_dump(mode="json")), command.proposal_id),
            )
            self._record_decision(
                connection,
                command,
                updated_event,
                stage_version=updated_stage["version"],
                work_ids=list(work_ids.values()),
            )
            self._before_work_approval_outbox(connection)
            PlanningService._enqueue_outbox(
                connection,
                event_type="stage.work_decomposition_approved",
                aggregate_type="STAGE",
                aggregate_id=stage["id"],
                aggregate_version=updated_stage["version"],
                payload={
                    "proposal_id": str(command.proposal_id),
                    "work_ids": [str(value) for value in work_ids.values()],
                    "work_share_total": sum(
                        item.work_share for item in work_plan.proposed_work
                    ),
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
            for item in work_plan.proposed_work:
                PlanningService._enqueue_outbox(
                    connection,
                    event_type="work.created",
                    aggregate_type="WORK",
                    aggregate_id=work_ids[item.temporary_work_ref],
                    aggregate_version=1,
                    payload={
                        "event_id": str(event["id"]),
                        "stage_id": str(stage["id"]),
                        "proposal_id": str(command.proposal_id),
                        "temporary_work_ref": item.temporary_work_ref,
                    },
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
            work = self._list_work(connection, stage["id"], command.proposal_id)
        return WorkPlanDecisionResult(
            proposal_id=command.proposal_id,
            status=ProposalStatus.APPROVED,
            work=work,
            event_version=updated_event["version"],
            stage_version=updated_stage["version"],
        )

    def get_request(self, request_id: UUID) -> WorkDesignRequest:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM work_design_requests WHERE id = %s", (request_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("work design request not found")
        return WorkDesignRequest.model_validate(row)

    def get_stage(self, stage_id: UUID) -> StageSnapshot:
        with self.database.connect() as connection:
            row = PlanningService._lock_stage(connection, stage_id)
            dependencies = connection.execute(
                "SELECT depends_on_stage_id FROM stage_dependencies WHERE stage_id = %s",
                (stage_id,),
            ).fetchall()
        return StageSnapshot.model_validate(
            {**row, "dependency_stage_ids": [item["depends_on_stage_id"] for item in dependencies]}
        )

    def list_work(self, stage_id: UUID) -> list[WorkSnapshot]:
        with self.database.connect() as connection:
            return self._list_work(connection, stage_id)

    @staticmethod
    def _lock_request(connection, request_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM work_design_requests WHERE id = %s FOR UPDATE",
            (request_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("work design request not found")
        return row

    @staticmethod
    def _stage_snapshot(stage: dict[str, Any]) -> StageSnapshot:
        return StageSnapshot.model_validate({**stage, "dependency_stage_ids": []})

    @staticmethod
    def _record_decision(
        connection,
        command: ProposalDecisionCommand,
        event: dict[str, Any],
        *,
        stage_version: int | None,
        work_ids: list[UUID],
    ) -> None:
        connection.execute(
            """
            INSERT INTO proposal_decisions (
                id, proposal_id, organizer_id, decision,
                decision_idempotency_key, applied_event_id,
                applied_event_version, application_result
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(), command.proposal_id, command.organizer_id,
                command.decision.value, command.decision_idempotency_key,
                event["id"], event["version"],
                Jsonb({
                    "stage_version": stage_version,
                    "work_ids": [str(value) for value in work_ids],
                }),
            ),
        )

    @staticmethod
    def _list_work(
        connection,
        stage_id: UUID,
        source_proposal_id: UUID | None = None,
    ) -> list[WorkSnapshot]:
        parameters: list[Any] = [stage_id]
        source_clause = ""
        if source_proposal_id is not None:
            source_clause = "AND w.source_proposal_id = %s"
            parameters.append(source_proposal_id)
        rows = connection.execute(
            f"""
            SELECT w.*,
                   COALESCE(array_agg(d.depends_on_work_id)
                     FILTER (WHERE d.depends_on_work_id IS NOT NULL), ARRAY[]::uuid[])
                     AS dependency_work_ids
            FROM work_items w
            LEFT JOIN work_dependencies d ON d.work_id = w.id
            WHERE w.stage_id = %s {source_clause}
            GROUP BY w.id
            ORDER BY w.work_order
            """,
            parameters,
        ).fetchall()
        return [WorkSnapshot.model_validate(row) for row in rows]

    def _before_work_approval_outbox(self, connection) -> None:
        """Test seam proving work application and outbox are one transaction."""
