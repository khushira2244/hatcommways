from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from services.agent_runtime.event_planning import EventPlanningWorkflow
from services.planning_foundation.errors import (
    AuthorizationError,
    StaleProposalError,
    ValidationError,
)
from services.planning_foundation.models import (
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
    StagePlanProposal,
)
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.stage_validation import StagePlanValidator
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.conftest import create_event


def stage_plan_payload(event, proposal_id=None):
    return {
        "proposal_id": str(proposal_id or uuid4()),
        "event_id": str(event.id),
        "base_event_version": event.version,
        "proposed_stages": [
            {
                "temporary_stage_ref": "stage-1",
                "canonical_name": "Preparation",
                "purpose": "Prepare the event area and execution conditions",
                "proposed_order": 1,
                "proposed_start": event.starts_at.isoformat(),
                "proposed_end": (event.starts_at + timedelta(hours=2)).isoformat(),
                "dependencies": [],
            },
            {
                "temporary_stage_ref": "stage-2",
                "canonical_name": "Community Action",
                "purpose": "Carry out the coordinated community activity",
                "proposed_order": 2,
                "proposed_start": (event.starts_at + timedelta(hours=2)).isoformat(),
                "proposed_end": event.ends_at.isoformat(),
                "dependencies": ["stage-1"],
            },
        ],
        "assumptions": ["Organizer will review all proposed timing"],
        "concise_rationale": "Preparation precedes the main community action.",
        "approval_required": True,
    }


def pending_stage_plan(database, base_service, organizer_id):
    event = create_event(base_service, organizer_id)
    service = StagePlanningService(database)
    request = service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        idempotency_key=f"request-{uuid4()}",
    )
    service.begin_request(request.id)
    proposal = StagePlanProposal.model_validate(stage_plan_payload(event))
    completed = service.complete_request(request.id, proposal)
    return service, event, completed, proposal


def decide(proposal_id, organizer_id, decision, *, key=None, edited_payload=None):
    return ProposalDecisionCommand(
        proposal_id=proposal_id,
        organizer_id=organizer_id,
        decision=decision,
        decision_idempotency_key=key or f"decision-{uuid4()}",
        edited_payload=edited_payload,
    )


def test_planning_request_precheck_and_scoped_tool(database, service, organizer_id):
    event = create_event(service, organizer_id)
    stage_service = StagePlanningService(database)
    request = stage_service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=1,
        idempotency_key="request-1",
    )
    assert request.base_event_version == 1
    tools = ScopedPlanningReadTools(service)
    brief = tools.get_event_brief(
        event_id=event.id, organizer_id=organizer_id, expected_version=1
    )
    assert set(brief.model_dump()) == {
        "event_id", "name", "purpose", "event_type", "starts_at", "ends_at",
        "timezone", "location_description", "version",
    }
    with pytest.raises(AuthorizationError):
        stage_service.request_event_planning(
            event_id=event.id,
            organizer_id=uuid4(),
            expected_event_version=1,
            idempotency_key="unauthorized",
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload, event: payload.update(proposed_stages=[]),
        lambda payload, event: payload["proposed_stages"][1].update(
            temporary_stage_ref="stage-1"
        ),
        lambda payload, event: payload["proposed_stages"][0].update(
            proposed_end=event.starts_at.isoformat()
        ),
        lambda payload, event: payload["proposed_stages"][0].update(
            dependencies=["stage-2"]
        ),
        lambda payload, event: payload["proposed_stages"][0].update(
            purpose="Use the confirmed venue for preparation"
        ),
        lambda payload, event: payload.update(authoritative_mutation={"apply": True}),
    ],
    ids=["empty", "duplicate-ref", "invalid-time", "cycle", "fabricated", "forbidden"],
)
def test_invalid_stage_proposals_rejected(service, organizer_id, mutate):
    event = create_event(service, organizer_id)
    payload = stage_plan_payload(event)
    mutate(payload, event)
    with pytest.raises(ValidationError):
        StagePlanValidator().parse_and_validate(payload, event)


def test_organizer_rejection_creates_no_stages(database, service, organizer_id):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )
    result = stage_service.decide_stage_plan(
        decide(request.proposal_id, organizer_id, ProposalDecision.REJECT)
    )
    assert result.status == ProposalStatus.REJECTED
    assert stage_service.list_stages(event.id) == []
    assert service.get_event(event.id).version == 1


def test_organizer_edit_is_revalidated(database, service, organizer_id):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_stages"][1]["temporary_stage_ref"] = "stage-1"
    with pytest.raises(ValidationError):
        stage_service.decide_stage_plan(
            decide(
                request.proposal_id,
                organizer_id,
                ProposalDecision.APPROVE,
                edited_payload=edited,
            )
        )
    assert stage_service.list_stages(event.id) == []


def test_empty_stage_plan_edit_is_revalidated(database, service, organizer_id):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )
    with pytest.raises(ValidationError):
        stage_service.decide_stage_plan(
            decide(
                request.proposal_id,
                organizer_id,
                ProposalDecision.APPROVE,
                edited_payload={},
            )
        )
    assert stage_service.list_stages(event.id) == []


def test_stale_approval_rejected(database, service, organizer_id):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )
    service.update_event_direct(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_version=1,
        changes={"purpose": "Newer organizer-authored purpose"},
    )
    result = stage_service.decide_stage_plan(
        decide(request.proposal_id, organizer_id, ProposalDecision.APPROVE)
    )
    assert result.status == ProposalStatus.STALE
    assert stage_service.list_stages(event.id) == []
    assert service.get_event(event.id).version == 2


def test_success_and_duplicate_approval_create_exact_stages_once(
    database, service, organizer_id
):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )
    edited = proposal.model_dump(mode="json")
    edited["proposed_stages"][0]["canonical_name"] = "Organizer Preparation"
    key = "approve-once"
    first = stage_service.decide_stage_plan(
        decide(
            request.proposal_id,
            organizer_id,
            ProposalDecision.APPROVE,
            key=key,
            edited_payload=edited,
        )
    )
    second = stage_service.decide_stage_plan(
        decide(
            request.proposal_id,
            organizer_id,
            ProposalDecision.APPROVE,
            key=key,
        )
    )
    assert first.status == ProposalStatus.APPROVED
    assert first.event_version == 2
    assert [stage.canonical_name for stage in first.stages] == [
        "Organizer Preparation", "Community Action"
    ]
    assert first.stages[1].dependency_stage_ids == [first.stages[0].id]
    assert second.duplicate is True
    assert len(stage_service.list_stages(event.id)) == 2


def test_stage_application_and_outbox_are_atomic(
    database, service, organizer_id, monkeypatch
):
    stage_service, event, request, proposal = pending_stage_plan(
        database, service, organizer_id
    )

    def fail_before_outbox(connection):
        raise RuntimeError("simulated stage outbox failure")

    monkeypatch.setattr(
        stage_service, "_before_stage_approval_outbox", fail_before_outbox
    )
    with pytest.raises(RuntimeError, match="stage outbox failure"):
        stage_service.decide_stage_plan(
            decide(request.proposal_id, organizer_id, ProposalDecision.APPROVE)
        )
    assert stage_service.list_stages(event.id) == []
    assert service.get_event(event.id).version == 1
    assert service.get_proposal(request.proposal_id).status == ProposalStatus.PENDING


class FreeFormRuntime:
    def generate(self, **kwargs):
        return "Here is an unstructured stage plan"


class FailingRuntime:
    def generate(self, **kwargs):
        raise RuntimeError("simulated Bedrock or scoped-tool failure")


@pytest.mark.parametrize("runtime", [FreeFormRuntime(), FailingRuntime()])
def test_runtime_failure_changes_no_authoritative_state(
    database, service, organizer_id, runtime
):
    event = create_event(service, organizer_id)
    stage_service = StagePlanningService(database)
    request = stage_service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=1,
        idempotency_key=f"runtime-failure-{uuid4()}",
    )
    with pytest.raises((ValidationError, RuntimeError)):
        EventPlanningWorkflow(stage_service, runtime).execute(request.id)
    assert stage_service.list_stages(event.id) == []
    assert service.get_event(event.id).version == 1
    assert stage_service.get_request(request.id).status.value == "FAILED"
    with database.connect() as connection:
        failed = connection.execute(
            """
            SELECT 1 FROM domain_outbox
            WHERE event_type = 'reasoning.execution_failed'
              AND aggregate_id = %s
            """,
            (event.id,),
        ).fetchone()
    assert failed is not None
