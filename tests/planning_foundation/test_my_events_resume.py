from uuid import UUID

from fastapi.testclient import TestClient

from services.api import create_app
from tests.planning_foundation.conftest import make_event_command


PASSWORD = "correct horse battery staple"


def account(client, email):
    created = client.post("/auth/signup", json={"email": email, "display_name": email.split("@")[0], "account_type": "INDIVIDUAL", "password": PASSWORD}).json()
    token = client.post("/auth/signin", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return created, {"Authorization": f"Bearer {token}"}


def test_creation_draft_my_events_resume_and_conversion(database):
    client = TestClient(create_app(database))
    owner, headers = account(client, "resume-owner@example.com")
    _other, other_headers = account(client, "resume-other@example.com")
    payload = {"name": "Gachibowli Cleanup Draft", "shortPurpose": "Cleanup", "venue": "Gachibowli Lake", "participants": ["Volunteers"]}

    saved = client.put("/me/event-drafts", headers=headers, json={"payload": payload, "current_step": 2})
    assert saved.status_code == 200
    draft = saved.json()
    listing = client.get("/me/events", headers=headers).json()
    assert listing["organizing"][0]["current_phase"] == "CREATION_DRAFT"
    assert listing["organizing"][0]["current_step"] == 2
    assert listing["organizing"][0]["resume_target"] == f"create-event.html?draft={draft['id']}"
    assert client.get(f"/me/event-drafts/{draft['id']}", headers=headers).json()["payload"] == payload
    assert client.get(f"/me/event-drafts/{draft['id']}", headers=other_headers).status_code == 404

    command = make_event_command(UUID(owner["id"]))
    body = command.model_dump(mode="json", exclude={"organizer_id"}) | {"category": "Environment", "idempotency_key": "resume-real-event", "draft_id": draft["id"]}
    event = client.post("/events", headers=headers, json=body)
    assert event.status_code == 201
    event_id = event.json()["id"]
    listing = client.get("/me/events", headers=headers).json()
    assert len(listing["organizing"]) == 1
    assert listing["organizing"][0]["event_id"] == event_id
    assert listing["organizing"][0]["category"] == "Environment"
    assert listing["organizing"][0]["current_phase"] == "GOVERNANCE"
    assert listing["organizing"][0]["resume_target"] == f"governance.html?event={event_id}"
    assert listing["participating"] == []

    resumed = client.put(f"/events/{event_id}/resume-state", headers=headers, json={"current_phase": "STAGE_PLANNING"})
    assert resumed.status_code == 200
    assert client.put(f"/events/{event_id}/resume-state", headers=other_headers, json={"current_phase": "STAGE_PLANNING"}).status_code == 403
    after = client.get("/me/events", headers=headers).json()["organizing"][0]
    assert after["resume_target"] == f"planning.html?event={event_id}"
    with database.connect() as connection:
        assert connection.execute("SELECT category FROM events WHERE id=%s", (event_id,)).fetchone()["category"] == "Environment"
        assert connection.execute("SELECT count(*) AS count FROM event_creation_drafts", ()).fetchone()["count"] == 0
        assert connection.execute("SELECT count(*) AS count FROM event_planning_requests", ()).fetchone()["count"] == 0
        assert connection.execute("SELECT count(*) AS count FROM work_design_requests", ()).fetchone()["count"] == 0
        assert connection.execute("SELECT count(*) AS count FROM actor_requirement_requests", ()).fetchone()["count"] == 0
