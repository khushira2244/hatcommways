"""Bounded Strands/Nova runtime for interpreting one immutable human report."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.human_update_interpretation_service import (
    HumanUpdateInterpretationService,
)
from services.planning_foundation.human_update_models import HumanUpdateInterpretation


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"
PROVIDER_NAME = "amazon-bedrock"
AGENT_NAME = "hatcommways-human-update-interpretation-agent"
AGENT_VERSION = "v1"


@dataclass(frozen=True)
class HumanUpdateInterpretationAgentResult:
    interpretation: HumanUpdateInterpretation
    provider_name: str
    model_id: str
    agent_name: str
    agent_version: str
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class HumanUpdateInterpretationRuntime(Protocol):
    def generate(
        self, *, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> HumanUpdateInterpretationAgentResult | HumanUpdateInterpretation | dict[str, Any]: ...


class StrandsHumanUpdateInterpretationAgent:
    def __init__(self, service: HumanUpdateInterpretationService):
        self.service = service

    def generate(
        self, *, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> HumanUpdateInterpretationAgentResult:
        session = boto3.Session(
            profile_name=os.environ.get("AWS_PROFILE"), region_name=REGION
        )
        model = BedrockModel(
            boto_session=session,
            model_id=MODEL_ID,
            temperature=0,
            max_tokens=1600,
        )
        call_count = 0

        @tool(
            name="get_human_update_context",
            description=(
                "Return the immutable report and its explicitly linked event, stage, work, "
                "and accepted-participation facts. It exposes no unrelated event data."
            ),
        )
        def get_human_update_context() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return self.service.context(event_id, update_id, organizer_id).model_dump(mode="json")

        agent = Agent(
            name=AGENT_NAME,
            model=model,
            tools=[get_human_update_context],
            structured_output_model=HumanUpdateInterpretation,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Human Update Interpretation Agent. "
                "Call get_human_update_context exactly once and use only those facts. "
                "Interpret what the person reported; do not decide authoritative blocker "
                "state, affected downstream work, schedule changes, assignments, plans, "
                "coordination, or replanning. Do not invent missing facts or IDs. Reference "
                "a stage or work only when that exact ID appears in the scoped context. "
                "possible_blocker means the report may materially prevent or disrupt the "
                "linked activity. Mark it true only when the report supplies a concrete "
                "obstruction, delay, access, resource, equipment, or safety condition. "
                "A completed task and its normal handoff are not blockers. When a report "
                "is too vague to identify a concrete condition, require clarification and "
                "set possible_blocker false rather than inferring an obstruction. Ask one "
                "concise clarification question when the meaning is too ambiguous. A bare "
                "claim such as 'it will not work' does not state the cause or condition: "
                "classify it as UNKNOWN or GENERAL_UPDATE, require clarification, and set "
                "possible_blocker false. Never treat uncertainty itself as a blocker. "
                "Return only the typed HumanUpdateInterpretation."
            ),
        )
        result = agent(
            f"Interpret human update {update_id} in event {event_id}. Preserve those exact IDs."
        )
        if call_count != 1:
            raise RuntimeError(
                f"scoped human update tool must be called exactly once; observed {call_count}"
            )
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed HumanUpdateInterpretation")
        return HumanUpdateInterpretationAgentResult(
            interpretation=HumanUpdateInterpretation.model_validate(result.structured_output),
            provider_name=PROVIDER_NAME,
            model_id=MODEL_ID,
            agent_name=AGENT_NAME,
            agent_version=AGENT_VERSION,
            stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage),
            scoped_tool_calls=call_count,
        )


class HumanUpdateInterpretationWorkflow:
    def __init__(
        self,
        service: HumanUpdateInterpretationService,
        runtime: HumanUpdateInterpretationRuntime,
    ):
        self.service = service
        self.runtime = runtime

    def execute(
        self,
        *,
        event_id: UUID,
        update_id: UUID,
        organizer_id: UUID,
        retry: bool = False,
    ):
        started = self.service.begin(event_id, update_id, organizer_id, retry=retry)
        if started.existing:
            return started.existing
        try:
            generated = self.runtime.generate(
                event_id=event_id, update_id=update_id, organizer_id=organizer_id
            )
            if isinstance(generated, HumanUpdateInterpretationAgentResult):
                interpretation = generated.interpretation
                provenance = {
                    "provider_name": generated.provider_name,
                    "model_id": generated.model_id,
                    "agent_name": generated.agent_name,
                    "agent_version": generated.agent_version,
                    "stop_reason": generated.stop_reason,
                    "usage": generated.usage,
                }
            else:
                interpretation = HumanUpdateInterpretation.model_validate(generated)
                provenance = {
                    "provider_name": "test-runtime",
                    "model_id": "deterministic-fixture",
                    "agent_name": AGENT_NAME,
                    "agent_version": AGENT_VERSION,
                    "stop_reason": "test-or-adapter",
                    "usage": {},
                }
            return self.service.complete(
                event_id,
                update_id,
                organizer_id,
                interpretation,
                **provenance,
            )
        except Exception as error:
            self.service.fail(event_id, update_id, type(error).__name__)
            raise
