import os
from typing import Any
from uuid import UUID
import boto3
from botocore.config import Config
from strands import Agent,tool
from strands.models import BedrockModel
from services.planning_foundation.governance_models import GovernanceProposal
from services.planning_foundation.governance_service import GovernanceService
REGION='us-east-1';MODEL_ID='us.amazon.nova-2-lite-v1:0'
class StrandsGovernanceAgent:
    def __init__(self,service:GovernanceService):self.service=service
    def generate(self,event_id:UUID,organizer_id:UUID)->GovernanceProposal:
        calls=0
        @tool(name='get_governance_event_facts',description='Get allowlisted authoritative facts for exactly one event. No participants, memberships, or unrelated events.')
        def get_governance_event_facts()->dict[str,Any]:
            nonlocal calls;calls+=1;return self.service.facts(event_id,organizer_id)
        model=BedrockModel(boto_session=boto3.Session(profile_name=os.environ.get('AWS_PROFILE','hatcommways'),region_name=REGION),boto_client_config=Config(connect_timeout=10,read_timeout=120,retries={'max_attempts':2,'mode':'standard'}),model_id=MODEL_ID,temperature=0,max_tokens=1800)
        agent=Agent(name='hatcommways-governance-agent',model=model,tools=[get_governance_event_facts],structured_output_model=GovernanceProposal,callback_handler=None,system_prompt="""You are the bounded Hatcommways Governance Agent. Call get_governance_event_facts exactly once. Then invoke the GovernanceProposal structured-output tool immediately; never answer in prose. Return only applicable governance checks, never a generic exhaustive checklist. Preserve uncertainty. Never describe a legal requirement as verified unless the supplied facts include a verified authority source; otherwise use COMMON_PRACTICE, AI_RISK_ADVISORY, or UNKNOWN. completeness must be NOT_REQUIRED, COMPLETE, or INCOMPLETE. internal_risk must be LOW, MEDIUM, or HIGH. review_mode must be NONE, ORGANIZER, or HATCOMMWAYS. organizer_visible_status must be NOT_REQUIRED, NEEDS_INFORMATION, EVIDENCE_REQUESTED, SUBMITTED, UNDER_REVIEW, or CLEARED. Tiny simple events should normally require no governance. Roadside activity may need only traffic/access and possibly public-space information. Large public events involving food, sound, traffic, temporary structures or large crowds may require several selective checks, HIGH internal risk, and HATCOMMWAYS review. Governance never blocks planning. Internal risk is backend-only. Do not mutate event state.""")
        event=self.service.base.get_event(event_id)
        result=agent(f'Assess event_id {event_id} at base_event_version {event.version}. Use this exact event_id and version. Call the scoped facts tool once, then submit exactly one typed GovernanceProposal using the structured-output tool.')
        if calls!=1:raise RuntimeError(f'governance facts tool must be called exactly once; observed {calls}')
        if result.structured_output is None:raise RuntimeError('Strands returned no typed GovernanceProposal')
        return GovernanceProposal.model_validate(result.structured_output)
class GovernanceWorkflow:
    def __init__(self,service:GovernanceService,runtime:StrandsGovernanceAgent):self.service=service;self.runtime=runtime
    def execute(self,event_id,organizer_id):return self.service.store_assessment(self.runtime.generate(event_id,organizer_id),organizer_id)
