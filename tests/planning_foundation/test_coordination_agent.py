from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from services.agent_runtime.coordination import CoordinationWorkflow, SYSTEM_PROMPT, _agent_context
from services.api import create_app
from services.planning_foundation.coordination_service import CoordinationService
from services.planning_foundation.errors import IdempotencyConflictError
from tests.planning_foundation.test_affected_work_resolver import (
    assessed_blocker,
    resolver_endpoint,
)
from tests.planning_foundation.test_human_updates_blockers import scenario as scenario_fixture


@pytest.fixture
def scenario(database, service):
    return scenario_fixture.__wrapped__(database, service)


class FakeRuntime:
    def __init__(self):
        self.calls = []
        self.output = None
        self.error = None

    def generate(self, *, event_id, blocker_id, organizer_id):
        self.calls.append((event_id, blocker_id, organizer_id))
        if self.error:
            raise self.error
        return self.output


def prepare(database, scenario):
    base_client, _update, assessment, _assessment_runtime, _interpretation_runtime = assessed_blocker(database, scenario)
    blocker_id = assessment["authoritative_blocker_id"]
    resolution_response = base_client.post(resolver_endpoint(scenario, blocker_id), headers=scenario["oh"])
    assert resolution_response.status_code == 200, resolution_response.text
    return blocker_id, resolution_response.json()


def decision(scenario, blocker_id, resolution_id, **changes):
    values = {
        "event_id": str(scenario["event"].id),
        "blocker_id": str(blocker_id),
        "affected_work_resolution_id": str(resolution_id),
        "coordination_possible": True,
        "requires_replanning": False,
        "actions": [{
            "action_type": "TEMPORARY_WORKAROUND",
            "target_actor_id": str(scenario["actor"]),
            "target_work_id": str(scenario["work"][0].id),
            "target_meeting_id": None,
            "resource_reference": None,
            "concise_instruction": "Give Priya a short replacement briefing before she starts.",
            "expected_effect": "Priya receives the missed operational context without changing work timing.",
            "requires_human_approval": True,
            "reversible": True,
        }],
        "rationale": "A bounded replacement briefing preserves the confirmed work plan.",
        "confidence": 0.9,
    }
    values.update(changes)
    return values


def protected_state(database, event_id, blocker_id):
    with database.connect() as connection:
        return {
            table: connection.execute(
                f"SELECT * FROM {table} WHERE event_id=%s ORDER BY id", (event_id,)
            ).fetchall()
            for table in (
                "stages", "work_items", "actor_requirements", "participations",
                "event_meetings", "actor_updates"
            )
        } | {
            "work_dependencies": connection.execute(
                """SELECT d.* FROM work_dependencies d JOIN work_items w ON w.id=d.work_id
                   WHERE w.event_id=%s ORDER BY d.work_id,d.depends_on_work_id""", (event_id,)
            ).fetchall(),
            "blocker": connection.execute("SELECT * FROM blockers WHERE id=%s", (blocker_id,)).fetchone(),
        }


def test_explicit_non_replan_coordination_is_scoped_typed_persisted_and_reused(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    runtime = FakeRuntime()
    runtime.output = decision(scenario, blocker_id, resolution["id"])
    client = TestClient(create_app(database, coordination_runtime=runtime))
    before = protected_state(database, scenario["event"].id, blocker_id)
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM coordination_requests").fetchone()["count"] == 0
    response = client.post(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate",
        headers=scenario["oh"], json={},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["coordination_possible"] is True
    assert result["requires_replanning"] is False
    assert result["provider_name"] == "test-runtime"
    assert len(runtime.calls) == 1
    assert client.post(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate",
        headers=scenario["oh"], json={},
    ).json()["id"] == result["id"]
    assert len(runtime.calls) == 1
    assert client.get(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordination",
        headers=scenario["oh"],
    ).json()["id"] == result["id"]
    assert protected_state(database, scenario["event"].id, blocker_id) == before
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM coordination_proposals").fetchone()["count"] == 1


def test_hard_scenario_can_recommend_replanning_without_creating_it(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    runtime = FakeRuntime()
    runtime.output = decision(
        scenario, blocker_id, resolution["id"],
        coordination_possible=False, requires_replanning=True, actions=[],
        rationale="The one-hour arrival delay conflicts with confirmed work and its dependent handoff.",
    )
    client = TestClient(create_app(database, coordination_runtime=runtime))
    result = client.post(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate",
        headers=scenario["oh"], json={},
    )
    assert result.status_code == 200, result.text
    assert result.json()["requires_replanning"] is True
    with database.connect() as connection:
        assert connection.execute("SELECT to_regclass('replanning_requests') AS name").fetchone()["name"] is None


def test_insufficient_facts_request_clarification_without_inventing_replan(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    runtime = FakeRuntime()
    runtime.output = decision(
        scenario, blocker_id, resolution["id"],
        coordination_possible=False, requires_replanning=False,
        actions=[{
            "action_type": "REQUEST_CLARIFICATION",
            "target_actor_id": str(scenario["actor"]),
            "target_work_id": str(scenario["work"][0].id),
            "target_meeting_id": None,
            "resource_reference": None,
            "concise_instruction": "Ask which access route remains available.",
            "expected_effect": "The organizer gets the missing fact needed to choose a safe workaround.",
            "requires_human_approval": False,
            "reversible": True,
        }],
        rationale="The scoped facts do not identify an available route.", confidence=0.65,
    )
    client = TestClient(create_app(database, coordination_runtime=runtime))
    response = client.post(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate",
        headers=scenario["oh"], json={},
    )
    assert response.status_code == 200, response.text
    assert response.json()["actions"][0]["action_type"] == "REQUEST_CLARIFICATION"
    assert response.json()["requires_replanning"] is False


def test_context_contains_only_affected_scope_relevant_actor_meetings_and_resources(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    service = CoordinationService(database)
    context = service.context(scenario["event"].id, UUID(blocker_id), scenario["owner"])
    assert {row["id"] for row in context.affected_work} == {
        UUID(item) for item in resolution["directly_affected_work_ids"] + resolution["downstream_affected_work_ids"]
    }
    assert {row["account_id"] for row in context.relevant_actors} == {scenario["actor"]}
    assert all(row["status"] == "ACCEPTED" for row in context.relevant_actors)
    agent_context = _agent_context(context)
    assert "relevant_actors" not in agent_context
    assert {row["actor_id"] for row in agent_context["eligible_actors"]} == {str(scenario["actor"])}
    assert all(row["role"] and row["work"] and row["stage"] for row in agent_context["eligible_actors"])
    assert all("availability" in row for row in agent_context["eligible_actors"])
    assert "original_text" not in context.model_dump_json()
    assert "email" not in context.model_dump_json()


def test_agent_contract_distinguishes_actor_id_from_other_scoped_ids():
    assert "exact eligible_actors[].actor_id values" in SYSTEM_PROMPT
    assert "never use participation_id, actor_requirement_id" in SYSTEM_PROMPT
    assert "Leave target_actor_id null" in SYSTEM_PROMPT


def test_invalid_action_ids_fail_and_runtime_failure_requires_explicit_retry(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    runtime = FakeRuntime()
    runtime.output = decision(scenario, blocker_id, resolution["id"])
    runtime.output["actions"][0]["target_actor_id"] = str(uuid4())
    client = TestClient(create_app(database, coordination_runtime=runtime))
    endpoint = f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate"
    response = client.post(endpoint, headers=scenario["oh"], json={})
    assert response.status_code == 422
    assert "unrelated actor" in response.json()["detail"]
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM coordination_proposals").fetchone()["count"] == 0
        assert connection.execute("SELECT status FROM coordination_requests").fetchone()["status"] == "FAILED"
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 409
    runtime.output = decision(scenario, blocker_id, resolution["id"])
    assert client.post(endpoint, headers=scenario["oh"], json={"retry": True}).status_code == 200


def test_stale_graph_or_relevant_state_rejects_silent_reuse(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    runtime = FakeRuntime()
    runtime.output = decision(scenario, blocker_id, resolution["id"])
    client = TestClient(create_app(database, coordination_runtime=runtime))
    endpoint = f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate"
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 200
    with database.connect() as connection:
        connection.execute("UPDATE blockers SET version=version+1 WHERE id=%s", (blocker_id,))
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 409
    assert len(runtime.calls) == 1


def test_concurrent_coordinate_runs_model_once(database, scenario):
    blocker_id, resolution = prepare(database, scenario)
    entered, release = Event(), Event()

    class BlockingRuntime(FakeRuntime):
        def generate(self, **kwargs):
            self.calls.append(kwargs)
            entered.set()
            release.wait(5)
            return self.output

    runtime = BlockingRuntime()
    runtime.output = decision(scenario, blocker_id, resolution["id"])
    workflow = CoordinationWorkflow(CoordinationService(database), runtime)
    args = dict(event_id=scenario["event"].id, blocker_id=UUID(blocker_id), organizer_id=scenario["owner"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(workflow.execute, **args)
        assert entered.wait(5)
        second = pool.submit(workflow.execute, **args)
        with pytest.raises(IdempotencyConflictError):
            second.result(timeout=5)
        release.set()
        assert first.result(timeout=5).coordination_possible is True
    assert len(runtime.calls) == 1


@pytest.mark.real_bedrock
def test_real_nova_coordination_returns_typed_scoped_result(database, scenario):
    if not __import__("os").environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK"):
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    blocker_id, _resolution = prepare(database, scenario)
    client = TestClient(create_app(database, execute_planning_requests=True))
    response = client.post(
        f"/events/{scenario['event'].id}/blockers/{blocker_id}/coordinate",
        headers=scenario["oh"], json={},
    )
    assert response.status_code == 200, response.text
    assert response.json()["agent_name"] == "hatcommways-coordination-agent"
