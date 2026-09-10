"""Typed contracts for bounded, advisory coordination proposals."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CoordinationActionType(StrEnum):
    NOTIFY_ACTOR = "NOTIFY_ACTOR"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    USE_EXISTING_RESOURCE = "USE_EXISTING_RESOURCE"
    MOVE_EXISTING_RESOURCE = "MOVE_EXISTING_RESOURCE"
    RESCHEDULE_MEETING = "RESCHEDULE_MEETING"
    REASSIGNMENT_SUGGESTION = "REASSIGNMENT_SUGGESTION"
    TEMPORARY_WORKAROUND = "TEMPORARY_WORKAROUND"
    WAIT_FOR_CONDITION = "WAIT_FOR_CONDITION"
    OTHER = "OTHER"


class CoordinationAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action_type: CoordinationActionType
    target_actor_id: UUID | None = None
    target_work_id: UUID | None = None
    target_meeting_id: UUID | None = None
    resource_reference: str | None = Field(default=None, min_length=1, max_length=200)
    concise_instruction: str = Field(min_length=1, max_length=500)
    expected_effect: str = Field(min_length=1, max_length=500)
    requires_human_approval: bool
    reversible: bool


class CoordinationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    event_id: UUID
    blocker_id: UUID
    affected_work_resolution_id: UUID
    coordination_possible: bool
    requires_replanning: bool
    actions: list[CoordinationAction] = Field(default_factory=list, max_length=12)
    rationale: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def coherent_outcome(self):
        if self.coordination_possible and self.requires_replanning:
            raise ValueError("coordination_possible and requires_replanning cannot both be true")
        if self.coordination_possible and not self.actions:
            raise ValueError("a possible coordination outcome requires at least one action")
        return self


class CoordinationProposalSnapshot(CoordinationDecision):
    id: UUID
    request_id: UUID
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_versions: dict[str, Any]
    provider_name: str
    model_id: str
    agent_name: str
    agent_version: str
    stop_reason: str
    usage: dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class CoordinateBlockerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retry: bool = False


class CoordinationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: dict[str, Any]
    blocker: dict[str, Any]
    blocker_assessment: dict[str, Any]
    affected_work_resolution: dict[str, Any]
    affected_stages: list[dict[str, Any]] = Field(default_factory=list)
    affected_work: list[dict[str, Any]] = Field(default_factory=list)
    relevant_actors: list[dict[str, Any]] = Field(default_factory=list)
    relevant_meetings: list[dict[str, Any]] = Field(default_factory=list)
    existing_resources: list[dict[str, Any]] = Field(default_factory=list)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_versions: dict[str, Any]
