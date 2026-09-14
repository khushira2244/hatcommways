from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from services.api import create_app
from services.agent_runtime.runtime_events import RuntimeEventEnvelope
from services.agent_runtime.runtime_worker import PostgresRuntimeRunRegistry, RuntimeHandler, RuntimeRouter, consume_runtime_event
from services.agent_runtime.sponsor_fit import SponsorFitWorkflow
from services.planning_foundation.support_offer_models import SponsorFit
from services.planning_foundation.support_offer_service import SupportOfferService
from tests.planning_foundation.conftest import create_event
from tests.planning_foundation.test_participation_flow import user


def test_offer_submit_runtime_fit_review_and_isolation(database, service):
    client = TestClient(create_app(database))
    owner, oh = user(client,'offer-owner@example.test','Organizer')
    actor, ah = user(client,'offer-sponsor@example.test','Bindeshwar Services')
    stranger, sh = user(client,'offer-stranger@example.test','Other account')
    event = create_event(service,owner)
    other = create_event(service,stranger)
    with database.connect() as c:
        c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')",(event.id,owner))
    setup = {'expected_version':0,'idempotency_key':str(uuid4()),'resources':[{'name':'Waste Transport Vehicle','quantity':1,'unit':'vehicle','note':'Vehicle with driver'}], 'privacy_settings':{'event_visibility':'PUBLIC','show_resources':True,'show_sponsors':True}}
    response=client.put(f'/events/{event.id}/setup',headers=oh,json=setup)
    assert response.status_code==200,response.text
    base=f'/events/{event.id}'
    workspace=client.get(base+'/support-offers',headers=ah).json()
    resource=workspace['needs'][0]['id']
    payload={'resource_need_id':resource,'support_type':'Transport','quantity':1,'availability_start':event.starts_at.isoformat(),'availability_end':event.ends_at.isoformat(),'comment':'We can provide one pickup vehicle and driver for waste transportation.','idempotency_key':str(uuid4())}
    response=client.post(base+'/support-offers',headers=ah,json=payload)
    assert response.status_code==201,response.text
    offer=response.json(); oid=offer['id']
    assert offer['status']=='PENDING'
    assert client.post(base+'/support-offers',headers=ah,json=payload).json()['id']==oid
    assert client.post(base+'/support-offers',headers=ah,json=dict(payload,comment='changed')).status_code==422
    assert client.get(base+'/support-offers',headers=sh).json()['offers']==[]
    assert client.get(base+'/support-offers',headers=oh).json()['approved']==[]
    notes=client.get(base+'/support-notifications',headers=oh).json()
    assert notes[0]['offer_id']==oid and notes[0]['event_id']==str(event.id) and not notes[0]['is_read']
    assert client.get(base+'/participation-notifications',headers=oh).json()==[]
    with database.connect() as c:
        row=c.execute("SELECT * FROM domain_outbox WHERE event_type='support_offer.submitted' AND aggregate_id=%s",(UUID(oid),)).fetchone()
    envelope=RuntimeEventEnvelope.from_outbox(row)
    calls=[]
    def generate(context):
        calls.append(context)
        assert context['event']['id']==event.id and context['remaining_gap']==1
        assert context['sponsor_profile']=={'display_name':'Bindeshwar Services'}
        return SponsorFit(match_level='STRONG',matches_need=True,timing_fit=True,remaining_gap_fit=True,summary='One vehicle matches the open transport need.',issues=[]),{'provider':'focused-fixture'}
    offers=SupportOfferService(database)
    workflow=SponsorFitWorkflow(offers,generate)
    router=RuntimeRouter({'support_offer.submitted':RuntimeHandler('hatcommways-sponsor-fit-agent',workflow.execute)})
    registry=PostgresRuntimeRunRegistry(database)
    result=consume_runtime_event(envelope,router=router,registry=registry)
    assert result.status=='SUCCEEDED',result
    assert consume_runtime_event(envelope,router=router,registry=registry).reused
    assert len(calls)==1
    assert offers.existing_fit(event.id,UUID(oid))['result']['match_level']=='STRONG'
    decision={'decision':'APPROVED','expected_version':1}
    assert client.post(base+f'/support-offers/{oid}/decision',headers=ah,json=decision).status_code==403
    assert client.post(f'/events/{other.id}/support-offers/{oid}/decision',headers=sh,json=decision).status_code in (404,422)
    # A second pending offer fits at submission; approval must recheck current gap.
    second=client.post(base+'/support-offers',headers=sh,json=dict(payload,idempotency_key=str(uuid4()))).json()['id']
    approved=client.post(base+f'/support-offers/{oid}/decision',headers=oh,json=decision)
    assert approved.status_code==200,approved.text
    assert client.post(base+f'/support-offers/{second}/decision',headers=oh,json=decision).status_code==422
    current=client.get(base+'/support-offers',headers=oh).json()
    assert len(current['approved'])==1 and current['needs'][0]['remaining']==0
    assert client.post(base+f'/support-offers/{second}/decision',headers=oh,json={'decision':'REJECTED','expected_version':1}).status_code==200
    after=client.get(base+'/support-offers',headers=oh).json()
    assert after['approved']==current['approved'] and after['needs']==current['needs']
    assert all(n['is_read'] for n in client.get(base+'/support-notifications',headers=oh).json())
    assert client.post(base+f'/support-offers/{oid}/decision',headers=oh,json=decision).status_code==409
    assert client.post(base+'/support-offers',headers=ah,json=dict(payload,resource_need_id=str(uuid4()),idempotency_key=str(uuid4()))).status_code==422
