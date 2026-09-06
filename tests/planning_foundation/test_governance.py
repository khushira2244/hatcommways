from uuid import UUID
from fastapi.testclient import TestClient
from services.api import create_app
from services.planning_foundation.governance_models import GovernanceProposal
from services.planning_foundation.governance_service import GovernanceService
from tests.planning_foundation.conftest import make_event_command

def account(client):
    body={'email':'governance@example.com','display_name':'Governance Owner','account_type':'INDIVIDUAL','password':'correct horse battery staple'}
    aid=client.post('/auth/signup',json=body).json()['id'];token=client.post('/auth/signin',json={'email':body['email'],'password':body['password']}).json()['access_token'];return UUID(aid),{'Authorization':f'Bearer {token}'}
def proposal(event,required,items,risk='LOW',review='NONE'):
    return GovernanceProposal.model_validate({'event_id':event.id,'base_event_version':event.version,'governance_required':required,'completeness':'INCOMPLETE' if required else 'NOT_REQUIRED','internal_risk':risk,'review_mode':review,'organizer_visible_status':'NEEDS_INFORMATION' if required else 'NOT_REQUIRED','location_context':event.location_description,'reasoning_summary':'Selective governance assessment.','items':items})
def item(category,label):return {'category':category,'label':label,'knowledge_type':'UNKNOWN','reason':'More event information is needed.','suggested_documents':['Organizer confirmation'],'status':'NEEDS_INFORMATION'}

def test_adaptive_governance_actions_ticket_and_boundaries(database,service):
    client=TestClient(create_app(database));owner,headers=account(client);gov=GovernanceService(database)
    events=[]
    for index,name in enumerate(('Tiny circle','Roadside cleanup','Large public festival')):
        event=service.create_event(make_event_command(owner,name=name,purpose=name),idempotency_key=f'gov-event-{index}');events.append(event)
        with database.connect() as c:c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')",(event.id,owner))
    tiny=gov.store_assessment(proposal(events[0],False,[]),owner);assert tiny['assessment']['governance_required'] is False and tiny['items']==[]
    road=gov.store_assessment(proposal(events[1],True,[item('TRAFFIC_ACCESS','Traffic / Access'),item('PUBLIC_SPACE_PERMISSION','Public Space Permission')],risk='MEDIUM',review='ORGANIZER'),owner);assert len(road['items'])==2
    complex_state=gov.store_assessment(proposal(events[2],True,[item('CROWD_CAPACITY','Crowd Capacity'),item('FOOD_VENDOR','Food Vendors'),item('SOUND_NOISE','Sound / Noise'),item('TRAFFIC_ACCESS','Traffic / Access'),item('EQUIPMENT_TEMPORARY_STRUCTURE','Temporary Structures')],risk='HIGH',review='HATCOMMWAYS'),owner);assert len(complex_state['items'])==5
    added=client.post(f'/events/{events[1].id}/governance/items',headers=headers,json={'category':'OTHER','label':'Local site approval','authority':'Local association','reason':'Organizer identified','evidence_reference':'SITE-42','idempotency_key':'manual-1'});assert added.status_code==201 and any(x['source']=='ORGANIZER_ADDED' for x in added.json()['items'])
    state=added.json();target=state['items'][0];evidence=client.post(f"/governance/items/{target['id']}/evidence",headers=headers,json={'evidence_type':'TEXT_CONFIRMATION','label':'Traffic confirmation','value_or_reference':'Organizer confirms marshals will manage access.','idempotency_key':'evidence-1'});assert evidence.status_code==201
    submitted=client.post(f'/events/{events[1].id}/governance/submit',headers=headers,json={'expected_version':evidence.json()['assessment']['version'],'idempotency_key':'submit-1'});assert submitted.status_code==200
    with database.connect() as c:
        assert c.execute('SELECT count(*) AS n FROM governance_tickets WHERE event_id=%s',(events[2].id,)).fetchone()['n']==1
        assert c.execute('SELECT internal_risk FROM governance_assessments WHERE event_id=%s',(events[2].id,)).fetchone()['internal_risk']=='HIGH'
        assert c.execute('SELECT count(*) AS n FROM stages').fetchone()['n']==0
        assert c.execute('SELECT count(*) AS n FROM event_memberships').fetchone()['n']==3
        types={r['event_type'] for r in c.execute("SELECT event_type FROM domain_outbox WHERE event_type LIKE 'governance.%'").fetchall()};assert {'governance.assessed','governance.submitted'}<=types
