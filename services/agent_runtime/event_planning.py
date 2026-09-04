"""Real Strands Event Planning Agent and deterministic execution workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.models import StagePlanProposal
from services.planning_foundation.stage_planning_service import StagePlanningService
from services.planning_foundation.stage_validation import StagePlanValidator
from services.planning_foundation.tools import ScopedPlanningReadTools


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"


@dataclass(frozen=True)
class EventPlanningAgentResult:
    proposal: StagePlanProposal
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class EventPlanningRuntime(Protocol):
    def generate(
        self,
        *,
        event_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        proposal_id: UUID,
    ) -> Any: ...


class StrandsEventPlanningAgent:
    """Proposal-only agent with one bound, read-only event brief tool."""

    def __init__(self, tools: ScopedPlanningReadTools) -> None:
        self.tools = tools

    def generate(
        self,
        *,
        event_id: UUID,
        organizer_id: UUID,
        base_event_version: int,
        proposal_id: UUID,
    ) -> EventPlanningAgentResult:
        profile = os.environ.get("AWS_PROFILE", "hatcommways")
        session = boto3.Session(profile_name=profile, region_name=REGION)
        model = BedrockModel(
            boto_session=session,
            model_id=MODEL_ID,
            temperature=0,
            max_tokens=2500,
        )
        call_count = 0

        @tool(
            name="get_event_planning_brief",
            description=(
                "Return the current versioned facts for the one event authorized "
                "for this planning run, including organizer-provided planning context. "
                "It exposes no participant identities, memberships, blockers, memory, "
                "or unrelated events."
            ),
        )
        def get_event_planning_brief() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            brief = self.tools.get_event_brief(
                event_id=event_id,
                organizer_id=organizer_id,
                expected_version=base_event_version,
            )
            return brief.model_dump(mode="json")

        agent = Agent(
            name="hatcommways-event-planning-agent",
            model=model,
            tools=[get_event_planning_brief],
            structured_output_model=StagePlanProposal,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Event Planning Agent. "
                "You propose major stages only; never work items, actor requirements, "
                "participant assignments, blockers, memory, or mutations. You MUST call "
                "get_event_planning_brief exactly once before proposing stages. Use only "
                "facts returned by that tool. Keep all stages inside the event window. "
                "Use unique temporary refs and contiguous order starting at 1. Dependencies "
                "may reference only earlier proposed stage refs and must be acyclic. Never "
                "claim that venues, permissions, resources, participants, volunteers, or "
                "sponsors are confirmed: planning-context resources and intended participant "
                "types are organizer-provided intentions only. Use theme solely for display "
                "vocabulary; it cannot alter canonical semantics, dependencies, permissions, "
                "counts, or approval rules. Return "
                "the typed proposal only."
            ),
        )
        result = agent(
            f"Create a stage plan proposal. Use proposal_id {proposal_id}, event_id "
            f"{event_id}, base_event_version {base_event_version}, and set "
            "approval_required to true. Include assumptions and a concise rationale."
        )
        if call_count != 1:
            raise RuntimeError(
                f"scoped event tool must be called exactly once; observed {call_count}"
            )
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed StagePlanProposal")
        return EventPlanningAgentResult(
            proposal=StagePlanProposal.model_validate(result.structured_output),
            stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage),
            scoped_tool_calls=call_count,
        )


class EventPlanningWorkflow:
    """Deterministically controls when and how the reasoning agent may run."""

    def __init__(
        self,
        service: StagePlanningService,
        runtime: EventPlanningRuntime,
    ) -> None:
        self.service = service
        self.runtime = runtime
        self.validator = StagePlanValidator()

    def execute(self, request_id: UUID) -> EventPlanningAgentResult:
        request = self.service.begin_request(request_id)
        proposal_id = uuid4()
        try:
            generated = self.runtime.generate(
                event_id=request.event_id,
                organizer_id=request.organizer_id,
                base_event_version=request.base_event_version,
                proposal_id=proposal_id,
            )
            if isinstance(generated, EventPlanningAgentResult):
                result = generated
                proposal = generated.proposal
            else:
                proposal = self.validator.parse(generated)
                result = EventPlanningAgentResult(
                    proposal=proposal,
                    stop_reason="test-or-adapter",
                    usage={},
                    scoped_tool_calls=0,
                )
            event = self.service.base.get_event(request.event_id)
            self.validator.validate(
                proposal, event, expected_proposal_id=proposal_id
            )
            self.service.complete_request(request_id, proposal)
            return result
        except Exception as error:
            self.service.fail_request(request_id, type(error).__name__)
            raise
