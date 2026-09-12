"""Bounded Strands/Nova runtime for direct execution-impact assessment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.blocker_assessment_service import (
    BlockerAssessmentService,
)
from services.planning_foundation.human_update_models import BlockerAssessment


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"
PROVIDER_NAME = "amazon-bedrock"
AGENT_NAME = "hatcommways-blocker-assessment-agent"
AGENT_VERSION = "v1"


@dataclass(frozen=True)
class BlockerAssessmentAgentResult:
    assessment: BlockerAssessment
    provider_name: str
    model_id: str
    agent_name: str
    agent_version: str
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class BlockerAssessmentRuntime(Protocol):
    def generate(
        self, *, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> BlockerAssessmentAgentResult | BlockerAssessment | dict[str, Any]: ...


class StrandsBlockerAssessmentAgent:
    def __init__(self, service: BlockerAssessmentService):
        self.service = service

    def generate(
        self, *, event_id: UUID, update_id: UUID, organizer_id: UUID
    ) -> BlockerAssessmentAgentResult:
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
            name="get_blocker_assessment_context",
            description=(
                "Return one exact human report, its persisted interpretation, and only "
                "its directly linked stage, work, participation, and meeting facts."
            ),
        )
        def get_blocker_assessment_context() -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return self.service.context(event_id, update_id, organizer_id).model_dump(mode="json")

        agent = Agent(
            name=AGENT_NAME,
            model=model,
            tools=[get_blocker_assessment_context],
            structured_output_model=BlockerAssessment,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Blocker Assessment Agent. Call "
                "get_blocker_assessment_context exactly once and use only those facts. "
                "Judge whether the interpreted condition materially interferes with the "
                "directly linked event execution. Do not calculate downstream affected "
                "work, inspect or invent dependencies, rewrite schedules, change work, "
                "assign people, coordinate a solution, or propose a plan. Copy only exact "
                "stage/work IDs present in the context. For a concrete late arrival that "
                "conflicts with accepted work start, mark an execution blocker, choose the "
                "best small kind such as AVAILABILITY, ACCESS, or SCHEDULE, reference the "
                "linked work, and normally mark coordination_needed true. Completion and "
                "normal handoff are not blockers: use NONE with both action flags false. "
                "If the persisted interpretation requires clarification, preserve that "
                "uncertainty, use NONE, LOW internal severity and urgency, false action "
                "flags, no invented references or cause, and one concise question. The "
                "internal severity and urgency are operational metadata, not legal or "
                "safety judgments. Never choose blocker lifecycle state and never create "
                "a blocker. Return only the typed BlockerAssessment."
            ),
        )
        result = agent(
            f"Assess update {update_id} in event {event_id}. Preserve the exact event, "
            "human update, and persisted interpretation IDs returned by the scoped tool."
        )
        if call_count != 1:
            raise RuntimeError(
                f"scoped blocker assessment tool must be called exactly once; observed {call_count}"
            )
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed BlockerAssessment")
        return BlockerAssessmentAgentResult(
            assessment=BlockerAssessment.model_validate(result.structured_output),
            provider_name=PROVIDER_NAME,
            model_id=MODEL_ID,
            agent_name=AGENT_NAME,
            agent_version=AGENT_VERSION,
            stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage),
            scoped_tool_calls=call_count,
        )


class BlockerAssessmentWorkflow:
    def __init__(
        self, service: BlockerAssessmentService, runtime: BlockerAssessmentRuntime
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
            if isinstance(generated, BlockerAssessmentAgentResult):
                assessment = generated.assessment
                provenance = {
                    "provider_name": generated.provider_name,
                    "model_id": generated.model_id,
                    "agent_name": generated.agent_name,
                    "agent_version": generated.agent_version,
                    "stop_reason": generated.stop_reason,
                    "usage": generated.usage,
                }
            else:
                assessment = BlockerAssessment.model_validate(generated)
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
                assessment,
                **provenance,
            )
        except Exception as error:
            self.service.fail(event_id, update_id, type(error).__name__)
            raise
