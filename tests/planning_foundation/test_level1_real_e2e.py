from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest

from services.agent_runtime.actor_requirement import (
    ActorRequirementWorkflow,
    StrandsActorRequirementAgent,
)
from services.agent_runtime.event_planning import (
    EventPlanningWorkflow,
    StrandsEventPlanningAgent,
)
from services.agent_runtime.work_design import (
    StrandsWorkDesignAgent,
    WorkDesignWorkflow,
)
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.models import (
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
)
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.tools import ScopedPlanningReadTools
from services.planning_foundation.work_design_service import WorkDesignService
from tests.planning_foundation.conftest import make_event_command


@pytest.mark.real_bedrock
def test_fresh_real_level1_flow(database, service, organizer_id):
    if os.environ.get("HATCOMMWAYS_RUN_REAL_BEDROCK") != "1":
        pytest.skip("set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test")

    correlation_id = uuid4()
    tools = ScopedPlanningReadTools(service)
    event = service.create_event(
        make_event_command(organizer_id),
        idempotency_key="level1-e2e-event",
        correlation_id=correlation_id,
    )

    stage_service = StagePlanningService(database)
    stage_request = stage_service.request_event_planning(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        idempotency_key="level1-e2e-stages",
        correlation_id=correlation_id,
    )
    stage_result = EventPlanningWorkflow(
        stage_service, StrandsEventPlanningAgent(tools)
    ).execute(stage_request.id)
    stage_decision = stage_service.decide_stage_plan(
        ProposalDecisionCommand(
            proposal_id=stage_result.proposal.proposal_id,
            organizer_id=organizer_id,
            decision=ProposalDecision.APPROVE,
            decision_idempotency_key="level1-e2e-stage-approval",
        )
    )
    assert stage_decision.status == ProposalStatus.APPROVED
    assert stage_decision.stages

    event = service.get_event(event.id)
    target_stage = stage_decision.stages[0]
    work_service = WorkDesignService(database)
    work_request = work_service.request_work_design(
        event_id=event.id,
        stage_id=target_stage.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=target_stage.version,
        idempotency_key="level1-e2e-work",
        correlation_id=correlation_id,
    )
    work_result = WorkDesignWorkflow(
        work_service, StrandsWorkDesignAgent(tools)
    ).execute(work_request.id)
    work_decision = work_service.decide_work_decomposition(
        ProposalDecisionCommand(
            proposal_id=work_result.proposal.proposal_id,
            organizer_id=organizer_id,
            decision=ProposalDecision.APPROVE,
            decision_idempotency_key="level1-e2e-work-approval",
        )
    )
    assert work_decision.status == ProposalStatus.APPROVED
    assert work_decision.work
    assert sum(item.work_share for item in work_decision.work) == pytest.approx(
        100, abs=0.20
    )

    event = service.get_event(event.id)
    target_stage = work_service.get_stage(target_stage.id)
    target_work = work_decision.work[0]
    actor_service = ActorRequirementService(database)
    actor_request = actor_service.request_actor_requirements(
        event_id=event.id,
        stage_id=target_stage.id,
        work_id=target_work.id,
        organizer_id=organizer_id,
        expected_event_version=event.version,
        expected_stage_version=target_stage.version,
        expected_work_version=target_work.version,
        idempotency_key="level1-e2e-actor-requirements",
        correlation_id=correlation_id,
    )
    actor_result = ActorRequirementWorkflow(
        actor_service, StrandsActorRequirementAgent(tools)
    ).execute(actor_request.id)
    actor_decision = actor_service.decide_actor_requirements(
        ProposalDecisionCommand(
            proposal_id=actor_result.proposal.proposal_id,
            organizer_id=organizer_id,
            decision=ProposalDecision.APPROVE,
            decision_idempotency_key="level1-e2e-actor-approval",
        )
    )
    assert actor_decision.status == ProposalStatus.APPROVED
    assert actor_decision.requirements

    with database.connect() as connection:
        final_event = connection.execute(
            "SELECT id,name,version FROM events WHERE id=%s", (event.id,)
        ).fetchone()
        stages = connection.execute(
            "SELECT id,canonical_name,stage_order,version FROM stages WHERE event_id=%s ORDER BY stage_order",
            (event.id,),
        ).fetchall()
        work = connection.execute(
            """
            SELECT id,stage_id,canonical_name,work_order,estimated_person_hours,
                   work_share,version FROM work_items WHERE event_id=%s
            ORDER BY stage_id,work_order
            """,
            (event.id,),
        ).fetchall()
        requirements = connection.execute(
            """
            SELECT id,work_id,role_category,canonical_role_name,
                   minimum_required_count,relevant_capabilities,version
            FROM actor_requirements WHERE event_id=%s
            ORDER BY work_id,role_category,canonical_role_name
            """,
            (event.id,),
        ).fetchall()
        outbox = connection.execute(
            """
            SELECT event_type,aggregate_type,aggregate_id,aggregate_version,
                   correlation_id,causation_id,payload
            FROM domain_outbox WHERE correlation_id=%s ORDER BY occurred_at,id
            """,
            (correlation_id,),
        ).fetchall()

    assert all(row["correlation_id"] == correlation_id for row in outbox)
    assert len(stages) == len(stage_result.proposal.proposed_stages)
    assert len(work) == len(work_result.proposal.proposed_work)
    assert len(requirements) == len(actor_result.proposal.proposed_requirements)
    assert all(row["stage_id"] == target_stage.id for row in work)
    assert all(row["work_id"] == target_work.id for row in requirements)

    proof = {
        "correlation_id": correlation_id,
        "stage_plan_proposal": stage_result.proposal.model_dump(mode="json"),
        "work_decomposition_proposal": work_result.proposal.model_dump(mode="json"),
        "actor_requirement_proposal": actor_result.proposal.model_dump(mode="json"),
        "authoritative_state": {
            "event": final_event,
            "stages": stages,
            "work": work,
            "actor_requirements": requirements,
        },
        "work_share_total": sum(float(row["work_share"]) for row in work),
        "outbox": outbox,
    }
    print("LEVEL1_REAL_PROOF=" + json.dumps(proof, default=str, sort_keys=True))

