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


class NamingTheme(StrEnum):
    HERO = "Hero / Avengers-style"
    MISSION = "Mission / Operations"
    COMMUNITY = "Community / Neighbor"
    PROFESSIONAL = "Professional / Formal"
    FESTIVAL = "Festival / Celebration"
    CUSTOM = "Custom"


class EventPlanningContext(BaseModel):
    """Organizer-provided planning facts; none are confirmed execution state."""

    model_config = ConfigDict(extra="forbid")

    detailed_purpose: str = Field(min_length=1, max_length=4000)
    expected_scale: int | None = Field(default=None, ge=1, le=1_000_000)
    intended_participants: list[str] = Field(default_factory=list, max_length=20)
    custom_intended_participant: str | None = Field(default=None, max_length=200)
    known_resources: str | None = Field(default=None, max_length=4000)
    known_requirements: str | None = Field(default=None, max_length=4000)
    constraints: str | None = Field(default=None, max_length=4000)
    desired_outcomes: str | None = Field(default=None, max_length=4000)
    organizer_notes: str | None = Field(default=None, max_length=4000)
    theme: NamingTheme
    custom_theme: str | None = Field(default=None, max_length=200)

    @field_validator("detailed_purpose")
    @classmethod
    def trim_required_context(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator(
        "custom_intended_participant", "known_resources", "known_requirements",
        "constraints", "desired_outcomes", "organizer_notes", "custom_theme",
        mode="before",
    )
    @classmethod
    def normalize_optional_context(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("intended_participants")
    @classmethod
    def validate_participant_types(cls, values: list[str]) -> list[str]:
        allowed = {
            "Community Members", "Volunteers", "Students", "Families",
            "Organizations", "Local Businesses", "Experts / Specialists", "Other",
        }
        normalized = [value.strip() for value in values]
        if any(value not in allowed for value in normalized):
            raise ValueError("contains an unsupported intended participant type")
        if len(normalized) != len(set(normalized)):
            raise ValueError("intended participant types must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_custom_values(self) -> "EventPlanningContext":
        if "Other" in self.intended_participants and not self.custom_intended_participant:
            raise ValueError("custom intended participant is required when Other is selected")
        if "Other" not in self.intended_participants:
            self.custom_intended_participant = None
        if self.theme == NamingTheme.CUSTOM and not self.custom_theme:
            raise ValueError("custom theme is required when Custom is selected")
        if self.theme != NamingTheme.CUSTOM:
            self.custom_theme = None
        return self


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
    planning_context: EventPlanningContext | None = None

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
    planning_context: EventPlanningContext | None = None
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
    planning_context: EventPlanningContext | None = None
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


class ProposedActorRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_category: str = Field(min_length=1, max_length=100)
    canonical_role_name: str = Field(min_length=1, max_length=200)
    responsibility_summary: str = Field(min_length=1, max_length=2000)
    minimum_required_count: int = Field(ge=0, le=100000)
    relevant_capabilities: list[str] = Field(default_factory=list, max_length=50)
    rough_effort_expectation: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=2000)

    @field_validator(
        "role_category", "canonical_role_name", "responsibility_summary",
        "rough_effort_expectation", "rationale",
    )
    @classmethod
    def reject_blank_requirement_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("relevant_capabilities")
    @classmethod
    def normalize_capabilities(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("capabilities must not be blank")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("capabilities must be unique")
        return normalized


class ActorRequirementProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    event_id: UUID
    stage_id: UUID
    work_id: UUID
    base_event_version: int = Field(ge=1)
    base_stage_version: int = Field(ge=1)
    base_work_version: int = Field(ge=1)
    proposed_requirements: list[ProposedActorRequirement]
    assumptions: list[str] = Field(default_factory=list)
    concise_rationale: str = Field(min_length=1, max_length=4000)
    approval_required: bool

    @field_validator("concise_rationale")
    @classmethod
    def reject_blank_actor_rationale(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ActorRequirementSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    stage_id: UUID
    work_id: UUID
    role_category: str
    canonical_role_name: str
    responsibility_summary: str
    minimum_required_count: int
    relevant_capabilities: list[str]
    rough_effort_expectation: str
    rationale: str
    version: int
    source_proposal_id: UUID
    created_at: datetime
    updated_at: datetime


class ActorRequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    stage_id: UUID
    work_id: UUID
    organizer_id: UUID
    base_event_version: int
    base_stage_version: int
    base_work_version: int
    status: PlanningRequestStatus
    idempotency_key: str
    correlation_id: UUID
    proposal_id: UUID | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class ActorRequirementDecisionResult(BaseModel):
    proposal_id: UUID
    status: ProposalStatus
    requirements: list[ActorRequirementSnapshot] = Field(default_factory=list)
    event_version: int | None = None
    stage_version: int | None = None
    work_version: int | None = None
    duplicate: bool = False


class WorkActorContext(BaseModel):
    """Allowlisted facts for one authoritative work item and its ancestors."""

    event_id: UUID
    event_name: str
    event_purpose: str
    event_type: str
    event_version: int
    stage_id: UUID
    stage_name: str
    stage_purpose: str
    stage_version: int
    work_id: UUID
    work_name: str
    work_purpose: str
    estimated_person_hours: float
    work_share: float
    work_start: datetime
    work_end: datetime
    work_version: int
