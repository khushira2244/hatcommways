from __future__ import annotations

import os
import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from services.api import create_app
from services.agent_runtime.event_planning import (
    MODEL_ID,
    REGION,
)
from services.planning_foundation.models import PlanningRequestStatus, ProposalStatus
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.conftest import make_event_command


@pytest.mark.real_bedrock
def test_real_bedrock_produces_valid_pending_stage_plan(database, service):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    client = TestClient(create_app(database, execute_planning_requests=True))
    account = client.post(
        "/auth/signup",
        json={
            "email": "real-context-plan@example.com",
            "display_name": "Real Context Planner",
            "account_type": "ORGANIZATION",
            "password": "correct horse battery staple",
        },
    ).json()
    token = client.post(
        "/auth/signin",
        json={
            "email": "real-context-plan@example.com",
            "password": "correct horse battery staple",
        },
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    event_body = make_event_command(UUID(account["id"])).model_dump(mode="json")
    event_body.pop("organizer_id")
    event_body["planning_context"] = {
        "detailed_purpose": "Restore the lakefront and teach responsible waste separation.",
        "expected_scale": 75,
        "intended_participants": ["Community Members", "Volunteers", "Organizations"],
        "known_resources": "Gloves and collection bags may be available.",
        "known_requirements": "Municipal permission and a safety briefing are required.",
        "constraints": "Avoid the nesting area and finish before dusk.",
        "desired_outcomes": "Remove litter and document a reusable cleanup practice.",
        "organizer_notes": "Use concise operational names.",
        "theme": "Mission / Operations",
    }
    event_body["idempotency_key"] = "real-context-event"
    created_response = client.post("/events", headers=headers, json=event_body)
    assert created_response.status_code == 201, created_response.text
    event = service.get_event(UUID(created_response.json()["id"]))

    brief = ScopedPlanningReadTools(service).get_event_brief(
        event_id=event.id,
        organizer_id=UUID(account["id"]),
        expected_version=event.version,
    )
    assert brief.planning_context.model_dump(mode="json") == event_body["planning_context"] | {
        "custom_intended_participant": None,
        "custom_theme": None,
    }

    request_response = client.post(
        f"/events/{event.id}/planning-requests",
        headers=headers,
        json={
            "expected_event_version": event.version,
            "idempotency_key": "real-bedrock-context-stage-plan",
        },
    )
    assert request_response.status_code == 201, request_response.text
    completed_response = request_response.json()
    stage_service = StagePlanningService(database)
    completed = stage_service.get_request(UUID(completed_response["id"]))
    stored = service.get_proposal(completed.proposal_id)

    assert REGION == "us-east-1"
    assert MODEL_ID == "us.amazon.nova-2-lite-v1:0"
    assert completed.status == PlanningRequestStatus.SUCCEEDED
    assert stored.status == ProposalStatus.PENDING
    assert stage_service.list_stages(event.id) == []

    with database.connect() as connection:
        persisted_context = connection.execute(
            "SELECT planning_context FROM events WHERE id=%s", (event.id,)
        ).fetchone()["planning_context"]
        outbox = connection.execute(
            """
            SELECT event_type, aggregate_version, correlation_id, payload
            FROM domain_outbox
            WHERE aggregate_id=%s
            ORDER BY occurred_at, id
            """,
            (event.id,),
        ).fetchall()
    assert persisted_context == brief.planning_context.model_dump(mode="json")
    assert [row["event_type"] for row in outbox] == [
        "event.created", "event.planning_requested", "event.stage_plan_proposed"
    ]
    assert outbox[1]["correlation_id"] == outbox[2]["correlation_id"]

    print(json.dumps({
        "event_id": str(event.id),
        "persisted_planning_context": persisted_context,
        "scoped_agent_brief": brief.model_dump(mode="json"),
        "proposal": stored.payload,
        "proposal_status": stored.status,
        "authoritative_stage_count_before_approval": 0,
        "outbox": [
            {
                "event_type": row["event_type"],
                "aggregate_version": row["aggregate_version"],
                "correlation_id": str(row["correlation_id"]),
            }
            for row in outbox
        ],
    }, default=str, indent=2))
