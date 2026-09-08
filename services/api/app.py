from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import UploadFile

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


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=4000)
    event_type: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=1, max_length=100)
    location_description: str = Field(min_length=1, max_length=500)
    planning_context: EventPlanningContext | None = None
    idempotency_key: str = Field(min_length=1, max_length=200)


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


def create_app(database: Database, *, execute_planning_requests: bool = False, governance_upload_root: Path | None = None) -> FastAPI:
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
        if isinstance(error, (StaleProposalError, ProposalAlreadyDecidedError)):
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

    @app.post("/events", status_code=201)
    def create_event(
        body: EventCreateRequest,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        values = body.model_dump(exclude={"idempotency_key"})
        command = EventCreate(organizer_id=session.account.id, **values)
        return authorization.create_event_for_account(
            command, idempotency_key=body.idempotency_key
        )

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
        return {
            "event": event,
            "stages": stages,
            "selected_stage": selected_stage,
            "work_items": items,
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

    @app.get("/events/{event_id}/setup", response_model=EventSetupSnapshot)
    def get_event_setup(
        event_id: UUID,
        session: AuthenticatedSession = Depends(authenticated),
    ):
        authorization.require_active_organizer(event_id, session.account.id)
        return setup_service.get(event_id, session.account.id)

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
