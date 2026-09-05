from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.models import ActorRequirementProposal, ProposalDecision, ProposalDecisionCommand
from tests.planning_foundation.test_actor_requirement import actor_payload
from tests.planning_foundation.work_helpers import create_approved_work


def signup(client, email):
    account = client.post("/auth/signup", json={
        "email": email, "display_name": "Setup Owner",
        "account_type": "INDIVIDUAL", "password": "correct horse battery staple",
    }).json()
    token = client.post("/auth/signin", json={
        "email": email, "password": "correct horse battery staple",
    }).json()["access_token"]
    return account, {"Authorization": f"Bearer {token}"}


def test_event_setup_defaults_save_edit_authorization_and_boundaries(database, service):
    client = TestClient(create_app(database))
    account, headers = signup(client, "setup-owner@example.com")
    event, stage, work, _ = create_approved_work(database, service, UUID(account["id"]))
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO event_memberships (event_id,account_id,role,status) VALUES (%s,%s,'ORGANIZER','ACTIVE')",
            (event.id, UUID(account["id"])),
        )
    actor_service = ActorRequirementService(database)
    request = actor_service.request_actor_requirements(
        event_id=event.id, stage_id=stage.id, work_id=work[0].id,
        organizer_id=UUID(account["id"]), expected_event_version=event.version,
        expected_stage_version=stage.version, expected_work_version=work[0].version,
        idempotency_key="setup-proof-actor-request",
    )
    actor_service.begin_request(request.id)
    proposal = ActorRequirementProposal.model_validate(actor_payload(event, stage, work[0]))
    completed = actor_service.complete_request(request.id, proposal)
    actor_service.decide_actor_requirements(ProposalDecisionCommand(
        proposal_id=completed.proposal_id, organizer_id=UUID(account["id"]),
        decision=ProposalDecision.APPROVE,
        decision_idempotency_key="setup-proof-actor-approve",
    ))

    baseline = {}
    with database.connect() as connection:
        for table in ("stages", "work_items", "actor_requirements", "proposals", "event_memberships"):
            baseline[table] = connection.execute(
                f"SELECT count(*) AS count FROM {table} WHERE " +
                ("event_id=%s" if table != "proposals" else "target_id=%s OR target_id IN (SELECT id FROM stages WHERE event_id=%s) OR target_id IN (SELECT id FROM work_items WHERE event_id=%s)"),
                ((event.id,) if table != "proposals" else (event.id, event.id, event.id)),
            ).fetchone()["count"]

    empty = client.get(f"/events/{event.id}/setup", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["version"] == 0
    assert empty.json()["initial_invites"] == []
    assert empty.json()["privacy_settings"]["event_visibility"] == "PRIVATE"

    payload = {
        "expected_version": 0,
        "idempotency_key": "setup-save-1",
        "initial_invites": [{"display_name":"Asha", "email":"asha@example.com", "intended_role_text":"Coordinator"}],
        "sponsors_support": [{"name":"City Partner", "type":"SUPPORT_PARTNER", "description":"Venue support", "website_url":"https://example.org", "visibility_enabled":True}],
        "resources": [{"name":"Safety gloves", "category":"Equipment", "quantity":40, "unit":"pairs", "note":"Reusable preferred"}],
        "contribution_links": [{"label":"External support page", "provider":"Community Fund", "external_url":"https://example.org/support", "purpose":"Materials", "visibility_enabled":True}],
        "map_settings": {"map_enabled":True, "default_view":"CITY", "participation_dimensions":["AREA","ROLE","ORGANIZATION","PROFESSION"]},
        "privacy_settings": {"event_visibility":"PUBLIC", "show_participant_counts":True, "show_actor_tree":True, "show_sponsors":True, "show_resources":True, "show_payment_links":True},
    }
    saved = client.put(f"/events/{event.id}/setup", headers=headers, json=payload)
    assert saved.status_code == 200
    assert saved.json()["version"] == 1
    assert client.get(f"/events/{event.id}/setup", headers=headers).json() == saved.json()

    edited_payload = saved.json()
    for key in ("event_id", "created_at", "updated_at"):
        edited_payload.pop(key)
    edited_payload["expected_version"] = edited_payload.pop("version")
    edited_payload["idempotency_key"] = "setup-save-2"
    edited_payload["contribution_links"][0]["external_url"] = "https://example.org/new-support"
    edited_payload["privacy_settings"]["show_payment_links"] = False
    edited = client.put(f"/events/{event.id}/setup", headers=headers, json=edited_payload)
    assert edited.status_code == 200
    assert edited.json()["version"] == 2
    assert edited.json()["contribution_links"][0]["external_url"] == "https://example.org/new-support"
    assert edited.json()["privacy_settings"]["show_payment_links"] is False

    other, other_headers = signup(client, "setup-other@example.com")
    denied = client.put(f"/events/{event.id}/setup", headers=other_headers, json=edited_payload | {"idempotency_key":"denied"})
    assert denied.status_code == 403

    with database.connect() as connection:
        row = connection.execute("SELECT * FROM event_setups WHERE event_id=%s", (event.id,)).fetchone()
        assert row["version"] == 2
        assert row["contribution_links"][0]["external_url"] == "https://example.org/new-support"
        assert row["show_payment_links"] is False
        assert connection.execute("SELECT count(*) AS count FROM event_setup_updates WHERE event_id=%s", (event.id,)).fetchone()["count"] == 2
        assert connection.execute("SELECT count(*) AS count FROM domain_outbox WHERE aggregate_type='EVENT_SETUP' AND aggregate_id=%s", (event.id,)).fetchone()["count"] == 2
        for table in ("stages", "work_items", "actor_requirements", "event_memberships"):
            assert connection.execute(f"SELECT count(*) AS count FROM {table} WHERE event_id=%s", (event.id,)).fetchone()["count"] == baseline[table]
