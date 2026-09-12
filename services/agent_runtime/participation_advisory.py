import os
from typing import Any
import boto3
from strands import Agent
from strands.models import BedrockModel
from services.planning_foundation.participation_models import ParticipationAdvisory

REGION='us-east-1'; MODEL_ID='us.amazon.nova-2-lite-v1:0'
class StrandsParticipationAdvisoryAgent:
    def generate(self,context:dict[str,Any])->ParticipationAdvisory:
        session=boto3.Session(profile_name=os.environ.get('AWS_PROFILE'),region_name=REGION)
        agent=Agent(name='hatcommways-participation-advisory-agent',model=BedrockModel(boto_session=session,model_id=MODEL_ID,temperature=0,max_tokens=1800),structured_output_model=ParticipationAdvisory,callback_handler=None,system_prompt='You are Hatcommways Participation Advisory. Assess schedule overlap, partial availability, conflicting selections, excessive requested time, and timing compatibility. Suggest alternatives only when allowed. You are advisory only: never approve, reject, assign, judge personal capability, or prevent submission. Return only the typed advisory.')
        result=agent(f'Assess this authoritative participation context: {context}')
        if result.structured_output is None: raise RuntimeError('Strands returned no typed participation advisory')
        return ParticipationAdvisory.model_validate(result.structured_output)

class DeterministicParticipationAdvisory:
    def generate(self,context):
        availability=context['availability']; findings=[]
        if availability['availability_type']=='PARTIAL': findings.append({'level':'WARNING','message':'Your availability covers only part of the selected work window.','affected_selection_ids':[x['actor_requirement_id'] for x in context['selections']]})
        return ParticipationAdvisory(overall_advisory='REVIEW_SUGGESTED' if findings else 'GOOD_FIT',findings=findings,suggested_adjustments=[],explanation='Selections were compared with authoritative work timing and current commitments. Organizer review is still required.')
