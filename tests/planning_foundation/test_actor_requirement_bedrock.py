from __future__ import annotations

import os

import pytest

from services.agent_runtime.actor_requirement import (
    MODEL_ID,
    REGION,
    ActorRequirementWorkflow,
    StrandsActorRequirementAgent,
)
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.actor_requirement_validation import ROLE_CATEGORIES
from services.planning_foundation.models import PlanningRequestStatus, ProposalStatus
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.work_helpers import create_approved_work


@pytest.mark.real_bedrock
def test_real_bedrock_produces_valid_pending_actor_requirements(
    database, service, organizer_id
):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    target = work[0]
    actor_service = ActorRequirementService(database)
    request = actor_service.request_actor_requirements(
        event_id=event.id,
        stage_id=stage.id,
        work_id=target.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stage.version,
        expected_work_version=target.version,
        idempotency_key="real-bedrock-actor-requirements",
    )
    runtime = StrandsActorRequirementAgent(ScopedPlanningReadTools(service))
    result = ActorRequirementWorkflow(actor_service, runtime).execute(request.id)

    completed = actor_service.get_request(request.id)
    stored = service.get_proposal(completed.proposal_id)
    assert REGION == "us-east-1"
    assert MODEL_ID == "us.amazon.nova-2-lite-v1:0"
    assert result.scoped_tool_calls == 1
    assert result.usage["totalTokens"] > 0
    assert result.proposal.event_id == event.id
    assert result.proposal.stage_id == stage.id
    assert result.proposal.work_id == target.id
    assert result.proposal.base_event_version == event.version
    assert result.proposal.base_stage_version == stage.version
    assert result.proposal.base_work_version == target.version
    assert result.proposal.approval_required is True
    assert result.proposal.proposed_requirements
    assert all(
        requirement.role_category.upper() in ROLE_CATEGORIES
        for requirement in result.proposal.proposed_requirements
    )
    assert completed.status == PlanningRequestStatus.SUCCEEDED
    assert stored.status == ProposalStatus.PENDING
    assert actor_service.list_requirements(target.id) == []

