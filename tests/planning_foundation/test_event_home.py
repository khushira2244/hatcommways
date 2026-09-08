from uuid import UUID

from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.governance_models import GovernanceProposal
from services.planning_foundation.governance_service import GovernanceService
from services.planning_foundation.models import ActorRequirementProposal, ProposalDecision, ProposalDecisionCommand
from tests.planning_foundation.test_actor_requirement import actor_payload
from tests.planning_foundation.work_helpers import create_approved_work


PASSWORD = "correct horse battery staple"


def signed_in(client, email):
    account = client.post("/auth/signup", json={"email": email, "display_name": "Event Owner", "account_type": "INDIVIDUAL", "password": PASSWORD}).json()
    token = client.post("/auth/signin", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return account, {"Authorization": f"Bearer {token}"}


def test_final_event_home_is_authoritative_and_read_only(database, service):
    client = TestClient(create_app(database))
    account, headers = signed_in(client, "event-home@example.com")
    organizer_id = UUID(account["id"])
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    with database.connect() as connection:
        connection.execute("UPDATE events SET category='Environment' WHERE id=%s", (event.id,))
        connection.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')", (event.id, organizer_id))

    actor_service = ActorRequirementService(database)
    request = actor_service.request_actor_requirements(event_id=event.id, stage_id=stage.id, work_id=work[0].id, organizer_id=organizer_id, expected_event_version=event.version, expected_stage_version=stage.version, expected_work_version=work[0].version, idempotency_key="home-actor-request")
    actor_service.begin_request(request.id)
    completed = actor_service.complete_request(request.id, ActorRequirementProposal.model_validate(actor_payload(event, stage, work[0])))
    actor_service.decide_actor_requirements(ProposalDecisionCommand(proposal_id=completed.proposal_id, organizer_id=organizer_id, decision=ProposalDecision.APPROVE, decision_idempotency_key="home-actor-approve"))

    current_event = service.get_event(event.id)
    GovernanceService(database).store_assessment(GovernanceProposal.model_validate({"event_id":str(event.id),"base_event_version":current_event.version,"governance_required":True,"completeness":"INCOMPLETE","internal_risk":"MEDIUM","review_mode":"HATCOMMWAYS","organizer_visible_status":"UNDER_REVIEW","reasoning_summary":"Organizer-visible review is underway.","items":[]}), organizer_id)
    setup = {"expected_version":0,"idempotency_key":"home-setup","initial_invites":[],"sponsors_support":[{"name":"Lake Partner","type":"SUPPORT_PARTNER","description":"Collection support","website_url":"https://example.org","visibility_enabled":True}],"resources":[{"name":"Safety gloves","category":"Equipment","quantity":50,"unit":"pairs","note":"Reusable"}],"contribution_links":[{"label":"Community fund","provider":"External provider","external_url":"https://example.org/support","purpose":"Cleanup materials","visibility_enabled":True}],"map_settings":{"map_enabled":True,"default_view":"CITY","participation_dimensions":["AREA","ROLE"]},"privacy_settings":{"event_visibility":"PUBLIC","show_participant_counts":False,"show_actor_tree":True,"show_sponsors":True,"show_resources":True,"show_payment_links":True}}
    assert client.put(f"/events/{event.id}/setup", headers=headers, json=setup).status_code == 200
    assert client.put(f"/events/{event.id}/resume-state", headers=headers, json={"current_phase":"READY"}).status_code == 200

    with database.connect() as connection:
        before = {table: connection.execute(f"SELECT count(*) AS count FROM {table} WHERE event_id=%s", (event.id,)).fetchone()["count"] for table in ("event_planning_requests", "work_design_requests", "actor_requirement_requests")}
    home = client.get(f"/events/{event.id}/home", headers=headers)
    assert home.status_code == 200
    data = home.json()
    assert data["event"]["category"] == "Environment"
    assert data["current_phase"] == "READY"
    assert data["relationship"] == "ORGANIZER"
    assert data["governance"]["assessment"]["organizer_visible_status"] == "UNDER_REVIEW"
    assert data["stages"] and data["actor_requirements"]
    assert data["setup"]["resources"][0]["quantity"] == 50
    assert data["setup"]["contribution_links"][0]["external_url"] == "https://example.org/support"
    listing = client.get("/me/events", headers=headers).json()["organizing"][0]
    assert listing["resume_target"] == f"event.html?event={event.id}"
    with database.connect() as connection:
        after = {table: connection.execute(f"SELECT count(*) AS count FROM {table} WHERE event_id=%s", (event.id,)).fetchone()["count"] for table in before}
    assert after == before

    _, other_headers = signed_in(client, "event-home-other@example.com")
    visitor_home = client.get(f"/events/{event.id}/home", headers=other_headers)
    assert visitor_home.status_code == 200
    assert visitor_home.json()["relationship"] == "VISITOR"
