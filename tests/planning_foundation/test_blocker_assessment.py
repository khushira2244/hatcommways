from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from services.agent_runtime.blocker_assessment import (
    BlockerAssessmentWorkflow,
    StrandsBlockerAssessmentAgent,
)
from services.api import create_app
from services.planning_foundation.blocker_assessment_service import (
    BlockerAssessmentService,
)
from services.planning_foundation.errors import IdempotencyConflictError
from services.planning_foundation.human_update_interpretation_service import (
    HumanUpdateInterpretationService,
)
from services.planning_foundation.human_update_models import HumanUpdateInterpretation
from tests.planning_foundation.test_human_update_interpretation import (
    protected_state,
)
from tests.planning_foundation.test_human_updates_blockers import scenario as scenario_fixture


DELAY = "I can only arrive at 11 because the road is blocked."
COMPLETE = "Shoreline cleanup is finished and all bags have been moved to sorting."
AMBIGUOUS = "It won't work."


@pytest.fixture
def scenario(database, service):
    return scenario_fixture.__wrapped__(database, service)


def interpretation_payload(update_id, event_id, **changes):
    values = {
        "update_id": str(update_id),
        "event_id": str(event_id),
        "interpretation_type": "AVAILABILITY_CHANGE",
        "concise_summary": "Priya expects to arrive at 11 due to a blocked road.",
        "reported_condition": "Arrival is delayed by blocked road access.",
        "temporal_signal": "Arrival at 11 for work scheduled from 10 to 13",
        "location_signal": "Road access is blocked",
        "referenced_stage_id": None,
        "referenced_work_id": None,
        "possible_blocker": True,
        "blocker_reason": "Availability conflicts with the accepted work start.",
        "confidence": 0.91,
        "requires_clarification": False,
        "clarification_question": None,
    }
    values.update(changes)
    return values


def assessment_payload(update_id, event_id, interpretation_id, **changes):
    values = {
        "event_id": str(event_id),
        "human_update_id": str(update_id),
        "interpretation_id": str(interpretation_id),
        "is_execution_blocker": True,
        "blocker_kind": "AVAILABILITY",
        "concise_reason": "Accepted availability now conflicts with the work start.",
        "directly_referenced_stage_id": None,
        "directly_referenced_work_id": None,
        "severity_internal": "MEDIUM",
        "urgency_internal": "HIGH",
        "coordination_needed": True,
        "replanning_may_be_needed": True,
        "requires_clarification": False,
        "clarification_question": None,
        "confidence": 0.92,
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


def submit_and_interpret(database, scenario, assessment_runtime, *, text=DELAY, linked=True):
    interpretation_runtime = FakeRuntime()
    client = TestClient(
        create_app(
            database,
            human_update_interpretation_runtime=interpretation_runtime,
            blocker_assessment_runtime=assessment_runtime,
        )
    )
    update = client.post(
        f"/events/{scenario['event'].id}/human-updates",
        headers=scenario["ah"],
        json={
            "text": text,
            "work_id": str(scenario["work"][0].id) if linked else None,
        },
    ).json()
    if text == COMPLETE:
        semantic = {
            "interpretation_type": "COMPLETION_UPDATE",
            "concise_summary": "Cleanup is complete and bags moved to sorting.",
            "reported_condition": "The linked work is complete.",
            "temporal_signal": None,
            "location_signal": "Sorting",
            "possible_blocker": False,
            "blocker_reason": None,
            "confidence": 0.97,
        }
    elif text == AMBIGUOUS:
        semantic = {
            "interpretation_type": "UNKNOWN",
            "concise_summary": "An unspecified thing will not work.",
            "reported_condition": "The condition is not identified.",
            "temporal_signal": None,
            "location_signal": None,
            "possible_blocker": False,
            "blocker_reason": None,
            "requires_clarification": True,
            "clarification_question": "What is not working?",
            "confidence": 0.2,
        }
    else:
        semantic = {
            "referenced_stage_id": str(scenario["stage"].id),
            "referenced_work_id": str(scenario["work"][0].id),
        }
    interpretation_runtime.outputs[update["id"]] = interpretation_payload(
        update["id"], scenario["event"].id, **semantic
    )
    response = client.post(
        f"/events/{scenario['event'].id}/human-updates/{update['id']}/interpret",
        headers=scenario["oh"],
        json={},
    )
    assert response.status_code == 200, response.text
    return client, update, response.json(), interpretation_runtime


def test_assessment_is_explicit_typed_persisted_and_creates_one_deterministic_blocker(
    database, scenario
):
    runtime = FakeRuntime()
    client, update, interpretation, interpretation_runtime = submit_and_interpret(
        database, scenario, runtime
    )
    assert runtime.calls == []
    assert len(interpretation_runtime.calls) == 1
    before = protected_state(database, scenario["event"].id)
    with database.connect() as connection:
        immutable_interpretation = connection.execute(
            """SELECT interpretation_type,concise_summary,reported_condition,temporal_signal,
                      location_signal,possible_blocker,blocker_reason,confidence,
                      requires_clarification,clarification_question,provider_name,model_id,
                      agent_name,agent_version,created_at
               FROM human_update_interpretations WHERE id=%s""",
            (interpretation["id"],),
        ).fetchone()
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"],
        scenario["event"].id,
        interpretation["id"],
        directly_referenced_stage_id=str(scenario["stage"].id),
        directly_referenced_work_id=str(scenario["work"][0].id),
    )
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker"
    response = client.post(endpoint, headers=scenario["oh"], json={})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["is_execution_blocker"] is True
    assert result["provider_name"] == "test-runtime"
    assert result["agent_name"] == "hatcommways-blocker-assessment-agent"
    assert result["authoritative_blocker_id"]
    blocker = client.get(
        f"/events/{scenario['event'].id}/blockers", headers=scenario["oh"]
    ).json()
    assert len(blocker) == 1
    assert blocker[0]["id"] == result["authoritative_blocker_id"]
    assert (blocker[0]["handling_state"], blocker[0]["condition_state"]) == (
        "ACKNOWLEDGED",
        "OPEN",
    )
    assert blocker[0]["category"] == "AVAILABILITY"
    assert client.get(
        endpoint.replace("assess-blocker", "blocker-assessment"),
        headers=scenario["oh"],
    ).json()["id"] == result["id"]
    replay = client.post(endpoint, headers=scenario["oh"], json={})
    assert replay.json()["id"] == result["id"]
    assert len(runtime.calls) == 1
    assert protected_state(database, scenario["event"].id) == before
    with database.connect() as connection:
        assert connection.execute(
            "SELECT count(*) FROM blocker_assessments WHERE human_update_id=%s",
            (update["id"],),
        ).fetchone()["count"] == 1
        assert connection.execute(
            "SELECT original_text FROM human_updates WHERE id=%s", (update["id"],)
        ).fetchone()["original_text"] == DELAY
        current_interpretation = connection.execute(
            """SELECT interpretation_type,concise_summary,reported_condition,temporal_signal,
                      location_signal,possible_blocker,blocker_reason,confidence,
                      requires_clarification,clarification_question,provider_name,model_id,
                      agent_name,agent_version,created_at
               FROM human_update_interpretations WHERE id=%s""",
            (interpretation["id"],),
        ).fetchone()
        assessment_events = [
            row["event_type"]
            for row in connection.execute(
                """SELECT event_type FROM domain_outbox
                   WHERE event_type LIKE 'blocker_assessment.%'
                   ORDER BY occurred_at"""
            ).fetchall()
        ]
    assert current_interpretation == immutable_interpretation
    assert assessment_events == [
        "blocker_assessment.requested",
        "blocker_assessment.assessed",
    ]


def test_scoped_context_has_only_direct_facts_and_no_dependency_graph(database, scenario):
    runtime = FakeRuntime()
    client, update, interpretation, _ = submit_and_interpret(database, scenario, runtime)
    meeting = client.post(
        f"/events/{scenario['event'].id}/meetings",
        headers=scenario["oh"],
        json={
            "title": "Shoreline check-in",
            "meeting_type": "CHECK_IN",
            "start_time": scenario["work"][0].starts_at.isoformat(),
            "end_time": (scenario["work"][0].starts_at + timedelta(minutes=15)).isoformat(),
            "audience": "WORK",
            "stage_id": str(scenario["stage"].id),
            "work_id": str(scenario["work"][0].id),
        },
    )
    assert meeting.status_code == 201, meeting.text
    context = BlockerAssessmentService(database).context(
        scenario["event"].id, update["id"], scenario["owner"]
    ).model_dump()
    assert context["original_text"] == DELAY
    assert context["interpretation"]["id"] == UUID(interpretation["id"])
    assert "provider_name" not in context["interpretation"]
    assert "blocker_assessment_status" not in context["interpretation"]
    assert context["work"]["id"] == scenario["work"][0].id
    assert context["accepted_participation"]["id"] == scenario["participation"]["id"]
    assert [item["title"] for item in context["directly_relevant_meetings"]] == [
        "Shoreline check-in"
    ]
    serialized = str(context)
    assert str(scenario["work"][1].id) not in serialized
    assert str(scenario["other_stage"].id) not in serialized
    assert "dependencies" not in serialized.lower()


@pytest.mark.parametrize(
    ("text", "linked", "assessment_changes", "expected_clarification"),
    [
        (
            COMPLETE,
            True,
            {
                "is_execution_blocker": False,
                "blocker_kind": "NONE",
                "concise_reason": "The linked work is reported complete.",
                "severity_internal": "LOW",
                "urgency_internal": "LOW",
                "coordination_needed": False,
                "replanning_may_be_needed": False,
                "confidence": 0.96,
            },
            False,
        ),
        (
            AMBIGUOUS,
            False,
            {
                "is_execution_blocker": False,
                "blocker_kind": "NONE",
                "concise_reason": "The report lacks enough detail for impact assessment.",
                "severity_internal": "LOW",
                "urgency_internal": "LOW",
                "coordination_needed": False,
                "replanning_may_be_needed": False,
                "requires_clarification": True,
                "clarification_question": "What is not working?",
                "confidence": 0.2,
            },
            True,
        ),
    ],
)
def test_non_blocker_and_ambiguous_assessments_create_no_blocker(
    database, scenario, text, linked, assessment_changes, expected_clarification
):
    runtime = FakeRuntime()
    client, update, interpretation, _ = submit_and_interpret(
        database, scenario, runtime, text=text, linked=linked
    )
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"], scenario["event"].id, interpretation["id"], **assessment_changes
    )
    result = client.post(
        f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker",
        headers=scenario["oh"],
        json={},
    ).json()
    assert result["is_execution_blocker"] is False
    assert result["blocker_kind"] == "NONE"
    assert result["requires_clarification"] is expected_clarification
    assert result["authoritative_blocker_id"] is None
    assert client.get(
        f"/events/{scenario['event'].id}/blockers", headers=scenario["oh"]
    ).json() == []


def test_requires_interpretation_and_failure_retry_is_safe(database, scenario):
    runtime = FakeRuntime()
    client = TestClient(create_app(database, blocker_assessment_runtime=runtime))
    update = client.post(
        f"/events/{scenario['event'].id}/human-updates",
        headers=scenario["ah"],
        json={"text": DELAY, "work_id": str(scenario["work"][0].id)},
    ).json()
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker"
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 422
    assert runtime.calls == []

    client, update, interpretation, _ = submit_and_interpret(database, scenario, runtime)
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker"
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"],
        scenario["event"].id,
        interpretation["id"],
        directly_referenced_work_id=str(uuid4()),
    )
    invalid = client.post(endpoint, headers=scenario["oh"], json={})
    assert invalid.status_code == 422
    with database.connect() as connection:
        state = connection.execute(
            """SELECT blocker_assessment_status,blocker_assessment_failure_code,
                      blocker_assessment_attempt_count
               FROM human_update_interpretations WHERE id=%s""",
            (interpretation["id"],),
        ).fetchone()
        assert connection.execute("SELECT count(*) FROM blocker_assessments").fetchone()[
            "count"
        ] == 0
        assert connection.execute("SELECT count(*) FROM blockers").fetchone()["count"] == 0
    assert state == {
        "blocker_assessment_status": "FAILED",
        "blocker_assessment_failure_code": "ValidationError",
        "blocker_assessment_attempt_count": 1,
    }
    assert client.post(endpoint, headers=scenario["oh"], json={}).status_code == 409
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"],
        scenario["event"].id,
        interpretation["id"],
        is_execution_blocker=False,
        blocker_kind="NONE",
        coordination_needed=False,
        replanning_may_be_needed=False,
        severity_internal="LOW",
        urgency_internal="LOW",
    )
    retried = client.post(endpoint, headers=scenario["oh"], json={"retry": True})
    assert retried.status_code == 200, retried.text
    with database.connect() as connection:
        assert connection.execute(
            "SELECT blocker_assessment_attempt_count FROM human_update_interpretations WHERE id=%s",
            (interpretation["id"],),
        ).fetchone()["blocker_assessment_attempt_count"] == 2


def test_runtime_or_contradictory_output_persists_no_assessment_or_blocker(database, scenario):
    runtime = FakeRuntime()
    client, update, interpretation, _ = submit_and_interpret(database, scenario, runtime)
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker"
    runtime.error = RuntimeError("provider returned private details")
    with pytest.raises(RuntimeError):
        client.post(endpoint, headers=scenario["oh"], json={})
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM blocker_assessments").fetchone()[
            "count"
        ] == 0
        assert connection.execute("SELECT count(*) FROM blockers").fetchone()["count"] == 0

    runtime.error = None
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"],
        scenario["event"].id,
        interpretation["id"],
        is_execution_blocker=False,
        blocker_kind="ACCESS",
    )
    with pytest.raises(Exception):
        client.post(endpoint, headers=scenario["oh"], json={"retry": True})
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM blocker_assessments").fetchone()[
            "count"
        ] == 0
        assert connection.execute("SELECT count(*) FROM blockers").fetchone()["count"] == 0


@pytest.mark.parametrize(
    "invalid_field",
    ["event_id", "human_update_id", "interpretation_id", "directly_referenced_stage_id"],
)
def test_invalid_assessment_identity_or_scope_is_rejected(
    database, scenario, invalid_field
):
    runtime = FakeRuntime()
    client, update, interpretation, _ = submit_and_interpret(database, scenario, runtime)
    output = assessment_payload(
        update["id"], scenario["event"].id, interpretation["id"]
    )
    output[invalid_field] = str(uuid4())
    runtime.outputs[update["id"]] = output
    response = client.post(
        f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker",
        headers=scenario["oh"],
        json={},
    )
    assert response.status_code == 422
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM blocker_assessments").fetchone()[
            "count"
        ] == 0
        assert connection.execute("SELECT count(*) FROM blockers").fetchone()["count"] == 0

def test_existing_blocker_is_reused_and_permissions_and_disabled_execution_hold(
    database, service, scenario
):
    runtime = FakeRuntime()
    client, update, interpretation, _ = submit_and_interpret(database, scenario, runtime)
    existing = client.post(
        f"/events/{scenario['event'].id}/blockers",
        headers=scenario["oh"],
        json={
            "human_update_id": update["id"],
            "title": "Organizer-reviewed access issue",
            "summary": "Road access delays the accepted participant.",
        },
    ).json()
    runtime.outputs[update["id"]] = assessment_payload(
        update["id"], scenario["event"].id, interpretation["id"]
    )
    endpoint = f"/events/{scenario['event'].id}/human-updates/{update['id']}/assess-blocker"
    assert client.post(endpoint, headers=scenario["ah"], json={}).status_code == 403
    assert client.post(endpoint, headers=scenario["sh"], json={}).status_code == 403
    assert client.post(endpoint, json={}).status_code == 401
    result = client.post(endpoint, headers=scenario["oh"], json={}).json()
    assert result["authoritative_blocker_id"] == existing["id"]
    assert len(client.get(
        f"/events/{scenario['event'].id}/blockers", headers=scenario["oh"]
    ).json()) == 1

    disabled = TestClient(create_app(database))
    assert disabled.post(endpoint, headers=scenario["oh"], json={}).status_code == 422


def test_concurrent_assessment_invokes_runtime_once(database, scenario):
    setup_runtime = FakeRuntime()
    _, update, interpretation, _ = submit_and_interpret(database, scenario, setup_runtime)
    entered = Event()
    release = Event()
    calls = []

    class BlockingRuntime:
        def generate(self, *, event_id, update_id, organizer_id):
            calls.append(update_id)
            entered.set()
            assert release.wait(10)
            return assessment_payload(update_id, event_id, interpretation["id"])

    workflow = BlockerAssessmentWorkflow(
        BlockerAssessmentService(database), BlockingRuntime()
    )

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
    assert result.human_update_id == UUID(update["id"])
    assert calls == [UUID(update["id"])]
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM blocker_assessments").fetchone()[
            "count"
        ] == 1
        assert connection.execute("SELECT count(*) FROM blockers").fetchone()["count"] == 1


@pytest.mark.real_bedrock
def test_real_nova_assesses_blocker_completion_and_ambiguity(database, scenario):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    scheduled_start = scenario["event"].starts_at.replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    scheduled_end = scheduled_start + timedelta(hours=3)
    with database.connect() as connection:
        connection.execute(
            "UPDATE work_items SET starts_at=%s,ends_at=%s WHERE id=%s",
            (scheduled_start, scheduled_end, scenario["work"][0].id),
        )
        connection.execute(
            """UPDATE participations SET approved_start=%s,approved_end=%s
               WHERE event_id=%s AND account_id=%s""",
            (scheduled_start, scheduled_end, scenario["event"].id, scenario["actor"]),
        )

    assessment_service = BlockerAssessmentService(database)
    workflow = BlockerAssessmentWorkflow(
        assessment_service, StrandsBlockerAssessmentAgent(assessment_service)
    )
    cases = [
        (DELAY, True, False),
        (COMPLETE, False, False),
        (AMBIGUOUS, False, True),
    ]
    for text, expected_blocker, expected_clarification in cases:
        linked = text != AMBIGUOUS
        update = scenario["client"].post(
            f"/events/{scenario['event'].id}/human-updates",
            headers=scenario["ah"],
            json={
                "text": text,
                "work_id": str(scenario["work"][0].id) if linked else None,
            },
        ).json()
        interpretation_service = HumanUpdateInterpretationService(database)
        interpretation_service.begin(
            scenario["event"].id, update["id"], scenario["owner"], retry=False
        )
        if text == COMPLETE:
            semantic = {
                "interpretation_type": "COMPLETION_UPDATE",
                "concise_summary": "Cleanup is complete and bags moved to sorting.",
                "reported_condition": "The linked work is complete.",
                "temporal_signal": None,
                "location_signal": "Sorting",
                "possible_blocker": False,
                "blocker_reason": None,
                "confidence": 0.97,
            }
        elif text == AMBIGUOUS:
            semantic = {
                "interpretation_type": "UNKNOWN",
                "concise_summary": "An unspecified thing will not work.",
                "reported_condition": "The condition is not identified.",
                "temporal_signal": None,
                "location_signal": None,
                "possible_blocker": False,
                "blocker_reason": None,
                "requires_clarification": True,
                "clarification_question": "What is not working?",
                "confidence": 0.2,
            }
        else:
            semantic = {
                "referenced_stage_id": str(scenario["stage"].id),
                "referenced_work_id": str(scenario["work"][0].id),
            }
        interpretation = HumanUpdateInterpretation.model_validate(
            interpretation_payload(update["id"], scenario["event"].id, **semantic)
        )
        persisted = interpretation_service.complete(
            scenario["event"].id,
            update["id"],
            scenario["owner"],
            interpretation,
            provider_name="deterministic-test-setup",
            model_id="typed-fixture",
            agent_name="test-interpretation-setup",
            agent_version="v1",
            stop_reason="typed-fixture",
            usage={},
        )
        result = workflow.execute(
            event_id=scenario["event"].id,
            update_id=update["id"],
            organizer_id=scenario["owner"],
        )
        assert result.interpretation_id == persisted.id
        assert result.is_execution_blocker is expected_blocker
        assert result.requires_clarification is expected_clarification
        assert result.provider_name == "amazon-bedrock"
        assert result.model_id == "us.amazon.nova-2-lite-v1:0"
        if text == DELAY:
            assert result.blocker_kind.value in {"AVAILABILITY", "ACCESS", "SCHEDULE"}
            assert result.directly_referenced_work_id == scenario["work"][0].id
            assert result.coordination_needed is True
            assert result.authoritative_blocker_id is not None
        else:
            assert result.blocker_kind.value == "NONE"
            assert result.authoritative_blocker_id is None
            if text == AMBIGUOUS:
                assert result.directly_referenced_stage_id is None
                assert result.directly_referenced_work_id is None
    with database.connect() as connection:
        blockers = connection.execute(
            "SELECT handling_state,condition_state FROM blockers WHERE event_id=%s",
            (scenario["event"].id,),
        ).fetchall()
    assert blockers == [{"handling_state": "ACKNOWLEDGED", "condition_state": "OPEN"}]
