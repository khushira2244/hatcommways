"""Deterministic affected-work traversal from persisted blocker assessments."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.affected_work_service import AffectedWorkService
from services.planning_foundation.errors import ValidationError
from tests.planning_foundation.test_blocker_assessment import (
    FakeRuntime,
    assessment_payload,
    submit_and_interpret,
)
from tests.planning_foundation.test_human_updates_blockers import scenario as scenario_fixture
from tests.planning_foundation.work_helpers import create_approved_work


@pytest.fixture
def scenario(database, service):
    return scenario_fixture.__wrapped__(database, service)


def extend_graph(database, scenario):
    event_id = scenario["event"].id
    stage_id = scenario["stage"].id
    source = scenario["work"][0].source_proposal_id
    ids = {name: uuid4() for name in ("c", "d", "e", "f")}
    with database.connect() as connection:
        connection.execute(
            "UPDATE work_items SET canonical_name='Waste Sorting' WHERE id=%s",
            (scenario["work"][1].id,),
        )
        for order, (key, name) in enumerate(
            (("c", "Water Sampling"), ("d", "Waste Handoff"),
             ("e", "Lab Handoff"), ("f", "Photo Documentation")),
            start=3,
        ):
            connection.execute(
                """INSERT INTO work_items(
                       id,event_id,stage_id,canonical_name,purpose,work_order,
                       estimated_person_hours,work_share,starts_at,ends_at,source_proposal_id)
                   SELECT %s,event_id,stage_id,%s,'Confirmed test work',%s,
                          1,1,starts_at,ends_at,%s
                   FROM work_items WHERE id=%s""",
                (ids[key], name, order, source, scenario["work"][0].id),
            )
        for dependent, prerequisite in (
            (ids["c"], scenario["work"][0].id),
            (ids["d"], scenario["work"][1].id),
            (ids["e"], ids["c"]),
        ):
            connection.execute(
                "INSERT INTO work_dependencies(work_id,depends_on_work_id) VALUES(%s,%s)",
                (dependent, prerequisite),
            )
    return ids


def assessed_blocker(
    database, scenario, *, direct_work=True, direct_work_id=None, blocking=True
):
    runtime = FakeRuntime()
    client, update, interpretation, interpretation_runtime = submit_and_interpret(
        database, scenario, runtime
    )
    changes = {
        "directly_referenced_stage_id": str(scenario["stage"].id),
        "directly_referenced_work_id": (
            str(direct_work_id or scenario["work"][0].id) if direct_work else None
        ),
    }
    if not blocking:
        changes.update(
            is_execution_blocker=False,
            blocker_kind="NONE",
            coordination_needed=False,
            replanning_may_be_needed=False,
            concise_reason="The update does not block execution.",
        )
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"], scenario["event"].id, interpretation["id"], **changes
    )
    response = client.post(
        f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker",
        headers=scenario["oh"],
        json={},
    )
    assert response.status_code == 200, response.text
    return client, update, response.json(), runtime, interpretation_runtime


def resolver_endpoint(scenario, blocker_id):
    return f"/events/{scenario['event'].id}/blockers/{blocker_id}/resolve-affected-work"


def test_branch_precise_resolution_is_persisted_reused_and_agent_free(
    database, scenario, monkeypatch
):
    ids = extend_graph(database, scenario)
    client, _update, assessment, assessment_runtime, interpretation_runtime = assessed_blocker(
        database, scenario
    )

    def forbidden(*_args, **_kwargs):
        pytest.fail("affected-work resolution invoked an agent")

    monkeypatch.setattr(FakeRuntime, "generate", forbidden)
    blocker_id = assessment["authoritative_blocker_id"]
    with database.connect() as connection:
        before = {
            "event": connection.execute("SELECT * FROM events WHERE id=%s", (scenario["event"].id,)).fetchone(),
            "stages": connection.execute("SELECT * FROM stages WHERE event_id=%s ORDER BY id", (scenario["event"].id,)).fetchall(),
            "work": connection.execute("SELECT * FROM work_items WHERE event_id=%s ORDER BY id", (scenario["event"].id,)).fetchall(),
            "dependencies": connection.execute(
                """SELECT d.* FROM work_dependencies d JOIN work_items w ON w.id=d.work_id
                   WHERE w.event_id=%s ORDER BY d.work_id,d.depends_on_work_id""",
                (scenario["event"].id,),
            ).fetchall(),
            "actor_requirements": connection.execute(
                "SELECT * FROM actor_requirements WHERE event_id=%s ORDER BY id",
                (scenario["event"].id,),
            ).fetchall(),
            "participations": connection.execute(
                "SELECT * FROM participations WHERE event_id=%s ORDER BY id",
                (scenario["event"].id,),
            ).fetchall(),
            "blocker": connection.execute("SELECT * FROM blockers WHERE id=%s", (blocker_id,)).fetchone(),
        }
    response = client.post(resolver_endpoint(scenario, blocker_id), headers=scenario["oh"])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["directly_affected_work_ids"] == [str(scenario["work"][0].id)]
    assert result["downstream_affected_work_ids"] == [
        str(scenario["work"][1].id), str(ids["c"]), str(ids["d"]), str(ids["e"])
    ]
    assert str(ids["f"]) not in result["downstream_affected_work_ids"]
    assert result["affected_stage_ids"] == [str(scenario["stage"].id)]
    assert len(result["graph_fingerprint"]) == 64
    assert client.post(resolver_endpoint(scenario, blocker_id), headers=scenario["oh"]).json()["id"] == result["id"]
    assert client.get(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/affected-work",
        headers=scenario["oh"],
    ).json()["id"] == result["id"]
    assert len(assessment_runtime.calls) == 1
    assert len(interpretation_runtime.calls) == 1
    with database.connect() as connection:
        after = {
            "event": connection.execute("SELECT * FROM events WHERE id=%s", (scenario["event"].id,)).fetchone(),
            "stages": connection.execute("SELECT * FROM stages WHERE event_id=%s ORDER BY id", (scenario["event"].id,)).fetchall(),
            "work": connection.execute("SELECT * FROM work_items WHERE event_id=%s ORDER BY id", (scenario["event"].id,)).fetchall(),
            "dependencies": connection.execute(
                """SELECT d.* FROM work_dependencies d JOIN work_items w ON w.id=d.work_id
                   WHERE w.event_id=%s ORDER BY d.work_id,d.depends_on_work_id""",
                (scenario["event"].id,),
            ).fetchall(),
            "actor_requirements": connection.execute(
                "SELECT * FROM actor_requirements WHERE event_id=%s ORDER BY id",
                (scenario["event"].id,),
            ).fetchall(),
            "participations": connection.execute(
                "SELECT * FROM participations WHERE event_id=%s ORDER BY id",
                (scenario["event"].id,),
            ).fetchall(),
            "blocker": connection.execute("SELECT * FROM blockers WHERE id=%s", (blocker_id,)).fetchone(),
        }
        assert connection.execute(
            "SELECT count(*) FROM affected_work_resolutions WHERE blocker_id=%s", (blocker_id,)
        ).fetchone()["count"] == 1
        assert connection.execute(
            "SELECT count(*) FROM domain_outbox WHERE event_type='blocker.affected_work_resolved' AND aggregate_id=%s",
            (blocker_id,),
        ).fetchone()["count"] == 1
    assert after == before


def test_branch_start_excludes_upstream_and_sibling_branch(database, scenario):
    ids = extend_graph(database, scenario)
    scoped = dict(scenario)
    scoped["work"] = [scenario["work"][1], scenario["work"][0]]
    scoped["ah"] = scenario["oh"]
    client, _update, assessment, _runtime, _interpretation = assessed_blocker(
        database, scoped, direct_work_id=scenario["work"][1].id
    )
    result = client.post(
        resolver_endpoint(scenario, assessment["authoritative_blocker_id"]), headers=scenario["oh"]
    ).json()
    assert result["directly_affected_work_ids"] == [str(scenario["work"][1].id)]
    assert result["downstream_affected_work_ids"] == [str(ids["d"])]
    assert str(ids["c"]) not in result["downstream_affected_work_ids"]
    assert str(ids["e"]) not in result["downstream_affected_work_ids"]


def test_stage_only_resolution_does_not_infer_every_work_item(database, scenario):
    extend_graph(database, scenario)
    client, _update, assessment, _runtime, _interpretation = assessed_blocker(
        database, scenario, direct_work=False
    )
    result = client.post(
        resolver_endpoint(scenario, assessment["authoritative_blocker_id"]), headers=scenario["oh"]
    ).json()
    assert result["directly_affected_work_ids"] == []
    assert result["downstream_affected_work_ids"] == []
    assert result["affected_stage_ids"] == [str(scenario["stage"].id)]
    assert "not inferred" in result["deterministic_reason"]


def test_nonblocking_or_unassessed_blocker_is_rejected(database, scenario):
    client, update, _assessment, _runtime, _interpretation = assessed_blocker(
        database, scenario, blocking=False
    )
    manual = client.post(
        f"/events/{scenario['event'].id}/blockers",
        headers=scenario["oh"],
        json={"human_update_id": update["id"], "title": "Manual", "summary": "Manual blocker"},
    )
    assert manual.status_code == 201, manual.text
    response = client.post(
        resolver_endpoint(scenario, manual.json()["id"]), headers=scenario["oh"]
    )
    assert response.status_code == 422
    assert "blocking assessment" in response.json()["detail"]


def test_cycle_and_cross_event_edges_fail_safely(database, service, scenario):
    client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    endpoint = resolver_endpoint(scenario, assessment["authoritative_blocker_id"])
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO work_dependencies(work_id,depends_on_work_id) VALUES(%s,%s)",
            (scenario["work"][0].id, scenario["work"][1].id),
        )
    response = client.post(endpoint, headers=scenario["oh"])
    assert response.status_code == 422
    assert "cycle" in response.json()["detail"]

    with database.connect() as connection:
        connection.execute(
            "DELETE FROM work_dependencies WHERE work_id=%s AND depends_on_work_id=%s",
            (scenario["work"][0].id, scenario["work"][1].id),
        )
    other, _stage, other_work, _ = create_approved_work(database, service, scenario["owner"])
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO work_dependencies(work_id,depends_on_work_id) VALUES(%s,%s)",
            (scenario["work"][0].id, other_work[0].id),
        )
    response = client.post(endpoint, headers=scenario["oh"])
    assert response.status_code == 422
    assert "crosses event" in response.json()["detail"]


def test_stale_before_resolution_and_fingerprint_change_after_resolution(database, scenario):
    client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    endpoint = resolver_endpoint(scenario, assessment["authoritative_blocker_id"])
    with database.connect() as connection:
        connection.execute("UPDATE events SET version=version+1 WHERE id=%s", (scenario["event"].id,))
    assert client.post(endpoint, headers=scenario["oh"]).status_code == 409

    # Restore the assessed version, resolve once, then mutate an edge without a version bump.
    with database.connect() as connection:
        connection.execute(
            "UPDATE events SET version=%s WHERE id=%s",
            (assessment["assessed_event_version"], scenario["event"].id),
        )
    first = client.post(endpoint, headers=scenario["oh"])
    assert first.status_code == 200, first.text
    with database.connect() as connection:
        connection.execute(
            "DELETE FROM work_dependencies WHERE work_id=%s AND depends_on_work_id=%s",
            (scenario["work"][1].id, scenario["work"][0].id),
        )
    assert client.post(endpoint, headers=scenario["oh"]).status_code == 409


def test_cleared_blocker_keeps_history_but_cannot_get_first_resolution(database, scenario):
    client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    blocker_id = assessment["authoritative_blocker_id"]
    endpoint = resolver_endpoint(scenario, blocker_id)
    cleared = client.patch(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}",
        headers=scenario["oh"],
        json={"expected_version": 1, "condition_state": "CLEARED"},
    )
    assert cleared.status_code == 200
    assert client.post(endpoint, headers=scenario["oh"]).status_code == 422

    # Re-open, resolve, clear again, and prove the immutable historical result is returned.
    reopened = client.patch(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}",
        headers=scenario["oh"],
        json={"expected_version": 2, "condition_state": "OPEN"},
    )
    assert reopened.status_code == 200
    original = client.post(endpoint, headers=scenario["oh"]).json()
    client.patch(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}",
        headers=scenario["oh"],
        json={"expected_version": 3, "condition_state": "CLEARED"},
    )
    with database.connect() as connection:
        connection.execute(
            "DELETE FROM work_dependencies WHERE work_id=%s", (scenario["work"][1].id,)
        )
    assert client.post(endpoint, headers=scenario["oh"]).json()["id"] == original["id"]


def test_concurrent_resolution_and_duplicate_edges_are_idempotent(database, scenario):
    ids = extend_graph(database, scenario)
    _client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    service = AffectedWorkService(database)
    blocker_id = UUID(assessment["authoritative_blocker_id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _item: service.resolve(scenario["event"].id, blocker_id, scenario["owner"]),
                range(2),
            )
        )
    assert results[0].id == results[1].id
    assert len(results[0].downstream_affected_work_ids) == len(set(results[0].downstream_affected_work_ids))
    assert AffectedWorkService._downstream(
        {scenario["work"][0].id},
        [(ids["c"], scenario["work"][0].id), (ids["c"], scenario["work"][0].id)],
    ) == {ids["c"]}


def test_pending_proposal_is_ignored_and_unconfirmed_direct_work_is_rejected(database, scenario):
    proposal_id = uuid4()
    pending_work_id = uuid4()
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO proposals(
                   id,proposal_type,target_type,target_id,created_by,base_versions,payload,
                   status,idempotency_key,correlation_id)
               VALUES(%s,'WORK_DECOMPOSITION','STAGE',%s,'test:pending','{}'::jsonb,
                      '{}'::jsonb,'PENDING',%s,%s)""",
            (proposal_id, scenario["stage"].id, f"pending-{uuid4()}", uuid4()),
        )
        connection.execute(
            """INSERT INTO work_items(
                   id,event_id,stage_id,canonical_name,purpose,work_order,
                   estimated_person_hours,work_share,starts_at,ends_at,source_proposal_id)
               SELECT %s,event_id,stage_id,'Pending fabrication','Must stay excluded',99,
                      1,1,starts_at,ends_at,%s
               FROM work_items WHERE id=%s""",
            (pending_work_id, proposal_id, scenario["work"][0].id),
        )

    client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    confirmed = client.post(
        resolver_endpoint(scenario, assessment["authoritative_blocker_id"]), headers=scenario["oh"]
    )
    assert confirmed.status_code == 200, confirmed.text
    assert str(pending_work_id) not in confirmed.json()["downstream_affected_work_ids"]

    scoped = dict(scenario)
    scoped["work"] = [SimpleNamespace(id=pending_work_id)]
    scoped["ah"] = scenario["oh"]
    client, _update, pending_assessment, _runtime, _interpretation = assessed_blocker(
        database, scoped, direct_work_id=pending_work_id
    )
    rejected = client.post(
        resolver_endpoint(scenario, pending_assessment["authoritative_blocker_id"]),
        headers=scenario["oh"],
    )
    assert rejected.status_code == 422
    assert "not confirmed authoritative" in rejected.json()["detail"]


def test_missing_and_cross_event_blocker_ids_do_not_leak(database, service, scenario):
    client = scenario["client"]
    missing = uuid4()
    assert client.post(resolver_endpoint(scenario, missing), headers=scenario["oh"]).status_code == 404
    assert client.get(
        f"/events/{scenario['event'].id}/blockers/{missing}/affected-work",
        headers=scenario["oh"],
    ).status_code == 404

    _client, _update, assessment, _runtime, _interpretation = assessed_blocker(database, scenario)
    other, _stage, _work, _other_stage = create_approved_work(database, service, scenario["owner"])
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO event_memberships(event_id,account_id,role,status)
               VALUES(%s,%s,'ORGANIZER','ACTIVE')""",
            (other.id, scenario["owner"]),
        )
    wrong_event = f"/events/{other.id}/blockers/{assessment['authoritative_blocker_id']}/resolve-affected-work"
    assert client.post(wrong_event, headers=scenario["oh"]).status_code == 404
