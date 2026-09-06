from uuid import UUID,uuid4
from psycopg.types.json import Jsonb
from .database import Database
from .errors import NotFoundError,StaleProposalError,ValidationError
from .governance_models import GovernanceProposal,ManualItem,ItemPatch,EvidenceCreate,SubmitGovernance
from .services import PlanningService

class GovernanceService:
    def __init__(self,database:Database): self.database=database; self.base=PlanningService(database)
    def facts(self,event_id:UUID,organizer_id:UUID):
        event=self.base.get_event(event_id)
        if event.organizer_id!=organizer_id: raise ValidationError('organizer authorization required')
        with self.database.connect() as c:
            setup=c.execute('SELECT resource_needs,sponsors_support,event_visibility FROM event_setups WHERE event_id=%s',(event_id,)).fetchone()
        return {'event_id':str(event.id),'event_version':event.version,'purpose':event.purpose,'location':event.location_description,'event_type':event.event_type,'starts_at':event.starts_at.isoformat(),'ends_at':event.ends_at.isoformat(),'planning_context':event.planning_context.model_dump(mode='json') if event.planning_context else None,'setup':dict(setup) if setup else None}
    def store_assessment(self,proposal:GovernanceProposal,organizer_id:UUID):
        facts=self.facts(proposal.event_id,organizer_id)
        if proposal.base_event_version!=facts['event_version']: raise StaleProposalError('event changed during governance assessment')
        correlation=uuid4()
        with self.database.connect() as c:
            existing=c.execute('SELECT id,version FROM governance_assessments WHERE event_id=%s FOR UPDATE',(proposal.event_id,)).fetchone()
            if existing:
                aid=existing['id']; version=existing['version']+1
                c.execute('DELETE FROM governance_items WHERE assessment_id=%s',(aid,))
                c.execute('UPDATE governance_assessments SET version=%s,governance_required=%s,completeness=%s,internal_risk=%s,review_mode=%s,organizer_visible_status=%s,location_context=%s,event_facts_snapshot=%s,reasoning_summary=%s,correlation_id=%s,updated_at=now() WHERE id=%s',(version,proposal.governance_required,proposal.completeness,proposal.internal_risk,proposal.review_mode,proposal.organizer_visible_status,proposal.location_context,Jsonb(facts),proposal.reasoning_summary,correlation,aid))
            else:
                aid=uuid4(); version=1
                c.execute('INSERT INTO governance_assessments(id,event_id,governance_required,completeness,internal_risk,review_mode,organizer_visible_status,location_context,event_facts_snapshot,reasoning_summary,correlation_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(aid,proposal.event_id,proposal.governance_required,proposal.completeness,proposal.internal_risk,proposal.review_mode,proposal.organizer_visible_status,proposal.location_context,Jsonb(facts),proposal.reasoning_summary,correlation))
            for item in proposal.items:
                c.execute('INSERT INTO governance_items(id,assessment_id,category,label,source,knowledge_type,reason,suggested_documents,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(uuid4(),aid,item.category,item.label,'AI_DETECTED',item.knowledge_type,item.reason,Jsonb(item.suggested_documents),item.status))
            if proposal.review_mode=='HATCOMMWAYS':
                number=f'GOV-{str(aid).replace("-","")[:8].upper()}'
                c.execute("INSERT INTO governance_tickets(id,event_id,assessment_id,ticket_number,status,internal_risk) VALUES(%s,%s,%s,%s,'UNDER_REVIEW',%s) ON CONFLICT(assessment_id) DO NOTHING",(uuid4(),proposal.event_id,aid,number,proposal.internal_risk))
            PlanningService._enqueue_outbox(c,event_type='governance.assessed',aggregate_type='GOVERNANCE',aggregate_id=aid,aggregate_version=version,payload={'event_id':str(proposal.event_id),'governance_required':proposal.governance_required},correlation_id=correlation,causation_id=None)
        return self.get(proposal.event_id,organizer_id)
    def get(self,event_id:UUID,organizer_id:UUID):
        self.facts(event_id,organizer_id)
        with self.database.connect() as c:
            a=c.execute('SELECT * FROM governance_assessments WHERE event_id=%s',(event_id,)).fetchone()
            if not a:return {'event_id':str(event_id),'assessment':None,'items':[]}
            items=c.execute('SELECT * FROM governance_items WHERE assessment_id=%s ORDER BY created_at,id',(a['id'],)).fetchall()
            result=[]
            for item in items:
                evidence=c.execute('SELECT id,evidence_type,label,value_or_reference,submitted_at FROM governance_evidence WHERE governance_item_id=%s ORDER BY submitted_at',(item['id'],)).fetchall()
                result.append(dict(item)|{'evidence':[dict(x) for x in evidence]})
        visible={k:a[k] for k in ('id','event_id','version','governance_required','completeness','review_mode','organizer_visible_status','location_context','reasoning_summary','created_at','updated_at')}
        return {'event_id':str(event_id),'assessment':visible,'items':result}
    def add_item(self,event_id,organizer_id,command:ManualItem):
        state=self.get(event_id,organizer_id); a=state['assessment']
        if not a: raise NotFoundError('governance assessment not found')
        with self.database.connect() as c:
            item_id=uuid4(); reason=command.reason or command.authority
            c.execute("INSERT INTO governance_items(id,assessment_id,category,label,source,knowledge_type,reason,status,organizer_note) VALUES(%s,%s,%s,%s,'ORGANIZER_ADDED','UNKNOWN',%s,'NEEDS_INFORMATION',%s)",(item_id,a['id'],command.category,command.label,reason,command.authority))
            c.execute('UPDATE governance_assessments SET version=version+1,governance_required=true,completeness=\'INCOMPLETE\',organizer_visible_status=\'NEEDS_INFORMATION\',updated_at=now() WHERE id=%s',(a['id'],))
            if command.evidence_reference:c.execute("INSERT INTO governance_evidence(id,governance_item_id,evidence_type,label,value_or_reference,submitted_by) VALUES(%s,%s,'REFERENCE_NUMBER','Organizer reference',%s,%s)",(uuid4(),item_id,command.evidence_reference,organizer_id))
        return self.get(event_id,organizer_id)
    def patch_item(self,item_id,organizer_id,command:ItemPatch):
        with self.database.connect() as c:
            row=c.execute('SELECT a.event_id,a.id,a.version FROM governance_items i JOIN governance_assessments a ON a.id=i.assessment_id WHERE i.id=%s FOR UPDATE',(item_id,)).fetchone()
            if not row:raise NotFoundError('governance item not found')
            self.facts(row['event_id'],organizer_id)
            if row['version']!=command.expected_assessment_version:raise StaleProposalError('governance version is stale')
            note=command.not_applicable_reason if command.status=='NOT_APPLICABLE' else command.organizer_note
            if command.status=='NOT_APPLICABLE' and not note:raise ValidationError('reason is required when marking not applicable')
            c.execute('UPDATE governance_items SET status=%s,organizer_note=%s,updated_at=now() WHERE id=%s',(command.status,note,item_id));c.execute('UPDATE governance_assessments SET version=version+1,updated_at=now() WHERE id=%s',(row['id'],))
        return self.get(row['event_id'],organizer_id)
    def add_evidence(self,item_id,organizer_id,command:EvidenceCreate):
        if command.evidence_type not in {'FILE_REFERENCE','URL','REFERENCE_NUMBER','TEXT_CONFIRMATION'}:raise ValidationError('invalid evidence type')
        with self.database.connect() as c:
            row=c.execute('SELECT a.event_id,a.id FROM governance_items i JOIN governance_assessments a ON a.id=i.assessment_id WHERE i.id=%s',(item_id,)).fetchone()
            if not row:raise NotFoundError('governance item not found')
            self.facts(row['event_id'],organizer_id);c.execute('INSERT INTO governance_evidence(id,governance_item_id,evidence_type,label,value_or_reference,submitted_by) VALUES(%s,%s,%s,%s,%s,%s)',(uuid4(),item_id,command.evidence_type,command.label,command.value_or_reference,organizer_id));c.execute("UPDATE governance_items SET status='PROVIDED',updated_at=now() WHERE id=%s",(item_id,));c.execute('UPDATE governance_assessments SET version=version+1,updated_at=now() WHERE id=%s',(row['id'],))
        return self.get(row['event_id'],organizer_id)
    def submit(self,event_id,organizer_id,command:SubmitGovernance):
        state=self.get(event_id,organizer_id);a=state['assessment']
        if not a:raise NotFoundError('governance assessment not found')
        if a['version']!=command.expected_version:raise StaleProposalError('governance version is stale')
        with self.database.connect() as c:
            status='UNDER_REVIEW' if a['review_mode']=='HATCOMMWAYS' else 'SUBMITTED';c.execute('UPDATE governance_assessments SET version=version+1,organizer_visible_status=%s,updated_at=now() WHERE id=%s',(status,a['id']));c.execute("UPDATE governance_items SET status='SUBMITTED',updated_at=now() WHERE assessment_id=%s AND status IN ('PROVIDED','NEEDS_INFORMATION','EVIDENCE_REQUESTED')",(a['id'],));PlanningService._enqueue_outbox(c,event_type='governance.submitted',aggregate_type='GOVERNANCE',aggregate_id=a['id'],aggregate_version=a['version']+1,payload={'event_id':str(event_id)},correlation_id=uuid4(),causation_id=None)
        return self.get(event_id,organizer_id)
