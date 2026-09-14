"""Bounded sponsor submission and advisory contracts."""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OfferSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    resource_need_id: UUID | None = None
    support_type: str = Field(min_length=1, max_length=100)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    availability_start: datetime | None = None
    availability_end: datetime | None = None
    comment: str = Field(default="", max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if bool(self.availability_start) != bool(self.availability_end):
            raise ValueError("Provide both availability dates")
        if self.availability_start:
            if not self.availability_start.tzinfo or not self.availability_end.tzinfo:
                raise ValueError("Availability must include timezone")
            if self.availability_end <= self.availability_start:
                raise ValueError("Availability end must follow start")
        if self.quantity is not None and self.resource_need_id is None:
            raise ValueError("Select a resource need for a quantity contribution")
        return self


class OfferDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVED", "REJECTED"]
    expected_version: int = Field(ge=1)


class SponsorFit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    match_level: Literal["STRONG", "PARTIAL", "WEAK"]
    matches_need: bool
    timing_fit: bool
    remaining_gap_fit: bool
    summary: str = Field(min_length=1, max_length=600)
    issues: list[str] = Field(max_length=6)

    @model_validator(mode="after")
    def bounded_issues(self) -> Self:
        if any(not issue.strip() or len(issue) > 240 for issue in self.issues):
            raise ValueError("Fit issues must be specific and at most 240 characters")
        if self.match_level == "STRONG" and not all((self.matches_need, self.timing_fit, self.remaining_gap_fit)):
            raise ValueError("Strong fit requires all fit checks")
        return self
