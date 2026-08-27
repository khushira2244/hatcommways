"""Deterministic proposal and payload validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .errors import ValidationError
from .models import EventSnapshot, ProposalCreate, StageSnapshot
from .stage_validation import StagePlanValidator
from .work_validation import WorkDecompositionValidator


class EventUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = Field(default=None, min_length=1, max_length=4000)
    event_type: str | None = Field(default=None, min_length=1, max_length=100)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    location_description: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("name", "purpose", "event_type", "timezone", "location_description")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def require_change(self) -> "EventUpdatePayload":
        if not self.model_fields_set:
            raise ValueError("at least one event change is required")
        return self


class ProposalValidator:
    EVENT_UPDATE = "EVENT_UPDATE"
    STAGE_PLAN = "STAGE_PLAN"
    WORK_DECOMPOSITION = "WORK_DECOMPOSITION"

    def validate_for_storage(
        self,
        command: ProposalCreate,
        event: EventSnapshot | None = None,
        stage: StageSnapshot | None = None,
    ) -> dict[str, Any]:
        if command.proposal_type == self.WORK_DECOMPOSITION:
            if command.target_type != "STAGE":
                raise ValidationError("WORK_DECOMPOSITION must target STAGE")
            if set(command.base_versions) != {"event", "stage"}:
                raise ValidationError(
                    "WORK_DECOMPOSITION requires event and stage base versions"
                )
            if event is None or stage is None:
                raise ValidationError(
                    "WORK_DECOMPOSITION validation requires current event and stage"
                )
            proposal = WorkDecompositionValidator().parse_and_validate(
                command.payload, event, stage
            )
            return proposal.model_dump(mode="json")
        if command.proposal_type == self.STAGE_PLAN:
            if command.target_type != "EVENT":
                raise ValidationError("STAGE_PLAN must target EVENT")
            if set(command.base_versions) != {"event"}:
                raise ValidationError("STAGE_PLAN requires exactly the event base version")
            if event is None:
                raise ValidationError("STAGE_PLAN validation requires the current event")
            proposal = StagePlanValidator().parse_and_validate(command.payload, event)
            return proposal.model_dump(mode="json")
        if command.proposal_type != self.EVENT_UPDATE:
            raise ValidationError(f"unsupported proposal type: {command.proposal_type}")
        if command.target_type != "EVENT":
            raise ValidationError("EVENT_UPDATE must target EVENT")
        if set(command.base_versions) != {"event"}:
            raise ValidationError("EVENT_UPDATE requires exactly the event base version")
        return self.validate_payload(command.payload)

    def validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return EventUpdatePayload.model_validate(payload).model_dump(
                mode="json", exclude_none=True
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error

    def validate_effective_time_range(
        self,
        current: dict[str, Any],
        changes: dict[str, Any],
    ) -> None:
        starts_at = changes.get("starts_at", current["starts_at"])
        ends_at = changes.get("ends_at", current["ends_at"])
        if isinstance(starts_at, str):
            starts_at = datetime.fromisoformat(starts_at)
        if isinstance(ends_at, str):
            ends_at = datetime.fromisoformat(ends_at)
        if ends_at <= starts_at:
            raise ValidationError("effective event end must be after start")
