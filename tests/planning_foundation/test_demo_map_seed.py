"""Proof for the deterministic four-event synthetic map fixture."""
from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.demo_map_seed import (
    DEMO_PASSWORD,
    EVENTS,
    FIXTURE_VERSION,
    seed_demo_map,
)


def counts(database):
    tables=(
        "events","stages","work_items","actor_requirements",
        "participation_advisories","participation_requests",
        "participation_request_items","participations","map_locations",
    )
    with database.connect() as connection:
        return {
            table:connection.execute(f"SELECT count(*) n FROM {table}").fetchone()["n"]
            for table in tables
        }


def test_demo_map_seed_is_authoritative_private_safe_and_idempotent(database):
    first=seed_demo_map(database)
    after_first=counts(database)
    second=seed_demo_map(database)
    after_second=counts(database)

    assert first == second
    assert after_first == after_second
    assert first["synthetic_demo"] is True
    assert len(first["events"]) == 4
    assert len({event["event_id"] for event in first["events"]}) == 4
    assert [event["marker_count"] for event in first["events"]] == [18,13,13,14]
    assert first["total_markers"] == 58
    assert first["distribution"] == {
        "ACCESS_POINT":6,
        "ACTOR":24,
        "EVENT":4,
        "MEETING_POINT":2,
        "PARKING":2,
        "RESOURCE":13,
        "SPONSOR":3,
        "SUPPORT_PARTNER":3,
        "TRANSPORT":1,
    }

    event_ids=[event["event_id"] for event in first["events"]]
    with database.connect() as connection:
        orphan_actors=connection.execute(
            """SELECT count(*) n FROM map_locations ml
               LEFT JOIN participations p
                 ON p.event_id=ml.event_id AND p.account_id=ml.entity_id
                AND p.status='ACCEPTED'
               WHERE ml.entity_type='ACTOR'
                 AND ml.metadata->>'fixture'=%s AND p.id IS NULL""",
            (FIXTURE_VERSION,),
        ).fetchone()["n"]
        unsafe=connection.execute(
            """SELECT count(*) n FROM map_locations
               WHERE metadata->>'fixture'=%s
                 AND (location_precision NOT IN('DEMO_APPROXIMATE','ZONE')
                      OR metadata->>'synthetic_demo'<>'true')""",
            (FIXTURE_VERSION,),
        ).fetchone()["n"]
        dimensions=connection.execute(
            """SELECT count(DISTINCT metadata->>'organization') organizations,
                      count(DISTINCT metadata->>'profession') professions,
                      count(DISTINCT area_label) areas
               FROM map_locations WHERE metadata->>'fixture'=%s""",
            (FIXTURE_VERSION,),
        ).fetchone()
    assert orphan_actors == 0
    assert unsafe == 0
    assert dimensions["organizations"] >= 8
    assert dimensions["professions"] >= 8
    assert dimensions["areas"] >= 12

    client=TestClient(create_app(database))
    signin=client.post(
        "/auth/signin",
        json={
            "email":"ghasi-talab.organizer@demo.hatcommways.invalid",
            "password":DEMO_PASSWORD,
        },
    )
    assert signin.status_code == 200, signin.text
    headers={"Authorization":f"Bearer {signin.json()['access_token']}"}
    home=client.get(f"/events/{event_ids[0]}/home",headers=headers)
    assert home.status_code == 200, home.text
    assert home.json()["event"]["name"] == EVENTS[0].name
    seen=set()
    expected={event.key:event for event in EVENTS}
    for seeded in first["events"]:
        response=client.get(f"/events/{seeded['event_id']}/map",headers=headers)
        assert response.status_code == 200, response.text
        payload=response.json()
        assert payload["event"]["id"] == seeded["event_id"]
        assert payload["event"]["name"] == seeded["event_name"]
        assert len(payload["markers"]) == seeded["marker_count"]
        assert {marker["event_id"] for marker in payload["markers"]} == {
            seeded["event_id"]
        }
        assert not seen.intersection(marker["id"] for marker in payload["markers"])
        seen.update(marker["id"] for marker in payload["markers"])
        assert len(payload["available_filters"]["area_label"]) >= 3
        assert payload["available_filters"]["role"]
        assert payload["available_filters"]["resource_type"]
        assert len(expected[seeded["fixture_key"]].markers) == len(payload["markers"])
        assert all(
            marker["location_precision"] in {"DEMO_APPROXIMATE","ZONE"}
            for marker in payload["markers"]
        )
        assert all(
            marker["metadata"].get("source_label")
            == "Synthetic demo location — not live GPS"
            for marker in payload["markers"]
        )
    assert len(seen) == 58
