from __future__ import annotations

from uuid import uuid4

import pytest

from services.agent_runtime.work_design import WorkDesignWorkflow
from services.planning_foundation.errors import (
    AuthorizationError,
    NotFoundError,
    StaleProposalError,
    ValidationError,
)
from services.planning_foundation.models import (
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
    WorkDecompositionProposal,
)
from services.planning_foundation.tools import ScopedPlanningReadTools
from services.planning_foundation.work_design_service import WorkDesignService
from services.planning_foundation.work_validation import (
    WorkDecompositionValidator,
    calculate_work_shares,
)
from tests.planning_foundation.work_helpers import (
    create_approved_stages,
    make_work_proposal,
    work_plan_payload,
)


def pending_work_plan(database, base_service, organizer_id):
    event, stages = create_approved_stages(database, base_service, organizer_id)
    service = WorkDesignService(database)
    stage = stages[0]
    request = service.request_work_design(
        event_id=event.id,
        stage_id=stage.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stage.version,
        idempotency_key=f"work-request-{uuid4()}",
    )
    service.begin_request(request.id)
    proposal = make_work_proposal(event, stage)
    completed = service.complete_request(request.id, proposal)
    return service, event, stages, completed, proposal


def decide(proposal_id, organizer_id, decision, *, key=None, edited_payload=None):
    return ProposalDecisionCommand(
        proposal_id=proposal_id,
        organizer_id=organizer_id,
        decision=decision,
        decision_idempotency_key=key or f"work-decision-{uuid4()}",
        edited_payload=edited_payload,
    )


def test_agent_work_shares_are_derived_from_person_hours():
    payload = {
        "proposal_id": str(uuid4()),
        "event_id": str(uuid4()),
        "stage_id": str(uuid4()),
        "base_event_version": 1,
        "base_stage_version": 1,
        "proposed_work": [
            {
                "temporary_work_ref": ref,
                "canonical_name": ref,
                "purpose": "A valid proposed work purpose",
                "estimated_person_hours": effort,
                "work_share": 1,
                "proposed_start": "2026-09-05T08:00:00Z",
                "proposed_end": "2026-09-05T09:00:00Z",
                "dependencies": [],
            }
            for ref, effort in (("a", 1), ("b", 1), ("c", 1))
        ],
        "assumptions": [],
        "concise_rationale": "A valid concise rationale",
        "approval_required": True,
    }
    proposal = calculate_work_shares(WorkDecompositionProposal.model_validate(payload))

    assert [item.work_share for item in proposal.proposed_work] == [33.33, 33.33, 33.34]
    assert sum(item.work_share for item in proposal.proposed_work) == 100


def test_only_approved_targeted_stage_is_eligible(database, service, organizer_id):
    event, stages = create_approved_stages(database, service, organizer_id)
    work_service = WorkDesignService(database)
    request = work_service.request_work_design(
        event_id=event.id,
        stage_id=stages[0].id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stages[0].version,
        idempotency_key="eligible-work-request",
    )
    assert request.stage_id == stages[0].id
    with pytest.raises(NotFoundError):
        work_service.request_work_design(
            event_id=event.id,
            stage_id=uuid4(),
            organizer_id=organizer_id,
            expected_event_version=event.version,
            expected_stage_version=1,
            idempotency_key="unapproved-stage",
        )


def test_scoped_tool_exposes_only_target_stage(database, service, organizer_id):
    event, stages = create_approved_stages(database, service, organizer_id)
    context = ScopedPlanningReadTools(service).get_stage_work_context(
        event_id=event.id,
        stage_id=stages[0].id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stages[0].version,
    )
    assert context.stage_id == stages[0].id
    assert context.stage_id != stages[1].id
    assert set(context.model_dump()) == {
        "event_id", "event_name", "event_purpose", "event_type", "event_version",
        "stage_id", "stage_name", "stage_purpose", "stage_start", "stage_end",
        "stage_version",
    }
    with pytest.raises(AuthorizationError):
        ScopedPlanningReadTools(service).get_stage_work_context(
            event_id=event.id,
            stage_id=stages[0].id,
            organizer_id=uuid4(),
            expected_event_version=event.version,
            expected_stage_version=stages[0].version,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload, event, stage: payload.update(proposed_work=[]),
        lambda payload, event, stage: payload["proposed_work"][1].update(
            temporary_work_ref="work-1"
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            proposed_end=stage.starts_at.isoformat()
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            dependencies=["work-2"]
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            work_share=40
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            participant_assignments=["person-1"]
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            actor_requirements=[{"role": "field"}]
        ),
        lambda payload, event, stage: payload["proposed_work"][0].update(
            purpose="Use the confirmed equipment for preparation"
        ),
        lambda payload, event, stage: payload.update(
            stage_mutation={"canonical_name": "Changed"}
        ),
    ],
    ids=[
        "empty", "duplicate-ref", "invalid-time", "cycle", "work-share",
        "participant", "actor-requirement", "fabricated-resource", "stage-mutation",
    ],
)
def test_invalid_work_proposals_rejected(
    database, service, organizer_id, mutate
):
    event, stages = create_approved_stages(database, service, organizer_id)
    payload = work_plan_payload(event, stages[0])
    mutate(payload, event, stages[0])
    with pytest.raises(ValidationError):
        WorkDecompositionValidator().parse_and_validate(
            payload, event, stages[0]
        )


def test_organizer_rejection_creates_no_work(database, service, organizer_id):
    work_service, event, stages, request, proposal = pending_work_plan(
        database, service, organizer_id
    )
    result = work_service.decide_work_decomposition(
        decide(request.proposal_id, organizer_id, ProposalDecision.REJECT)
    )
    assert result.status == ProposalStatus.REJECTED
    assert work_service.list_work(stages[0].id) == []
    assert service.get_event(event.id).version == event.version


def test_organizer_edit_is_revalidated(database, service, organizer_id):
    work_service, event, stages, request, proposal = pending_work_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_work"][0]["work_share"] = 50
    with pytest.raises(ValidationError):
        work_service.decide_work_decomposition(
            decide(
                request.proposal_id,
                organizer_id,
                ProposalDecision.APPROVE,
                edited_payload=edited,
            )
        )
    assert work_service.list_work(stages[0].id) == []


@pytest.mark.parametrize("stale_target", ["event", "stage"])
def test_stale_event_or_stage_rejected(
    database, service, organizer_id, stale_target
):
    work_service, event, stages, request, proposal = pending_work_plan(
        database, service, organizer_id
    )
    if stale_target == "event":
        service.update_event_direct(
            event_id=event.id,
            organizer_id=organizer_id,
            expected_version=event.version,
            changes={"purpose": "Newer organizer event state"},
        )
    else:
        with database.connect() as connection:
            connection.execute(
                "UPDATE stages SET version = version + 1 WHERE id = %s",
                (stages[0].id,),
            )
    result = work_service.decide_work_decomposition(
        decide(request.proposal_id, organizer_id, ProposalDecision.APPROVE)
    )
    assert result.status == ProposalStatus.STALE
    assert work_service.list_work(stages[0].id) == []


def test_success_duplicate_and_unrelated_stage_preserved(
    database, service, organizer_id
):
    work_service, event, stages, request, proposal = pending_work_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_work"][0]["canonical_name"] = "Organizer Area Assessment"
    key = "approve-work-once"
    first = work_service.decide_work_decomposition(
        decide(
            request.proposal_id,
            organizer_id,
            ProposalDecision.APPROVE,
            key=key,
            edited_payload=edited,
        )
    )
    second = work_service.decide_work_decomposition(
        decide(
            request.proposal_id,
            organizer_id,
            ProposalDecision.APPROVE,
            key=key,
        )
    )
    assert [item.canonical_name for item in first.work] == [
        "Organizer Area Assessment", "Site Preparation"
    ]
    assert sum(item.work_share for item in first.work) == pytest.approx(100)
    assert first.work[1].dependency_work_ids == [first.work[0].id]
    assert first.event_version == event.version + 1
    assert first.stage_version == stages[0].version + 1
    assert second.duplicate is True
    assert len(work_service.list_work(stages[0].id)) == 2
    assert work_service.list_work(stages[1].id) == []
    assert work_service.get_stage(stages[1].id).version == stages[1].version


def test_work_application_and_outbox_are_atomic(
    database, service, organizer_id, monkeypatch
):
    work_service, event, stages, request, proposal = pending_work_plan(
        database, service, organizer_id
    )

    def fail_before_outbox(connection):
        raise RuntimeError("simulated work outbox failure")

    monkeypatch.setattr(work_service, "_before_work_approval_outbox", fail_before_outbox)
    with pytest.raises(RuntimeError, match="work outbox failure"):
        work_service.decide_work_decomposition(
            decide(request.proposal_id, organizer_id, ProposalDecision.APPROVE)
        )
    assert work_service.list_work(stages[0].id) == []
    assert service.get_event(event.id).version == event.version
    assert work_service.get_stage(stages[0].id).version == stages[0].version
    assert service.get_proposal(request.proposal_id).status == ProposalStatus.PENDING


class FreeFormRuntime:
    def generate(self, **kwargs):
        return "Unstructured work suggestions"


class FailingRuntime:
    def generate(self, **kwargs):
        raise RuntimeError("simulated Bedrock or scoped-tool failure")


@pytest.mark.parametrize("runtime", [FreeFormRuntime(), FailingRuntime()])
def test_runtime_failure_changes_no_authoritative_state(
    database, service, organizer_id, runtime
):
    event, stages = create_approved_stages(database, service, organizer_id)
    work_service = WorkDesignService(database)
    request = work_service.request_work_design(
        event_id=event.id,
        stage_id=stages[0].id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stages[0].version,
        idempotency_key=f"failed-work-runtime-{uuid4()}",
    )
    with pytest.raises((ValidationError, RuntimeError)):
        WorkDesignWorkflow(work_service, runtime).execute(request.id)
    assert work_service.list_work(stages[0].id) == []
    assert service.get_event(event.id).version == event.version
    assert work_service.get_request(request.id).status.value == "FAILED"
