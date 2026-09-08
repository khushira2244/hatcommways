from uuid import UUID, uuid4
from psycopg.types.json import Jsonb
from .errors import AuthorizationError, NotFoundError, ValidationError


class ActorDashboardService:
    def __init__(self, database): self.database = database

    def _organizer(self, c, event_id, account_id):
        if not c.execute("SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s AND role='ORGANIZER' AND status='ACTIVE'", (event_id, account_id)).fetchone():
            raise AuthorizationError('organizer authorization required')

    def get(self, event_id: UUID, account_id: UUID):
        with self.database.connect() as c:
            event=c.execute('SELECT * FROM events WHERE id=%s',(event_id,)).fetchone()
            if not event: raise NotFoundError('event not found')
            assignments=c.execute("""SELECT p.*,w.canonical_name work_name,w.purpose work_purpose,s.canonical_name stage_name,
                ar.canonical_role_name role_name,ar.responsibility_summary
                FROM participations p JOIN work_items w ON w.id=p.work_id JOIN stages s ON s.id=p.stage_id
                JOIN actor_requirements ar ON ar.id=p.actor_requirement_id
                WHERE p.event_id=%s AND p.account_id=%s AND p.status='ACCEPTED' ORDER BY p.approved_start""",(event_id,account_id)).fetchall()
            latest=c.execute("SELECT id,status FROM participation_requests WHERE event_id=%s AND requester_account_id=%s ORDER BY created_at DESC LIMIT 1",(event_id,account_id)).fetchone()
            if not assignments and (not latest or latest['status'] not in ('APPROVED','PARTIALLY_APPROVED')): raise AuthorizationError('approved participation required')
            meetings=c.execute("""SELECT DISTINCT m.* FROM event_meetings m LEFT JOIN participations p ON p.event_id=m.event_id AND p.account_id=%s AND p.status='ACCEPTED'
                WHERE m.event_id=%s AND (m.audience='ALL_ACTORS' OR (m.audience='STAGE' AND m.stage_id=p.stage_id) OR
                (m.audience='WORK' AND m.work_id=p.work_id) OR (m.audience='ROLE' AND m.actor_requirement_id=p.actor_requirement_id) OR
                (m.audience='SPECIFIC_ACTORS' AND m.specific_actor_ids @> %s::jsonb)) ORDER BY m.start_time""",(account_id,event_id,Jsonb([str(account_id)]))).fetchall()
            updates=c.execute("""SELECT * FROM actor_updates WHERE event_id=%s AND
                (audience='ALL_ACTORS' OR recipient_account_id=%s) ORDER BY created_at DESC""",(event_id,account_id)).fetchall()
            setup=c.execute('SELECT * FROM event_setups WHERE event_id=%s',(event_id,)).fetchone()
            organizer=c.execute("""SELECT a.id,a.display_name FROM event_memberships em JOIN accounts a ON a.id=em.account_id
                WHERE em.event_id=%s AND em.role='ORGANIZER' AND em.status='ACTIVE' LIMIT 1""",(event_id,)).fetchone()
            rejected=c.execute("""SELECT w.canonical_name work_name,ar.canonical_role_name role_name FROM participation_request_items pri
                JOIN participation_requests pr ON pr.id=pri.participation_request_id JOIN work_items w ON w.id=pri.work_id
                JOIN actor_requirements ar ON ar.id=pri.actor_requirement_id WHERE pr.event_id=%s AND pr.requester_account_id=%s AND pri.status='REJECTED'""",(event_id,account_id)).fetchall()
        participant_setup={'resources': setup['resource_needs'] if setup and setup['show_resources'] else [],
                           'map_enabled': bool(setup and setup['map_enabled']),
                           'default_view': setup['default_view'] if setup else None}
        return {'event':event,'participation_status':latest['status'] if latest else 'APPROVED','assignments':assignments,'rejected_selections':rejected,
                'meetings':meetings,'updates':updates,'setup':participant_setup,'organizer':organizer}

    def create_meeting(self,event_id,account_id,data):
        with self.database.connect() as c:
            self._organizer(c,event_id,account_id); meeting_id=uuid4()
            c.execute("""INSERT INTO event_meetings(id,event_id,title,meeting_type,start_time,end_time,location,note,audience,stage_id,work_id,actor_requirement_id,specific_actor_ids,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(meeting_id,event_id,data.title,data.meeting_type,data.start_time,data.end_time,data.location,data.note,data.audience,data.stage_id,data.work_id,data.actor_requirement_id,Jsonb([str(x) for x in data.specific_actor_ids]),account_id))
            c.execute("INSERT INTO actor_updates(id,event_id,audience,update_type,title,message,priority,meeting_id) VALUES(%s,%s,'ALL_ACTORS','MEETING_UPDATE',%s,%s,'NORMAL',%s)",(uuid4(),event_id,'Meeting scheduled',f'{data.title} was scheduled.',meeting_id))
            return dict(c.execute('SELECT * FROM event_meetings WHERE id=%s',(meeting_id,)).fetchone())

    def update_meeting(self,event_id,meeting_id,account_id,data):
        with self.database.connect() as c:
            self._organizer(c,event_id,account_id)
            row=c.execute('SELECT * FROM event_meetings WHERE id=%s AND event_id=%s FOR UPDATE',(meeting_id,event_id)).fetchone()
            if not row: raise NotFoundError('meeting not found')
            if row['version']!=data.expected_version: raise ValidationError('meeting version is stale')
            updated=c.execute("""UPDATE event_meetings SET start_time=%s,end_time=%s,location=%s,note=%s,status=%s,version=version+1,updated_at=now()
                WHERE id=%s RETURNING *""",(data.start_time,data.end_time,data.location,data.note,data.status,meeting_id)).fetchone()
            c.execute("INSERT INTO actor_updates(id,event_id,audience,update_type,title,message,priority,meeting_id) VALUES(%s,%s,'ALL_ACTORS','MEETING_UPDATE',%s,%s,'NORMAL',%s)",(uuid4(),event_id,'Meeting updated',f"{row['title']} was {data.status.lower()}.",meeting_id))
            return dict(updated)

    def announce(self,event_id,account_id,data):
        with self.database.connect() as c:
            self._organizer(c,event_id,account_id); row={'id':uuid4(),'event_id':event_id,'title':data.title,'message':data.message,'priority':data.priority}
            c.execute("INSERT INTO actor_updates(id,event_id,audience,update_type,title,message,priority) VALUES(%s,%s,'ALL_ACTORS','ORGANIZER_ANNOUNCEMENT',%s,%s,%s)",(row['id'],event_id,data.title,data.message,data.priority))
        return row
