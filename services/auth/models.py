from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AccountType(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    ORGANIZATION = "ORGANIZATION"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("invalid email address")
    return normalized


class SignUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    display_name: str = Field(min_length=1, max_length=200)
    account_type: AccountType
    password: SecretStr = Field(min_length=10, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str
    display_name: str
    account_type: AccountType
    status: AccountStatus
    created_at: datetime
    updated_at: datetime


class SessionResult(BaseModel):
    account: AccountSnapshot
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AuthenticatedSession(BaseModel):
    session_id: UUID
    account: AccountSnapshot
    expires_at: datetime

