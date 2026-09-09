"""Real PostgreSQL contracts for human reports and blocker state, with no agents."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.human_update_service import HumanUpdateService
from services.planning_foundation.human_update_models import HumanUpdateCreate, BlockerCreate
from services.planning_foundation.models import ActorRequirementProposal, ProposalDecisionCommand
from tests.planning_foundation.work_helpers import create_approved_work
from tests.planning_foundation.test_actor_requirement import actor_payload
from tests.planning_foundation.test_participation_flow import user

TEXT = 'I can only arrive at 11 because the road is blocked.'


@pytest.fixture
def scenario(database, service):
    client = TestClient(create_app(database))
    owner, oh = user(client, 'reports-owner@example.com', 'Organizer')
    actor, ah = user(client, 'reports-priya@example.com', 'Priya')
    stranger, sh = user(client, 'reports-other@example.com', 'Unrelated')
    event, stage, work, other_stage = create_approved_work(database, service, owner)
    with database.connect() as c:
        c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')", (event.id,owner))
        c.execute("UPDATE events SET name='Gachibowli Lake Cleanup' WHERE id=%s", (event.id,))
        c.execute("UPDATE work_items SET canonical_name='Shoreline Cleanup' WHERE id=%s", (work[0].id,))
    actors = ActorRequirementService(database)
    request = actors.request_actor_requirements(event_id=event.id,stage_id=stage.id,work_id=work[0].id,organizer_id=owner,
        expected_event_version=event.version,expected_stage_version=stage.version,expected_work_version=work[0].version,idempotency_key='report-roles')
    actors.begin_request(request.id)
    done = actors.complete_request(request.id,ActorRequirementProposal.model_validate(actor_payload(event,stage,work[0])))
    actors.decide_actor_requirements(ProposalDecisionCommand(proposal_id=done.proposal_id,organizer_id=owner,decision='APPROVE',decision_idempotency_key='report-roles-ok'))
    setup = {'expected_version':0,'idempotency_key':'public','initial_invites':[],'sponsors_support':[],'resources':[],'contribution_links':[],
        'map_settings':{'map_enabled':False,'participation_dimensions':[]},'privacy_settings':{'event_visibility':'PUBLIC','show_participant_counts':False,'show_actor_tree':True,'show_sponsors':False,'show_resources':False,'show_payment_links':False}}
    assert client.put(f'/events/{event.id}/setup',headers=oh,json=setup).status_code == 200
    roles = client.get(f'/events/{event.id}/join-options',headers=ah).json()['options']
    advisory = client.post(f'/events/{event.id}/participation-advisories',headers=ah,json={'selections':[{'actor_requirement_id':r['actor_requirement_id']} for r in roles],'availability':{'availability_type':'FULL'}}).json()
    requested = client.post(f'/events/{event.id}/participation-requests',headers=ah,json={'advisory_id':advisory['id'],'idempotency_key':'priya-join'}).json()
    accepted, rejected = requested['items']
    assert client.post(f"/participation-request-items/{accepted['id']}/decision",headers=oh,json={'decision':'APPROVE','idempotency_key':'accept-priya'}).status_code == 200
    result = client.post(f"/participation-request-items/{rejected['id']}/decision",headers=oh,json={'decision':'REJECT','idempotency_key':'reject-optional'})
    assert result.json()['status'] == 'PARTIALLY_APPROVED'
    meeting = client.post(f'/events/{event.id}/meetings',headers=oh,json={'title':'Volunteer briefing','meeting_type':'BRIEFING','start_time':work[0].starts_at.isoformat(),'end_time':work[0].ends_at.isoformat(),'audience':'ALL_ACTORS'})
    assert meeting.status_code == 201
    with database.connect() as c:
        participation = c.execute("SELECT * FROM participations WHERE account_id=%s AND event_id=%s",(actor,event.id)).fetchone()
    return dict(client=client,owner=owner,actor=actor,stranger=stranger,oh=oh,ah=ah,sh=sh,event=event,stage=stage,work=work,other_stage=other_stage,participation=participation,rejected_role=rejected['actor_requirement_id'])


def unchanged_state(database):
    tables = ['events','stages','work_items','event_meetings','accounts','participations','event_memberships',
              'actor_requirements','actor_requirement_requests','event_planning_requests','work_design_requests',
              'participation_requests','participation_request_items','proposals','domain_outbox','event_notifications','actor_updates']
    with database.connect() as c:
        return {table:c.execute(f'SELECT * FROM {table} ORDER BY ' + ('event_id,account_id' if table == 'event_memberships' else 'id')).fetchall() for table in tables}


def report(s, **changes):
    return s['client'].post(f"/events/{s['event'].id}/human-updates",headers=s['ah'],json={'text':TEXT,'work_id':str(s['work'][0].id),**changes})


def create_blocker(s, source, **changes):
    return s['client'].post(f"/events/{s['event'].id}/blockers",headers=s['oh'],json={'human_update_id':source,'title':'Late arrival affecting shoreline cleanup','summary':'Priya can only arrive at 11.',**changes})


def test_priya_report_blocker_lifecycle_exact_text_and_no_plan_or_agent_changes(database, scenario, monkeypatch):
    s = scenario
    from services.agent_runtime.event_planning import EventPlanningWorkflow
    from services.agent_runtime.work_design import WorkDesignWorkflow
    from services.agent_runtime.actor_requirement import ActorRequirementWorkflow
    from services.agent_runtime.governance import GovernanceWorkflow
    def forbidden(*args, **kwargs):
        pytest.fail('human update/blocker executed an agent')
    for workflow in (EventPlanningWorkflow,WorkDesignWorkflow,ActorRequirementWorkflow,GovernanceWorkflow):
        monkeypatch.setattr(workflow,'execute',forbidden)
    before = unchanged_state(database)
    response = report(s)
    assert response.status_code == 201, response.text
    update = response.json()
    assert update['original_text'] == TEXT
    assert update['reporter_account_id'] == str(s['actor']) and update['source_type'] == 'ACTOR'
    assert update['stage_id'] == str(s['stage'].id)
    assert update['interpretation_status'] == 'NOT_REQUESTED' and update['interpreted_at'] is None
    base = f"/events/{s['event'].id}"
    assert s['client'].get(base+'/blockers',headers=s['oh']).json() == []
    assert s['client'].get(base+'/human-updates',headers=s['oh']).json()[0]['original_text'] == TEXT
    created = create_blocker(s,update['id']); assert created.status_code == 201, created.text
    b = created.json()
    assert (b['handling_state'],b['condition_state']) == ('ACKNOWLEDGED','OPEN')
    assert b['source_human_update']['original_text'] == TEXT
    assert b['reported_by_display_name'] == 'Priya' and b['work_name'] == 'Shoreline Cleanup'
    endpoint = base+f"/blockers/{b['id']}"
    working = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':1,'handling_state':'WORKING'}).json()
    assert working['handling_state'] == 'WORKING' and working['condition_state'] == 'OPEN'
    cleared = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':2,'condition_state':'CLEARED'}).json()
    assert cleared['condition_state'] == 'CLEARED' and cleared['cleared_at'] is not None and cleared['handling_state'] == 'WORKING'
    replay = create_blocker(s,update['id']).json()
    assert replay['id'] == b['id'] and replay['condition_state'] == 'CLEARED' and replay['version'] == 3
    stale = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':1,'handling_state':'STALLED'})
    assert stale.status_code == 409
    stalled = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':3,'handling_state':'STALLED'}).json()
    assert stalled['condition_state'] == 'CLEARED' and stalled['cleared_at'] == cleared['cleared_at']
    opened = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':4,'condition_state':'OPEN'}).json()
    assert opened['condition_state'] == 'OPEN' and opened['cleared_at'] is None and opened['handling_state'] == 'STALLED'
    noop = s['client'].patch(endpoint,headers=s['oh'],json={'expected_version':5,'condition_state':'OPEN'}).json()
    assert noop['version'] == 5
    assert len(s['client'].get(base+'/blockers',headers=s['oh']).json()) == 1
    assert unchanged_state(database) == before


def test_exact_whitespace_unicode_immutable_at_database_and_no_classification_input(database, scenario):
    s = scenario
    text = '\t  I can only arrive at 11.\r\nRoad blocked — near the lake.  \n'
    response = report(s,text=text,idempotency_key='exact')
    assert response.status_code == 201 and response.json()['original_text'] == text
    assert report(s,text=text,idempotency_key='exact').json()['id'] == response.json()['id']
    assert report(s,text=text+'changed',idempotency_key='exact').status_code == 409
    with pytest.raises(psycopg.errors.CheckViolation):
        with database.connect() as c:
            c.execute('UPDATE human_updates SET original_text=%s WHERE id=%s',('changed',response.json()['id']))
    with database.connect() as c:
        assert c.execute('SELECT original_text FROM human_updates WHERE id=%s',(response.json()['id'],)).fetchone()['original_text'] == text
    for payload in ({'text':'  \t\r\n'}, {'text':'x'*10001}, {'text':'x','reporter_account_id':str(s['owner'])}, {'text':'x','source_type':'ORGANIZER'}):
        assert s['client'].post(f"/events/{s['event'].id}/human-updates",headers=s['ah'],json=payload).status_code == 422


def test_participant_scope_permissions_and_organizer_reports(database, scenario):
    s = scenario; base=f"/events/{s['event'].id}"
    assert s['client'].post(base+'/human-updates',json={'text':TEXT}).status_code == 401
    assert s['client'].post(base+'/human-updates',headers=s['sh'],json={'text':TEXT}).status_code == 403
    assert report(s,work_id=str(s['work'][1].id)).status_code == 403
    assert report(s,work_id=None,stage_id=str(s['other_stage'].id)).status_code == 403
    assert report(s,actor_requirement_id=s['rejected_role']).status_code == 403
    assert report(s,participation_id=str(s['participation']['id'])).status_code == 201
    assert report(s,work_id=None).status_code == 201  # Event-level report by accepted actor.
    assert report(s,stage_id=str(s['other_stage'].id)).status_code == 422
    own=s['client'].post(base+'/human-updates',headers=s['oh'],json={'text':'Organizer report','work_id':str(s['work'][1].id)})
    assert own.status_code == 201 and own.json()['source_type'] == 'ORGANIZER'
    update=report(s).json()
    for headers in (s['ah'],s['sh']):
        assert s['client'].get(base+'/human-updates',headers=headers).status_code == 403
        assert s['client'].get(base+'/blockers',headers=headers).status_code == 403
        assert s['client'].post(base+'/blockers',headers=headers,json={'human_update_id':update['id'],'title':'Blocker','summary':'Summary'}).status_code == 403
    blocker=create_blocker(s,update['id']).json()
    assert s['client'].patch(base+f"/blockers/{blocker['id']}",headers=s['ah'],json={'expected_version':1,'condition_state':'CLEARED'}).status_code == 403
    with database.connect() as c:
        c.execute("UPDATE participations SET status='WITHDRAWN_BY_PARTICIPANT' WHERE id=%s",(s['participation']['id'],))
    assert report(s).status_code == 403


def test_cross_event_source_context_and_blocker_ids_rejected(database, service, scenario):
    s=scenario
    other,other_stage,other_work,_=create_approved_work(database,service,s['owner'])
    with database.connect() as c:
        c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')",(other.id,s['owner']))
    assert report(s,work_id=str(other_work[0].id)).status_code == 422
    source=report(s).json()['id']
    body={'human_update_id':source,'title':'Blocked','summary':'Summary'}
    assert s['client'].post(f'/events/{other.id}/blockers',headers=s['oh'],json=body).status_code == 422
    assert create_blocker(s,source,work_id=str(other_work[0].id)).status_code == 422
    assert create_blocker(s,source,stage_id=str(other_stage.id)).status_code == 422
    blocker=create_blocker(s,source).json()
    assert s['client'].patch(f"/events/{other.id}/blockers/{blocker['id']}",headers=s['oh'],json={'expected_version':1,'condition_state':'CLEARED'}).status_code == 404
    assert s['client'].get(f'/events/{other.id}/blockers',headers=s['oh']).json() == []
    assert s['client'].post(f'/events/{other.id}/human-updates',headers=s['ah'],json={'text':TEXT}).status_code == 403


def test_concurrent_reports_blockers_dedup_and_conflicting_payloads(database, scenario):
    s=scenario; service=HumanUpdateService(database)
    body=HumanUpdateCreate(text=TEXT,work_id=s['work'][0].id,idempotency_key='same-report')
    with ThreadPoolExecutor(max_workers=2) as pool:
        updates=list(pool.map(lambda _:service.submit(s['event'].id,s['actor'],body),range(2)))
    assert updates[0].id == updates[1].id
    create=BlockerCreate(human_update_id=updates[0].id,title='Late arrival affecting shoreline cleanup',summary='Priya can only arrive at 11.',idempotency_key='same-blocker')
    with ThreadPoolExecutor(max_workers=2) as pool:
        blockers=list(pool.map(lambda _:service.create_blocker(s['event'].id,s['owner'],create),range(2)))
    assert blockers[0].id == blockers[1].id
    assert create_blocker(s,str(updates[0].id),title='Different title').status_code == 409
    assert create_blocker(s,str(updates[0].id),idempotency_key='different-key').status_code == 409
    another=report(s).json()['id']
    assert create_blocker(s,another,idempotency_key='same-blocker').status_code == 409
    with database.connect() as c:
        assert c.execute('SELECT count(*) FROM blockers').fetchone()['count'] == 1
        assert c.execute('SELECT count(*) FROM human_updates').fetchone()['count'] == 2
    endpoint=f"/events/{s['event'].id}/blockers/{blockers[0].id}"
    for patch in ({'expected_version':1}, {'expected_version':1,'handling_state':None}, {'expected_version':1,'handling_state':'RESOLVED'}, {'expected_version':1,'condition_state':'WORKING'}, {'expected_version':1,'work_id':str(s['work'][1].id)}):
        assert s['client'].patch(endpoint,headers=s['oh'],json=patch).status_code == 422

def test_pending_and_fully_approved_actor_and_foreign_participation_scope(database, scenario):
    s=scenario; base=f"/events/{s['event'].id}"
    role=str(s['participation']['actor_requirement_id'])
    advisory=s['client'].post(base+'/participation-advisories',headers=s['sh'],json={'selections':[{'actor_requirement_id':role}],'availability':{'availability_type':'FULL'}}).json()
    pending=s['client'].post(base+'/participation-requests',headers=s['sh'],json={'advisory_id':advisory['id'],'idempotency_key':'other-participant'}).json()
    assert pending['status']=='PENDING'
    assert s['client'].post(base+'/human-updates',headers=s['sh'],json={'text':TEXT}).status_code==403
    item=pending['items'][0]
    approved=s['client'].post(f"/participation-request-items/{item['id']}/decision",headers=s['oh'],json={'decision':'APPROVE','idempotency_key':'other-approved'})
    assert approved.json()['status']=='APPROVED'
    with database.connect() as c:
        other=c.execute('SELECT id FROM participations WHERE account_id=%s',(s['stranger'],)).fetchone()['id']
    own=s['client'].post(base+'/human-updates',headers=s['sh'],json={'text':TEXT,'participation_id':str(other)})
    assert own.status_code==201 and own.json()['work_id']==str(s['work'][0].id)
    assert report(s,participation_id=str(other)).status_code==403
    with database.connect() as c:
        c.execute("UPDATE participations SET status='REMOVED_BY_ORGANIZER' WHERE id=%s",(other,))
    assert s['client'].post(base+'/human-updates',headers=s['sh'],json={'text':TEXT}).status_code==403


def test_concurrent_state_changes_reject_stale_writer_and_inactive_organizer(database, scenario):
    from services.planning_foundation.human_update_models import BlockerPatch
    from services.planning_foundation.errors import StaleVersionError
    s=scenario; source=report(s).json()['id']; blocker=create_blocker(s,source).json()
    service=HumanUpdateService(database)
    def change(state):
        try:
            return service.update_blocker(s['event'].id,blocker['id'],s['owner'],BlockerPatch(expected_version=1,handling_state=state)).version
        except StaleVersionError:
            return 'STALE'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(change,['WORKING','STALLED']))
    assert sorted(map(str,results))==['2','STALE']
    with database.connect() as c:
        c.execute("UPDATE event_memberships SET status='INACTIVE' WHERE event_id=%s AND account_id=%s AND role='ORGANIZER'",(s['event'].id,s['owner']))
    base=f"/events/{s['event'].id}"
    assert s['client'].get(base+'/human-updates',headers=s['oh']).status_code==403
    assert s['client'].get(base+'/blockers',headers=s['oh']).status_code==403
    assert create_blocker(s,source).status_code==403
    assert s['client'].patch(base+f"/blockers/{blocker['id']}",headers=s['oh'],json={'expected_version':2,'condition_state':'CLEARED'}).status_code==403
