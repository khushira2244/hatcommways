"""Deterministic lifecycle and application for actor requirement proposals."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .actor_requirement_validation import ActorRequirementValidator
from .database import Database
from .errors import (
    NotFoundError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
    ValidationError,
)
from .models import (
    ActorRequirementDecisionResult,
    ActorRequirementProposal,
    ActorRequirementRequest,
    ActorRequirementSnapshot,
    EventSnapshot,
    PlanningRequestStatus,
    ProposalCreate,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
    StageSnapshot,
    WorkSnapshot,
)
from .services import PlanningService


class ActorRequirementService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.base = PlanningService(database)
        self.validator = ActorRequirementValidator()

    def request_actor_requirements(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        work_id: UUID,
        organizer_id: UUID,
        expected_event_version: int,
        expected_stage_version: int,
        expected_work_version: int,
        idempotency_key: str,
        correlation_id: UUID | None = None,
    ) -> ActorRequirementRequest:
        request_id = uuid4()
        correlation_id = correlation_id or uuid4()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM actor_requirement_requests WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                return ActorRequirementRequest.model_validate(existing)
            event, stage, work = self._lock_hierarchy(
                connection, event_id, stage_id, work_id
            )
            PlanningService._require_organizer(event, organizer_id)
            self._require_versions(
                event, stage, work,
                expected_event_version, expected_stage_version, expected_work_version,
                "actor requirement request",
            )
            if connection.execute(
                "SELECT 1 FROM actor_requirements WHERE work_id = %s LIMIT 1", (work_id,)
            ).fetchone():
                raise ValidationError("work already has authoritative actor requirements")
            if connection.execute(
                """
                SELECT 1 FROM actor_requirement_requests
                WHERE work_id = %s AND status IN ('REQUESTED', 'RUNNING') LIMIT 1
                """,
                (work_id,),
            ).fetchone():
                raise ValidationError("an actor requirement request is already active")
            if connection.execute(
                """
                SELECT 1 FROM proposals
                WHERE target_id = %s AND proposal_type = 'ACTOR_REQUIREMENT'
                  AND status = 'PENDING' LIMIT 1
                """,
                (work_id,),
            ).fetchone():
                raise ValidationError("actor requirements are already pending approval")
            row = connection.execute(
                """
                INSERT INTO actor_requirement_requests (
                    id, event_id, stage_id, work_id, organizer_id,
                    base_event_version, base_stage_version, base_work_version,
                    status, idempotency_key, correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'REQUESTED', %s, %s)
                RETURNING *
                """,
                (
                    request_id, event_id, stage_id, work_id, organizer_id,
                    expected_event_version, expected_stage_version,
                    expected_work_version, idempotency_key, correlation_id,
                ),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="work.actor_requirements_requested",
                aggregate_type="WORK",
                aggregate_id=work_id,
                aggregate_version=work["version"],
                payload={
                    "actor_requirement_request_id": str(request_id),
                    "event_id": str(event_id),
                    "stage_id": str(stage_id),
                    "work_id": str(work_id),
                    "base_event_version": event["version"],
                    "base_stage_version": stage["version"],
                    "base_work_version": work["version"],
                },
                correlation_id=correlation_id,
            )
        return ActorRequirementRequest.model_validate(row)

    def begin_request(self, request_id: UUID) -> ActorRequirementRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            if request["status"] != PlanningRequestStatus.REQUESTED:
                raise ValidationError("actor requirement request is not eligible to run")
            event, stage, work = self._lock_hierarchy(
                connection, request["event_id"], request["stage_id"], request["work_id"]
            )
            self._require_versions(
                event, stage, work,
                request["base_event_version"], request["base_stage_version"],
                request["base_work_version"], "actor requirement execution",
            )
            row = connection.execute(
                """
                UPDATE actor_requirement_requests
                SET status = 'RUNNING', updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (request_id,),
            ).fetchone()
        return ActorRequirementRequest.model_validate(row)

    def complete_request(
        self, request_id: UUID, proposal: ActorRequirementProposal
    ) -> ActorRequirementRequest:
        request = self.get_request(request_id)
        if request.status != PlanningRequestStatus.RUNNING:
            raise ValidationError("actor requirement request is not running")
        event = self.base.get_event(request.event_id)
        stage = self.get_stage(request.stage_id)
        work = self.get_work(request.work_id)
        self.validator.validate(proposal, event, stage, work)
        stored = self.base.store_proposal(
            ProposalCreate(
                proposal_type="ACTOR_REQUIREMENT",
                target_type="WORK",
                target_id=request.work_id,
                created_by="actor-requirement-agent:v1",
                base_versions={
                    "event": request.base_event_version,
                    "stage": request.base_stage_version,
                    "work": request.base_work_version,
                },
                payload=proposal.model_dump(mode="json"),
                idempotency_key=f"actor-requirement:{request.id}",
                correlation_id=request.correlation_id,
            )
        )
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE actor_requirement_requests
                SET status = 'SUCCEEDED', proposal_id = %s, updated_at = now()
                WHERE id = %s AND status = 'RUNNING' RETURNING *
                """,
                (stored.id, request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("actor requirement completion lost its state")
            PlanningService._enqueue_outbox(
                connection,
                event_type="work.actor_requirements_proposed",
                aggregate_type="WORK",
                aggregate_id=request.work_id,
                aggregate_version=request.base_work_version,
                payload={
                    "actor_requirement_request_id": str(request_id),
                    "proposal_id": str(stored.id),
                    "requirement_count": len(proposal.proposed_requirements),
                },
                correlation_id=request.correlation_id,
                causation_id=request_id,
            )
        return ActorRequirementRequest.model_validate(row)

    def fail_request(self, request_id: UUID, failure_code: str) -> ActorRequirementRequest:
        with self.database.connect() as connection:
            request = self._lock_request(connection, request_id)
            row = connection.execute(
                """
                UPDATE actor_requirement_requests
                SET status = 'FAILED', failure_code = %s, updated_at = now()
                WHERE id = %s AND status IN ('REQUESTED', 'RUNNING') RETURNING *
                """,
                (failure_code[:100], request_id),
            ).fetchone()
            if row is None:
                raise ValidationError("completed actor requirement request cannot be failed")
            PlanningService._enqueue_outbox(
                connection,
                event_type="reasoning.execution_failed",
                aggregate_type="WORK",
                aggregate_id=request["work_id"],
                aggregate_version=request["base_work_version"],
                payload={
                    "actor_requirement_request_id": str(request_id),
                    "failure_code": failure_code[:100],
                },
                correlation_id=request["correlation_id"],
                causation_id=request_id,
            )
        return ActorRequirementRequest.model_validate(row)

    def decide_actor_requirements(
        self, command: ProposalDecisionCommand
    ) -> ActorRequirementDecisionResult:
        with self.database.connect() as connection:
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE id = %s FOR UPDATE", (command.proposal_id,)
            ).fetchone()
            if proposal is None or proposal["proposal_type"] != "ACTOR_REQUIREMENT":
                raise NotFoundError("actor requirement proposal not found")
            work = PlanningService._lock_work(connection, proposal["target_id"])
            stage = PlanningService._lock_stage(connection, work["stage_id"])
            event = PlanningService._lock_event(connection, work["event_id"])
            PlanningService._require_organizer(event, command.organizer_id)
            existing = connection.execute(
                "SELECT * FROM proposal_decisions WHERE proposal_id = %s",
                (command.proposal_id,),
            ).fetchone()
            if existing is not None:
                if existing["decision_idempotency_key"] != command.decision_idempotency_key:
                    raise ProposalAlreadyDecidedError("proposal already decided")
                application = existing["application_result"] or {}
                return ActorRequirementDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus(proposal["status"]),
                    requirements=self._list_requirements(
                        connection, work["id"], command.proposal_id
                    ),
                    event_version=existing["applied_event_version"],
                    stage_version=application.get("stage_version"),
                    work_version=application.get("work_version"),
                    duplicate=True,
                )
            if proposal["status"] != ProposalStatus.PENDING:
                raise ProposalAlreadyDecidedError("proposal is not pending")

            if command.decision == ProposalDecision.REJECT:
                connection.execute(
                    "UPDATE proposals SET status = 'REJECTED', decided_at = now() WHERE id = %s",
                    (command.proposal_id,),
                )
                self._record_decision(connection, command, event, stage, work, [])
                PlanningService._enqueue_outbox(
                    connection,
                    event_type="work.actor_requirements_rejected",
                    aggregate_type="WORK",
                    aggregate_id=work["id"],
                    aggregate_version=work["version"],
                    payload={"proposal_id": str(command.proposal_id)},
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return ActorRequirementDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.REJECTED,
                    event_version=event["version"],
                    stage_version=stage["version"],
                    work_version=work["version"],
                )

            expected = proposal["base_versions"]
            if (
                event["version"] != expected["event"]
                or stage["version"] != expected["stage"]
                or work["version"] != expected["work"]
            ):
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
                        "expected_versions": expected,
                        "current_versions": {
                            "event": event["version"], "stage": stage["version"],
                            "work": work["version"],
                        },
                    },
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
                return ActorRequirementDecisionResult(
                    proposal_id=command.proposal_id,
                    status=ProposalStatus.STALE,
                    event_version=event["version"],
                    stage_version=stage["version"],
                    work_version=work["version"],
                )

            payload = command.edited_payload if command.edited_payload is not None else proposal["payload"]
            plan = self.validator.parse_and_validate(
                payload,
                EventSnapshot.model_validate(event),
                self._stage_snapshot(stage),
                self._work_snapshot(work),
                expected_proposal_id=command.proposal_id,
            )
            requirement_ids: list[UUID] = []
            for requirement in plan.proposed_requirements:
                requirement_id = uuid4()
                requirement_ids.append(requirement_id)
                connection.execute(
                    """
                    INSERT INTO actor_requirements (
                        id, event_id, stage_id, work_id, role_category,
                        canonical_role_name, responsibility_summary,
                        minimum_required_count, relevant_capabilities,
                        rough_effort_expectation, rationale, source_proposal_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        requirement_id, event["id"], stage["id"], work["id"],
                        requirement.role_category.upper(), requirement.canonical_role_name,
                        requirement.responsibility_summary,
                        requirement.minimum_required_count,
                        Jsonb(requirement.relevant_capabilities),
                        requirement.rough_effort_expectation, requirement.rationale,
                        command.proposal_id,
                    ),
                )
            updated_work = connection.execute(
                "UPDATE work_items SET version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                (work["id"],),
            ).fetchone()
            updated_stage = connection.execute(
                "UPDATE stages SET version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                (stage["id"],),
            ).fetchone()
            updated_event = connection.execute(
                "UPDATE events SET version=version+1, updated_at=now() WHERE id=%s RETURNING *",
                (event["id"],),
            ).fetchone()
            connection.execute(
                "UPDATE proposals SET status='APPROVED', payload=%s, decided_at=now() WHERE id=%s",
                (Jsonb(plan.model_dump(mode="json")), command.proposal_id),
            )
            self._record_decision(
                connection, command, updated_event, updated_stage, updated_work,
                requirement_ids,
            )
            self._before_requirement_approval_outbox(connection)
            PlanningService._enqueue_outbox(
                connection,
                event_type="work.actor_requirements_approved",
                aggregate_type="WORK",
                aggregate_id=work["id"],
                aggregate_version=updated_work["version"],
                payload={
                    "proposal_id": str(command.proposal_id),
                    "requirement_ids": [str(value) for value in requirement_ids],
                },
                correlation_id=proposal["correlation_id"],
                causation_id=command.proposal_id,
            )
            for requirement_id in requirement_ids:
                PlanningService._enqueue_outbox(
                    connection,
                    event_type="actor_requirement.created",
                    aggregate_type="ACTOR_REQUIREMENT",
                    aggregate_id=requirement_id,
                    aggregate_version=1,
                    payload={
                        "event_id": str(event["id"]), "stage_id": str(stage["id"]),
                        "work_id": str(work["id"]),
                        "proposal_id": str(command.proposal_id),
                    },
                    correlation_id=proposal["correlation_id"],
                    causation_id=command.proposal_id,
                )
            requirements = self._list_requirements(
                connection, work["id"], command.proposal_id
            )
        return ActorRequirementDecisionResult(
            proposal_id=command.proposal_id,
            status=ProposalStatus.APPROVED,
            requirements=requirements,
            event_version=updated_event["version"],
            stage_version=updated_stage["version"],
            work_version=updated_work["version"],
        )

    def get_request(self, request_id: UUID) -> ActorRequirementRequest:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM actor_requirement_requests WHERE id = %s", (request_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("actor requirement request not found")
        return ActorRequirementRequest.model_validate(row)

    def get_stage(self, stage_id: UUID) -> StageSnapshot:
        with self.database.connect() as connection:
            row = PlanningService._lock_stage(connection, stage_id)
        return self._stage_snapshot(row)

    def get_work(self, work_id: UUID) -> WorkSnapshot:
        with self.database.connect() as connection:
            row = PlanningService._lock_work(connection, work_id)
        return self._work_snapshot(row)

    def list_requirements(self, work_id: UUID) -> list[ActorRequirementSnapshot]:
        with self.database.connect() as connection:
            return self._list_requirements(connection, work_id)

    @staticmethod
    def _lock_request(connection, request_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM actor_requirement_requests WHERE id=%s FOR UPDATE",
            (request_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError("actor requirement request not found")
        return row

    @staticmethod
    def _lock_hierarchy(connection, event_id: UUID, stage_id: UUID, work_id: UUID):
        event = PlanningService._lock_event(connection, event_id)
        stage = PlanningService._lock_stage(connection, stage_id)
        work = PlanningService._lock_work(connection, work_id)
        if stage["event_id"] != event_id or work["event_id"] != event_id or work["stage_id"] != stage_id:
            raise ValidationError("work does not belong to the targeted event and stage")
        return event, stage, work

    @staticmethod
    def _require_versions(event, stage, work, event_version, stage_version, work_version, action):
        if event["version"] != event_version:
            raise StaleProposalError(f"{action} uses a stale event version")
        if stage["version"] != stage_version:
            raise StaleProposalError(f"{action} uses a stale stage version")
        if work["version"] != work_version:
            raise StaleProposalError(f"{action} uses a stale work version")

    @staticmethod
    def _stage_snapshot(stage) -> StageSnapshot:
        return StageSnapshot.model_validate({**stage, "dependency_stage_ids": []})

    @staticmethod
    def _work_snapshot(work) -> WorkSnapshot:
        return WorkSnapshot.model_validate({**work, "dependency_work_ids": []})

    @staticmethod
    def _record_decision(connection, command, event, stage, work, requirement_ids):
        connection.execute(
            """
            INSERT INTO proposal_decisions (
                id, proposal_id, organizer_id, decision, decision_idempotency_key,
                applied_event_id, applied_event_version, application_result
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(), command.proposal_id, command.organizer_id,
                command.decision.value, command.decision_idempotency_key,
                event["id"], event["version"],
                Jsonb({
                    "stage_version": stage["version"], "work_version": work["version"],
                    "requirement_ids": [str(value) for value in requirement_ids],
                }),
            ),
        )

    @staticmethod
    def _list_requirements(connection, work_id, source_proposal_id=None):
        parameters: list[Any] = [work_id]
        source_clause = ""
        if source_proposal_id is not None:
            source_clause = "AND source_proposal_id = %s"
            parameters.append(source_proposal_id)
        rows = connection.execute(
            f"""
            SELECT * FROM actor_requirements
            WHERE work_id = %s {source_clause}
            ORDER BY role_category, canonical_role_name
            """,
            parameters,
        ).fetchall()
        return [ActorRequirementSnapshot.model_validate(row) for row in rows]

    def _before_requirement_approval_outbox(self, connection) -> None:
        """Test seam proving authoritative application and outbox atomicity."""

