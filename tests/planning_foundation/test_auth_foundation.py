from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.models import StagePlanProposal
from services.planning_foundation.stage_planning_service import StagePlanningService
from tests.planning_foundation.conftest import make_event_command


PASSWORD = "correct horse battery staple"


@pytest.fixture
def client(database):
    return TestClient(create_app(database))


def signup(client, *, email, account_type="INDIVIDUAL", display_name="Test Account"):
    return client.post(
        "/auth/signup",
        json={
            "email": email,
            "display_name": display_name,
            "account_type": account_type,
            "password": PASSWORD,
        },
    )


def signin(client, *, email, password=PASSWORD):
    return client.post("/auth/signin", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("account_type", ["INDIVIDUAL", "ORGANIZATION"])
def test_account_can_register_sign_in_and_read_current_session(
    client, database, account_type
):
    email = f"  {account_type.lower()}@Example.COM  "
    registered = signup(
        client,
        email=email,
        account_type=account_type,
        display_name=f"{account_type.title()} Account",
    )
    assert registered.status_code == 201
    assert registered.json()["email"] == f"{account_type.lower()}@example.com"
    assert registered.json()["account_type"] == account_type
    assert "password" not in registered.json()

    signed_in = signin(client, email=email)
    assert signed_in.status_code == 200
    token = signed_in.json()["access_token"]
    current = client.get("/auth/me", headers=bearer(token))
    assert current.status_code == 200
    assert current.json()["id"] == registered.json()["id"]
    assert "password_hash" not in current.json()

    with database.connect() as connection:
        account = connection.execute(
            "SELECT email,password_hash FROM accounts WHERE id=%s",
            (UUID(registered.json()["id"]),),
        ).fetchone()
        session = connection.execute(
            "SELECT token_hash FROM auth_sessions WHERE account_id=%s",
            (UUID(registered.json()["id"]),),
        ).fetchone()
    assert account["email"] == f"{account_type.lower()}@example.com"
    assert account["password_hash"].startswith("$argon2id$")
    assert PASSWORD not in account["password_hash"]
    assert session["token_hash"] != token


def test_duplicate_normalized_email_and_invalid_credentials_are_rejected(client):
    assert signup(client, email="owner@example.com").status_code == 201
    duplicate = signup(client, email=" OWNER@EXAMPLE.COM ")
    assert duplicate.status_code == 409
    assert signin(client, email="owner@example.com", password="incorrect").status_code == 401
    assert signin(client, email="missing@example.com", password="incorrect").status_code == 401


def test_sign_out_revokes_session(client):
    signup(client, email="signout@example.com")
    token = signin(client, email="signout@example.com").json()["access_token"]
    assert client.get("/auth/me", headers=bearer(token)).status_code == 200
    assert client.post("/auth/signout", headers=bearer(token)).status_code == 204
    assert client.get("/auth/me", headers=bearer(token)).status_code == 401


def test_unauthenticated_planning_action_is_rejected(client):
    response = client.post(
        "/events/00000000-0000-0000-0000-000000000001/planning-requests",
        json={"expected_event_version": 1, "idempotency_key": "unauthenticated"},
    )
    assert response.status_code == 401


def test_authenticated_organizer_membership_controls_level1_approval(
    client, database
):
    organizer = signup(client, email="organizer@example.com").json()
    other = signup(client, email="other@example.com").json()
    organizer_token = signin(client, email="organizer@example.com").json()["access_token"]
    other_token = signin(client, email="other@example.com").json()["access_token"]

    event_values = make_event_command(UUID(organizer["id"])).model_dump(mode="json")
    event_values.pop("organizer_id")
    created = client.post(
        "/events",
        headers=bearer(organizer_token),
        json={**event_values, "idempotency_key": "authenticated-event"},
    )
    assert created.status_code == 201
    event = created.json()
    event_id = UUID(event["id"])
    with database.connect() as connection:
        membership = connection.execute(
            "SELECT role,status FROM event_memberships WHERE event_id=%s AND account_id=%s",
            (event_id, UUID(organizer["id"])),
        ).fetchone()
    assert membership == {"role": "ORGANIZER", "status": "ACTIVE"}

    denied_request = client.post(
        f"/events/{event_id}/planning-requests",
        headers=bearer(other_token),
        json={"expected_event_version": 1, "idempotency_key": "other-request"},
    )
    assert denied_request.status_code == 403

    requested = client.post(
        f"/events/{event_id}/planning-requests",
        headers=bearer(organizer_token),
        json={"expected_event_version": 1, "idempotency_key": "organizer-request"},
    )
    assert requested.status_code == 201
    request = requested.json()

    stage_service = StagePlanningService(database)
    stage_service.begin_request(UUID(request["id"]))
    starts_at = make_event_command(UUID(organizer["id"])).starts_at
    ends_at = make_event_command(UUID(organizer["id"])).ends_at
    proposal = StagePlanProposal.model_validate(
        {
            "proposal_id": "10000000-0000-0000-0000-000000000001",
            "event_id": str(event_id),
            "base_event_version": 1,
            "proposed_stages": [
                {
                    "temporary_stage_ref": "stage-1",
                    "canonical_name": "Preparation",
                    "purpose": "Prepare the event",
                    "proposed_order": 1,
                    "proposed_start": starts_at.isoformat(),
                    "proposed_end": ends_at.isoformat(),
                    "dependencies": [],
                }
            ],
            "assumptions": [],
            "concise_rationale": "A single stage covers this test event.",
            "approval_required": True,
        }
    )
    completed = stage_service.complete_request(UUID(request["id"]), proposal)
    decision_body = {
        "decision": "APPROVE",
        "decision_idempotency_key": "authenticated-stage-approval",
    }
    denied_approval = client.post(
        f"/stage-proposals/{completed.proposal_id}/decision",
        headers=bearer(other_token),
        json=decision_body,
    )
    assert denied_approval.status_code == 403

    approved = client.post(
        f"/stage-proposals/{completed.proposal_id}/decision",
        headers=bearer(organizer_token),
        json=decision_body,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert len(approved.json()["stages"]) == 1

