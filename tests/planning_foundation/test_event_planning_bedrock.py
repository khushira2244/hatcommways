from __future__ import annotations

import os

import pytest

from services.agent_runtime.event_planning import (
    MODEL_ID,
    REGION,
    EventPlanningWorkflow,
    StrandsEventPlanningAgent,
)
from services.planning_foundation.models import PlanningRequestStatus, ProposalStatus
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.conftest import create_event


@pytest.mark.real_bedrock
def test_real_bedrock_produces_valid_pending_stage_plan(
    database, service, organizer_id
):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    event = create_event(service, organizer_id)
    stage_service = StagePlanningService(database)
    request = stage_service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        idempotency_key="real-bedrock-stage-plan",
    )
    runtime = StrandsEventPlanningAgent(ScopedPlanningReadTools(service))
    result = EventPlanningWorkflow(stage_service, runtime).execute(request.id)

    completed = stage_service.get_request(request.id)
    stored = service.get_proposal(completed.proposal_id)
    assert REGION == "us-east-1"
    assert MODEL_ID == "us.amazon.nova-2-lite-v1:0"
    assert result.scoped_tool_calls == 1
    assert result.usage["totalTokens"] > 0
    assert result.proposal.event_id == event.id
    assert result.proposal.base_event_version == event.version
    assert result.proposal.approval_required is True
    assert result.proposal.proposed_stages
    assert completed.status == PlanningRequestStatus.SUCCEEDED
    assert stored.status == ProposalStatus.PENDING
    assert stage_service.list_stages(event.id) == []
