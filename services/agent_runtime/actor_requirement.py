"""Real bounded Strands Actor Requirement Agent and execution workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.actor_requirement_validation import (
    ActorRequirementValidator,
    ROLE_CATEGORIES,
)
from services.planning_foundation.models import ActorRequirementProposal
from services.planning_foundation.tools import ScopedPlanningReadTools


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"


@dataclass(frozen=True)
class ActorRequirementAgentResult:
    proposal: ActorRequirementProposal
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class ActorRequirementRuntime(Protocol):
    def generate(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        work_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        base_stage_version: int,
        base_work_version: int,
        proposal_id: UUID,
    ) -> Any: ...


class StrandsActorRequirementAgent:
    """Proposal-only agent with one read-only, work-bound context tool."""

    def __init__(self, tools: ScopedPlanningReadTools) -> None:
        self.tools = tools

    def generate(
        self,
        *,
        event_id: UUID,
        stage_id: UUID,
        work_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        base_stage_version: int,
        base_work_version: int,
        proposal_id: UUID,
    ) -> ActorRequirementAgentResult:
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
            name="get_work_actor_context",
            description=(
                "Return allowlisted planning facts for exactly one authoritative work "
                "item and its event/stage. No people, participants, protected traits, "
                "assignments, memory, or unrelated work are exposed."
            ),
        )
        def get_work_actor_context() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            context = self.tools.get_work_actor_context(
                event_id=event_id,
                stage_id=stage_id,
                work_id=work_id,
                organizer_id=organizer_id,
                expected_event_version=base_event_version,
                expected_stage_version=base_stage_version,
                expected_work_version=base_work_version,
            )
            return context.model_dump(mode="json")

        categories = ", ".join(sorted(ROLE_CATEGORIES))
        agent = Agent(
            name="hatcommways-actor-requirement-agent",
            model=model,
            tools=[get_work_actor_context],
            structured_output_model=ActorRequirementProposal,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Actor Requirement Agent. Determine "
                "only the planning-baseline roles genuinely relevant to exactly one "
                "authoritative work item. You MUST call get_work_actor_context exactly "
                "once and use only those facts. Allowed role_category values are: "
                f"{categories}. Minimum required count may be zero. Requirements are "
                "role baselines, never assignments. Never identify, recommend, rank, "
                "score, or infer characteristics of people. Never reason about protected "
                "traits. Never assign participants or mutate the work, stage, or event. "
                "Do not invent confirmed people, availability, organizations, resources, "
                "or capabilities. Include only relevant role categories; do not emit all "
                "categories by default. Return only the typed ActorRequirementProposal."
            ),
        )
        result = agent(
            f"Create one actor requirement proposal. Use proposal_id {proposal_id}, "
            f"event_id {event_id}, stage_id {stage_id}, work_id {work_id}, "
            f"base_event_version {base_event_version}, base_stage_version "
            f"{base_stage_version}, base_work_version {base_work_version}, and set "
            "approval_required to true. Include assumptions and a concise rationale."
        )
        if call_count != 1:
            raise RuntimeError(
                f"scoped work tool must be called exactly once; observed {call_count}"
            )
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed ActorRequirementProposal")
        return ActorRequirementAgentResult(
            proposal=ActorRequirementProposal.model_validate(result.structured_output),
            stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage),
            scoped_tool_calls=call_count,
        )


class ActorRequirementWorkflow:
    def __init__(
        self, service: ActorRequirementService, runtime: ActorRequirementRuntime
    ) -> None:
        self.service = service
        self.runtime = runtime
        self.validator = ActorRequirementValidator()

    def execute(self, request_id: UUID) -> ActorRequirementAgentResult:
        request = self.service.begin_request(request_id)
        proposal_id = uuid4()
        try:
            generated = self.runtime.generate(
                event_id=request.event_id,
                stage_id=request.stage_id,
                work_id=request.work_id,
                organizer_id=request.organizer_id,
                base_event_version=request.base_event_version,
                base_stage_version=request.base_stage_version,
                base_work_version=request.base_work_version,
                proposal_id=proposal_id,
            )
            if isinstance(generated, ActorRequirementAgentResult):
                result = generated
                proposal = generated.proposal
            else:
                proposal = self.validator.parse(generated)
                result = ActorRequirementAgentResult(
                    proposal=proposal,
                    stop_reason="test-or-adapter",
                    usage={},
                    scoped_tool_calls=0,
                )
            event = self.service.base.get_event(request.event_id)
            stage = self.service.get_stage(request.stage_id)
            work = self.service.get_work(request.work_id)
            self.validator.validate(
                proposal, event, stage, work, expected_proposal_id=proposal_id
            )
            self.service.complete_request(request_id, proposal)
            return result
        except Exception as error:
            self.service.fail_request(request_id, type(error).__name__)
            raise

