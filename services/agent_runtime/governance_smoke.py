import json
import os
from uuid import UUID
from services.agent_runtime.governance import StrandsGovernanceAgent
from services.planning_foundation.database import Database
from services.planning_foundation.governance_service import GovernanceService

database=Database(os.environ['HATCOMMWAYS_DATABASE_URL'])
event_id=UUID(os.environ['HATCOMMWAYS_GOVERNANCE_EVENT_ID'])
with database.connect() as connection:
    organizer_id=connection.execute("SELECT account_id FROM event_memberships WHERE event_id=%s AND role='ORGANIZER' AND status='ACTIVE'",(event_id,)).fetchone()['account_id']
proposal=StrandsGovernanceAgent(GovernanceService(database)).generate(event_id,organizer_id)
state=GovernanceService(database).store_assessment(proposal,organizer_id)
print(json.dumps({'typed':type(proposal).__name__,'event_id':str(proposal.event_id),'assessment_id':str(state['assessment']['id']),'governance_required':proposal.governance_required,'completeness':proposal.completeness,'review_mode':proposal.review_mode,'organizer_visible_status':state['assessment']['organizer_visible_status'],'item_categories':[str(item.category) for item in proposal.items]},indent=2,default=str))
