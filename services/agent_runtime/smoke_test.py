"""Verify the Hatcommways Strands-to-Amazon-Bedrock foundation."""

from __future__ import annotations

import json
import os

import boto3
from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel


REGION = "us-east-1"
MODEL_ID = "us.amazon.nova-2-lite-v1:0"


class SmokeResult(BaseModel):
    status: str
    message: str


def main() -> None:
    profile = os.environ.get("AWS_PROFILE", "hatcommways")
    session = boto3.Session(profile_name=profile, region_name=REGION)
    model = BedrockModel(
        boto_session=session,
        model_id=MODEL_ID,
        temperature=0,
        max_tokens=100,
    )
    agent = Agent(
        name="hatcommways-foundation-smoke-test",
        model=model,
        tools=[],
        system_prompt=(
            "Return the requested structured result exactly. "
            "Do not add commentary or call tools."
        ),
        structured_output_model=SmokeResult,
    )

    result = agent(
        "Confirm the Hatcommways Strands foundation by returning status 'ok' "
        "and message 'Hatcommways Strands foundation is working'."
    )
    if result.structured_output is None:
        raise RuntimeError("Strands returned no structured model output")

    output = result.structured_output.model_dump()
    if output != {
        "status": "ok",
        "message": "Hatcommways Strands foundation is working",
    }:
        raise RuntimeError(f"Unexpected model response: {output!r}")

    proof = {
        "provider": "amazon-bedrock",
        "model": MODEL_ID,
        "region": REGION,
        "strands_agent": agent.name,
        "stop_reason": result.stop_reason,
        "usage": result.metrics.accumulated_usage,
        "result": output,
    }
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
