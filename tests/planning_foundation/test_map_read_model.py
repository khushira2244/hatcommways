"""Database-backed contracts for the privacy-safe event map read model."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from services.api import create_app
from tests.planning_foundation.conftest import make_event_command
from tests.planning_foundation.test_human_updates_blockers import scenario as scenario_fixture


@pytest.fixture
def scenario(database, service):
    return scenario_fixture.__wrapped__(database, service)


def add_marker(connection, event_id, entity_type, display_name, latitude, longitude,
               entity_id=None, precision="APPROXIMATE", metadata=None):
    marker_id = uuid4()
    connection.execute(
        """INSERT INTO map_locations(
               id,event_id,entity_type,entity_id,display_name,latitude,longitude,
               area_label,location_precision,status,visible,metadata
           ) VALUES(%s,%s,%s,%s,%s,%s,%s,'Zone A',%s,'ACTIVE',true,%s)""",
        (marker_id,event_id,entity_type,entity_id,display_name,latitude,longitude,
         precision,Jsonb(metadata or {})),
    )
    return marker_id


def enable_map(connection, event_id, *, actors=True, resources=True, sponsors=True):
    connection.execute(
        """UPDATE event_setups
           SET map_enabled=true,show_actor_tree=%s,show_resources=%s,show_sponsors=%s,
               resource_needs=%s,sponsors_support=%s
           WHERE event_id=%s""",
        (actors,resources,sponsors,
         Jsonb([{"name":"First Aid","category":"Medical"}]),
         Jsonb([{"name":"City Partner","type":"SUPPORT_PARTNER",
                 "visibility_enabled":True}]),event_id),
    )


def test_authoritative_map_privacy_filters_and_pure_deterministic_read(
    database, service, scenario, monkeypatch
):
    s = scenario
    other = service.create_event(
        make_event_command(s["owner"], name="Other"),
        idempotency_key=f"other-{uuid4()}",
    )
    with database.connect() as connection:
        enable_map(connection, s["event"].id)
        add_marker(connection,s["event"].id,"EVENT","Gachibowli Lake Cleanup",
                   17.44,78.35,s["event"].id)
        add_marker(connection,s["event"].id,"ACTOR","Priya",17.441,78.351,
                   s["actor"],"DEMO_APPROXIMATE",
                   {"zone":"A","private_address":"never"})
        add_marker(connection,s["event"].id,"ACTOR","Priya exact",17.44123,
                   78.35123,s["actor"],"EXACT")
        add_marker(connection,s["event"].id,"ACTOR","Pending Person",17.45,
                   78.36,s["stranger"])
        add_marker(connection,s["event"].id,"RESOURCE","First Aid",17.442,78.352)
        add_marker(connection,s["event"].id,"RESOURCE","Fabricated Resource",
                   17.443,78.353)
        add_marker(connection,s["event"].id,"SUPPORT_PARTNER","City Partner",
                   17.444,78.354)
        add_marker(connection,other.id,"OTHER","Other Event Secret",10,10)
        tables=("events","map_locations","participations","work_items",
                "actor_requirements")
        before={table:connection.execute(
            f"SELECT count(*) n FROM {table}").fetchone()["n"] for table in tables}

    from strands import Agent
    monkeypatch.setattr(
        Agent,"__call__",
        lambda *_args,**_kwargs: pytest.fail("map read invoked an agent"),
    )
    client=TestClient(create_app(database))
    url=f"/events/{s['event'].id}/map"
    first=client.get(url,headers=s["oh"])
    assert first.status_code == 200, first.text
    second=client.get(url,headers=s["oh"])
    assert first.json() == second.json()

    data=first.json()
    marker_types=[item["entity_type"] for item in data["markers"]]
    names=[item["display_name"] for item in data["markers"]]
    assert data["event"]["location_description"] == s["event"].location_description
    assert "EVENT" in marker_types
    assert "Priya" in names
    assert "Priya exact" not in names
    assert "Pending Person" not in names
    assert "First Aid" in names
    assert "Fabricated Resource" not in names
    assert "City Partner" in names
    assert "Other Event Secret" not in names
    priya=next(item for item in data["markers"] if item["display_name"]=="Priya")
    assert priya["role"]
    assert priya["metadata"] == {"zone":"A"}
    assert data["available_filters"]["marker_type"] == sorted(set(marker_types))

    with database.connect() as connection:
        after={table:connection.execute(
            f"SELECT count(*) n FROM {table}").fetchone()["n"] for table in tables}
    assert after == before


def test_visibility_switches_remove_actor_resource_and_support(database, scenario):
    s=scenario
    with database.connect() as connection:
        enable_map(connection,s["event"].id,actors=False,resources=False,sponsors=False)
        add_marker(connection,s["event"].id,"EVENT","Event",17,78,s["event"].id)
        add_marker(connection,s["event"].id,"ACTOR","Priya",17.1,78.1,s["actor"])
        add_marker(connection,s["event"].id,"RESOURCE","First Aid",17.2,78.2)
        add_marker(connection,s["event"].id,"SUPPORT_PARTNER","City Partner",17.3,78.3)

    response=TestClient(create_app(database)).get(
        f"/events/{s['event'].id}/map",headers=s["oh"])
    assert response.status_code == 200, response.text
    assert [item["entity_type"] for item in response.json()["markers"]] == ["EVENT"]


def test_private_map_requires_event_membership_or_accepted_participation(
    database, scenario
):
    s=scenario
    with database.connect() as connection:
        connection.execute(
            "UPDATE event_setups SET event_visibility='PRIVATE' WHERE event_id=%s",
            (s["event"].id,),
        )

    client=TestClient(create_app(database))
    assert client.get(f"/events/{s['event'].id}/map").status_code == 401
    assert client.get(
        f"/events/{s['event'].id}/map",headers=s["sh"]
    ).status_code == 403
    assert client.get(
        f"/events/{s['event'].id}/map",headers=s["ah"]
    ).status_code == 200


def test_authenticated_web_config_returns_injected_google_maps_key(
    database, scenario
):
    client=TestClient(create_app(
        database,
        google_maps_api_key="browser-test-key",
        google_maps_map_id="browser-test-map-id",
    ))
    response=client.get("/web-config",headers=scenario["oh"])
    assert response.status_code == 200
    assert response.json() == {
        "google_maps_api_key":"browser-test-key",
        "google_maps_map_id":"browser-test-map-id",
    }
