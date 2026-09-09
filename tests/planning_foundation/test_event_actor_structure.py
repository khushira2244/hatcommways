"""Event-wide actor requirements: authoritative hierarchy, reuse, and approval isolation."""
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from services.api import create_app
from services.planning_foundation.actor_requirement_service import ActorRequirementService
from services.planning_foundation.models import ActorRequirementProposal, ProposalDecisionCommand
from services.planning_foundation.errors import ValidationError
from services.planning_foundation.work_design_service import WorkDesignService
from tests.planning_foundation.work_helpers import create_approved_work, make_work_proposal
from tests.planning_foundation.test_actor_requirement import actor_payload


def multi_stage(database, service, organizer_id):
    event, first, _, second = create_approved_work(database, service, organizer_id)
    work_service = WorkDesignService(database)
    request = work_service.request_work_design(
        event_id=event.id, stage_id=second.id, organizer_id=organizer_id,
        expected_event_version=event.version, expected_stage_version=second.version,
        idempotency_key=f"second-work-{uuid4()}",
    )
    work_service.begin_request(request.id)
    completed = work_service.complete_request(request.id, make_work_proposal(event, second))
    work_service.decide_work_decomposition(ProposalDecisionCommand(
        proposal_id=completed.proposal_id, organizer_id=organizer_id,
        decision="APPROVE", decision_idempotency_key=f"second-work-approval-{uuid4()}",
    ))
    incomplete = uuid4()
    with database.connect() as connection:
        connection.execute("""INSERT INTO stages(id,event_id,canonical_name,purpose,stage_order,starts_at,ends_at,source_proposal_id)
            SELECT %s,event_id,'Incomplete stage',purpose,3,starts_at,ends_at,source_proposal_id FROM stages WHERE id=%s""", (incomplete, second.id))
    return service.get_event(event.id), incomplete


def pending(service, base, item, organizer):
    work = service.get_work(item['work'].id)
    stage = service.get_stage(work.stage_id)
    event = base.get_event(work.event_id)
    request = service.request_actor_requirements(
        event_id=event.id, stage_id=stage.id, work_id=work.id, organizer_id=organizer,
        expected_event_version=event.version, expected_stage_version=stage.version,
        expected_work_version=work.version, idempotency_key=f"actor-{work.id}",
    )
    service.begin_request(request.id)
    return service.complete_request(request.id, ActorRequirementProposal.model_validate(actor_payload(event, stage, work)))


def test_event_tree_reads_all_stages_and_confirms_across_stages_without_people(database, service):
    client = TestClient(create_app(database))
    owner = client.post('/auth/signup', json={'email':'event-tree@example.com','display_name':'Owner','account_type':'INDIVIDUAL','password':'correct horse battery staple'}).json()
    token = client.post('/auth/signin', json={'email':'event-tree@example.com','password':'correct horse battery staple'}).json()['access_token']
    headers = {'Authorization':f'Bearer {token}'}
    organizer = UUID(owner['id'])
    event, incomplete = multi_stage(database, service, organizer)
    with database.connect() as connection:
        connection.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ORGANIZER','ACTIVE')", (event.id,organizer))
        before = {table:connection.execute(f'SELECT count(*) FROM {table}').fetchone()['count'] for table in ['accounts','participations','event_memberships']}
    actors = ActorRequirementService(database)
    endpoint = f'/events/{event.id}/actor-tree-workspace'
    first = client.get(endpoint, headers=headers).json()
    assert len(first['stages']) == 3
    assert {i['work']['stage_id'] for i in first['work_items']} == {s['id'] for s in first['stages'] if s['id'] != str(incomplete)}
    assert len(first['work_items']) == 4
    assert 'participations' not in first
    proposals = [pending(actors, service, item, organizer) for item in actors.event_workspace(event.id)['work_items']]
    assert all(i['proposal']['status'] == 'PENDING' for i in client.get(endpoint, headers=headers).json()['work_items'])
    for request in proposals:
        response = client.post(f'/actor-requirement-proposals/{request.proposal_id}/decision', headers=headers,
            json={'decision':'APPROVE','decision_idempotency_key':f'actor-approval:{request.proposal_id}'})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'APPROVED'
        duplicate = client.post(f'/actor-requirement-proposals/{request.proposal_id}/decision', headers=headers,
            json={'decision':'APPROVE','decision_idempotency_key':f'actor-approval:{request.proposal_id}'})
        assert duplicate.json()['duplicate'] is True
    final = client.get(endpoint, headers=headers).json()
    assert len(final['stages']) == 3
    assert all(len(i['requirements']) == 2 for i in final['work_items'])
    assert all(r['stage_id'] == i['work']['stage_id'] for i in final['work_items'] for r in i['requirements'])
    saved = client.put(f'/events/{event.id}/resume-state', headers=headers, json={'current_phase':'ACTOR_REQUIREMENTS','last_open_stage_id':None})
    assert saved.status_code == 200
    listing = client.get('/me/events', headers=headers).json()
    assert next(i for i in listing['organizing'] if i['event_id']==str(event.id))['resume_target'] == f'actor-tree.html?event={event.id}'
    assert client.get(f'/events/{event.id}/setup', headers=headers).status_code == 200
    with database.connect() as connection:
        after = {table:connection.execute(f'SELECT count(*) FROM {table}').fetchone()['count'] for table in before}
        assert before == after
        assert connection.execute('SELECT count(*) FROM actor_requirement_requests').fetchone()['count'] == 4
        assert connection.execute('SELECT count(*) FROM actor_requirements').fetchone()['count'] == 8
    assert client.get(endpoint).status_code == 401
    stranger = client.post('/auth/signup', json={'email':'other-tree@example.com','display_name':'Other','account_type':'INDIVIDUAL','password':'correct horse battery staple'})
    other = client.post('/auth/signin', json={'email':'other-tree@example.com','password':'correct horse battery staple'}).json()['access_token']
    assert client.get(endpoint, headers={'Authorization':f'Bearer {other}'}).status_code == 403


def test_empty_approved_structure_is_reused_and_not_regenerated(database, service, organizer_id):
    event, _, _, _ = create_approved_work(database, service, organizer_id)
    actors = ActorRequirementService(database)
    item = actors.event_workspace(event.id)['work_items'][0]
    request = pending(actors, service, item, organizer_id)
    payload = service.get_proposal(request.proposal_id).payload
    payload['proposed_requirements'] = []
    actors.decide_actor_requirements(ProposalDecisionCommand(proposal_id=request.proposal_id, organizer_id=organizer_id, decision='APPROVE', decision_idempotency_key='empty-approve', edited_payload=payload))
    current = next(i for i in actors.event_workspace(event.id)['work_items'] if i['work'].id == item['work'].id)
    assert current['proposal']['status'] == 'APPROVED'
    assert current['requirements'] == []
    work = actors.get_work(item['work'].id); stage = actors.get_stage(work.stage_id)
    with pytest.raises(ValidationError, match='pending or approved'):
        actors.request_actor_requirements(event_id=event.id, stage_id=stage.id, work_id=work.id, organizer_id=organizer_id,
            expected_event_version=service.get_event(event.id).version, expected_stage_version=stage.version, expected_work_version=work.version, idempotency_key='attempt-new')


def test_concurrent_identical_requests_create_one_request_and_one_agent_run(database, service, organizer_id):
    from services.agent_runtime.actor_requirement import ActorRequirementWorkflow
    event, stage, work, _ = create_approved_work(database, service, organizer_id)
    actors = ActorRequirementService(database)
    args = dict(event_id=event.id,stage_id=stage.id,work_id=work[0].id,organizer_id=organizer_id,
        expected_event_version=event.version,expected_stage_version=stage.version,expected_work_version=work[0].version,idempotency_key='concurrent-actor')
    with ThreadPoolExecutor(max_workers=2) as pool:
        requests = list(pool.map(lambda _: actors.request_actor_requirements(**args), range(2)))
    assert requests[0].id == requests[1].id
    calls = []
    class Runtime:
        def generate(self, **kwargs):
            calls.append(kwargs['work_id'])
            return actor_payload(event,stage,work[0],kwargs['proposal_id'])
    workflow = ActorRequirementWorkflow(actors,Runtime())
    def execute(_):
        try: workflow.execute(requests[0].id)
        except ValidationError: pass
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(execute, range(2)))
    assert calls == [work[0].id]
    assert actors.get_request(requests[0].id).status.value == 'SUCCEEDED'


def test_cross_stage_approval_does_not_allow_unrelated_event_edit(database, service, organizer_id):
    event, _ = multi_stage(database, service, organizer_id)
    actors = ActorRequirementService(database)
    requests = [pending(actors,service,item,organizer_id) for item in actors.event_workspace(event.id)['work_items']]
    actors.decide_actor_requirements(ProposalDecisionCommand(proposal_id=requests[0].proposal_id,organizer_id=organizer_id,decision='APPROVE',decision_idempotency_key='first'))
    with database.connect() as connection:
        connection.execute('UPDATE events SET version=version+1 WHERE id=%s',(event.id,))
    result=actors.decide_actor_requirements(ProposalDecisionCommand(proposal_id=requests[-1].proposal_id,organizer_id=organizer_id,decision='APPROVE',decision_idempotency_key='stale'))
    assert result.status.value == 'STALE'
