from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.models import StagePlanProposal
from services.planning_foundation.stage_planning_service import StagePlanningService
from tests.planning_foundation.conftest import make_event_command
from tests.planning_foundation.work_helpers import create_approved_work


def test_workspace_reads_pending_then_authoritative_confirmed_stages(database):
    client = TestClient(create_app(database))
    account = client.post("/auth/signup", json={
        "email":"workspace@example.com", "display_name":"Workspace Owner",
        "account_type":"INDIVIDUAL", "password":"correct horse battery staple",
    }).json()
    token = client.post("/auth/signin", json={
        "email":"workspace@example.com", "password":"correct horse battery staple",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    command = make_event_command(UUID(account["id"]))
    body = command.model_dump(mode="json", exclude={"organizer_id"}) | {"idempotency_key":"workspace-event"}
    event = client.post("/events", headers=headers, json=body).json()
    service = StagePlanningService(database)

    empty = client.get(f"/events/{event['id']}/stage-plan-workspace", headers=headers)
    refreshed_empty = client.get(f"/events/{event['id']}/stage-plan-workspace", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["mode"] == "EMPTY"
    assert empty.json()["planning_request"] is None
    assert empty.json()["proposal"] is None
    assert refreshed_empty.json()["mode"] == "EMPTY"
    with database.connect() as connection:
        assert connection.execute(
            "SELECT count(*) AS count FROM event_planning_requests WHERE event_id=%s",
            (UUID(event["id"]),),
        ).fetchone()["count"] == 0

    request = service.request_event_planning(
        event_id=UUID(event["id"]), organizer_id=UUID(account["id"]),
        expected_event_version=1, idempotency_key="workspace-request",
    )
    running = client.get(f"/events/{event['id']}/stage-plan-workspace", headers=headers)
    assert running.status_code == 200
    assert running.json()["mode"] == "RUNNING"
    assert running.json()["planning_request"]["status"] == "REQUESTED"
    assert running.json()["proposal"] is None
    service.begin_request(request.id)
    proposal = StagePlanProposal.model_validate({
        "proposal_id":"50000000-0000-0000-0000-000000000001",
        "event_id":event["id"], "base_event_version":1,
        "proposed_stages":[{
            "temporary_stage_ref":"stage-1", "canonical_name":"Preparation",
            "purpose":"Prepare safely", "proposed_order":1,
            "proposed_start":command.starts_at,
            "proposed_end":command.starts_at + timedelta(hours=2), "dependencies":[],
        }], "assumptions":[], "concise_rationale":"Prepare before execution.",
        "approval_required":True,
    })
    completed = service.complete_request(request.id, proposal)

    pending = client.get(f"/events/{event['id']}/stage-plan-workspace", headers=headers)
    assert pending.status_code == 200
    assert pending.json()["mode"] == "PROPOSAL"
    assert pending.json()["proposal"]["status"] == "PENDING"
    assert pending.json()["stages"] == []

    edited = proposal.model_dump(mode="json")
    edited["proposed_stages"][0]["canonical_name"] = "Organizer Preparation"
    approved = client.post(
        f"/stage-proposals/{completed.proposal_id}/decision", headers=headers,
        json={"decision":"APPROVE", "decision_idempotency_key":"workspace-approve", "edited_payload":edited},
    )
    assert approved.status_code == 200
    confirmed = client.get(f"/events/{event['id']}/stage-plan-workspace", headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["mode"] == "CONFIRMED"
    assert confirmed.json()["stages"][0]["canonical_name"] == "Organizer Preparation"
    selected_stage = confirmed.json()["stages"][0]

    inside = client.get(
        f"/events/{event['id']}/stages/{selected_stage['id']}/work-design-workspace",
        headers=headers,
    )
    assert inside.status_code == 200
    assert inside.json()["mode"] == "EMPTY"
    assert inside.json()["selected_stage"]["id"] == selected_stage["id"]
    assert inside.json()["proposal"] is None
    assert inside.json()["work"] == []
    with database.connect() as connection:
        assert connection.execute(
            "SELECT count(*) AS count FROM work_design_requests WHERE stage_id=%s",
            (UUID(selected_stage["id"]),),
        ).fetchone()["count"] == 0

    other = client.post("/auth/signup", json={
        "email":"workspace-other@example.com", "display_name":"Other",
        "account_type":"INDIVIDUAL", "password":"correct horse battery staple",
    }).json()
    other_token = client.post("/auth/signin", json={
        "email":other["email"], "password":"correct horse battery staple",
    }).json()["access_token"]
    denied = client.get(
        f"/events/{event['id']}/stage-plan-workspace",
        headers={"Authorization":f"Bearer {other_token}"},
    )
    assert denied.status_code == 403
    denied_inside = client.get(
        f"/events/{event['id']}/stages/{selected_stage['id']}/work-design-workspace",
        headers={"Authorization":f"Bearer {other_token}"},
    )
    assert denied_inside.status_code == 403


def test_actor_tree_workspace_returns_event_stages_and_authoritative_work(database):
    client = TestClient(create_app(database))
    account = client.post("/auth/signup", json={
        "email":"actor-tree@example.com", "display_name":"Actor Tree Owner",
        "account_type":"INDIVIDUAL", "password":"correct horse battery staple",
    }).json()
    token = client.post("/auth/signin", json={
        "email":"actor-tree@example.com", "password":"correct horse battery staple",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    service = StagePlanningService(database)
    event, stage, work, _other_stage = create_approved_work(
        database, service.base, UUID(account["id"])
    )
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO event_memberships (event_id,account_id,role,status)
            VALUES (%s,%s,'ORGANIZER','ACTIVE')
            """,
            (event.id, UUID(account["id"])),
        )

    response = client.get(
        f"/events/{event.id}/stages/{stage.id}/actor-tree-workspace",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event"]["id"] == str(event.id)
    assert payload["selected_stage"]["id"] == str(stage.id)
    assert len(payload["stages"]) == 2
    assert [item["work"]["id"] for item in payload["work_items"]] == [
        str(item.id) for item in work
    ]
    assert all(item["proposal"] is None for item in payload["work_items"])
    assert all(item["requirements"] == [] for item in payload["work_items"])
