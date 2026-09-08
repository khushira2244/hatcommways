import os
import pytest
from services.agent_runtime.participation_advisory import StrandsParticipationAdvisoryAgent

pytestmark=pytest.mark.skipif(os.environ.get('HATCOMMWAYS_RUN_REAL_BEDROCK')!='1',reason='set HATCOMMWAYS_RUN_REAL_BEDROCK=1 for the real model test')

def test_real_nova_participation_advisory_is_typed():
    result=StrandsParticipationAdvisoryAgent().generate({'event':{'name':'Lake Cleanup','starts_at':'2026-10-01T09:00:00+00:00','ends_at':'2026-10-01T15:00:00+00:00'},'selections':[{'actor_requirement_id':'11111111-1111-1111-1111-111111111111','work_name':'Waste collection','role_name':'Cleanup volunteer','starts_at':'2026-10-01T09:00:00+00:00','ends_at':'2026-10-01T12:00:00+00:00','preference':'PREFERRED'}],'availability':{'availability_type':'PARTIAL','availability_start':'2026-10-01T10:00:00+00:00','availability_end':'2026-10-01T12:00:00+00:00','max_commitment_minutes':120,'allow_alternative_work':True},'accepted_commitments':[],'pending_requests':[]})
    assert result.overall_advisory in {'GOOD_FIT','REVIEW_SUGGESTED','CONFLICT'}
    assert result.explanation
