from __future__ import annotations
import os
from typing import Protocol,Any
from uuid import UUID
import boto3
from strands import Agent,tool
from strands.models import BedrockModel
from services.planning_foundation.replanning_models import ReplanDecision
from services.planning_foundation.replanning_service import ReplanningService
MODEL_ID='us.amazon.nova-2-lite-v1:0';AGENT_NAME='hatcommways-replanning-agent'
class ReplanningRuntime(Protocol):
 def generate(self,*,event_id:UUID,blocker_id:UUID,organizer_id:UUID)->Any:...
class StrandsReplanningAgent:
 def __init__(self,service):self.service=service
 def generate(self,*,event_id,blocker_id,organizer_id):
  calls=0
  @tool(name='get_selective_replan_context',description='Return only affected plan scope and frozen unaffected work IDs.')
  def context():
   nonlocal calls;calls+=1;return self.service.context(event_id,blocker_id,organizer_id).model_dump(mode='json')
  model=BedrockModel(boto_session=boto3.Session(profile_name=os.environ.get('AWS_PROFILE','hatcommways'),region_name='us-east-1'),model_id=MODEL_ID,temperature=0,max_tokens=2600)
  agent=Agent(name=AGENT_NAME,model=model,tools=[context],structured_output_model=ReplanDecision,callback_handler=None,system_prompt='Call the scoped tool exactly once. Propose the smallest safe timing changes only for affected IDs. Never change unrelated work, apply changes, clear blockers, alter dependencies, assign actors, or self-approve. Return only typed output.')
  result=agent(f'Propose a selective replan for blocker {blocker_id} in event {event_id}.')
  if calls!=1 or result.structured_output is None:raise RuntimeError('replanning scoped tool contract failed')
  return ReplanDecision.model_validate(result.structured_output)
class ReplanningWorkflow:
 def __init__(self,service:ReplanningService,runtime:ReplanningRuntime):self.service=service;self.runtime=runtime
 def execute(self,*,event_id,blocker_id,organizer_id,retry=False):
  start=self.service.begin(event_id,blocker_id,organizer_id,retry=retry)
  if start.existing:return start.existing
  try:
   d=ReplanDecision.model_validate(self.runtime.generate(event_id=event_id,blocker_id=blocker_id,organizer_id=organizer_id))
   return self.service.complete(event_id,blocker_id,organizer_id,start.request_id,d,provider_name='amazon-bedrock',model_id=MODEL_ID,agent_name=AGENT_NAME,agent_version='v1',stop_reason='structured-output',usage={})
  except Exception as e:self.service.fail(event_id,blocker_id,start.request_id,type(e).__name__);raise
