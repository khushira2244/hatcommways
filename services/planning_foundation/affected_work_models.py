"""Typed deterministic output for authoritative affected-work traversal."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AffectedWorkResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: UUID
    blocker_id: UUID
    blocker_assessment_id: UUID
    directly_affected_work_ids: list[UUID] = Field(default_factory=list)
    downstream_affected_work_ids: list[UUID] = Field(default_factory=list)
    affected_stage_ids: list[UUID] = Field(default_factory=list)
    deterministic_reason: str = Field(min_length=1, max_length=500)
    graph_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessed_event_version: int = Field(ge=1)
    resolved_event_version: int = Field(ge=1)
    source_versions: dict[str, Any]
    created_at: datetime
