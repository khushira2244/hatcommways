"""Argon2 credentials and revocable opaque PostgreSQL sessions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from psycopg.errors import UniqueViolation

from services.planning_foundation.database import Database

from .errors import DuplicateEmailError, InvalidCredentialsError, InvalidSessionError
from .models import (
    AccountSnapshot,
    AccountStatus,
    AuthenticatedSession,
    SessionResult,
    SignInRequest,
    SignUpRequest,
)


SESSION_LIFETIME = timedelta(hours=24)


class AuthService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.password_hasher = PasswordHasher()
        self._dummy_hash = self.password_hasher.hash("hatcommways-dummy-password")

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def sign_up(self, command: SignUpRequest) -> AccountSnapshot:
        account_id = uuid4()
        password_hash = self.password_hasher.hash(command.password.get_secret_value())
        try:
            with self.database.connect() as connection:
                row = connection.execute(
                    """
                    INSERT INTO accounts (
                        id, email, display_name, account_type, status, password_hash
                    ) VALUES (%s, %s, %s, %s, 'ACTIVE', %s)
                    RETURNING id,email,display_name,account_type,status,created_at,updated_at
                    """,
                    (
                        account_id, command.email, command.display_name,
                        command.account_type.value, password_hash,
                    ),
                ).fetchone()
        except UniqueViolation as error:
            raise DuplicateEmailError("an account with this email already exists") from error
        return AccountSnapshot.model_validate(row)

    def sign_in(self, command: SignInRequest) -> SessionResult:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE email = %s", (command.email,)
            ).fetchone()
        supplied_password = command.password.get_secret_value()
        candidate_hash = row["password_hash"] if row is not None else self._dummy_hash
        try:
            valid = self.password_hasher.verify(candidate_hash, supplied_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            valid = False
        if row is None or not valid or row["status"] != AccountStatus.ACTIVE:
            raise InvalidCredentialsError("invalid email or password")
        if self.password_hasher.check_needs_rehash(row["password_hash"]):
            replacement = self.password_hasher.hash(supplied_password)
            with self.database.connect() as connection:
                connection.execute(
                    "UPDATE accounts SET password_hash=%s,updated_at=now() WHERE id=%s",
                    (replacement, row["id"]),
                )
        return self._create_session(self._account_snapshot(row))

    def _create_session(self, account: AccountSnapshot) -> SessionResult:
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._token_hash(raw_token)
        expires_at = datetime.now(timezone.utc) + SESSION_LIFETIME
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_sessions (id,account_id,token_hash,expires_at)
                VALUES (%s,%s,%s,%s)
                """,
                (uuid4(), account.id, token_hash, expires_at),
            )
        return SessionResult(
            account=account, access_token=raw_token, expires_at=expires_at
        )

    @staticmethod
    def _account_snapshot(row) -> AccountSnapshot:
        return AccountSnapshot.model_validate(
            {
                key: row[key]
                for key in (
                    "id", "email", "display_name", "account_type", "status",
                    "created_at", "updated_at",
                )
            }
        )

    def authenticate(self, token: str) -> AuthenticatedSession:
        if not token:
            raise InvalidSessionError("authentication required")
        token_hash = self._token_hash(token)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT s.id AS session_id,s.expires_at,
                       a.id,a.email,a.display_name,a.account_type,a.status,
                       a.created_at,a.updated_at
                FROM auth_sessions s
                JOIN accounts a ON a.id=s.account_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL
                  AND s.expires_at > now() AND a.status='ACTIVE'
                """,
                (token_hash,),
            ).fetchone()
            if row is None:
                raise InvalidSessionError("session is invalid or expired")
            connection.execute(
                "UPDATE auth_sessions SET last_seen_at=now() WHERE id=%s",
                (row["session_id"],),
            )
        return AuthenticatedSession(
            session_id=row["session_id"],
            expires_at=row["expires_at"],
            account=AccountSnapshot.model_validate(
                {key: row[key] for key in (
                    "id", "email", "display_name", "account_type", "status",
                    "created_at", "updated_at",
                )}
            ),
        )

    def sign_out(self, token: str) -> None:
        token_hash = self._token_hash(token)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE auth_sessions SET revoked_at=now()
                WHERE token_hash=%s AND revoked_at IS NULL RETURNING id
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            raise InvalidSessionError("session is invalid or already signed out")
