from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb
from uuid import uuid4
from starlette.datastructures import UploadFile
from psycopg.types.json import Jsonb

from services.auth.authorization import AccountAuthorizationService
from services.auth.errors import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from services.auth.models import (
    AccountSnapshot,
    AuthenticatedSession,
    SessionResult,
    SignInRequest,
    SignUpRequest,
)
from services.auth.service import AuthService
from services.agent_runtime.event_planning import EventPlanningWorkflow, StrandsEventPlanningAgent
from services.agent_runtime.work_design import WorkDesignWorkflow, StrandsWorkDesignAgent
from services.agent_runtime.actor_requirement import (
    ActorRequirementWorkflow,
    StrandsActorRequirementAgent,
)
from services.agent_runtime.governance import GovernanceWorkflow, StrandsGovernanceAgent
from services.agent_runtime.human_update_interpretation import (
    HumanUpdateInterpretationRuntime,
    HumanUpdateInterpretationWorkflow,
    StrandsHumanUpdateInterpretationAgent,
)
from services.agent_runtime.participation_advisory import DeterministicParticipationAdvisory, StrandsParticipationAdvisoryAgent
from services.planning_foundation.governance_service import GovernanceService
from services.planning_foundation.governance_evidence_storage import LocalGovernanceEvidenceStorage, MAX_EVIDENCE_BYTES
from services.planning_foundation.governance_models import ManualItem, ItemPatch, EvidenceCreate, SubmitGovernance
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.event_setup_models import EventSetupSnapshot, EventSetupUpdateRequest
from services.planning_foundation.event_setup_service import EventSetupService
from services.planning_foundation.database import Database
from services.planning_foundation.errors import (
    AuthorizationError,
    NotFoundError,
    PlanningError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
    StaleVersionError,
    IdempotencyConflictError,
    ValidationError,
)
from services.planning_foundation.models import (
    EventCreate,
    EventPlanningContext,
    ProposalDecision,
    ProposalDecisionCommand,
)
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.work_design_service import WorkDesignService
from services.planning_foundation.tools import ScopedPlanningReadTools
from services.planning_foundation.participation_models import AdvisoryRequest, ParticipationSubmit, ParticipationDecisionBody
from services.planning_foundation.participation_service import ParticipationService
from services.planning_foundation.actor_dashboard_service import ActorDashboardService
from services.planning_foundation.human_update_service import HumanUpdateService
from services.planning_foundation.human_update_interpretation_service import HumanUpdateInterpretationService
from services.planning_foundation.human_update_models import (
    BlockerCreate,
    BlockerPatch,
    BlockerSnapshot,
    HumanUpdateCreate,
    HumanUpdateInterpretationSnapshot,
    HumanUpdateSnapshot,
    InterpretHumanUpdateRequest,
)

class MeetingCreateBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1,max_length=200)
    meeting_type: Literal['BRIEFING','COORDINATION','HANDOFF','CHECK_IN','REVIEW','OTHER']
    start_time: datetime
    end_time: datetime
    location: str | None = None
    note: str | None = None
    audience: Literal['ALL_ACTORS','STAGE','WORK','ROLE','SPECIFIC_ACTORS']
    stage_id: UUID | None = None
    work_id: UUID | None = None
    actor_requirement_id: UUID | None = None
    specific_actor_ids: list[UUID] = []

class MeetingUpdateBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    start_time: datetime
    end_time: datetime
    location: str | None = None
    note: str | None = None
    status: Literal['SCHEDULED','RESCHEDULED','CANCELLED']

class AnnouncementBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1,max_length=200)
    message: str = Field(min_length=1,max_length=4000)
    priority: Literal['LOW','NORMAL','HIGH'] = 'NORMAL'


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=4000)
    event_type: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=1, max_length=100)
    location_description: str = Field(min_length=1, max_length=500)
    planning_context: EventPlanningContext | None = None
    idempotency_key: str = Field(min_length=1, max_length=200)
    draft_id: UUID | None = None


class PlanningRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_event_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=200)


class WorkDesignRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    expected_event_version: int = Field(ge=1)
    expected_stage_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=200)


class ActorRequirementRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    stage_id: UUID
    expected_event_version: int = Field(ge=1)
    expected_stage_version: int = Field(ge=1)
    expected_work_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=200)


class DecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: ProposalDecision
    decision_idempotency_key: str = Field(min_length=1, max_length=200)
    edited_payload: dict[str, Any] | None = None


class EventDraftBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: UUID | None = None
    payload: dict[str, Any]
    current_step: int = Field(ge=1, le=4)


class ResumeStateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_phase: Literal["GOVERNANCE", "STAGE_PLANNING", "WORK_DESIGN", "ACTOR_REQUIREMENTS", "EVENT_SETUP", "READY", "PUBLISHED"]
    last_open_stage_id: UUID | None = None


def create_app(
    database: Database,
    *,
    execute_planning_requests: bool = False,
    governance_upload_root: Path | None = None,
    human_update_interpretation_runtime: HumanUpdateInterpretationRuntime | None = None,
) -> FastAPI:
    app = FastAPI(title="Hatcommways API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    auth = AuthService(database)
    authorization = AccountAuthorizationService(database)
    stage_service = StagePlanningService(database)
    stage_workflow = EventPlanningWorkflow(
        stage_service,
        StrandsEventPlanningAgent(ScopedPlanningReadTools(stage_service.base)),
    )
    work_service = WorkDesignService(database)
    work_workflow = WorkDesignWorkflow(
        work_service,
        StrandsWorkDesignAgent(ScopedPlanningReadTools(work_service.base)),
    )
    actor_service = ActorRequirementService(database)
    participation_service = ParticipationService(database)
    actor_dashboard_service = ActorDashboardService(database)
    human_update_service = HumanUpdateService(database)
    human_update_interpretation_service = HumanUpdateInterpretationService(database)
    interpretation_runtime = human_update_interpretation_runtime or StrandsHumanUpdateInterpretationAgent(
        human_update_interpretation_service
    )
    human_update_interpretation_workflow = HumanUpdateInterpretationWorkflow(
        human_update_interpretation_service, interpretation_runtime
    )
    interpretation_execution_enabled = (
        execute_planning_requests or human_update_interpretation_runtime is not None
    )
    participation_advisor = StrandsParticipationAdvisoryAgent() if execute_planning_requests else DeterministicParticipationAdvisory()
    setup_service = EventSetupService(database)
    governance_service = GovernanceService(database)
    governance_storage = LocalGovernanceEvidenceStorage(governance_upload_root)
    governance_workflow = GovernanceWorkflow(governance_service, StrandsGovernanceAgent(governance_service))
    actor_workflow = ActorRequirementWorkflow(
        actor_service,
        StrandsActorRequirementAgent(ScopedPlanningReadTools(actor_service.base)),
    )
    bearer = HTTPBearer(auto_error=False)

    @app.exception_handler(DuplicateEmailError)
    async def duplicate_email_handler(_request, error):
        return _error_response(409, str(error))

    @app.exception_handler(InvalidCredentialsError)
    async def credentials_handler(_request, error):
        return _error_response(401, str(error), authenticate=True)

    @app.exception_handler(InvalidSessionError)
    async def session_handler(_request, error):
        return _error_response(401, str(error), authenticate=True)

    @app.exception_handler(PlanningError)
    async def planning_error_handler(_request, error):
        if isinstance(error, AuthorizationError):
            return _error_response(403, str(error))
        if isinstance(error, NotFoundError):
            return _error_response(404, str(error))
        if isinstance(error, (StaleProposalError, ProposalAlreadyDecidedError, StaleVersionError, IdempotencyConflictError)):
            return _error_response(409, str(error))
        return _error_response(422, str(error))

    def authenticated(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> AuthenticatedSession:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise InvalidSessionError("authentication required")
        return auth.authenticate(credentials.credentials)

    def authenticated_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> tuple[str, AuthenticatedSession]:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise InvalidSessionError("authentication required")
        return credentials.credentials, auth.authenticate(credentials.credentials)

    def require_proposal_organizer(proposal_id: UUID, account_id: UUID) -> None:
        with database.connect() as connection:
            row = connection.execute(
                """
                SELECT CASE p.target_type
                    WHEN 'EVENT' THEN p.target_id
                    WHEN 'STAGE' THEN s.event_id
                    WHEN 'WORK' THEN w.event_id
                END AS event_id
                FROM proposals p
                LEFT JOIN stages s ON p.target_type='STAGE' AND s.id=p.target_id
                LEFT JOIN work_items w ON p.target_type='WORK' AND w.id=p.target_id
                WHERE p.id=%s
                """,
                (proposal_id,),
            ).fetchone()
        if row is None or row["event_id"] is None:
            raise NotFoundError("proposal not found")
        authorization.require_active_organizer(row["event_id"], account_id)

    @app.post("/auth/signup", response_model=AccountSnapshot, status_code=201)
    def sign_up(command: SignUpRequest):
        return auth.sign_up(command)

    @app.post("/auth/signin", response_model=SessionResult)
    def sign_in(command: SignInRequest):
        return auth.sign_in(command)

    @app.post("/auth/signout", status_code=204)
    def sign_out(
        token_and_session: tuple[str, AuthenticatedSession] = Depends(authenticated_token),
    ):
        token, _session = token_and_session
        auth.sign_out(token)
        return Response(status_code=204)

    @app.get("/auth/me", response_model=AccountSnapshot)
    def current_account(session: AuthenticatedSession = Depends(authenticated)):
        return session.account

    @app.put("/me/event-drafts")
    def save_event_draft(body: EventDraftBody, session: AuthenticatedSession = Depends(authenticated)):
        draft_id = body.draft_id or uuid4()
        with database.connect() as connection:
            existing = connection.execute("SELECT account_id FROM event_creation_drafts WHERE id=%s", (draft_id,)).fetchone()
            if existing is not None and existing["account_id"] != session.account.id:
                raise AuthorizationError("event draft belongs to another account")
            row = connection.execute(
                """INSERT INTO event_creation_drafts(id,account_id,name,current_step,payload)
                   VALUES(%s,%s,%s,%s,%s)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,current_step=excluded.current_step,
                     payload=excluded.payload,version=event_creation_drafts.version+1,updated_at=now()
                   RETURNING *""",
                (draft_id, session.account.id, str(body.payload.get("name") or "Untitled event").strip() or "Untitled event", body.current_step, Jsonb(body.payload)),
            ).fetchone()
        return row

    @app.get("/me/event-drafts/{draft_id}")
    def get_event_draft(draft_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        with database.connect() as connection:
            row = connection.execute("SELECT * FROM event_creation_drafts WHERE id=%s AND account_id=%s", (draft_id, session.account.id)).fetchone()
        if row is None:
            raise NotFoundError("event draft not found")
        return row

    @app.put("/events/{event_id}/resume-state")
    def save_resume_state(event_id: UUID, body: ResumeStateBody, session: AuthenticatedSession = Depends(authenticated)):
        authorization.require_active_organizer(event_id, session.account.id)
        if body.last_open_stage_id is not None:
            with database.connect() as connection:
                stage = connection.execute("SELECT event_id FROM stages WHERE id=%s", (body.last_open_stage_id,)).fetchone()
            if stage is None or stage["event_id"] != event_id:
                raise ValidationError("last open stage must belong to the event")
        with database.connect() as connection:
            row = connection.execute(
                """INSERT INTO event_resume_states(event_id,account_id,current_phase,last_open_stage_id)
                   VALUES(%s,%s,%s,%s)
                   ON CONFLICT(event_id) DO UPDATE SET account_id=excluded.account_id,current_phase=excluded.current_phase,
                     last_open_stage_id=excluded.last_open_stage_id,updated_at=now() RETURNING *""",
                (event_id, session.account.id, body.current_phase, body.last_open_stage_id),
            ).fetchone()
        return row

    @app.get("/me/events")
    def my_events(session: AuthenticatedSession = Depends(authenticated)):
        with database.connect() as connection:
            drafts = connection.execute("SELECT * FROM event_creation_drafts WHERE account_id=%s ORDER BY updated_at DESC", (session.account.id,)).fetchall()
            events = connection.execute(
                """SELECT e.*,m.role,m.status AS relationship_status,r.current_phase,r.last_open_stage_id,r.updated_at AS resume_updated_at,
                    g.organizer_visible_status AS governance_status,
                    (SELECT count(*) FROM stages s WHERE s.event_id=e.id) AS stage_count,
                    (SELECT count(*) FROM work_items w WHERE w.event_id=e.id) AS work_count,
                    (SELECT count(*) FROM actor_requirements a WHERE a.event_id=e.id) AS actor_requirement_count,
                    EXISTS(SELECT 1 FROM event_setups es WHERE es.event_id=e.id) AS setup_saved
                   FROM event_memberships m JOIN events e ON e.id=m.event_id
                   LEFT JOIN event_resume_states r ON r.event_id=e.id AND r.account_id=m.account_id
                   LEFT JOIN LATERAL (SELECT organizer_visible_status FROM governance_assessments ga WHERE ga.event_id=e.id ORDER BY updated_at DESC LIMIT 1) g ON true
                   WHERE m.account_id=%s ORDER BY e.updated_at DESC""",
                (session.account.id,),
            ).fetchall()
            requested_events = connection.execute(
                """SELECT DISTINCT ON (pr.event_id) e.*,pr.id AS request_id,pr.status AS participation_status,
                          pr.updated_at AS participation_updated_at,
                          (SELECT count(*) FROM participation_request_items pri WHERE pri.participation_request_id=pr.id) AS requested_assignment_count,
                          (SELECT string_agg(ar.canonical_role_name, ', ' ORDER BY ar.canonical_role_name) FROM participation_request_items pri JOIN actor_requirements ar ON ar.id=pri.actor_requirement_id WHERE pri.participation_request_id=pr.id AND pri.status='APPROVED') AS approved_roles,
                          (SELECT min(p.approved_start) FROM participations p WHERE p.event_id=pr.event_id AND p.account_id=pr.requester_account_id AND p.status='ACCEPTED') AS approved_start,
                          (SELECT max(p.approved_end) FROM participations p WHERE p.event_id=pr.event_id AND p.account_id=pr.requester_account_id AND p.status='ACCEPTED') AS approved_end
                   FROM participation_requests pr JOIN events e ON e.id=pr.event_id
                   WHERE pr.requester_account_id=%s ORDER BY pr.event_id,pr.updated_at DESC""", (session.account.id,)
            ).fetchall()
        organizing=[]; participating=[]
        for event in events:
            if event["role"] != "ORGANIZER":
                request = next((x for x in requested_events if x["id"] == event["id"]), None)
                participation_status=request["participation_status"] if request else "APPROVED"
                target=f"actor-dashboard.html?event={event['id']}" if participation_status in ('APPROVED','PARTIALLY_APPROVED') else f"join-actor.html?event={event['id']}"
                participating.append({"event_id":event["id"],"event_name":event["name"],"category":event["category"],"location":event["location_description"],"starts_at":event["starts_at"],"ends_at":event["ends_at"],"relationship":"ACTOR","relationship_status":participation_status,"current_phase":participation_status,"last_saved_at":request["participation_updated_at"] if request else event["updated_at"],"resume_target":target,"requested_assignment_count":request["requested_assignment_count"] if request else 0,"approved_roles":request["approved_roles"] if request else None,"approved_start":request["approved_start"] if request else None,"approved_end":request["approved_end"] if request else None,"published":True})
                continue
            phase = event["current_phase"] or "GOVERNANCE"
            stage_id = event["last_open_stage_id"]
            if phase == "WORK_DESIGN" and stage_id is None:
                with database.connect() as connection:
                    incomplete = connection.execute("""SELECT s.id FROM stages s WHERE s.event_id=%s AND NOT EXISTS(SELECT 1 FROM work_items w WHERE w.stage_id=s.id) ORDER BY s.stage_order LIMIT 1""", (event["id"],)).fetchone()
                stage_id = incomplete["id"] if incomplete else None
            routes={"GOVERNANCE":f"governance.html?event={event['id']}","STAGE_PLANNING":f"planning.html?event={event['id']}","WORK_DESIGN":f"stage.html?event={event['id']}&id={stage_id}" if stage_id else f"planning.html?event={event['id']}","ACTOR_REQUIREMENTS":f"actor-tree.html?event={event['id']}","EVENT_SETUP":f"event-setup.html?event={event['id']}","READY":f"event.html?event={event['id']}","PUBLISHED":f"event.html?event={event['id']}"}
            item={"event_id":event["id"],"event_name":event["name"],"category":event["category"],"location":event["location_description"],"starts_at":event["starts_at"],"ends_at":event["ends_at"],"relationship":event["role"],"relationship_status":event["relationship_status"],"current_phase":phase,"last_saved_at":event["resume_updated_at"] or event["updated_at"],"resume_target":routes.get(phase,routes["GOVERNANCE"]),"last_open_stage_id":stage_id,"governance_status":event["governance_status"],"stage_count":event["stage_count"],"work_count":event["work_count"],"actor_requirement_count":event["actor_requirement_count"],"event_setup_status":"SAVED" if event["setup_saved"] else "NOT_STARTED","published":phase=="PUBLISHED"}
            (organizing if event["role"]=="ORGANIZER" else participating).append(item)
        existing_participating={item["event_id"] for item in participating}
        for event in requested_events:
            if event["id"] in existing_participating: continue
            target=f"actor-dashboard.html?event={event['id']}" if event['participation_status'] in ('APPROVED','PARTIALLY_APPROVED') else f"join-actor.html?event={event['id']}"
            participating.append({"event_id":event["id"],"event_name":event["name"],"category":event["category"],"location":event["location_description"],"starts_at":event["starts_at"],"ends_at":event["ends_at"],"relationship":"REQUESTER","relationship_status":event["participation_status"],"current_phase":event["participation_status"],"last_saved_at":event["participation_updated_at"],"resume_target":target,"requested_assignment_count":event["requested_assignment_count"],"approved_roles":event["approved_roles"],"approved_start":event["approved_start"],"approved_end":event["approved_end"],"published":True})
        draft_items=[{"draft_id":row["id"],"event_name":row["name"],"current_phase":"CREATION_DRAFT","current_step":row["current_step"],"last_saved_at":row["updated_at"],"resume_target":f"create-event.html?draft={row['id']}"} for row in drafts]
        return {"organizing":draft_items+organizing,"participating":participating}

    @app.post("/events", status_code=201)
    def create_event(
        body: EventCreateRequest,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        values = body.model_dump(exclude={"idempotency_key", "draft_id"})
        command = EventCreate(organizer_id=session.account.id, **values)
        event = authorization.create_event_for_account(
            command, idempotency_key=body.idempotency_key
        )
        with database.connect() as connection:
            connection.execute("INSERT INTO event_resume_states(event_id,account_id,current_phase) VALUES(%s,%s,'GOVERNANCE') ON CONFLICT(event_id) DO NOTHING", (event.id, session.account.id))
            if body.draft_id is not None:
                connection.execute("DELETE FROM event_creation_drafts WHERE id=%s AND account_id=%s", (body.draft_id, session.account.id))
        return event

    @app.post("/events/{event_id}/planning-requests", status_code=201)
    def request_event_planning(
        event_id: UUID,
        body: PlanningRequestBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        planning_request = stage_service.request_event_planning(
            event_id=event_id,
            organizer_id=session.account.id,
            expected_event_version=body.expected_event_version,
            idempotency_key=body.idempotency_key,
        )
        if execute_planning_requests and planning_request.status.value == "REQUESTED":
            stage_workflow.execute(planning_request.id)
        return stage_service.get_request(planning_request.id)

    @app.get("/events/{event_id}/stage-plan-workspace")
    def get_stage_plan_workspace(
        event_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        event = stage_service.base.get_event(event_id)
        stages = stage_service.list_stages(event_id)
        with database.connect() as connection:
            request = connection.execute(
                """
                SELECT * FROM event_planning_requests
                WHERE event_id=%s
                ORDER BY created_at DESC LIMIT 1
                """,
                (event_id,),
            ).fetchone()
        proposal = (
            stage_service.base.get_proposal(request["proposal_id"])
            if request is not None and request["proposal_id"] is not None else None
        )
        if stages:
            mode = "CONFIRMED"
        elif proposal is not None and proposal.status.value == "PENDING":
            mode = "PROPOSAL"
        elif request is not None and request["status"] in ("REQUESTED", "RUNNING"):
            mode = "RUNNING"
        elif request is not None and request["status"] == "FAILED":
            mode = "FAILED"
        else:
            mode = "EMPTY"
        return {
            "mode": mode,
            "event": event,
            "planning_request": request,
            "proposal": proposal,
            "stages": stages,
        }

    @app.post("/stage-proposals/{proposal_id}/decision")
    def decide_stage_plan(
        proposal_id: UUID,
        body: DecisionBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        require_proposal_organizer(proposal_id, session.account.id)
        return stage_service.decide_stage_plan(
            ProposalDecisionCommand(
                proposal_id=proposal_id,
                organizer_id=session.account.id,
                **body.model_dump(),
            )
        )

    @app.post("/stages/{stage_id}/work-design-requests", status_code=201)
    def request_work_design(
        stage_id: UUID,
        body: WorkDesignRequestBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(body.event_id, session.account.id)
        work_request = work_service.request_work_design(
            event_id=body.event_id,
            stage_id=stage_id,
            organizer_id=session.account.id,
            expected_event_version=body.expected_event_version,
            expected_stage_version=body.expected_stage_version,
            idempotency_key=body.idempotency_key,
        )
        if execute_planning_requests and work_request.status.value == "REQUESTED":
            work_workflow.execute(work_request.id)
        return work_service.get_request(work_request.id)

    @app.get("/events/{event_id}/stages/{stage_id}/work-design-workspace")
    def get_work_design_workspace(
        event_id: UUID,
        stage_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        event = work_service.base.get_event(event_id)
        stage = work_service.get_stage(stage_id)
        if stage.event_id != event_id:
            raise NotFoundError("stage is not part of this event")
        stages = stage_service.list_stages(event_id)
        work = work_service.list_work(stage_id)
        with database.connect() as connection:
            request = connection.execute(
                """
                SELECT * FROM work_design_requests
                WHERE event_id=%s AND stage_id=%s
                ORDER BY created_at DESC LIMIT 1
                """,
                (event_id, stage_id),
            ).fetchone()
        proposal = (
            work_service.base.get_proposal(request["proposal_id"])
            if request is not None and request["proposal_id"] is not None else None
        )
        if work:
            mode = "CONFIRMED"
        elif proposal is not None and proposal.status.value == "PENDING":
            mode = "PROPOSAL"
        elif request is not None:
            mode = request["status"]
        else:
            mode = "EMPTY"
        return {
            "mode": mode,
            "event": event,
            "stages": stages,
            "selected_stage": stage,
            "work_design_request": request,
            "proposal": proposal,
            "work": work,
        }

    @app.post("/work-proposals/{proposal_id}/decision")
    def decide_work(
        proposal_id: UUID,
        body: DecisionBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        require_proposal_organizer(proposal_id, session.account.id)
        return work_service.decide_work_decomposition(
            ProposalDecisionCommand(
                proposal_id=proposal_id,
                organizer_id=session.account.id,
                **body.model_dump(),
            )
        )

    @app.post("/work/{work_id}/actor-requirement-requests", status_code=201)
    def request_actor_requirements(
        work_id: UUID,
        body: ActorRequirementRequestBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(body.event_id, session.account.id)
        actor_request = actor_service.request_actor_requirements(
            event_id=body.event_id,
            stage_id=body.stage_id,
            work_id=work_id,
            organizer_id=session.account.id,
            expected_event_version=body.expected_event_version,
            expected_stage_version=body.expected_stage_version,
            expected_work_version=body.expected_work_version,
            idempotency_key=body.idempotency_key,
        )
        if execute_planning_requests and actor_request.status.value == "REQUESTED":
            actor_workflow.execute(actor_request.id)
        return actor_service.get_request(actor_request.id)

    @app.get("/events/{event_id}/actor-tree-workspace")
    def get_event_actor_tree_workspace(
        event_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        return actor_service.event_workspace(event_id)

    @app.get("/events/{event_id}/stages/{stage_id}/actor-tree-workspace")
    def get_actor_tree_workspace(
        event_id: UUID,
        stage_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        event = actor_service.base.get_event(event_id)
        selected_stage = actor_service.get_stage(stage_id)
        if selected_stage.event_id != event_id:
            raise NotFoundError("stage is not part of this event")
        stages = stage_service.list_stages(event_id)
        work = work_service.list_work(stage_id)
        items = []
        with database.connect() as connection:
            for work_item in work:
                request = connection.execute(
                    """
                    SELECT * FROM actor_requirement_requests
                    WHERE event_id=%s AND stage_id=%s AND work_id=%s
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (event_id, stage_id, work_item.id),
                ).fetchone()
                proposal = (
                    actor_service.base.get_proposal(request["proposal_id"])
                    if request is not None and request["proposal_id"] is not None
                    else None
                )
                items.append({
                    "work": work_item,
                    "actor_requirement_request": request,
                    "proposal": proposal,
                    "requirements": actor_service.list_requirements(work_item.id),
                })
            participations = connection.execute(
                """SELECT p.*,a.display_name,a.email FROM participations p
                   JOIN accounts a ON a.id=p.account_id
                   WHERE p.event_id=%s AND p.status='ACCEPTED'""", (event_id,)
            ).fetchall()
        return {
            "event": event,
            "stages": stages,
            "selected_stage": selected_stage,
            "work_items": items,
            "participations": participations,
        }

    @app.post("/actor-requirement-proposals/{proposal_id}/decision")
    def decide_actor_requirements(
        proposal_id: UUID,
        body: DecisionBody,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        require_proposal_organizer(proposal_id, session.account.id)
        return actor_service.decide_actor_requirements(
            ProposalDecisionCommand(
                proposal_id=proposal_id,
                organizer_id=session.account.id,
                **body.model_dump(),
            )
        )

    @app.get("/events/{event_id}/join-options")
    def get_join_options(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return participation_service.join_options(event_id, session.account.id)

    @app.post("/events/{event_id}/participation-advisories", status_code=201)
    def create_participation_advisory(event_id: UUID, body: AdvisoryRequest, session: AuthenticatedSession = Depends(authenticated)):
        context = participation_service.advisory_context(event_id, session.account.id, body)
        result = participation_advisor.generate(context)
        return participation_service.store_advisory(event_id, session.account.id, body, result)

    @app.post("/events/{event_id}/participation-requests", status_code=201)
    def create_participation_request(event_id: UUID, body: ParticipationSubmit, session: AuthenticatedSession = Depends(authenticated)):
        return participation_service.submit(event_id, session.account.id, body)

    @app.get("/participation-requests/{request_id}")
    def get_participation_request(request_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return participation_service.get_request(request_id, session.account.id)

    @app.get("/events/{event_id}/participation-notifications")
    def get_participation_notifications(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return participation_service.notifications(event_id, session.account.id)

    @app.post("/participation-request-items/{item_id}/decision")
    def decide_participation_item(item_id: UUID, body: ParticipationDecisionBody, session: AuthenticatedSession = Depends(authenticated)):
        return participation_service.decide_item(item_id, session.account.id, body.decision, body.idempotency_key)

    @app.post('/events/{event_id}/human-updates', status_code=201, response_model=HumanUpdateSnapshot)
    def submit_human_update(event_id: UUID, body: HumanUpdateCreate, session: AuthenticatedSession = Depends(authenticated)):
        return human_update_service.submit(event_id, session.account.id, body)

    @app.get('/events/{event_id}/human-updates', response_model=list[HumanUpdateSnapshot])
    def list_human_updates(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return human_update_service.list_updates(event_id, session.account.id)

    @app.post(
        '/events/{event_id}/human-updates/{update_id}/interpret',
        response_model=HumanUpdateInterpretationSnapshot,
    )
    def interpret_human_update(
        event_id: UUID,
        update_id: UUID,
        body: InterpretHumanUpdateRequest = InterpretHumanUpdateRequest(),
        session: AuthenticatedSession = Depends(authenticated),
    ):
        if not interpretation_execution_enabled:
            raise ValidationError('human update interpretation agent execution is disabled')
        return human_update_interpretation_workflow.execute(
            event_id=event_id,
            update_id=update_id,
            organizer_id=session.account.id,
            retry=body.retry,
        )

    @app.get(
        '/events/{event_id}/human-updates/{update_id}/interpretation',
        response_model=HumanUpdateInterpretationSnapshot | None,
    )
    def get_human_update_interpretation(
        event_id: UUID,
        update_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        return human_update_interpretation_service.get_interpretation(
            event_id, update_id, session.account.id
        )

    @app.post('/events/{event_id}/blockers', status_code=201, response_model=BlockerSnapshot)
    def create_blocker(event_id: UUID, body: BlockerCreate, session: AuthenticatedSession = Depends(authenticated)):
        return human_update_service.create_blocker(event_id, session.account.id, body)

    @app.get('/events/{event_id}/blockers', response_model=list[BlockerSnapshot])
    def list_blockers(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return human_update_service.list_blockers(event_id, session.account.id)

    @app.patch('/events/{event_id}/blockers/{blocker_id}', response_model=BlockerSnapshot)
    def update_blocker(event_id: UUID, blocker_id: UUID, body: BlockerPatch, session: AuthenticatedSession = Depends(authenticated)):
        return human_update_service.update_blocker(event_id, blocker_id, session.account.id, body)

    @app.get('/events/{event_id}/actor-dashboard')
    def actor_dashboard(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        return actor_dashboard_service.get(event_id, session.account.id)

    @app.post('/events/{event_id}/meetings', status_code=201)
    def create_meeting(event_id: UUID, body: MeetingCreateBody, session: AuthenticatedSession = Depends(authenticated)):
        return actor_dashboard_service.create_meeting(event_id, session.account.id, body)

    @app.put('/events/{event_id}/meetings/{meeting_id}')
    def update_meeting(event_id: UUID, meeting_id: UUID, body: MeetingUpdateBody, session: AuthenticatedSession = Depends(authenticated)):
        return actor_dashboard_service.update_meeting(event_id, meeting_id, session.account.id, body)

    @app.post('/events/{event_id}/announcements', status_code=201)
    def create_announcement(event_id: UUID, body: AnnouncementBody, session: AuthenticatedSession = Depends(authenticated)):
        return actor_dashboard_service.announce(event_id, session.account.id, body)

    @app.get("/events/{event_id}/setup", response_model=EventSetupSnapshot)
    def get_event_setup(
        event_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        return setup_service.get(event_id, session.account.id)

    @app.get("/events/{event_id}/home")
    def get_event_home(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        event = stage_service.base.get_event(event_id)
        stages = stage_service.list_stages(event_id)
        with database.connect() as connection:
            setup_row = connection.execute("SELECT * FROM event_setups WHERE event_id=%s", (event_id,)).fetchone()
            setup = setup_service._snapshot(event_id, setup_row)
            membership = connection.execute("SELECT role FROM event_memberships WHERE event_id=%s AND account_id=%s AND status='ACTIVE' ORDER BY CASE role WHEN 'ORGANIZER' THEN 0 ELSE 1 END LIMIT 1", (event_id, session.account.id)).fetchone()
            if setup.privacy_settings.event_visibility.value == 'PRIVATE' and membership is None:
                raise AuthorizationError('this event is private')
            assessment = connection.execute("SELECT id,event_id,version,governance_required,completeness,review_mode,organizer_visible_status,location_context,reasoning_summary,created_at,updated_at FROM governance_assessments WHERE event_id=%s", (event_id,)).fetchone()
            governance = {"event_id": str(event_id), "assessment": assessment, "items": []}
            requirements = connection.execute(
                """SELECT id,event_id,stage_id,work_id,role_category,
                          canonical_role_name,responsibility_summary,
                          minimum_required_count,version
                   FROM actor_requirements WHERE event_id=%s
                   ORDER BY stage_id,canonical_role_name,id""",
                (event_id,),
            ).fetchall()
            resume = connection.execute(
                "SELECT current_phase FROM event_resume_states WHERE event_id=%s ORDER BY updated_at DESC LIMIT 1",
                (event_id,),
            ).fetchone()
            organizer = connection.execute(
                """SELECT a.id,a.display_name,a.email
                   FROM event_memberships em
                   JOIN accounts a ON a.id=em.account_id
                   WHERE em.event_id=%s AND em.role='ORGANIZER' AND em.status='ACTIVE'
                   ORDER BY em.created_at LIMIT 1""",
                (event_id,),
            ).fetchone()
        return {"event": event, "stages": stages, "actor_requirements": requirements,
                "setup": setup, "governance": governance, "relationship": membership["role"] if membership else "VISITOR",
                "organizer": dict(organizer) if organizer else None,
                "current_phase": resume["current_phase"] if resume else "EVENT_SETUP"}

    @app.put("/events/{event_id}/setup", response_model=EventSetupSnapshot)
    def update_event_setup(
        event_id: UUID,
        body: EventSetupUpdateRequest,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        return setup_service.update(event_id, session.account.id, body)

    @app.post("/events/{event_id}/governance-assessment")
    def assess_governance(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        authorization.require_active_organizer(event_id, session.account.id)
        if not execute_planning_requests:
            raise ValidationError("governance agent execution is disabled")
        return governance_workflow.execute(event_id, session.account.id)

    @app.get("/events/{event_id}/governance")
    def get_governance(event_id: UUID, session: AuthenticatedSession = Depends(authenticated)):
        authorization.require_active_organizer(event_id, session.account.id)
        return governance_service.get(event_id, session.account.id)

    @app.post("/events/{event_id}/governance/items", status_code=201)
    def add_governance_item(event_id: UUID, body: ManualItem, session: AuthenticatedSession = Depends(authenticated)):
        authorization.require_active_organizer(event_id, session.account.id)
        return governance_service.add_item(event_id, session.account.id, body)

    @app.patch("/governance/items/{item_id}")
    def patch_governance_item(item_id: UUID, body: ItemPatch, session: AuthenticatedSession = Depends(authenticated)):
        return governance_service.patch_item(item_id, session.account.id, body)

    @app.post("/governance/items/{item_id}/evidence", status_code=201)
    async def add_governance_evidence(item_id: UUID, request: Request, session: AuthenticatedSession = Depends(authenticated)):
        content_type = request.headers.get("content-type", "")
        if content_type.lower().startswith("multipart/form-data"):
            form = await request.form()
            upload = form.get("file")
            if not isinstance(upload, UploadFile):
                raise ValidationError("an evidence file is required")
            content = await upload.read(MAX_EVIDENCE_BYTES + 1)
            stored = governance_storage.save(upload.filename or "", upload.content_type or "", content)
            label = str(form.get("label") or stored.original_filename).strip()
            note = str(form.get("note") or "").strip() or None
            if not label or len(label) > 200:
                governance_storage.delete(stored.storage_key)
                raise ValidationError("evidence label must be between 1 and 200 characters")
            if note and len(note) > 2000:
                governance_storage.delete(stored.storage_key)
                raise ValidationError("evidence note must be 2000 characters or fewer")
            try:
                return governance_service.add_file_evidence(item_id, session.account.id, stored, label, note)
            except Exception:
                governance_storage.delete(stored.storage_key)
                raise
        body = EvidenceCreate.model_validate(await request.json())
        return governance_service.add_evidence(item_id, session.account.id, body)

    @app.post("/events/{event_id}/governance/submit")
    def submit_governance(event_id: UUID, body: SubmitGovernance, session: AuthenticatedSession = Depends(authenticated)):
        authorization.require_active_organizer(event_id, session.account.id)
        return governance_service.submit(event_id, session.account.id, body)

    return app


def _error_response(status_code: int, detail: str, *, authenticate: bool = False):
    from fastapi.responses import JSONResponse

    headers = {"WWW-Authenticate": "Bearer"} if authenticate else None
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)
