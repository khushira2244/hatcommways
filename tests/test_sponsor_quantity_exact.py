"""Exact sponsor ledger regression checks in an isolated, rolled-back schema."""
import os
from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb
from services.planning_foundation.database import Database
from services.planning_foundation.support_offer_service import SupportOfferService
from services.planning_foundation.support_offer_models import OfferSubmit, OfferDecision
from services.planning_foundation.errors import ValidationError

@pytest.fixture
def ledger():
    dsn=os.environ.get('HATCOMMWAYS_QUANTITY_TEST_DATABASE_URL')
    if not dsn:pytest.skip('Set HATCOMMWAYS_QUANTITY_TEST_DATABASE_URL for isolated PostgreSQL checks')
    c=Database(dsn).connect()
    try:
        schema='quantity_test_'+uuid4().hex
        c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        c.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(schema)))
        c.execute(Path('services/planning_foundation/schema.sql').read_text(encoding='utf8'))
        owner,sponsor,event=uuid4(),uuid4(),uuid4()
        for aid in [owner,sponsor]:
            c.execute("INSERT INTO accounts(id,email,display_name,account_type,password_hash) VALUES(%s,%s,'Quantity test','ORGANIZATION','not-a-login')",(aid,str(aid)+'@example.test'))
        c.execute("INSERT INTO events(id,organizer_id,name,purpose,event_type,starts_at,ends_at,timezone,location_description) VALUES(%s,%s,'Quantity test','Test exact quantities','community',now(),now()+interval '1 day','UTC','Test location')",(event,owner))
        class Shared:
            def connect(self):return nullcontext(c)
        yield c,SupportOfferService(Shared()),owner,sponsor,event
    finally:
        c.rollback();c.close()

@pytest.mark.parametrize('required,quantities,expected',[
    ('1',['1'],'1'),('5',['2'],'2'),('1',['0.1','0.2','0.7'],'1'),('5',['2','1'],'3'),('1',['0.992'],'0.992')])
def test_exact_approved_quantity(ledger,required,quantities,expected):
    c,svc,owner,sponsor,event=ledger
    needs=[{'name':'Test resource','quantity':float(required),'unit':'units'}]
    c.execute("INSERT INTO event_setups(event_id,resource_needs,show_resources,show_sponsors,event_visibility) VALUES(%s,%s,true,true,'PUBLIC')",(event,Jsonb(needs)))
    rid=svc.workspace(event,sponsor)['needs'][0]['id']
    def submit(q):return svc.submit(event,sponsor,OfferSubmit(resource_need_id=rid,support_type='Material',quantity=q,idempotency_key=str(uuid4())))
    pending=submit('0.001');rejected=submit('0.001')
    svc.decide(event,rejected['id'],owner,OfferDecision(decision='REJECTED',expected_version=1))
    for q in quantities:
        offer=submit(q);assert offer['quantity']==Decimal(q)
        approved=svc.decide(event,offer['id'],owner,OfferDecision(decision='APPROVED',expected_version=1))
        assert approved['quantity']==Decimal(q)
    result=svc.workspace(event,owner)['needs'][0]
    assert result['pledged']==Decimal(expected)
    assert result['remaining']==Decimal(required)-Decimal(expected)
    assert c.execute('SELECT resource_needs FROM event_setups WHERE event_id=%s',(event,)).fetchone()['resource_needs']==needs
    with pytest.raises(ValidationError):submit(str(Decimal(required)-Decimal(expected)+Decimal('0.001')))
    if Decimal(required)==Decimal(expected):
        with pytest.raises(ValidationError):svc.decide(event,pending['id'],owner,OfferDecision(decision='APPROVED',expected_version=1))

