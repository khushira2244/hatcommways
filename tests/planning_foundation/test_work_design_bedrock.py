from __future__ import annotations

import os

import pytest

from services.agent_runtime.work_design import (
    MODEL_ID,
    REGION,
    StrandsWorkDesignAgent,
    WorkDesignWorkflow,
)
from services.planning_foundation.models import PlanningRequestStatus, ProposalStatus
from services.planning_foundation.tools import ScopedPlanningReadTools
from services.planning_foundation.work_design_service import WorkDesignService
from tests.planning_foundation.work_helpers import create_approved_stages


@pytest.mark.real_bedrock
def test_real_bedrock_produces_valid_pending_work_decomposition(
    database, service, organizer_id
):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")
    event, stages = create_approved_stages(database, service, organizer_id)
    stage = stages[0]
    work_service = WorkDesignService(database)
    request = work_service.request_work_design(
        event_id=event.id,
        stage_id=stage.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=stage.version,
        idempotency_key="real-bedrock-work-design",
    )
    runtime = StrandsWorkDesignAgent(ScopedPlanningReadTools(service))
    result = WorkDesignWorkflow(work_service, runtime).execute(request.id)

    completed = work_service.get_request(request.id)
    stored = service.get_proposal(completed.proposal_id)
    assert REGION == "us-east-1"
    assert MODEL_ID == "us.amazon.nova-2-lite-v1:0"
    assert result.scoped_tool_calls == 1
    assert result.usage["totalTokens"] > 0
    assert result.proposal.event_id == event.id
    assert result.proposal.stage_id == stage.id
    assert result.proposal.base_event_version == event.version
    assert result.proposal.base_stage_version == stage.version
    assert result.proposal.approval_required is True
    assert result.proposal.proposed_work
    assert sum(item.work_share for item in result.proposal.proposed_work) == pytest.approx(
        100, abs=0.20
    )
    assert completed.status == PlanningRequestStatus.SUCCEEDED
    assert stored.status == ProposalStatus.PENDING
    assert work_service.list_work(stage.id) == []
