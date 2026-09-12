from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from uuid import UUID,uuid4
from psycopg.types.json import Jsonb
from .coordination_service import CoordinationService
from .database import Database
from .errors import IdempotencyConflictError,NotFoundError,ProposalAlreadyDecidedError,StaleVersionError,ValidationError
from .human_update_service import HumanUpdateService
from .replanning_models import ReplanContext,ReplanDecision,ReplanProposalSnapshot
from .services import PlanningService

@dataclass(frozen=True)
class ReplanStart: request_id:UUID; context:ReplanContext; existing:ReplanProposalSnapshot|None

class ReplanningService:
    def __init__(self,database:Database): self.database=database;self.human=HumanUpdateService(database);self.coordination=CoordinationService(database)
    @staticmethod
    def _proposal(row): return ReplanProposalSnapshot.model_validate(row)
    def _context(self,c,event,blocker):
        coord_context=self.coordination._context(c,event,blocker)
        coordination=c.execute("SELECT * FROM coordination_proposals WHERE event_id=%s AND blocker_id=%s",(event['id'],blocker['id'])).fetchone()
        if coordination is None or not coordination['requires_replanning']: raise ValidationError('successful coordination must explicitly require replanning')
        if coordination['source_fingerprint']!=coord_context.source_fingerprint: raise StaleVersionError('coordination proposal is stale')
        affected_ids=[UUID(str(x['id'])) for x in coord_context.affected_work]
        all_work=c.execute("""SELECT w.id FROM work_items w JOIN proposals p ON p.id=w.source_proposal_id WHERE w.event_id=%s AND p.status='APPROVED' AND p.proposal_type='WORK_DECOMPOSITION' ORDER BY w.id""",(event['id'],)).fetchall()
        unaffected=[x['id'] for x in all_work if x['id'] not in set(affected_ids)]
        versions={**coord_context.source_versions,'coordination_proposal':str(coordination['id'])}
        fingerprint=hashlib.sha256(json.dumps(versions,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return ReplanContext(event=coord_context.event,blocker=coord_context.blocker,assessment=coord_context.blocker_assessment,resolution=coord_context.affected_work_resolution,
            coordination={k:coordination[k] for k in ('id','coordination_possible','requires_replanning','actions','rationale','confidence')},affected_stages=coord_context.affected_stages,
            affected_work=coord_context.affected_work,affected_actors=coord_context.relevant_actors,relevant_meetings=coord_context.relevant_meetings,unaffected_work_ids=unaffected,source_fingerprint=fingerprint,source_versions=versions)
    def context(self,event_id,blocker_id,organizer_id):
        with self.database.connect() as c:
            event=self.human._event(c,event_id,organizer_id);self.human._require_organizer(c,event,organizer_id)
            blocker=c.execute('SELECT * FROM blockers WHERE id=%s AND event_id=%s',(blocker_id,event_id)).fetchone()
            if not blocker: raise NotFoundError('blocker not found in this event')
            if blocker['condition_state']!='OPEN': raise ValidationError('only an open blocker can be replanned')
            return self._context(c,event,blocker)
    def begin(self,event_id,blocker_id,organizer_id,*,retry):
        with self.database.connect() as c:
            event=self.human._event(c,event_id,organizer_id,write=True);self.human._require_organizer(c,event,organizer_id)
            blocker=c.execute('SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE',(blocker_id,event_id)).fetchone()
            if not blocker: raise NotFoundError('blocker not found in this event')
            if blocker['condition_state']!='OPEN': raise ValidationError('only an open blocker can be replanned')
            context=self._context(c,event,blocker); req=c.execute('SELECT * FROM replan_requests WHERE blocker_id=%s FOR UPDATE',(blocker_id,)).fetchone()
            if req:
                if req['source_fingerprint']!=context.source_fingerprint: raise StaleVersionError('replanning source state changed')
                if req['status'] in ('PROPOSED','APPROVED','REJECTED'):
                    row=c.execute('SELECT * FROM replan_proposals WHERE request_id=%s',(req['id'],)).fetchone();return ReplanStart(req['id'],context,self._proposal(row))
                if req['status']=='RUNNING': raise IdempotencyConflictError('replanning is already running')
                if not retry: raise IdempotencyConflictError('explicit retry is required after replanning failure')
                req=c.execute("UPDATE replan_requests SET status='RUNNING',failure_code=NULL,failed_at=NULL,attempt_count=attempt_count+1,updated_at=now() WHERE id=%s RETURNING *",(req['id'],)).fetchone()
            else:
                req=c.execute("INSERT INTO replan_requests(id,event_id,blocker_id,coordination_proposal_id,organizer_id,source_fingerprint,source_versions,status,attempt_count) VALUES(%s,%s,%s,%s,%s,%s,%s,'RUNNING',1) RETURNING *",(uuid4(),event_id,blocker_id,UUID(str(context.coordination['id'])),organizer_id,context.source_fingerprint,Jsonb(context.source_versions))).fetchone()
            PlanningService._enqueue_outbox(c,event_type='replan.requested',aggregate_type='REPLAN_REQUEST',aggregate_id=req['id'],aggregate_version=req['attempt_count'],payload={'event_id':str(event_id),'blocker_id':str(blocker_id)},correlation_id=uuid4())
            return ReplanStart(req['id'],context,None)
    @staticmethod
    def validate(d:ReplanDecision,x:ReplanContext):
        if d.event_id!=UUID(str(x.event['id'])) or d.blocker_id!=UUID(str(x.blocker['id'])) or d.affected_work_resolution_id!=UUID(str(x.resolution['id'])) or d.coordination_proposal_id!=UUID(str(x.coordination['id'])): raise ValidationError('replan identifiers do not match scoped context')
        if d.current_plan_version!=x.event['version'] or d.source_graph_fingerprint!=x.resolution['graph_fingerprint']: raise StaleVersionError('replan source versions are stale')
        work={UUID(str(v['id'])):v for v in x.affected_work};stages={UUID(str(v['id'])):v for v in x.affected_stages};actors={UUID(str(v['account_id'])) for v in x.affected_actors};meetings={UUID(str(v['id'])) for v in x.relevant_meetings}
        for ch in d.proposed_changes:
            if ch.target_work_id and ch.target_work_id not in work: raise ValidationError('replan attempts to change unaffected work')
            if ch.target_stage_id and ch.target_stage_id not in stages: raise ValidationError('replan attempts to change unaffected stage')
            if ch.target_actor_id and ch.target_actor_id not in actors: raise ValidationError('replan references unaffected actor')
            if ch.target_meeting_id and ch.target_meeting_id not in meetings: raise ValidationError('replan references unrelated meeting')
            if ch.change_type in ('WORK_START_CHANGE','WORK_END_CHANGE','WORK_WINDOW_SHIFT','DEPENDENCY_TIMING_ADJUSTMENT') and (not ch.target_work_id or not ch.proposed_start): raise ValidationError('work timing change requires affected work and complete window')
            if ch.change_type=='STAGE_TIMING_CHANGE' and (not ch.target_stage_id or not ch.proposed_start): raise ValidationError('stage timing change requires affected stage and complete window')
            if ch.change_type=='MEETING_RESCHEDULE' and (not ch.target_meeting_id or not ch.proposed_start): raise ValidationError('meeting change requires relevant meeting and complete window')
    def complete(self,event_id,blocker_id,organizer_id,request_id,d,**p):
        with self.database.connect() as c:
            event=self.human._event(c,event_id,organizer_id,write=True);self.human._require_organizer(c,event,organizer_id);blocker=c.execute('SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE',(blocker_id,event_id)).fetchone();req=c.execute('SELECT * FROM replan_requests WHERE id=%s FOR UPDATE',(request_id,)).fetchone();x=self._context(c,event,blocker)
            if not req or req['status']!='RUNNING': raise IdempotencyConflictError('replan request is not running')
            if req['source_fingerprint']!=x.source_fingerprint: raise StaleVersionError('replanning source changed during execution')
            self.validate(d,x); actor_ids=sorted({UUID(str(v['account_id'])) for v in x.affected_actors},key=str)
            row=c.execute("""INSERT INTO replan_proposals(id,request_id,event_id,blocker_id,affected_work_resolution_id,coordination_proposal_id,current_plan_version,source_graph_fingerprint,proposed_changes,rationale,confidence,unaffected_work_ids,affected_actor_ids,status,source_fingerprint,source_versions,provider_name,model_id,agent_name,agent_version,stop_reason,usage) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PROPOSED',%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",(uuid4(),request_id,event_id,blocker_id,d.affected_work_resolution_id,d.coordination_proposal_id,d.current_plan_version,d.source_graph_fingerprint,Jsonb([v.model_dump(mode='json') for v in d.proposed_changes]),d.rationale,d.confidence,x.unaffected_work_ids,actor_ids,x.source_fingerprint,Jsonb(x.source_versions),p['provider_name'],p['model_id'],p['agent_name'],p['agent_version'],p['stop_reason'],Jsonb(p['usage']))).fetchone()
            c.execute("UPDATE replan_requests SET status='PROPOSED',proposal_id=%s,updated_at=now() WHERE id=%s",(row['id'],request_id));return self._proposal(row)
    def fail(self,event_id,blocker_id,request_id,code):
        with self.database.connect() as c:c.execute("UPDATE replan_requests SET status='FAILED',failure_code=%s,failed_at=now(),updated_at=now() WHERE id=%s AND status='RUNNING'",(code[:100],request_id))
    def get(self,event_id,blocker_id,organizer_id):
        with self.database.connect() as c:
            event=self.human._event(c,event_id,organizer_id);self.human._require_organizer(c,event,organizer_id);row=c.execute('SELECT * FROM replan_proposals WHERE event_id=%s AND blocker_id=%s',(event_id,blocker_id)).fetchone();return self._proposal(row) if row else None
    @staticmethod
    def _display_window(start, end):
        def clock(value):
            return value.strftime('%I:%M %p').lstrip('0')
        return f'{clock(start)} – {clock(end)}'

    def decide(self,event_id,blocker_id,proposal_id,organizer_id,expected_event_version,approve):
        with self.database.connect() as c:
            event=self.human._event(c,event_id,organizer_id,write=True)
            self.human._require_organizer(c,event,organizer_id)
            blocker=c.execute('SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE',(blocker_id,event_id)).fetchone()
            row=c.execute('SELECT * FROM replan_proposals WHERE id=%s AND blocker_id=%s AND event_id=%s FOR UPDATE',(proposal_id,blocker_id,event_id)).fetchone()
            if not blocker or not row: raise NotFoundError('replan proposal not found')
            if row['status']!='PROPOSED': raise ProposalAlreadyDecidedError('replan proposal already decided')
            if event['version']!=expected_event_version or event['version']!=row['current_plan_version']:
                c.execute("UPDATE replan_proposals SET status='STALE',decided_at=now() WHERE id=%s",(proposal_id,))
                c.execute("UPDATE replan_requests SET status='STALE',updated_at=now() WHERE id=%s",(row['request_id'],))
                raise StaleVersionError('replan proposal is stale')
            if not approve:
                row=c.execute("UPDATE replan_proposals SET status='REJECTED',decided_at=now() WHERE id=%s RETURNING *",(proposal_id,)).fetchone()
                c.execute("UPDATE replan_requests SET status='REJECTED',updated_at=now() WHERE id=%s",(row['request_id'],))
                return self._proposal(row)

            x=self._context(c,event,blocker)
            self.validate(ReplanDecision.model_validate({k:row[k] for k in ReplanDecision.model_fields}),x)
            before=[]
            actor_messages={}
            for ch in row['proposed_changes']:
                if ch.get('proposed_start') and ch.get('target_work_id'):
                    old=c.execute('SELECT * FROM work_items WHERE id=%s FOR UPDATE',(ch['target_work_id'],)).fetchone()
                    before.append(dict(old))
                    participations=c.execute(
                        """SELECT id,account_id FROM participations
                           WHERE event_id=%s AND work_id=%s AND status='ACCEPTED' FOR UPDATE""",
                        (event_id,ch['target_work_id']),
                    ).fetchall()
                    c.execute('UPDATE work_items SET starts_at=%s,ends_at=%s,version=version+1,updated_at=now() WHERE id=%s',(ch['proposed_start'],ch['proposed_end'],ch['target_work_id']))
                    if participations:
                        c.execute(
                            """UPDATE participations SET approved_start=%s,approved_end=%s,updated_at=now()
                               WHERE event_id=%s AND work_id=%s AND status='ACCEPTED'""",
                            (ch['proposed_start'],ch['proposed_end'],event_id,ch['target_work_id']),
                        )
                    detail=(
                        f"{old['canonical_name']}\n"
                        f"Previous: {self._display_window(old['starts_at'],old['ends_at'])}\n"
                        f"Updated: {self._display_window(ch['proposed_start'],ch['proposed_end'])}\n"
                        "Reason: Event coordination adjustment."
                    )
                    for participation in participations:
                        actor_messages.setdefault(participation['account_id'],[]).append(detail)
                elif ch.get('proposed_start') and ch.get('target_stage_id'):
                    old=c.execute('SELECT * FROM stages WHERE id=%s FOR UPDATE',(ch['target_stage_id'],)).fetchone()
                    before.append(dict(old))
                    c.execute('UPDATE stages SET starts_at=%s,ends_at=%s,version=version+1,updated_at=now() WHERE id=%s',(ch['proposed_start'],ch['proposed_end'],ch['target_stage_id']))
                elif ch.get('proposed_start') and ch.get('target_meeting_id'):
                    old=c.execute('SELECT * FROM event_meetings WHERE id=%s FOR UPDATE',(ch['target_meeting_id'],)).fetchone()
                    before.append(dict(old))
                    recipients=c.execute(
                        """SELECT DISTINCT p.account_id FROM participations p
                           WHERE p.event_id=%s AND p.status='ACCEPTED' AND
                           (%s='ALL_ACTORS' OR (%s='STAGE' AND p.stage_id=%s) OR
                            (%s='WORK' AND p.work_id=%s) OR (%s='ROLE' AND p.actor_requirement_id=%s) OR
                            (%s='SPECIFIC_ACTORS' AND %s::jsonb @> jsonb_build_array(p.account_id::text)))""",
                        (event_id,old['audience'],old['audience'],old['stage_id'],old['audience'],old['work_id'],
                         old['audience'],old['actor_requirement_id'],old['audience'],Jsonb(old['specific_actor_ids'])),
                    ).fetchall()
                    c.execute("UPDATE event_meetings SET start_time=%s,end_time=%s,status='RESCHEDULED',version=version+1,updated_at=now() WHERE id=%s",(ch['proposed_start'],ch['proposed_end'],ch['target_meeting_id']))
                    detail=(
                        f"{old['title']} meeting\n"
                        f"Previous: {self._display_window(old['start_time'],old['end_time'])}\n"
                        f"Updated: {self._display_window(ch['proposed_start'],ch['proposed_end'])}\n"
                        "Reason: Event coordination adjustment."
                    )
                    for recipient in recipients:
                        actor_messages.setdefault(recipient['account_id'],[]).append(detail)

            for account_id,changes in actor_messages.items():
                c.execute(
                    """INSERT INTO actor_updates(id,event_id,recipient_account_id,audience,update_type,title,message,priority)
                       VALUES(%s,%s,%s,'ACTOR','ORGANIZER_ANNOUNCEMENT','Plan updated',%s,'NORMAL')""",
                    (uuid4(),event_id,account_id,'Your work schedule changed.\n\n'+'\n\n'.join(changes)),
                )
            event=c.execute('UPDATE events SET version=version+1,updated_at=now() WHERE id=%s RETURNING *',(event_id,)).fetchone()
            history=json.loads(json.dumps(before,default=str))
            c.execute('INSERT INTO replan_applications(id,event_id,blocker_id,proposal_id,previous_event_version,new_event_version,previous_state) VALUES(%s,%s,%s,%s,%s,%s,%s)',(uuid4(),event_id,blocker_id,proposal_id,row['current_plan_version'],event['version'],Jsonb(history)))
            row=c.execute("UPDATE replan_proposals SET status='APPROVED',decided_at=now() WHERE id=%s RETURNING *",(proposal_id,)).fetchone()
            c.execute("UPDATE replan_requests SET status='APPROVED',updated_at=now() WHERE id=%s",(row['request_id'],))
            return self._proposal(row)
