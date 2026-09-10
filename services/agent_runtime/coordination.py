"""Bounded Strands/Nova runtime for advisory coordination proposals."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from services.planning_foundation.coordination_models import CoordinationDecision
from services.planning_foundation.coordination_service import CoordinationService


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"
PROVIDER_NAME = "amazon-bedrock"
AGENT_NAME = "hatcommways-coordination-agent"
AGENT_VERSION = "v1"


@dataclass(frozen=True)
class CoordinationAgentResult:
    proposal: CoordinationDecision
    provider_name: str
    model_id: str
    agent_name: str
    agent_version: str
    stop_reason: str
    usage: dict[str, int]
    scoped_tool_calls: int


class CoordinationRuntime(Protocol):
    def generate(self, *, event_id: UUID, blocker_id: UUID, organizer_id: UUID) -> CoordinationAgentResult | CoordinationDecision | dict[str, Any]: ...


class StrandsCoordinationAgent:
    def __init__(self, service: CoordinationService) -> None:
        self.service = service

    def generate(self, *, event_id: UUID, blocker_id: UUID, organizer_id: UUID) -> CoordinationAgentResult:
        session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE", "hatcommways"), region_name=REGION)
        model = BedrockModel(boto_session=session, model_id=MODEL_ID, temperature=0, max_tokens=2200)
        calls = 0

        @tool(name="get_coordination_context", description="Return only the authoritative blocker, affected work, relevant accepted actors, meetings, and existing event resources.")
        def get_coordination_context() -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return self.service.context(event_id, blocker_id, organizer_id).model_dump(mode="json")

        agent = Agent(
            name=AGENT_NAME,
            model=model,
            tools=[get_coordination_context],
            structured_output_model=CoordinationDecision,
            callback_handler=None,
            system_prompt=(
                "You are the bounded Hatcommways Coordination Agent. Call get_coordination_context "
                "exactly once and use only its facts. Propose small coordination actions that try to "
                "preserve the confirmed stage and work plan. Copy only event, blocker, resolution, actor, "
                "work, meeting, and resource identifiers present in context. Never change work or stage "
                "times, dependencies, work definitions, participation, assignments, blocker lifecycle, or "
                "send a notification. NOTIFY_ACTOR is only a proposed notification. RESCHEDULE_MEETING may "
                "change a relevant meeting suggestion but never work timing. REASSIGNMENT_SUGGESTION is an "
                "approval-required suggestion only. If known facts provide a safe workaround, set "
                "coordination_possible true and requires_replanning false. If preserving confirmed timing "
                "is not credible, set coordination_possible false and requires_replanning true. If facts "
                "are insufficient, request clarification without inventing details and keep replanning false. "
                "Return only the typed CoordinationDecision."
            ),
        )
        result = agent(f"Coordinate blocker {blocker_id} in event {event_id} without rewriting its plan.")
        if calls != 1:
            raise RuntimeError(f"scoped coordination tool must be called exactly once; observed {calls}")
        if result.structured_output is None:
            raise RuntimeError("Strands returned no typed CoordinationDecision")
        return CoordinationAgentResult(
            proposal=CoordinationDecision.model_validate(result.structured_output),
            provider_name=PROVIDER_NAME, model_id=MODEL_ID, agent_name=AGENT_NAME,
            agent_version=AGENT_VERSION, stop_reason=result.stop_reason,
            usage=dict(result.metrics.accumulated_usage), scoped_tool_calls=calls,
        )


class CoordinationWorkflow:
    def __init__(self, service: CoordinationService, runtime: CoordinationRuntime) -> None:
        self.service = service
        self.runtime = runtime

    def execute(self, *, event_id: UUID, blocker_id: UUID, organizer_id: UUID, retry: bool = False):
        started = self.service.begin(event_id, blocker_id, organizer_id, retry=retry)
        if started.existing:
            return started.existing
        try:
            generated = self.runtime.generate(event_id=event_id, blocker_id=blocker_id, organizer_id=organizer_id)
            if isinstance(generated, CoordinationAgentResult):
                decision = generated.proposal
                provenance = {key: getattr(generated, key) for key in ("provider_name", "model_id", "agent_name", "agent_version", "stop_reason", "usage")}
            else:
                decision = CoordinationDecision.model_validate(generated)
                provenance = {"provider_name":"test-runtime","model_id":"deterministic-fixture","agent_name":AGENT_NAME,"agent_version":AGENT_VERSION,"stop_reason":"test-or-adapter","usage":{}}
            return self.service.complete(event_id, blocker_id, organizer_id, started.request_id, decision, **provenance)
        except Exception as error:
            self.service.fail(event_id, blocker_id, started.request_id, type(error).__name__)
            raise
