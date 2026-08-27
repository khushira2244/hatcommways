"""Typed command and result models for deterministic planning operations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProposalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class ProposalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizer_id: UUID
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=4000)
    event_type: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(min_length=1, max_length=100)
    location_description: str = Field(min_length=1, max_length=500)

    @field_validator("name", "purpose", "event_type", "timezone", "location_description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("event timestamps must be timezone-aware")
        return self


class EventSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    organizer_id: UUID
    name: str
    purpose: str
    event_type: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    location_description: str
    version: int
    created_at: datetime
    updated_at: datetime


class ProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_type: str = Field(min_length=1, max_length=100)
    target_type: str = Field(min_length=1, max_length=100)
    target_id: UUID
    created_by: str = Field(min_length=1, max_length=200)
    base_versions: dict[str, int]
    payload: dict[str, Any]
    idempotency_key: str = Field(min_length=1, max_length=200)
    correlation_id: UUID = Field(default_factory=uuid4)

    @field_validator("base_versions")
    @classmethod
    def validate_base_versions(cls, value: dict[str, int]) -> dict[str, int]:
        if not value:
            raise ValueError("base_versions must not be empty")
        if any(version < 1 for version in value.values()):
            raise ValueError("base versions must be positive")
        return value


class ProposalSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    proposal_type: str
    target_type: str
    target_id: UUID
    created_by: str
    base_versions: dict[str, int]
    payload: dict[str, Any]
    status: ProposalStatus
    idempotency_key: str
    correlation_id: UUID
    created_at: datetime
    decided_at: datetime | None


class ProposalDecisionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    organizer_id: UUID
    decision: ProposalDecision
    decision_idempotency_key: str = Field(min_length=1, max_length=200)
    edited_payload: dict[str, Any] | None = None


class ProposalDecisionResult(BaseModel):
    proposal_id: UUID
    status: ProposalStatus
    applied_event: EventSnapshot | None = None
    duplicate: bool = False


class EventBrief(BaseModel):
    """Explicit allowlist returned by the scoped future-agent read tool."""

    event_id: UUID
    name: str
    purpose: str
    event_type: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    location_description: str
    version: int


class ProposedStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporary_stage_ref: str = Field(min_length=1, max_length=100)
    canonical_name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2000)
    proposed_order: int = Field(ge=1)
    proposed_start: datetime
    proposed_end: datetime
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("temporary_stage_ref", "canonical_name", "purpose")
    @classmethod
    def reject_blank_stage_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class StagePlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    event_id: UUID
    base_event_version: int = Field(ge=1)
    proposed_stages: list[ProposedStage]
    assumptions: list[str] = Field(default_factory=list)
    concise_rationale: str = Field(min_length=1, max_length=4000)
    approval_required: bool

    @field_validator("concise_rationale")
    @classmethod
    def reject_blank_rationale(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class StageSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    canonical_name: str
    purpose: str
    stage_order: int
    starts_at: datetime
    ends_at: datetime
    version: int
    source_proposal_id: UUID
    created_at: datetime
    updated_at: datetime
    dependency_stage_ids: list[UUID] = Field(default_factory=list)


class StagePlanDecisionResult(BaseModel):
    proposal_id: UUID
    status: ProposalStatus
    stages: list[StageSnapshot] = Field(default_factory=list)
    event_version: int | None = None
    duplicate: bool = False


class PlanningRequestStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventPlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    organizer_id: UUID
    base_event_version: int
    status: PlanningRequestStatus
    idempotency_key: str
    correlation_id: UUID
    proposal_id: UUID | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class ProposedWork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporary_work_ref: str = Field(min_length=1, max_length=100)
    canonical_name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2000)
    estimated_person_hours: float = Field(gt=0, le=100000)
    work_share: float = Field(gt=0, le=100)
    proposed_start: datetime
    proposed_end: datetime
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("temporary_work_ref", "canonical_name", "purpose")
    @classmethod
    def reject_blank_work_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class WorkDecompositionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    event_id: UUID
    stage_id: UUID
    base_event_version: int = Field(ge=1)
    base_stage_version: int = Field(ge=1)
    proposed_work: list[ProposedWork]
    assumptions: list[str] = Field(default_factory=list)
    concise_rationale: str = Field(min_length=1, max_length=4000)
    approval_required: bool

    @field_validator("concise_rationale")
    @classmethod
    def reject_blank_work_rationale(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class WorkSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    stage_id: UUID
    canonical_name: str
    purpose: str
    work_order: int
    estimated_person_hours: float
    work_share: float
    starts_at: datetime
    ends_at: datetime
    version: int
    source_proposal_id: UUID
    created_at: datetime
    updated_at: datetime
    dependency_work_ids: list[UUID] = Field(default_factory=list)


class WorkDesignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    stage_id: UUID
    organizer_id: UUID
    base_event_version: int
    base_stage_version: int
    status: PlanningRequestStatus
    idempotency_key: str
    correlation_id: UUID
    proposal_id: UUID | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class WorkPlanDecisionResult(BaseModel):
    proposal_id: UUID
    status: ProposalStatus
    work: list[WorkSnapshot] = Field(default_factory=list)
    event_version: int | None = None
    stage_version: int | None = None
    duplicate: bool = False


class StageWorkContext(BaseModel):
    """Allowlisted facts for one approved stage and its parent event."""

    event_id: UUID
    event_name: str
    event_purpose: str
    event_type: str
    event_version: int
    stage_id: UUID
    stage_name: str
    stage_purpose: str
    stage_start: datetime
    stage_end: datetime
    stage_version: int
