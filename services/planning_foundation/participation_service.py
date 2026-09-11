from uuid import UUID,uuid4
from psycopg.types.json import Jsonb
from .database import Database
from .errors import AuthorizationError,NotFoundError,ValidationError
from .participation_models import AdvisoryRequest,ParticipationAdvisory,ParticipationSubmit
from .services import PlanningService

class ParticipationService:
    def __init__(self,database:Database): self.database=database

    def join_options(self,event_id:UUID,account_id:UUID):
        with self.database.connect() as c:
            event=c.execute('SELECT * FROM events WHERE id=%s',(event_id,)).fetchone()
            if not event: raise NotFoundError('event not found')
            setup=c.execute('SELECT event_visibility FROM event_setups WHERE event_id=%s',(event_id,)).fetchone()
            membership=c.execute("SELECT role FROM event_memberships WHERE event_id=%s AND account_id=%s AND status='ACTIVE'",(event_id,account_id)).fetchone()
            if setup and setup['event_visibility']=='PRIVATE' and not membership: raise AuthorizationError('this event is private')
            options=c.execute("""SELECT ar.id AS actor_requirement_id,ar.stage_id,ar.work_id,ar.canonical_role_name AS role_name,
                    ar.responsibility_summary,ar.minimum_required_count,s.stage_order,s.canonical_name AS stage_name,
                    w.canonical_name AS work_name,w.purpose AS work_purpose,w.starts_at,w.ends_at,w.estimated_person_hours,
                    (SELECT count(*) FROM participations p WHERE p.actor_requirement_id=ar.id AND p.status='ACCEPTED') AS accepted_count
                FROM actor_requirements ar JOIN stages s ON s.id=ar.stage_id JOIN work_items w ON w.id=ar.work_id
                WHERE ar.event_id=%s ORDER BY s.stage_order,w.starts_at,w.canonical_name,ar.canonical_role_name""",(event_id,)).fetchall()
            latest=c.execute("SELECT id,status,created_at FROM participation_requests WHERE event_id=%s AND requester_account_id=%s ORDER BY created_at DESC LIMIT 1",(event_id,account_id)).fetchone()
            accepted=c.execute("SELECT count(*) AS count FROM participations WHERE event_id=%s AND account_id=%s AND status='ACCEPTED'",(event_id,account_id)).fetchone()['count']
        return {'event':event,'options':[dict(x)|{'remaining_count':max(0,x['minimum_required_count']-x['accepted_count'])} for x in options],'latest_request':latest,'accepted_participation_count':accepted}

    def advisory_context(self,event_id,account_id,body:AdvisoryRequest):
        options=self.join_options(event_id,account_id); by_id={str(x['actor_requirement_id']):x for x in options['options']}
        selected=[]
        for choice in body.selections:
            option=by_id.get(str(choice.actor_requirement_id))
            if not option: raise ValidationError('selected role is not an authoritative join option for this event')
            selected.append(option|{'preference':choice.preference})
        with self.database.connect() as c:
            commitments=c.execute("SELECT approved_start,approved_end FROM participations WHERE account_id=%s AND status='ACCEPTED'",(account_id,)).fetchall()
            pending=c.execute("SELECT pr.event_id,pri.availability_start,pri.availability_end FROM participation_request_items pri JOIN participation_requests pr ON pr.id=pri.participation_request_id WHERE pr.requester_account_id=%s AND pri.status='PENDING'",(account_id,)).fetchall()
        return {'event':options['event'],'selections':selected,'availability':body.availability.model_dump(mode='json'),'accepted_commitments':commitments,'pending_requests':pending}

    def store_advisory(self,event_id,account_id,body,result:ParticipationAdvisory):
        advisory_id=uuid4()
        with self.database.connect() as c:c.execute('INSERT INTO participation_advisories(id,event_id,requester_account_id,selections,availability,result) VALUES(%s,%s,%s,%s,%s,%s)',(advisory_id,event_id,account_id,Jsonb([x.model_dump(mode='json') for x in body.selections]),Jsonb(body.availability.model_dump(mode='json')),Jsonb(result.model_dump(mode='json'))))
        return {'id':advisory_id,'event_id':event_id,'result':result}

    def submit(self,event_id,account_id,body:ParticipationSubmit):
        with self.database.connect() as c:
            replay=c.execute('SELECT * FROM participation_requests WHERE idempotency_key=%s',(body.idempotency_key,)).fetchone()
            if replay:
                if replay['event_id']!=event_id or replay['requester_account_id']!=account_id: raise ValidationError('idempotency key already used')
                return self.get_request(replay['id'],account_id)
            advisory=c.execute('SELECT * FROM participation_advisories WHERE id=%s AND event_id=%s AND requester_account_id=%s',(body.advisory_id,event_id,account_id)).fetchone()
            if not advisory: raise ValidationError('a current advisory for this event is required')
            request_id=uuid4(); correlation=uuid4()
            c.execute("INSERT INTO participation_requests(id,event_id,requester_account_id,status,note,advisory_id,advisory_summary,idempotency_key,correlation_id) VALUES(%s,%s,%s,'PENDING',%s,%s,%s,%s,%s)",(request_id,event_id,account_id,body.note,body.advisory_id,Jsonb(advisory['result']),body.idempotency_key,correlation))
            availability=advisory['availability']
            for selection in advisory['selections']:
                row=c.execute('SELECT stage_id,work_id FROM actor_requirements WHERE id=%s AND event_id=%s',(selection['actor_requirement_id'],event_id)).fetchone()
                if not row: raise ValidationError('advisory selection is no longer available')
                c.execute("""INSERT INTO participation_request_items(id,participation_request_id,stage_id,work_id,actor_requirement_id,preference,availability_type,availability_start,availability_end,max_commitment_minutes,allow_alternative_work)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(uuid4(),request_id,row['stage_id'],row['work_id'],selection['actor_requirement_id'],selection['preference'],availability['availability_type'],availability.get('availability_start'),availability.get('availability_end'),availability.get('max_commitment_minutes'),availability['allow_alternative_work']))
            organizer=c.execute("SELECT account_id FROM event_memberships WHERE event_id=%s AND role='ORGANIZER' AND status='ACTIVE'",(event_id,)).fetchone()
            c.execute("INSERT INTO event_notifications(id,account_id,event_id,notification_type,participation_request_id) VALUES(%s,%s,%s,'PARTICIPATION_REQUEST',%s) ON CONFLICT DO NOTHING",(uuid4(),organizer['account_id'],event_id,request_id))
            PlanningService._enqueue_outbox(c,event_type='participation.requested',aggregate_type='PARTICIPATION_REQUEST',aggregate_id=request_id,aggregate_version=1,payload={'event_id':str(event_id),'requester_account_id':str(account_id),'requested_assignment_count':len(advisory['selections'])},correlation_id=correlation)
        return self.get_request(request_id,account_id)

    def get_request(self,request_id,account_id=None,organizer=False):
        with self.database.connect() as c:
            row=c.execute('SELECT pr.*,a.display_name,a.email FROM participation_requests pr JOIN accounts a ON a.id=pr.requester_account_id WHERE pr.id=%s',(request_id,)).fetchone()
            if not row: raise NotFoundError('participation request not found')
            if organizer:
                owner=c.execute("SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s AND role='ORGANIZER' AND status='ACTIVE'",(row['event_id'],account_id)).fetchone()
                if not owner: raise AuthorizationError('organizer authorization required')
            elif account_id and row['requester_account_id']!=account_id: raise AuthorizationError('request belongs to another account')
            items=c.execute("""SELECT pri.*,s.canonical_name AS stage_name,w.canonical_name AS work_name,w.starts_at AS work_start,w.ends_at AS work_end,
                    ar.canonical_role_name AS role_name,ar.minimum_required_count,
                    (SELECT count(*) FROM participations p WHERE p.actor_requirement_id=ar.id AND p.status='ACCEPTED') AS accepted_count
                FROM participation_request_items pri JOIN stages s ON s.id=pri.stage_id JOIN work_items w ON w.id=pri.work_id JOIN actor_requirements ar ON ar.id=pri.actor_requirement_id WHERE participation_request_id=%s ORDER BY pri.created_at""",(request_id,)).fetchall()
        return dict(row)|{'items':[dict(item)|{'remaining_count':max(0,item['minimum_required_count']-item['accepted_count'])} for item in items]}

    def notifications(self,event_id,organizer_id):
        with self.database.connect() as c:
            owner=c.execute("SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s AND role='ORGANIZER' AND status='ACTIVE'",(event_id,organizer_id)).fetchone()
            if not owner: raise AuthorizationError('organizer authorization required')
            notes=c.execute("SELECT * FROM event_notifications WHERE event_id=%s AND account_id=%s ORDER BY created_at DESC",(event_id,organizer_id)).fetchall()
        return [dict(n)|{'request':self.get_request(n['participation_request_id'],organizer_id,True)} for n in notes]

    def decide_item(self,item_id,organizer_id,decision,idempotency_key):
        with self.database.connect() as c:
            replay=c.execute('SELECT request_item_id,organizer_id,decision FROM participation_item_decisions WHERE idempotency_key=%s',(idempotency_key,)).fetchone()
            if replay:
                if replay['request_item_id']!=item_id or replay['organizer_id']!=organizer_id or replay['decision']!=decision: raise ValidationError('idempotency key already used for a different decision')
                request_id=c.execute('SELECT participation_request_id FROM participation_request_items WHERE id=%s',(item_id,)).fetchone()['participation_request_id']
                return self.get_request(request_id,organizer_id,True)
            item=c.execute("""SELECT pri.*,pr.event_id,pr.requester_account_id,pr.correlation_id,w.starts_at AS work_start,w.ends_at AS work_end
                FROM participation_request_items pri JOIN participation_requests pr ON pr.id=pri.participation_request_id JOIN work_items w ON w.id=pri.work_id WHERE pri.id=%s FOR UPDATE""",(item_id,)).fetchone()
            if not item: raise NotFoundError('participation request item not found')
            owner=c.execute("SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s AND role='ORGANIZER' AND status='ACTIVE'",(item['event_id'],organizer_id)).fetchone()
            if not owner: raise AuthorizationError('organizer authorization required')
            target='APPROVED' if decision=='APPROVE' else 'REJECTED'
            if item['status']!='PENDING' and item['status']!=target: raise ValidationError('request item was already decided differently')
            c.execute('INSERT INTO participation_item_decisions(id,request_item_id,organizer_id,decision,idempotency_key) VALUES(%s,%s,%s,%s,%s)',(uuid4(),item_id,organizer_id,decision,idempotency_key))
            c.execute('UPDATE participation_request_items SET status=%s,updated_at=now() WHERE id=%s',(target,item_id))
            role=c.execute('SELECT canonical_role_name FROM actor_requirements WHERE id=%s',(item['actor_requirement_id'],)).fetchone()
            work=c.execute('SELECT canonical_name FROM work_items WHERE id=%s',(item['work_id'],)).fetchone()
            c.execute("""INSERT INTO actor_updates(id,event_id,recipient_account_id,audience,update_type,title,message,priority)
                VALUES(%s,%s,%s,'ACTOR','PARTICIPATION_DECISION',%s,%s,'NORMAL')""",
                (uuid4(),item['event_id'],item['requester_account_id'],f"Assignment {target.lower()}",f"{work['canonical_name']} · {role['canonical_role_name']} was {target.lower()}."))
            if target=='APPROVED':
                start=item['availability_start'] or item['work_start'];end=item['availability_end'] or item['work_end']
                c.execute("""INSERT INTO participations(id,event_id,account_id,work_id,stage_id,actor_requirement_id,approved_from_request_item_id,approved_start,approved_end)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(approved_from_request_item_id) DO NOTHING""",(uuid4(),item['event_id'],item['requester_account_id'],item['work_id'],item['stage_id'],item['actor_requirement_id'],item_id,start,end))
                c.execute("INSERT INTO event_memberships(event_id,account_id,role,status) VALUES(%s,%s,'ACTOR','ACTIVE') ON CONFLICT(event_id,account_id,role) DO UPDATE SET status='ACTIVE',updated_at=now()",(item['event_id'],item['requester_account_id']))
            statuses=[x['status'] for x in c.execute('SELECT status FROM participation_request_items WHERE participation_request_id=%s',(item['participation_request_id'],)).fetchall()]
            status='PENDING' if 'PENDING' in statuses else ('APPROVED' if all(x=='APPROVED' for x in statuses) else ('REJECTED' if all(x=='REJECTED' for x in statuses) else 'PARTIALLY_APPROVED'))
            c.execute('UPDATE participation_requests SET status=%s,updated_at=now() WHERE id=%s',(status,item['participation_request_id']))
            PlanningService._enqueue_outbox(c,event_type='participation.request_item_decided',aggregate_type='PARTICIPATION_REQUEST',aggregate_id=item['participation_request_id'],aggregate_version=1,payload={'event_id':str(item['event_id']),'request_item_id':str(item_id),'decision':decision,'idempotency_key':idempotency_key},correlation_id=item['correlation_id'])
            if target=='APPROVED': PlanningService._enqueue_outbox(c,event_type='participation.created',aggregate_type='PARTICIPATION',aggregate_id=item_id,aggregate_version=1,payload={'event_id':str(item['event_id']),'account_id':str(item['requester_account_id'])},correlation_id=item['correlation_id'])
        return self.get_request(item['participation_request_id'],organizer_id,True)
