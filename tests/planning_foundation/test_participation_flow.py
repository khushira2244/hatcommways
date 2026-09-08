from uuid import UUID
from fastapi.testclient import TestClient
from services.api import create_app
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.models import ActorRequirementProposal,ProposalDecision,ProposalDecisionCommand
from tests.planning_foundation.test_actor_requirement import actor_payload
from tests.planning_foundation.work_helpers import create_approved_work

PASSWORD='correct horse battery staple'
def user(client,email,name):
    account=client.post('/auth/signup',json={'email':email,'display_name':name,'account_type':'INDIVIDUAL','password':PASSWORD}).json()
    token=client.post('/auth/signin',json={'email':email,'password':PASSWORD}).json()['access_token']
    return UUID(account['id']),{'Authorization':f'Bearer {token}'}

def test_join_advisory_partial_approval_notification_tree_and_my_events(database,service):
    client=TestClient(create_app(database));owner,oh=user(client,'join-owner@example.com','Organizer');actor,ah=user(client,'join-actor@example.com','Priya')
    event,stage,work,_=create_approved_work(database,service,owner)
    with database.connect() as c:c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')",(event.id,owner))
    ars=ActorRequirementService(database);req=ars.request_actor_requirements(event_id=event.id,stage_id=stage.id,work_id=work[0].id,organizer_id=owner,expected_event_version=event.version,expected_stage_version=stage.version,expected_work_version=work[0].version,idempotency_key='join-roles');ars.begin_request(req.id);done=ars.complete_request(req.id,ActorRequirementProposal.model_validate(actor_payload(event,stage,work[0])));ars.decide_actor_requirements(ProposalDecisionCommand(proposal_id=done.proposal_id,organizer_id=owner,decision=ProposalDecision.APPROVE,decision_idempotency_key='join-roles-ok'))
    setup={'expected_version':0,'idempotency_key':'join-public','initial_invites':[],'sponsors_support':[],'resources':[],'contribution_links':[],'map_settings':{'map_enabled':False,'participation_dimensions':[]},'privacy_settings':{'event_visibility':'PUBLIC','show_participant_counts':False,'show_actor_tree':True,'show_sponsors':False,'show_resources':False,'show_payment_links':False}}
    assert client.put(f'/events/{event.id}/setup',headers=oh,json=setup).status_code==200
    options=client.get(f'/events/{event.id}/join-options',headers=ah);assert options.status_code==200;choices=options.json()['options'];assert len(choices)==2 and all(x['remaining_count']==x['minimum_required_count'] for x in choices)
    selections=[{'actor_requirement_id':x['actor_requirement_id'],'preference':'PREFERRED' if i==0 else 'CAN_ALSO_HELP'} for i,x in enumerate(choices)]
    advisory=client.post(f'/events/{event.id}/participation-advisories',headers=ah,json={'selections':selections,'availability':{'availability_type':'FULL','allow_alternative_work':True}});assert advisory.status_code==201 and advisory.json()['result']['overall_advisory']=='GOOD_FIT'
    submitted=client.post(f'/events/{event.id}/participation-requests',headers=ah,json={'advisory_id':advisory.json()['id'],'note':'I can bring gloves.','idempotency_key':'join-submit'});assert submitted.status_code==201;request=submitted.json();assert request['status']=='PENDING' and len(request['items'])==2
    replay=client.post(f'/events/{event.id}/participation-requests',headers=ah,json={'advisory_id':advisory.json()['id'],'note':'I can bring gloves.','idempotency_key':'join-submit'});assert replay.json()['id']==request['id']
    notes=client.get(f'/events/{event.id}/participation-notifications',headers=oh);assert notes.status_code==200 and notes.json()[0]['request']['display_name']=='Priya'
    first,second=request['items'];approved=client.post(f"/participation-request-items/{first['id']}/decision",headers=oh,json={'decision':'APPROVE','idempotency_key':'decision-one'});assert approved.status_code==200
    rejected=client.post(f"/participation-request-items/{second['id']}/decision",headers=oh,json={'decision':'REJECT','idempotency_key':'decision-two'});assert rejected.json()['status']=='PARTIALLY_APPROVED'
    replay_decision=client.post(f"/participation-request-items/{first['id']}/decision",headers=oh,json={'decision':'APPROVE','idempotency_key':'decision-one'});assert replay_decision.status_code==200
    tree=client.get(f'/events/{event.id}/stages/{stage.id}/actor-tree-workspace',headers=oh).json();assert len(tree['participations'])==1 and tree['participations'][0]['display_name']=='Priya'
    mine=client.get('/me/events',headers=ah).json()['participating'];assert len(mine)==1 and mine[0]['relationship_status']=='PARTIALLY_APPROVED'
    assert mine[0]['resume_target']==f"actor-dashboard.html?event={event.id}"
    dashboard=client.get(f'/events/{event.id}/actor-dashboard',headers=ah);assert dashboard.status_code==200
    assert len(dashboard.json()['assignments'])==1 and len(dashboard.json()['rejected_selections'])==1
    meeting=client.post(f'/events/{event.id}/meetings',headers=oh,json={'title':'Volunteer Briefing','meeting_type':'BRIEFING','start_time':work[0].starts_at.isoformat(),'end_time':work[0].ends_at.isoformat(),'location':'Main entrance','audience':'ALL_ACTORS'});assert meeting.status_code==201
    meeting_data=meeting.json();rescheduled=client.put(f"/events/{event.id}/meetings/{meeting_data['id']}",headers=oh,json={'expected_version':meeting_data['version'],'start_time':work[0].starts_at.isoformat(),'end_time':work[0].ends_at.isoformat(),'location':'North gate','status':'RESCHEDULED'});assert rescheduled.status_code==200
    refreshed=client.get(f'/events/{event.id}/actor-dashboard',headers=ah).json();assert refreshed['meetings'][0]['location']=='North gate' and refreshed['meetings'][0]['status']=='RESCHEDULED'
    assert {x['update_type'] for x in refreshed['updates']}=={'PARTICIPATION_DECISION','MEETING_UPDATE'}
    with database.connect() as c:
        assert c.execute('SELECT count(*) AS n FROM participations WHERE event_id=%s',(event.id,)).fetchone()['n']==1
        assert c.execute("SELECT count(*) AS n FROM event_notifications WHERE event_id=%s AND notification_type='PARTICIPATION_REQUEST'",(event.id,)).fetchone()['n']==1
        types=[x['event_type'] for x in c.execute('SELECT event_type FROM domain_outbox WHERE aggregate_id=%s OR payload->>\'event_id\'=%s',(UUID(request['id']),str(event.id))).fetchall()]
        assert 'participation.requested' in types and 'participation.request_item_decided' in types and 'participation.created' in types
