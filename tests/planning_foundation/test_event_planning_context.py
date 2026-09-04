from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from psycopg.types.json import Jsonb

from services.api import create_app
from services.planning_foundation.errors import AuthorizationError
from services.planning_foundation.models import EventPlanningContext
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.conftest import make_event_command
from tests.planning_foundation.work_helpers import create_approved_stages


PASSWORD = "correct horse battery staple"


def full_context(**changes):
    values = {
        "detailed_purpose": "Restore the lake and teach waste separation.",
        "expected_scale": 75,
        "intended_participants": ["Community Members", "Volunteers"],
        "custom_intended_participant": None,
        "known_resources": "Gloves and collection bags may be available.",
        "known_requirements": "Organizer says municipal permission is required.",
        "constraints": "Avoid the nesting area and finish before dusk.",
        "desired_outcomes": "Remove litter and document reusable practices.",
        "organizer_notes": "Keep stage names concise.",
        "theme": "Mission / Operations",
        "custom_theme": None,
    }
    values.update(changes)
    return values


def test_theme_and_custom_context_validation():
    assert EventPlanningContext.model_validate(full_context()).theme.value == "Mission / Operations"
    custom = EventPlanningContext.model_validate(
        full_context(theme="Custom", custom_theme="Space mission / NASA-style")
    )
    assert custom.custom_theme == "Space mission / NASA-style"
    with pytest.raises(PydanticValidationError):
        EventPlanningContext.model_validate(full_context(theme="Custom"))
    predefined = EventPlanningContext.model_validate(
        full_context(custom_theme="inactive old value")
    )
    assert predefined.custom_theme is None


def test_other_participant_requires_custom_description():
    with pytest.raises(PydanticValidationError):
        EventPlanningContext.model_validate(
            full_context(intended_participants=["Volunteers", "Other"])
        )
    context = EventPlanningContext.model_validate(
        full_context(
            intended_participants=["Volunteers", "Other"],
            custom_intended_participant="Neighborhood coordinators",
        )
    )
    assert context.custom_intended_participant == "Neighborhood coordinators"


def test_context_persists_and_scoped_brief_exposes_authoritative_values(service, organizer_id):
    context = EventPlanningContext.model_validate(full_context())
    event = service.create_event(
        make_event_command(organizer_id, planning_context=context),
        idempotency_key="context-event",
    )
    stored = service.get_event(event.id)
    assert stored.planning_context == context

    brief = ScopedPlanningReadTools(service).get_event_brief(
        event_id=event.id, organizer_id=organizer_id, expected_version=1
    )
    assert brief.planning_context == context
    assert brief.planning_context.known_resources == context.known_resources
    with pytest.raises(AuthorizationError):
        ScopedPlanningReadTools(service).get_event_brief(
            event_id=event.id,
            organizer_id=UUID("00000000-0000-0000-0000-000000000099"),
            expected_version=1,
        )


def test_legacy_event_without_context_remains_readable(service, organizer_id):
    event = service.create_event(make_event_command(organizer_id), idempotency_key="legacy")
    assert service.get_event(event.id).planning_context is None


def test_work_design_scoped_context_receives_authoritative_theme(database, service, organizer_id):
    event, stages = create_approved_stages(database, service, organizer_id)
    with database.connect() as connection:
        connection.execute(
            "UPDATE events SET planning_context=%s WHERE id=%s",
            (Jsonb({"detailed_purpose": "Prepare the community action", "theme": "Festival / Celebration"}), event.id),
        )
    context = ScopedPlanningReadTools(service).get_stage_work_context(
        event_id=event.id, stage_id=stages[0].id, organizer_id=organizer_id,
        expected_event_version=event.version, expected_stage_version=stages[0].version,
    )
    assert context.naming_theme.value == "Festival / Celebration"
    assert context.custom_naming_style is None


def test_real_api_persists_context_and_planning_request_does_not_accept_browser_copy(database):
    client = TestClient(create_app(database))
    account = client.post(
        "/auth/signup",
        json={
            "email": "context-owner@example.com",
            "display_name": "Context Owner",
            "account_type": "INDIVIDUAL",
            "password": PASSWORD,
        },
    ).json()
    token = client.post(
        "/auth/signin",
        json={"email": "context-owner@example.com", "password": PASSWORD},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    body = make_event_command(UUID(account["id"])).model_dump(mode="json")
    body.pop("organizer_id")
    body["planning_context"] = full_context()
    body["idempotency_key"] = "api-context-event"
    response = client.post("/events", headers=headers, json=body)
    assert response.status_code == 201, response.text
    event = response.json()
    assert event["planning_context"] == full_context()

    request = client.post(
        f"/events/{event['id']}/planning-requests",
        headers=headers,
        json={"expected_event_version": 1, "idempotency_key": "context-plan"},
    )
    assert request.status_code == 201
    injected = client.post(
        f"/events/{event['id']}/planning-requests",
        headers=headers,
        json={
            "expected_event_version": 1,
            "idempotency_key": "context-plan-2",
            "planning_context": full_context(theme="Festival / Celebration"),
        },
    )
    assert injected.status_code == 422

    with database.connect() as connection:
        row = connection.execute(
            "SELECT planning_context FROM events WHERE id=%s", (UUID(event["id"]),)
        ).fetchone()
        stage_count = connection.execute(
            "SELECT count(*) AS count FROM stages WHERE event_id=%s", (UUID(event["id"]),)
        ).fetchone()["count"]
    assert row["planning_context"] == full_context()
    assert stage_count == 0
