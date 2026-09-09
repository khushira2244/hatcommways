from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from services.agent_runtime.human_update_interpretation import (
    HumanUpdateInterpretationAgentResult,
    HumanUpdateInterpretationWorkflow,
    StrandsHumanUpdateInterpretationAgent,
)
from services.api import create_app
from services.planning_foundation.errors import IdempotencyConflictError
from services.planning_foundation.human_update_interpretation_service import (
    HumanUpdateInterpretationService,
)
from services.planning_foundation.human_update_models import HumanUpdateInterpretation
from tests.planning_foundation.test_human_updates_blockers import scenario as scenario_fixture


REPORT = "I can only arrive at 11 because the road is blocked."


@pytest.fixture
def scenario(database, service):
    return scenario_fixture.__wrapped__(database, service)


def interpretation(update_id, event_id, **changes):
    values = {
        "update_id": str(update_id),
        "event_id": str(event_id),
        "interpretation_type": "AVAILABILITY_CHANGE",
        "concise_summary": "Participant expects to arrive at 11 due to a blocked road.",
        "reported_condition": "The participant can only arrive at 11.",
        "temporal_signal": "Arrival at 11",
        "location_signal": "Road is blocked",
        "referenced_stage_id": None,
        "referenced_work_id": None,
        "possible_blocker": True,
        "blocker_reason": "Late arrival may disrupt assigned work.",
        "confidence": 0.91,
        "requires_clarification": False,
        "clarification_question": None,
    }
    values.update(changes)
    return values


class FakeRuntime:
    def __init__(self):
        self.calls = []
        self.outputs = {}
        self.error = None

    def generate(self, *, event_id, update_id, organizer_id):
        self.calls.append((event_id, update_id, organizer_id))
        if self.error:
            raise self.error
        return self.outputs[str(update_id)]


def protected_state(database, event_id):
    with database.connect() as connection:
        return {
            "event": connection.execute(
                "SELECT version,starts_at,ends_at FROM events WHERE id=%s", (event_id,)
            ).fetchone(),
            "stages": connection.execute(
                "SELECT id,version,starts_at,ends_at FROM stages WHERE event_id=%s ORDER BY id",
                (event_id,),
            ).fetchall(),
            "work": connection.execute(
                "SELECT id,version,starts_at,ends_at FROM work_items WHERE event_id=%s ORDER BY id",
                (event_id,),
            ).fetchall(),
            "meetings": connection.execute(
                "SELECT id,version,start_time,end_time,status FROM event_meetings WHERE event_id=%s ORDER BY id",
                (event_id,),
            ).fetchall(),
            "participations": connection.execute(
                "SELECT * FROM participations WHERE event_id=%s ORDER BY id", (event_id,)
            ).fetchall(),
            "requirements": connection.execute(
                "SELECT * FROM actor_requirements WHERE event_id=%s ORDER BY id", (event_id,)
            ).fetchall(),
            "accounts": connection.execute("SELECT * FROM accounts ORDER BY id").fetchall(),
        }


def submit(client, scenario, text=REPORT):
    return client.post(
        f"/events/{scenario['event'].id}/human-updates",
        headers=scenario["ah"],
        json={"text": text, "work_id": str(scenario["work"][0].id)},
    )


def test_submission_is_truth_only_and_explicit_interpret_is_typed_deduplicated_and_scoped(
    database, scenario
):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, human_update_interpretation_runtime=runtime))
    update = submit(client, scenario).json()
    assert runtime.calls == []
    assert update["original_text"] == REPORT
    assert update["interpretation_status"] == "NOT_REQUESTED"
    before = protected_state(database, scenario["event"].id)
    runtime.outputs[update["id"]] = interpretation(
        update["id"],
        scenario["event"].id,
        referenced_stage_id=str(scenario["stage"].id),
        referenced_work_id=str(scenario["work"][0].id),
    )
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/interpret"
    response = client.post(endpoint, headers=scenario["oh"], json={})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["interpretation_type"] == "AVAILABILITY_CHANGE"
    assert result["possible_blocker"] is True
    assert result["provider_name"] == "test-runtime"
    assert result["agent_name"] == "hatcommways-human-update-interpretation-agent"
    assert len(runtime.calls) == 1
    replay = client.post(endpoint, headers=scenario["oh"], json={})
    assert replay.status_code == 200 and replay.json()["id"] == result["id"]
    assert len(runtime.calls) == 1
    direct = client.get(endpoint.replace("/interpret", "/interpretation"), headers=scenario["oh"])
    assert direct.json()["id"] == result["id"]
    reports = client.get(
        f"/events/{scenario['event'].id}/human-updates", headers=scenario["oh"]
    ).json()
    stored = next(item for item in reports if item["id"] == update["id"])
    assert stored["original_text"] == REPORT
    assert stored["interpretation_status"] == "INTERPRETED"
    assert stored["interpretation"]["id"] == result["id"]
    assert protected_state(database, scenario["event"].id) == before
    with database.connect() as connection:
        assert connection.execute(
            "SELECT count(*) FROM blockers WHERE event_id=%s", (scenario["event"].id,)
        ).fetchone()["count"] == 0
        assert connection.execute(
            "SELECT count(*) FROM human_update_interpretations WHERE human_update_id=%s",
            (update["id"],),
        ).fetchone()["count"] == 1
        events = [
            row["event_type"]
            for row in connection.execute(
                "SELECT event_type FROM domain_outbox WHERE aggregate_id=%s ORDER BY occurred_at",
                (update["id"],),
            ).fetchall()
        ]
    assert events == ["human_update.interpretation_requested", "human_update.interpreted"]


def test_agent_context_contains_only_the_report_and_explicitly_linked_facts(database, scenario):
    client = TestClient(create_app(database))
    update = submit(client, scenario).json()
    service = HumanUpdateInterpretationService(database)
    context = service.context(
        scenario["event"].id, update["id"], scenario["owner"]
    ).model_dump()
    assert context["original_text"] == REPORT
    assert context["reporter_relationship"].value == "ACTOR"
    assert context["reporter_display_name"] == "Priya"
    assert context["stage"]["id"] == scenario["stage"].id
    assert context["work"]["id"] == scenario["work"][0].id
    assert context["accepted_participation"]["id"] == scenario["participation"]["id"]
    serialized = str(context)
    assert str(scenario["work"][1].id) not in serialized
    assert str(scenario["other_stage"].id) not in serialized
    assert "blocker" not in serialized.lower()


@pytest.mark.parametrize(
    ("text", "output", "expected_type", "possible_blocker", "clarification"),
    [
        (
            "Shoreline cleanup is finished and all bags have been moved to sorting.",
            {
                "interpretation_type": "COMPLETION_UPDATE",
                "concise_summary": "Shoreline cleanup is complete and bags are at sorting.",
                "reported_condition": "The reported work is finished.",
                "temporal_signal": None,
                "location_signal": "Sorting",
                "possible_blocker": False,
                "blocker_reason": None,
                "confidence": 0.96,
                "requires_clarification": False,
                "clarification_question": None,
            },
            "COMPLETION_UPDATE",
            False,
            False,
        ),
        (
            "It won't work.",
            {
                "interpretation_type": "UNKNOWN",
                "concise_summary": "The reporter says something will not work.",
                "reported_condition": "An unspecified thing will not work.",
                "temporal_signal": None,
                "location_signal": None,
                "possible_blocker": False,
                "blocker_reason": None,
                "confidence": 0.25,
                "requires_clarification": True,
                "clarification_question": "What is not working?",
            },
            "UNKNOWN",
            False,
            True,
        ),
    ],
)
def test_completion_and_clarification_are_not_forced_into_blockers(
    database, scenario, text, output, expected_type, possible_blocker, clarification
):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, human_update_interpretation_runtime=runtime))
    update = submit(client, scenario, text).json()
    runtime.outputs[update["id"]] = interpretation(
        update["id"], scenario["event"].id, **output
    )
    result = client.post(
        f"/events/{scenario['event'].id}/human-updates/{update['id']}/interpret",
        headers=scenario["oh"],
        json={},
    ).json()
    assert result["interpretation_type"] == expected_type
    assert result["possible_blocker"] is possible_blocker
    assert result["requires_clarification"] is clarification


def test_invalid_output_fails_safely_requires_explicit_retry_and_then_succeeds(
    database, scenario
):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, human_update_interpretation_runtime=runtime))
    update = submit(client, scenario).json()
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/interpret"
    runtime.outputs[update["id"]] = interpretation(
        update["id"], scenario["event"].id, referenced_work_id=str(uuid4())
    )
    invalid = client.post(endpoint, headers=scenario["oh"], json={})
    assert invalid.status_code == 422
    reports = client.get(
        f"/events/{scenario['event'].id}/human-updates", headers=scenario["oh"]
    ).json()
    failed = next(item for item in reports if item["id"] == update["id"])
    assert failed["original_text"] == REPORT
    assert failed["interpretation_status"] == "FAILED"
    assert failed["interpretation_failure_code"] == "ValidationError"
    assert failed["interpretation"] is None
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 409
    runtime.outputs[update["id"]] = interpretation(update["id"], scenario["event"].id)
    retried = client.post(endpoint, headers=scenario["oh"], json={"retry": True})
    assert retried.status_code == 200
    reports = client.get(
        f"/events/{scenario['event'].id}/human-updates", headers=scenario["oh"]
    ).json()
    complete = next(item for item in reports if item["id"] == update["id"])
    assert complete["interpretation_status"] == "INTERPRETED"
    assert complete["interpretation_attempt_count"] == 2
    assert complete["interpretation_failure_code"] is None


def test_runtime_and_schema_failures_persist_no_malformed_interpretation(database, scenario):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, human_update_interpretation_runtime=runtime))
    first = submit(client, scenario).json()
    runtime.error = RuntimeError("provider included private details")
    with pytest.raises(RuntimeError):
        client.post(
            f"/events/{scenario['event'].id}/human-updates/{first['id']}/interpret",
            headers=scenario["oh"],
            json={},
        )
    second = submit(client, scenario, "It won't work.").json()
    runtime.error = None
    runtime.outputs[second["id"]] = interpretation(
        second["id"],
        scenario["event"].id,
        possible_blocker=False,
        blocker_reason="invalid conditional field",
    )
    with pytest.raises(Exception):
        client.post(
            f"/events/{scenario['event'].id}/human-updates/{second['id']}/interpret",
            headers=scenario["oh"],
            json={},
        )
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM human_update_interpretations").fetchone()[
            "count"
        ] == 0
        failure_codes = [
            row["interpretation_failure_code"]
            for row in connection.execute(
                "SELECT interpretation_failure_code FROM human_updates ORDER BY created_at"
            ).fetchall()
        ]
    assert failure_codes == ["RuntimeError", "ValidationError"]


def test_permissions_disabled_execution_and_cross_event_ids(database, service, scenario):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, human_update_interpretation_runtime=runtime))
    update = submit(client, scenario).json()
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/interpret"
    runtime.outputs[update["id"]] = interpretation(update["id"], scenario["event"].id)
    assert client.post(endpoint, headers=scenario["ah"], json={}).status_code == 403
    assert client.post(endpoint, headers=scenario["sh"], json={}).status_code == 403
    assert client.post(endpoint, json={}).status_code == 401
    other, _, _, _ = __import__(
        "tests.planning_foundation.work_helpers", fromlist=["create_approved_work"]
    ).create_approved_work(database, service, scenario["owner"])
    with database.connect() as connection:
        connection.execute(
            "INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')",
            (other.id, scenario["owner"]),
        )
    assert client.post(
        f"/events/{other.id}/human-updates/{update['id']}/interpret",
        headers=scenario["oh"],
        json={},
    ).status_code == 404
    disabled = TestClient(create_app(database))
    assert disabled.post(endpoint, headers=scenario["oh"], json={}).status_code == 422
    assert runtime.calls == []


def test_concurrent_interpret_actions_invoke_runtime_once(database, scenario):
    entered = Event()
    release = Event()
    calls = []

    class BlockingRuntime:
        def generate(self, *, event_id, update_id, organizer_id):
            calls.append(update_id)
            entered.set()
            assert release.wait(10)
            return interpretation(update_id, event_id)

    update = scenario["client"].post(
        f"/events/{scenario['event'].id}/human-updates",
        headers=scenario["ah"],
        json={"text": REPORT, "work_id": str(scenario["work"][0].id)},
    ).json()
    service = HumanUpdateInterpretationService(database)
    workflow = HumanUpdateInterpretationWorkflow(service, BlockingRuntime())

    def execute():
        return workflow.execute(
            event_id=scenario["event"].id,
            update_id=UUID(update["id"]),
            organizer_id=scenario["owner"],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(execute)
        assert entered.wait(10)
        second = pool.submit(execute)
        with pytest.raises(IdempotencyConflictError):
            second.result(timeout=10)
        release.set()
        result = first.result(timeout=10)
    assert result.update_id == UUID(update["id"])
    assert calls == [UUID(update["id"])]


@pytest.mark.real_bedrock
def test_real_nova_interprets_delay_completion_and_ambiguity(database, scenario):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    service = HumanUpdateInterpretationService(database)
    workflow = HumanUpdateInterpretationWorkflow(
        service, StrandsHumanUpdateInterpretationAgent(service)
    )
    scheduled_start = scenario["event"].starts_at.replace(hour=10, minute=0, second=0, microsecond=0)
    scheduled_end = scheduled_start + timedelta(hours=3)
    with database.connect() as connection:
        connection.execute(
            "UPDATE work_items SET starts_at = %s, ends_at = %s WHERE id = %s",
            (scheduled_start, scheduled_end, scenario["work"][0].id),
        )
        connection.execute(
            "UPDATE participations SET approved_start = %s, approved_end = %s "
            "WHERE event_id = %s AND account_id = %s",
            (scheduled_start, scheduled_end, scenario["event"].id, scenario["actor"]),
        )
    reports = [
        (REPORT, {"AVAILABILITY_CHANGE", "SCHEDULE_DELAY", "ACCESS_PROBLEM"}, True, False),
        (
            "Shoreline cleanup is finished and all bags have been moved to sorting.",
            {"COMPLETION_UPDATE"},
            False,
            False,
        ),
        ("It won't work.", {"UNKNOWN", "GENERAL_UPDATE"}, False, True),
    ]
    for text, allowed_types, possible_blocker, clarification in reports:
        update = scenario["client"].post(
            f"/events/{scenario['event'].id}/human-updates",
            headers=scenario["ah"],
            json={"text": text, "work_id": str(scenario["work"][0].id) if text != "It won't work." else None},
        ).json()
        result = workflow.execute(
            event_id=scenario["event"].id,
            update_id=update["id"],
            organizer_id=scenario["owner"],
        )
        assert result.interpretation_type.value in allowed_types
        assert result.possible_blocker is possible_blocker
        assert result.requires_clarification is clarification
        assert 0 <= result.confidence <= 1
        assert result.provider_name == "amazon-bedrock"
        assert result.model_id == "us.amazon.nova-2-lite-v1:0"
        if text == REPORT:
            signal = " ".join(
                part or ""
                for part in (
                    result.reported_condition,
                    result.temporal_signal,
                    result.location_signal,
                )
            ).lower()
            assert "11" in signal
            assert "road" in signal or "access" in signal or "block" in signal
