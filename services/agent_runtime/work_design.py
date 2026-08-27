"""Real bounded Strands Work Design Agent and execution workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.models import WorkDecompositionProposal
from services.planning_foundation.tools import ScopedPlanningReadTools
from services.planning_foundation.work_design_service import WorkDesignService
from services.planning_foundation.work_validation import (
    WorkDecompositionValidator,
    calculate_work_shares,
)


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"


@dataclass(frozen=True)
class WorkDesignAgentResult:
    proposal: WorkDecompositionProposal
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class WorkDesignRuntime(Protocol):
    def generate(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        base_stage_version: int,
        proposal_id: UUID,
    ) -> Any: ...


class StrandsWorkDesignAgent:
    """Proposal-only Work Design Agent with one stage-bound read tool."""

    def __init__(self, tools: ScopedPlanningReadTools) -> None:
        self.tools = tools

    def generate(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        base_stage_version: int,
        proposal_id: UUID,
    ) -> WorkDesignAgentResult:
        profile = os.environ.get("AWS_PROFILE", "hatcommways")
        session = boto3.Session(profile_name=profile, region_name=REGION)
        model = BedrockModel(
            boto_session=session,
            model_id=MODEL_ID,
            temperature=0,
            max_tokens=3000,
        )
        call_count = 0

        @tool(
            name="get_stage_work_context",
            description=(
                "Return current allowlisted facts for exactly one approved stage and "
                "its parent event. It exposes no participants, actor requirements, "
                "blockers, memory, resources, or unrelated stages."
            ),
        )
        def get_stage_work_context() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            context = self.tools.get_stage_work_context(
                event_id=event_id,
                stage_id=stage_id,
                organizer_id=organizer_id,
                expected_event_version=base_event_version,
                expected_stage_version=base_stage_version,
            )
            return context.model_dump(mode="json")

        agent = Agent(
            name="hatcommways-work-design-agent",
            model=model,
            tools=[get_stage_work_context],
            structured_output_model=WorkDecompositionProposal,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Work Design Agent. Decompose exactly "
                "one approved stage into meaningful work. Never propose stages, actor "
                "requirements, participant assignments, blockers, resources, memory, or "
                "mutations. You MUST call get_stage_work_context exactly once and use only "
                "its facts. Keep all work inside the stage window. Use unique temporary "
                "work refs. Dependencies may reference only proposed work refs and must be "
                "acyclic. Estimate positive person-hours based on execution effort, not "
                "scheduled duration alone. For every item calculate work_share = its "
                "estimated_person_hours / total estimated_person_hours for all proposed "
                "work in this stage * 100. Round work_share to two decimal places; the "
                "shares must total approximately 100. Never claim confirmed people, "
                "resources, equipment, materials, venues, permissions, or sponsors. Return "
                "only the typed WorkDecompositionProposal."
            ),
        )
        result = agent(
            f"Create one work decomposition proposal. Use proposal_id {proposal_id}, "
            f"event_id {event_id}, stage_id {stage_id}, base_event_version "
            f"{base_event_version}, base_stage_version {base_stage_version}, and set "
            "approval_required to true. Include assumptions and a concise rationale."
        )
        if call_count != 1:
            raise RuntimeError(
                f"scoped stage tool must be called exactly once; observed {call_count}"
            )
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed WorkDecompositionProposal")
        proposal = calculate_work_shares(
            WorkDecompositionProposal.model_validate(result.structured_output)
        )
        return WorkDesignAgentResult(
            proposal=proposal,
            stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage),
            scoped_tool_calls=call_count,
        )


class WorkDesignWorkflow:
    def __init__(self, service: WorkDesignService, runtime: WorkDesignRuntime) -> None:
        self.service = service
        self.runtime = runtime
        self.validator = WorkDecompositionValidator()

    def execute(self, request_id: UUID) -> WorkDesignAgentResult:
        request = self.service.begin_request(request_id)
        proposal_id = uuid4()
        try:
            generated = self.runtime.generate(
                event_id=request.event_id,
                stage_id=request.stage_id,
                organizer_id=request.organizer_id,
                base_event_version=request.base_event_version,
                base_stage_version=request.base_stage_version,
                proposal_id=proposal_id,
            )
            if isinstance(generated, WorkDesignAgentResult):
                result = generated
                proposal = generated.proposal
            else:
                proposal = self.validator.parse(generated)
                result = WorkDesignAgentResult(
                    proposal=proposal,
                    stop_reason="test-or-adapter",
                    usage={},
                    scoped_tool_calls=0,
                )
            event = self.service.base.get_event(request.event_id)
            stage = self.service.get_stage(request.stage_id)
            self.validator.validate(
                proposal,
                event,
                stage,
                expected_proposal_id=proposal_id,
            )
            self.service.complete_request(request_id, proposal)
            return result
        except Exception as error:
            self.service.fail_request(request_id, type(error).__name__)
            raise
