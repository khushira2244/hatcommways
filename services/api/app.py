from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

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
from services.planning_foundation.actor_requirement_service import ActorRequirementService
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


def create_app(database: Database, *, execute_planning_requests: bool = False) -> FastAPI:
    app = FastAPI(title="Hatcommways API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
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
    actor_service = ActorRequirementService(database)
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
        return work_service.request_work_design(
            event_id=body.event_id,
            stage_id=stage_id,
            organizer_id=session.account.id,
            expected_event_version=body.expected_event_version,
            expected_stage_version=body.expected_stage_version,
            idempotency_key=body.idempotency_key,
        )

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
        return actor_service.request_actor_requirements(
            event_id=body.event_id,
            stage_id=body.stage_id,
            work_id=work_id,
            organizer_id=session.account.id,
            expected_event_version=body.expected_event_version,
            expected_stage_version=body.expected_stage_version,
            expected_work_version=body.expected_work_version,
            idempotency_key=body.idempotency_key,
        )

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

    return app


def _error_response(status_code: int, detail: str, *, authenticate: bool = False):
    from fastapi.responses import JSONResponse

    headers = {"WWW-Authenticate": "Bearer"} if authenticate else None
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)
