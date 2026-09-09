"""Contracts for immutable human reports and independent blocker lifecycle axes."""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HandlingState(str, Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    WORKING = "WORKING"
    STALLED = "STALLED"


class ConditionState(str, Enum):
    OPEN = "OPEN"
    CLEARED = "CLEARED"


class SourceType(str, Enum):
    ACTOR = "ACTOR"
    ORGANIZER = "ORGANIZER"


class InterpretationStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    RUNNING = "RUNNING"
    INTERPRETED = "INTERPRETED"
    FAILED = "FAILED"


class HumanUpdateInterpretationType(str, Enum):
    AVAILABILITY_CHANGE = "AVAILABILITY_CHANGE"
    ACCESS_PROBLEM = "ACCESS_PROBLEM"
    RESOURCE_PROBLEM = "RESOURCE_PROBLEM"
    EQUIPMENT_PROBLEM = "EQUIPMENT_PROBLEM"
    SCHEDULE_DELAY = "SCHEDULE_DELAY"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    COMPLETION_UPDATE = "COMPLETION_UPDATE"
    GENERAL_UPDATE = "GENERAL_UPDATE"
    UNKNOWN = "UNKNOWN"


class HumanUpdateInterpretation(BaseModel):
    """Provider-neutral structured output returned by the interpretation agent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    update_id: UUID
    event_id: UUID
    interpretation_type: HumanUpdateInterpretationType
    concise_summary: str = Field(min_length=1, max_length=500)
    reported_condition: str = Field(min_length=1, max_length=1000)
    temporal_signal: str | None = Field(default=None, min_length=1, max_length=500)
    location_signal: str | None = Field(default=None, min_length=1, max_length=500)
    referenced_stage_id: UUID | None = None
    referenced_work_id: UUID | None = None
    possible_blocker: bool = Field(
        description=(
            "True only when the report explicitly supplies a concrete condition that may "
            "prevent or disrupt activity; false for completion or unexplained ambiguity."
        )
    )
    blocker_reason: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="The concrete reported condition supporting possible_blocker=true.",
    )
    confidence: float = Field(ge=0, le=1)
    requires_clarification: bool = Field(
        description="True when missing meaning or facts require one follow-up question."
    )
    clarification_question: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def conditional_explanations(self):
        if self.possible_blocker != (self.blocker_reason is not None):
            raise ValueError("blocker_reason is required exactly when possible_blocker is true")
        if self.requires_clarification != (self.clarification_question is not None):
            raise ValueError(
                "clarification_question is required exactly when requires_clarification is true"
            )
        return self


class HumanUpdateInterpretationSnapshot(HumanUpdateInterpretation):
    id: UUID
    provider_name: str
    model_id: str
    agent_name: str
    agent_version: str
    stop_reason: str
    usage: dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class HumanUpdateInterpretationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    update_id: UUID
    event_id: UUID
    original_text: str
    reporter_relationship: SourceType
    reporter_display_name: str
    event_name: str
    event_starts_at: datetime
    event_ends_at: datetime
    event_timezone: str
    event_location: str
    stage: dict[str, Any] | None = None
    work: dict[str, Any] | None = None
    accepted_participation: dict[str, Any] | None = None


class InterpretHumanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retry: bool = False


class ReportModel(BaseModel):
    # Unlike participation form models, reports must never strip whitespace.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class HumanUpdateCreate(ReportModel):
    text: str = Field(min_length=1, max_length=10000)
    stage_id: UUID | None = None
    work_id: UUID | None = None
    actor_requirement_id: UUID | None = None
    participation_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("text", "idempotency_key")
    @classmethod
    def not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class HumanUpdateSnapshot(ReportModel):
    id: UUID
    event_id: UUID
    reporter_account_id: UUID
    source_type: SourceType
    stage_id: UUID | None
    work_id: UUID | None
    actor_requirement_id: UUID | None
    participation_id: UUID | None
    original_text: str
    interpretation_status: InterpretationStatus
    interpreted_at: datetime | None
    interpretation_failed_at: datetime | None = None
    interpretation_failure_code: str | None = None
    interpretation_attempt_count: int = 0
    created_at: datetime
    version: int
    interpretation: HumanUpdateInterpretationSnapshot | None = None


class BlockerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    human_update_id: UUID
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    stage_id: UUID | None = None
    work_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class BlockerPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    handling_state: HandlingState | None = None
    condition_state: ConditionState | None = None

    @model_validator(mode="after")
    def require_state_change(self):
        states = self.model_fields_set & {"handling_state", "condition_state"}
        if not states or any(getattr(self, name) is None for name in states):
            raise ValueError("provide at least one non-null lifecycle state")
        return self


class BlockerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    event_id: UUID
    source_human_update_id: UUID
    reported_by_account_id: UUID
    created_by_account_id: UUID
    stage_id: UUID | None
    work_id: UUID | None
    title: str
    summary: str
    category: str | None
    handling_state: HandlingState
    condition_state: ConditionState
    created_at: datetime
    updated_at: datetime
    cleared_at: datetime | None
    version: int
    source_human_update: HumanUpdateSnapshot
    stage_name: str | None
    work_name: str | None
    reported_by_display_name: str
