from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SetupModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InviteStatus(StrEnum):
    DRAFT = "DRAFT"


class InitialInvite(SetupModel):
    display_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=1000)
    intended_role_text: str | None = Field(default=None, max_length=200)
    status: InviteStatus = InviteStatus.DRAFT

    @model_validator(mode="after")
    def require_identity_hint(self) -> Self:
        if not any((self.display_name, self.email, self.phone)):
            raise ValueError("invite requires display_name, email, or phone")
        return self


class SupportType(StrEnum):
    SPONSOR = "SPONSOR"
    SUPPORT_PARTNER = "SUPPORT_PARTNER"


def validate_external_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("external URL must use http or https")
    return value


class SponsorSupportEntry(SetupModel):
    name: str = Field(min_length=1, max_length=200)
    type: SupportType
    description: str | None = Field(default=None, max_length=2000)
    website_url: str | None = Field(default=None, max_length=2000)
    logo_url: str | None = Field(default=None, max_length=2000)
    visibility_enabled: bool = False

    _website = field_validator("website_url")(validate_external_url)
    _logo = field_validator("logo_url")(validate_external_url)


class ResourceNeedEntry(SetupModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=1000)


class ContributionLink(SetupModel):
    label: str = Field(min_length=1, max_length=200)
    provider: str | None = Field(default=None, max_length=100)
    external_url: str = Field(min_length=1, max_length=2000)
    purpose: str | None = Field(default=None, max_length=1000)
    visibility_enabled: bool = False

    _external = field_validator("external_url")(validate_external_url)


class ParticipationDimension(StrEnum):
    AREA = "AREA"
    ROLE = "ROLE"
    ORGANIZATION = "ORGANIZATION"
    PROFESSION = "PROFESSION"


class MapSettings(SetupModel):
    map_enabled: bool = False
    default_view: str | None = Field(default=None, max_length=100)
    participation_dimensions: list[ParticipationDimension] = Field(default_factory=list)

    @field_validator("participation_dimensions")
    @classmethod
    def unique_dimensions(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("participation_dimensions must be unique")
        return value


class EventVisibility(StrEnum):
    PUBLIC = "PUBLIC"
    UNLISTED = "UNLISTED"
    PRIVATE = "PRIVATE"


class PrivacySettings(SetupModel):
    event_visibility: EventVisibility = EventVisibility.PRIVATE
    show_participant_counts: bool = False
    show_actor_tree: bool = False
    show_sponsors: bool = False
    show_resources: bool = False
    show_payment_links: bool = False


class EventSetupSettings(SetupModel):
    initial_invites: list[InitialInvite] = Field(default_factory=list)
    sponsors_support: list[SponsorSupportEntry] = Field(default_factory=list)
    resources: list[ResourceNeedEntry] = Field(default_factory=list)
    contribution_links: list[ContributionLink] = Field(default_factory=list)
    map_settings: MapSettings = Field(default_factory=MapSettings)
    privacy_settings: PrivacySettings = Field(default_factory=PrivacySettings)


class EventSetupUpdateRequest(EventSetupSettings):
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=200)


class EventSetupSnapshot(EventSetupSettings):
    event_id: UUID
    version: int = Field(ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None
