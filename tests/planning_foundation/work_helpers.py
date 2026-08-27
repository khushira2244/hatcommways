from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from services.planning_foundation.models import (
    ProposalDecision,
    ProposalDecisionCommand,
    StagePlanProposal,
    WorkDecompositionProposal,
)
from services.planning_foundation.stage_planning_service import StagePlanningService
from tests.planning_foundation.conftest import create_event


def create_approved_stages(database, base_service, organizer_id):
    event = create_event(base_service, organizer_id)
    stage_service = StagePlanningService(database)
    request = stage_service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=1,
        idempotency_key=f"stage-request-{uuid4()}",
    )
    stage_service.begin_request(request.id)
    proposal = StagePlanProposal.model_validate(
        {
            "proposal_id": str(uuid4()),
            "event_id": str(event.id),
            "base_event_version": 1,
            "proposed_stages": [
                {
                    "temporary_stage_ref": "stage-1",
                    "canonical_name": "Preparation",
                    "purpose": "Prepare the event for community action",
                    "proposed_order": 1,
                    "proposed_start": event.starts_at.isoformat(),
                    "proposed_end": (event.starts_at + timedelta(hours=4)).isoformat(),
                    "dependencies": [],
                },
                {
                    "temporary_stage_ref": "stage-2",
                    "canonical_name": "Execution",
                    "purpose": "Carry out the community action",
                    "proposed_order": 2,
                    "proposed_start": (event.starts_at + timedelta(hours=4)).isoformat(),
                    "proposed_end": event.ends_at.isoformat(),
                    "dependencies": ["stage-1"],
                },
            ],
            "assumptions": ["Organizer will review the proposed stages"],
            "concise_rationale": "Preparation supports later execution.",
            "approval_required": True,
        }
    )
    completed = stage_service.complete_request(request.id, proposal)
    stage_service.decide_stage_plan(
        ProposalDecisionCommand(
            proposal_id=completed.proposal_id,
            organizer_id=organizer_id,
            decision=ProposalDecision.APPROVE,
            decision_idempotency_key=f"stage-approval-{uuid4()}",
        )
    )
    return base_service.get_event(event.id), stage_service.list_stages(event.id)


def work_plan_payload(event, stage, proposal_id=None):
    return {
        "proposal_id": str(proposal_id or uuid4()),
        "event_id": str(event.id),
        "stage_id": str(stage.id),
        "base_event_version": event.version,
        "base_stage_version": stage.version,
        "proposed_work": [
            {
                "temporary_work_ref": "work-1",
                "canonical_name": "Area Assessment",
                "purpose": "Assess the area and identify preparation needs",
                "estimated_person_hours": 4,
                "work_share": 33.33,
                "proposed_start": stage.starts_at.isoformat(),
                "proposed_end": (stage.starts_at + timedelta(hours=1.5)).isoformat(),
                "dependencies": [],
            },
            {
                "temporary_work_ref": "work-2",
                "canonical_name": "Site Preparation",
                "purpose": "Prepare the site based on the completed assessment",
                "estimated_person_hours": 8,
                "work_share": 66.67,
                "proposed_start": (stage.starts_at + timedelta(hours=1.5)).isoformat(),
                "proposed_end": stage.ends_at.isoformat(),
                "dependencies": ["work-1"],
            },
        ],
        "assumptions": ["Organizer will review provisional effort estimates"],
        "concise_rationale": "Assessment informs the subsequent site preparation.",
        "approval_required": True,
    }


def make_work_proposal(event, stage):
    return WorkDecompositionProposal.model_validate(work_plan_payload(event, stage))
