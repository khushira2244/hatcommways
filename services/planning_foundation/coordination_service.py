"""Persistence, scoping, validation, and lifecycle for coordination proposals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .affected_work_service import AffectedWorkService
from .coordination_models import (
    CoordinationContext,
    CoordinationDecision,
    CoordinationProposalSnapshot,
)
from .database import Database
from .errors import IdempotencyConflictError, NotFoundError, StaleVersionError, ValidationError
from .human_update_service import HumanUpdateService
from .services import PlanningService


@dataclass(frozen=True)
class CoordinationStart:
    request_id: UUID
    context: CoordinationContext
    existing: CoordinationProposalSnapshot | None


class CoordinationService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.human_updates = HumanUpdateService(database)
        self.affected_work = AffectedWorkService(database)

    @staticmethod
    def _proposal(row: dict[str, Any]) -> CoordinationProposalSnapshot:
        return CoordinationProposalSnapshot.model_validate({**row, "actions": row["actions"]})

    def get_proposal(self, event_id: UUID, blocker_id: UUID, organizer_id: UUID):
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id)
            self.human_updates._require_organizer(connection, event, organizer_id)
            if connection.execute(
                "SELECT 1 FROM blockers WHERE id=%s AND event_id=%s", (blocker_id, event_id)
            ).fetchone() is None:
                raise NotFoundError("blocker not found in this event")
            row = connection.execute(
                "SELECT * FROM coordination_proposals WHERE event_id=%s AND blocker_id=%s",
                (event_id, blocker_id),
            ).fetchone()
            return self._proposal(row) if row else None

    def begin(self, event_id: UUID, blocker_id: UUID, organizer_id: UUID, *, retry: bool) -> CoordinationStart:
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            blocker = connection.execute(
                "SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE",
                (blocker_id, event_id),
            ).fetchone()
            if blocker is None:
                raise NotFoundError("blocker not found in this event")
            if blocker["condition_state"] != "OPEN":
                raise ValidationError("only an open blocker can be coordinated")
            context = self._context(connection, event, blocker)
            request = connection.execute(
                "SELECT * FROM coordination_requests WHERE blocker_id=%s FOR UPDATE", (blocker_id,)
            ).fetchone()
            if request:
                if request["source_fingerprint"] != context.source_fingerprint:
                    raise StaleVersionError("coordination source state changed")
                if request["status"] == "SUCCEEDED":
                    proposal = connection.execute(
                        "SELECT * FROM coordination_proposals WHERE request_id=%s", (request["id"],)
                    ).fetchone()
                    return CoordinationStart(request["id"], context, self._proposal(proposal))
                if request["status"] == "RUNNING":
                    raise IdempotencyConflictError("coordination is already running")
                if request["status"] == "FAILED" and not retry:
                    raise IdempotencyConflictError("explicit retry is required after coordination failure")
                if request["status"] != "FAILED":
                    raise IdempotencyConflictError("coordination is not eligible to run")
                request = connection.execute(
                    """UPDATE coordination_requests SET status='RUNNING',failure_code=NULL,
                              failed_at=NULL,attempt_count=attempt_count+1,updated_at=now()
                       WHERE id=%s RETURNING *""",
                    (request["id"],),
                ).fetchone()
            else:
                request = connection.execute(
                    """INSERT INTO coordination_requests(
                           id,event_id,blocker_id,blocker_assessment_id,affected_work_resolution_id,
                           organizer_id,source_fingerprint,source_versions,status,attempt_count)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'RUNNING',1) RETURNING *""",
                    (
                        uuid4(), event_id, blocker_id,
                        UUID(str(context.blocker_assessment["id"])),
                        UUID(str(context.affected_work_resolution["id"])), organizer_id,
                        context.source_fingerprint, Jsonb(context.source_versions),
                    ),
                ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="coordination.requested",
                aggregate_type="COORDINATION_REQUEST",
                aggregate_id=request["id"],
                aggregate_version=request["attempt_count"],
                payload={"event_id": str(event_id), "blocker_id": str(blocker_id), "request_id": str(request["id"]), "attempt": request["attempt_count"]},
                correlation_id=correlation_id,
            )
            return CoordinationStart(request["id"], context, None)

    def context(self, event_id: UUID, blocker_id: UUID, organizer_id: UUID) -> CoordinationContext:
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id)
            self.human_updates._require_organizer(connection, event, organizer_id)
            blocker = connection.execute(
                "SELECT * FROM blockers WHERE id=%s AND event_id=%s", (blocker_id, event_id)
            ).fetchone()
            if blocker is None:
                raise NotFoundError("blocker not found in this event")
            return self._context(connection, event, blocker)

    def _context(self, connection, event, blocker) -> CoordinationContext:
        assessment = connection.execute(
            "SELECT * FROM blocker_assessments WHERE event_id=%s AND authoritative_blocker_id=%s",
            (event["id"], blocker["id"]),
        ).fetchone()
        resolution = connection.execute(
            "SELECT * FROM affected_work_resolutions WHERE event_id=%s AND blocker_id=%s",
            (event["id"], blocker["id"]),
        ).fetchone()
        if assessment is None or resolution is None:
            raise ValidationError("persisted blocker assessment and affected-work resolution are required")
        if event["version"] != resolution["resolved_event_version"]:
            raise StaleVersionError("event changed after affected-work resolution")
        graph = self.affected_work._load_confirmed_graph(connection, event["id"], event["version"])
        if graph["fingerprint"] != resolution["graph_fingerprint"]:
            raise StaleVersionError("confirmed graph changed after affected-work resolution")

        work_ids = list(dict.fromkeys(resolution["directly_affected_work_ids"] + resolution["downstream_affected_work_ids"]))
        stage_ids = list(dict.fromkeys(resolution["affected_stage_ids"]))
        work = [graph["work"][item] for item in work_ids if item in graph["work"]]
        stages = [graph["stages"][item] for item in stage_ids if item in graph["stages"]]
        if len(work) != len(work_ids) or len(stages) != len(stage_ids):
            raise StaleVersionError("affected-work scope is no longer authoritative")

        actors = connection.execute(
            """SELECT p.id AS participation_id,p.account_id,a.display_name,p.stage_id,s.canonical_name AS stage_name,
                      p.work_id,w.canonical_name AS work_name,p.actor_requirement_id,
                      ar.canonical_role_name,p.approved_start,p.approved_end,p.status,
                      pri.availability_type,pri.availability_start,pri.availability_end,
                      pri.max_commitment_minutes,pri.allow_alternative_work
               FROM participations p JOIN accounts a ON a.id=p.account_id
               JOIN actor_requirements ar ON ar.id=p.actor_requirement_id
               JOIN stages s ON s.id=p.stage_id
               JOIN work_items w ON w.id=p.work_id
               JOIN participation_request_items pri ON pri.id=p.approved_from_request_item_id
               WHERE p.event_id=%s AND p.status='ACCEPTED'
                 AND (p.work_id=ANY(%s::uuid[]) OR p.stage_id=ANY(%s::uuid[]))
               ORDER BY p.work_id,p.account_id""",
            (event["id"], work_ids, stage_ids),
        ).fetchall()
        role_ids = [row["actor_requirement_id"] for row in actors]
        meetings = connection.execute(
            """SELECT id,title,meeting_type,start_time,end_time,location,note,audience,
                      stage_id,work_id,actor_requirement_id,specific_actor_ids,status,version
               FROM event_meetings WHERE event_id=%s AND status<>'CANCELLED'
                 AND (audience='ALL_ACTORS' OR work_id=ANY(%s::uuid[])
                   OR stage_id=ANY(%s::uuid[]) OR actor_requirement_id=ANY(%s::uuid[]))
               ORDER BY start_time,id""",
            (event["id"], work_ids, stage_ids, role_ids),
        ).fetchall()
        setup = connection.execute(
            "SELECT version,resource_needs FROM event_setups WHERE event_id=%s", (event["id"],)
        ).fetchone()
        resources = list(setup["resource_needs"]) if setup else []
        source_versions = {
            "event": event["version"], "blocker": blocker["version"],
            "affected_graph_fingerprint": resolution["graph_fingerprint"],
            "stages": {str(row["id"]): row["version"] for row in stages},
            "work": {str(row["id"]): row["version"] for row in work},
            "participations": {str(row["participation_id"]): [row["status"], row["approved_start"].isoformat(), row["approved_end"].isoformat()] for row in actors},
            "meetings": {str(row["id"]): row["version"] for row in meetings},
            "event_setup": setup["version"] if setup else None,
        }
        canonical = json.dumps(source_versions, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return CoordinationContext(
            event={key: event[key] for key in ("id", "name", "starts_at", "ends_at", "timezone", "location_description", "version")},
            blocker={key: blocker[key] for key in ("id", "title", "summary", "category", "stage_id", "work_id", "handling_state", "condition_state", "version")},
            blocker_assessment={key: assessment[key] for key in ("id", "blocker_kind", "concise_reason", "directly_referenced_stage_id", "directly_referenced_work_id", "severity_internal", "urgency_internal", "coordination_needed", "replanning_may_be_needed", "requires_clarification", "clarification_question", "confidence")},
            affected_work_resolution={key: resolution[key] for key in ("id", "directly_affected_work_ids", "downstream_affected_work_ids", "affected_stage_ids", "deterministic_reason", "graph_fingerprint")},
            affected_stages=[{key: row[key] for key in ("id", "canonical_name", "purpose", "starts_at", "ends_at", "version")} for row in stages],
            affected_work=[{key: row[key] for key in ("id", "stage_id", "canonical_name", "purpose", "starts_at", "ends_at", "version")} for row in work],
            relevant_actors=[dict(row) for row in actors],
            relevant_meetings=[dict(row) for row in meetings],
            existing_resources=resources,
            source_fingerprint=fingerprint,
            source_versions=source_versions,
        )

    @staticmethod
    def validate(decision: CoordinationDecision, context: CoordinationContext) -> None:
        if decision.event_id != UUID(str(context.event["id"])) or decision.blocker_id != UUID(str(context.blocker["id"])):
            raise ValidationError("coordination result targets the wrong event or blocker")
        if decision.affected_work_resolution_id != UUID(str(context.affected_work_resolution["id"])):
            raise ValidationError("coordination result targets the wrong affected-work resolution")
        work_ids = {UUID(str(row["id"])) for row in context.affected_work}
        actor_ids = {UUID(str(row["account_id"])) for row in context.relevant_actors}
        meeting_ids = {UUID(str(row["id"])) for row in context.relevant_meetings}
        resources = {str(row.get("name")) for row in context.existing_resources}
        for action in decision.actions:
            if action.target_work_id is not None and action.target_work_id not in work_ids:
                raise ValidationError("coordination action references work outside affected scope")
            if action.target_actor_id is not None and action.target_actor_id not in actor_ids:
                raise ValidationError("coordination action references an unrelated actor")
            if action.target_meeting_id is not None and action.target_meeting_id not in meeting_ids:
                raise ValidationError("coordination action references an unrelated meeting")
            if action.resource_reference is not None and action.resource_reference not in resources:
                raise ValidationError("coordination action references an unavailable resource")
            if action.action_type in {"USE_EXISTING_RESOURCE", "MOVE_EXISTING_RESOURCE"} and action.resource_reference is None:
                raise ValidationError("resource coordination requires an existing resource reference")
            if action.action_type == "RESCHEDULE_MEETING" and action.target_meeting_id is None:
                raise ValidationError("meeting rescheduling requires a relevant meeting")
            if action.action_type == "REASSIGNMENT_SUGGESTION" and not action.requires_human_approval:
                raise ValidationError("reassignment suggestions require human approval")

    def complete(self, event_id, blocker_id, organizer_id, request_id, decision, **provenance):
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id, write=True)
            self.human_updates._require_organizer(connection, event, organizer_id)
            blocker = connection.execute("SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE", (blocker_id, event_id)).fetchone()
            request = connection.execute("SELECT * FROM coordination_requests WHERE id=%s AND blocker_id=%s FOR UPDATE", (request_id, blocker_id)).fetchone()
            if blocker is None or request is None or request["status"] != "RUNNING":
                raise IdempotencyConflictError("coordination request is not running")
            context = self._context(connection, event, blocker)
            if request["source_fingerprint"] != context.source_fingerprint:
                raise StaleVersionError("coordination source state changed during execution")
            self.validate(decision, context)
            row = connection.execute(
                """INSERT INTO coordination_proposals(
                       id,request_id,event_id,blocker_id,affected_work_resolution_id,
                       coordination_possible,requires_replanning,actions,rationale,confidence,
                       source_fingerprint,source_versions,provider_name,model_id,agent_name,
                       agent_version,stop_reason,usage)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (uuid4(), request_id, event_id, blocker_id, decision.affected_work_resolution_id,
                 decision.coordination_possible, decision.requires_replanning,
                 Jsonb([item.model_dump(mode="json") for item in decision.actions]), decision.rationale,
                 decision.confidence, context.source_fingerprint, Jsonb(context.source_versions),
                 provenance["provider_name"], provenance["model_id"], provenance["agent_name"],
                 provenance["agent_version"], provenance["stop_reason"], Jsonb(provenance["usage"])),
            ).fetchone()
            connection.execute("UPDATE coordination_requests SET status='SUCCEEDED',proposal_id=%s,updated_at=now() WHERE id=%s", (row["id"], request_id))
            PlanningService._enqueue_outbox(connection,event_type="coordination.proposed",aggregate_type="COORDINATION_PROPOSAL",aggregate_id=row["id"],aggregate_version=1,payload={"event_id":str(event_id),"blocker_id":str(blocker_id),"request_id":str(request_id),"proposal_id":str(row["id"]),"requires_replanning":decision.requires_replanning},correlation_id=correlation_id)
            return self._proposal(row)

    def fail(self, event_id: UUID, blocker_id: UUID, request_id: UUID, failure_code: str) -> None:
        with self.database.connect() as connection:
            request = connection.execute("SELECT * FROM coordination_requests WHERE id=%s AND event_id=%s AND blocker_id=%s FOR UPDATE", (request_id,event_id,blocker_id)).fetchone()
            if request is None or request["status"] != "RUNNING":
                return
            connection.execute("UPDATE coordination_requests SET status='FAILED',failure_code=%s,failed_at=now(),updated_at=now() WHERE id=%s", (failure_code[:100],request_id))
            PlanningService._enqueue_outbox(connection,event_type="coordination.failed",aggregate_type="COORDINATION_REQUEST",aggregate_id=request_id,aggregate_version=request["attempt_count"],payload={"event_id":str(event_id),"blocker_id":str(blocker_id),"request_id":str(request_id),"failure_code":failure_code[:100]},correlation_id=uuid4())
