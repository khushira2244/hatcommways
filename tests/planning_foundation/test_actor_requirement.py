from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest

from services.agent_runtime.actor_requirement import ActorRequirementWorkflow
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.actor_requirement_validation import ActorRequirementValidator
from services.planning_foundation.errors import (
    AuthorizationError,
    StaleProposalError,
    ValidationError,
)
from services.planning_foundation.models import (
    ActorRequirementProposal,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
)
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.work_helpers import create_approved_work


def actor_payload(event, stage, work, proposal_id=None):
    return {
        "proposal_id": str(proposal_id or uuid4()),
        "event_id": str(event.id),
        "stage_id": str(stage.id),
        "work_id": str(work.id),
        "base_event_version": event.version,
        "base_stage_version": stage.version,
        "base_work_version": work.version,
        "proposed_requirements": [
            {
                "role_category": "EXECUTION",
                "canonical_role_name": "Site Assessor",
                "responsibility_summary": "Inspect the area and record preparation needs",
                "minimum_required_count": 1,
                "relevant_capabilities": ["site observation", "clear documentation"],
                "rough_effort_expectation": "Approximately four person-hours",
                "rationale": "The assessment work requires a clear accountable execution role",
            },
            {
                "role_category": "REVIEW_VALIDATION",
                "canonical_role_name": "Assessment Reviewer",
                "responsibility_summary": "Review the assessment for completeness",
                "minimum_required_count": 0,
                "relevant_capabilities": ["quality review"],
                "rough_effort_expectation": "A short review near completion",
                "rationale": "Optional review can improve the preparation record",
            },
        ],
        "assumptions": ["The organizer will confirm whether optional review is needed"],
        "concise_rationale": "Execution and optional review cover this work baseline.",
        "approval_required": True,
    }


def pending_actor_plan(database, base_service, organizer_id):
    event, stage, work, unrelated_stage = create_approved_work(
        database, base_service, organizer_id
    )
    service = ActorRequirementService(database)
    target = work[0]
    request = service.request_actor_requirements(
        event_id=event.id,
        stage_id=stage.id,
        work_id=target.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stage.version,
        expected_work_version=target.version,
        idempotency_key=f"actor-request-{uuid4()}",
    )
    service.begin_request(request.id)
    proposal = ActorRequirementProposal.model_validate(
        actor_payload(event, stage, target)
    )
    completed = service.complete_request(request.id, proposal)
    return service, event, stage, work, unrelated_stage, completed, proposal


def decision(proposal_id, organizer_id, action, *, key=None, edited=None):
    return ProposalDecisionCommand(
        proposal_id=proposal_id,
        organizer_id=organizer_id,
        decision=action,
        decision_idempotency_key=key or f"actor-decision-{uuid4()}",
        edited_payload=edited,
    )


def test_only_authoritative_target_work_is_eligible(database, service, organizer_id):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    actor_service = ActorRequirementService(database)
    request = actor_service.request_actor_requirements(
        event_id=event.id, stage_id=stage.id, work_id=work[0].id,
        organizer_id=organizer_id, expected_event_version=event.version,
        expected_stage_version=stage.version, expected_work_version=work[0].version,
        idempotency_key="eligible-actor-request",
    )
    assert request.work_id == work[0].id
    with pytest.raises(StaleProposalError):
        actor_service.request_actor_requirements(
            event_id=event.id, stage_id=stage.id, work_id=work[1].id,
            organizer_id=organizer_id, expected_event_version=event.version,
            expected_stage_version=stage.version, expected_work_version=99,
            idempotency_key="stale-actor-request",
        )


def test_scoped_tool_exposes_only_target_work(database, service, organizer_id):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    tools = ScopedPlanningReadTools(service)
    context = tools.get_work_actor_context(
        event_id=event.id, stage_id=stage.id, work_id=work[0].id,
        organizer_id=organizer_id, expected_event_version=event.version,
        expected_stage_version=stage.version, expected_work_version=work[0].version,
    )
    assert context.work_id == work[0].id
    assert context.work_id != work[1].id
    assert "organizer_id" not in context.model_dump()
    assert "participant" not in " ".join(context.model_dump()).lower()
    with pytest.raises(AuthorizationError):
        tools.get_work_actor_context(
            event_id=event.id, stage_id=stage.id, work_id=work[0].id,
            organizer_id=uuid4(), expected_event_version=event.version,
            expected_stage_version=stage.version, expected_work_version=work[0].version,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["proposed_requirements"][0].update(role_category="UNKNOWN"),
        lambda p: p["proposed_requirements"][0].update(minimum_required_count=-1),
        lambda p: p["proposed_requirements"][0].update(participant_id=str(uuid4())),
        lambda p: p["proposed_requirements"][0].update(capability_score=0.9),
        lambda p: p["proposed_requirements"][0].update(
            rationale="Choose based on gender for this responsibility"
        ),
        lambda p: p.update(work_mutation={"canonical_name": "Changed"}),
    ],
    ids=["category", "count", "person", "scoring", "protected-trait", "work-mutation"],
)
def test_invalid_actor_requirement_output_rejected(
    database, service, organizer_id, mutate
):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    payload = actor_payload(event, stage, work[0])
    mutate(payload)
    with pytest.raises(ValidationError):
        ActorRequirementValidator().parse_and_validate(
            payload, event, stage, work[0]
        )


def test_zero_count_and_empty_organizer_edit_are_valid(
    database, service, organizer_id
):
    actor_service, event, stage, work, _, completed, proposal = pending_actor_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_requirements"] = []
    result = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE, edited=edited)
    )
    assert result.status == ProposalStatus.APPROVED
    assert result.requirements == []


def test_protected_trait_guard_does_not_match_age_inside_management(
    database, service, organizer_id
):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    payload = actor_payload(event, stage, work[0])
    payload["proposed_requirements"][0]["responsibility_summary"] = (
        "Manage staging and equipment preparation"
    )
    ActorRequirementValidator().parse_and_validate(payload, event, stage, work[0])


def test_rejection_creates_no_requirements(database, service, organizer_id):
    actor_service, _, _, work, _, completed, _ = pending_actor_plan(
        database, service, organizer_id
    )
    result = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.REJECT)
    )
    assert result.status == ProposalStatus.REJECTED
    assert actor_service.list_requirements(work[0].id) == []


def test_organizer_edit_is_revalidated(database, service, organizer_id):
    actor_service, _, _, work, _, completed, proposal = pending_actor_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_requirements"][0]["minimum_required_count"] = -1
    with pytest.raises(ValidationError):
        actor_service.decide_actor_requirements(
            decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE, edited=edited)
        )
    assert actor_service.list_requirements(work[0].id) == []


@pytest.mark.parametrize("aggregate", ["event", "stage", "work"])
def test_stale_actor_requirement_proposal_rejected(
    database, service, organizer_id, aggregate
):
    actor_service, event, stage, work, _, completed, _ = pending_actor_plan(
        database, service, organizer_id
    )
    table, identifier = {
        "event": ("events", event.id),
        "stage": ("stages", stage.id),
        "work": ("work_items", work[0].id),
    }[aggregate]
    with database.connect() as connection:
        connection.execute(
            f"UPDATE {table} SET version = version + 1 WHERE id = %s", (identifier,)
        )
    result = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE)
    )
    assert result.status == ProposalStatus.STALE
    assert actor_service.list_requirements(work[0].id) == []


def test_duplicate_approval_applies_once_and_preserves_unrelated_work(
    database, service, organizer_id
):
    actor_service, _, _, work, unrelated_stage, completed, _ = pending_actor_plan(
        database, service, organizer_id
    )
    key = "same-actor-decision"
    first = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE, key=key)
    )
    second = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE, key=key)
    )
    assert len(first.requirements) == 2
    assert second.duplicate is True
    assert len(actor_service.list_requirements(work[0].id)) == 2
    assert actor_service.list_requirements(work[1].id) == []
    with database.connect() as connection:
        unrelated = connection.execute(
            "SELECT version FROM stages WHERE id=%s", (unrelated_stage.id,)
        ).fetchone()
    assert unrelated["version"] == unrelated_stage.version


def test_sibling_work_actor_proposals_can_be_confirmed_as_one_stage_structure(
    database, service, organizer_id
):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    actor_service = ActorRequirementService(database)
    proposal_ids = []
    for index, target in enumerate(work):
        request = actor_service.request_actor_requirements(
            event_id=event.id, stage_id=stage.id, work_id=target.id,
            organizer_id=organizer_id, expected_event_version=event.version,
            expected_stage_version=stage.version, expected_work_version=target.version,
            idempotency_key=f"sibling-actor-request-{index}",
        )
        actor_service.begin_request(request.id)
        proposal = ActorRequirementProposal.model_validate(
            actor_payload(event, stage, target)
        )
        completed = actor_service.complete_request(request.id, proposal)
        proposal_ids.append(completed.proposal_id)

    results = [
        actor_service.decide_actor_requirements(
            decision(proposal_id, organizer_id, ProposalDecision.APPROVE)
        )
        for proposal_id in proposal_ids
    ]

    assert all(result.status == ProposalStatus.APPROVED for result in results)
    assert [len(actor_service.list_requirements(target.id)) for target in work] == [2, 2]


class FailingRuntime:
    def generate(self, **kwargs):
        raise RuntimeError("simulated Bedrock or scoped-tool failure")


def test_runtime_failure_changes_no_authoritative_state(database, service, organizer_id):
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    actor_service = ActorRequirementService(database)
    request = actor_service.request_actor_requirements(
        event_id=event.id, stage_id=stage.id, work_id=work[0].id,
        organizer_id=organizer_id, expected_event_version=event.version,
        expected_stage_version=stage.version, expected_work_version=work[0].version,
        idempotency_key="failing-actor-runtime",
    )
    with pytest.raises(RuntimeError):
        ActorRequirementWorkflow(actor_service, FailingRuntime()).execute(request.id)
    assert actor_service.list_requirements(work[0].id) == []
    assert actor_service.get_request(request.id).status.value == "FAILED"


def test_application_and_outbox_are_atomic(database, service, organizer_id, monkeypatch):
    actor_service, _, _, work, _, completed, _ = pending_actor_plan(
        database, service, organizer_id
    )

    def fail(_connection):
        raise RuntimeError("simulated outbox failure")

    monkeypatch.setattr(actor_service, "_before_requirement_approval_outbox", fail)
    with pytest.raises(RuntimeError):
        actor_service.decide_actor_requirements(
            decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE)
        )
    assert actor_service.list_requirements(work[0].id) == []
    assert service.get_proposal(completed.proposal_id).status == ProposalStatus.PENDING


def test_success_persists_exact_requirements_and_outbox(
    database, service, organizer_id
):
    actor_service, _, _, work, _, completed, proposal = pending_actor_plan(
        database, service, organizer_id
    )
    result = actor_service.decide_actor_requirements(
        decision(completed.proposal_id, organizer_id, ProposalDecision.APPROVE)
    )
    assert result.status == ProposalStatus.APPROVED
    assert [r.canonical_role_name for r in result.requirements] == [
        "Site Assessor", "Assessment Reviewer"
    ]
    assert [r.minimum_required_count for r in result.requirements] == [1, 0]
    with database.connect() as connection:
        events = connection.execute(
            "SELECT event_type FROM domain_outbox WHERE correlation_id=%s",
            (completed.correlation_id,),
        ).fetchall()
    event_types = [row["event_type"] for row in events]
    assert "work.actor_requirements_requested" in event_types
    assert "work.actor_requirements_proposed" in event_types
    assert "work.actor_requirements_approved" in event_types
    assert event_types.count("actor_requirement.created") == len(
        proposal.proposed_requirements
    )
