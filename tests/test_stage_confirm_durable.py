"""Stage Plan confirmation against real commits in a disposable PostgreSQL schema."""
import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from services.api import create_app
from services.planning_foundation.models import StagePlanProposal
from services.planning_foundation.stage_planning_service import StagePlanningService


@pytest.fixture
def isolated_stage_db():
    dsn = os.environ.get('HATCOMMWAYS_STAGE_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set HATCOMMWAYS_STAGE_TEST_DATABASE_URL for isolated PostgreSQL tests')
    schema = 'stage_confirm_test_' + uuid4().hex
    with psycopg.connect(dsn) as connection:
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    class Isolated:
        def connect(self):
            return psycopg.connect(dsn, row_factory=dict_row, options=f'-c search_path={schema}')
    database = Isolated()
    try:
        with database.connect() as connection:
            connection.execute(Path('services/planning_foundation/schema.sql').read_text(encoding='utf8'))
        yield database
    finally:
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_persisted_plan_confirm_retry_and_reload(isolated_stage_db):
    db=isolated_stage_db
    client=TestClient(create_app(db))
    credentials={'email':'stage-confirm@example.test','password':'stage-confirm-test-password'}
    account=client.post('/auth/signup',json={**credentials,'display_name':'Test owner','account_type':'INDIVIDUAL'}).json()
    token=client.post('/auth/signin',json=credentials).json()['access_token']
    headers={'Authorization':f'Bearer {token}'}
    event_response=client.post('/events',headers=headers,json={
        'name':'Stage confirmation test','purpose':'Test persisted confirmation','event_type':'community',
        'starts_at':'2026-10-01T08:00:00Z','ends_at':'2026-10-01T16:00:00Z','timezone':'UTC',
        'location_description':'Test location','idempotency_key':'stage-confirm-event'})
    assert event_response.status_code==201,event_response.text
    event=event_response.json();eid=event['id']
    service=StagePlanningService(db)
    request=service.request_event_planning(event_id=UUID(eid),organizer_id=UUID(account['id']),expected_event_version=1,idempotency_key='stage-confirm-request')
    service.begin_request(request.id)
    proposal=StagePlanProposal.model_validate({
        'proposal_id':str(uuid4()),'event_id':eid,'base_event_version':1,'approval_required':True,
        'assumptions':[],'concise_rationale':'Prepare before execution','proposed_stages':[
            {'temporary_stage_ref':'prepare','canonical_name':'Preparation','purpose':'Prepare safely','proposed_order':1,'proposed_start':event['starts_at'],'proposed_end':'2026-10-01T10:00:00Z','dependencies':[]},
            {'temporary_stage_ref':'execute','canonical_name':'Execution','purpose':'Carry out work','proposed_order':2,'proposed_start':'2026-10-01T10:00:00Z','proposed_end':event['ends_at'],'dependencies':['prepare']}]})
    service.complete_request(request.id,proposal)
    url=f'/events/{eid}/stage-plan-workspace'
    assert client.get(url,headers=headers).json()['mode']=='PROPOSAL'
    decision_url=f'/stage-proposals/{proposal.proposal_id}/decision'
    body={'decision':'APPROVE','decision_idempotency_key':f'stage-approval:{proposal.proposal_id}'}
    # No model/raw JSON and no edited payload are needed for confirmation.
    first=client.post(decision_url,headers=headers,json=body)
    assert first.status_code==200,first.text
    assert first.json()['status']=='APPROVED'
    ids=[s['id'] for s in first.json()['stages']]
    # New app + new connections recover committed truth even if POST response was lost.
    reloaded=TestClient(create_app(db)).get(url,headers=headers)
    assert reloaded.status_code==200
    assert reloaded.json()['mode']=='CONFIRMED'
    assert [s['id'] for s in reloaded.json()['stages']]==ids
    duplicate=client.post(decision_url,headers=headers,json=body)
    assert duplicate.status_code==200
    assert duplicate.json()['duplicate'] is True
    assert [s['id'] for s in duplicate.json()['stages']]==ids
    with db.connect() as c:
        assert c.execute('SELECT count(*) AS n FROM stages').fetchone()['n']==2
        assert c.execute('SELECT count(*) AS n FROM stage_dependencies').fetchone()['n']==1
        assert c.execute('SELECT count(*) AS n FROM proposal_decisions').fetchone()['n']==1
        assert c.execute('SELECT count(*) AS n FROM work_items').fetchone()['n']==0
        assert c.execute('SELECT version FROM events').fetchone()['version']==2
        assert c.execute("SELECT count(*) AS n FROM domain_outbox WHERE event_type='event.stage_plan_approved'").fetchone()['n']==1
