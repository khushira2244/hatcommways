"""Pure authoritative map projection; it never creates or infers locations."""
from __future__ import annotations
from uuid import UUID
from .database import Database
from .errors import AuthorizationError,NotFoundError
from .map_models import MapMarker,MapReadModel

SAFE_METADATA={'subtype','instruction','active_from','active_until','zone','source_label'}
class MapReadService:
    def __init__(self,database:Database):self.database=database
    def get(self,event_id:UUID,account_id:UUID)->MapReadModel:
        with self.database.connect() as c:
            event=c.execute('SELECT * FROM events WHERE id=%s',(event_id,)).fetchone()
            if not event:raise NotFoundError('event not found')
            account=c.execute("SELECT id FROM accounts WHERE id=%s AND status='ACTIVE'",(account_id,)).fetchone()
            if not account:raise AuthorizationError('active account required')
            setup=c.execute('SELECT * FROM event_setups WHERE event_id=%s',(event_id,)).fetchone()
            visibility=setup['event_visibility'] if setup else 'PRIVATE'
            member=c.execute("SELECT role FROM event_memberships WHERE event_id=%s AND account_id=%s AND status='ACTIVE'",(event_id,account_id)).fetchone()
            accepted=c.execute("SELECT 1 FROM participations WHERE event_id=%s AND account_id=%s AND status='ACCEPTED'",(event_id,account_id)).fetchone()
            if visibility=='PRIVATE' and not member and not accepted:raise AuthorizationError('this event map is private')
            rows=c.execute("SELECT * FROM map_locations WHERE event_id=%s AND visible=true ORDER BY entity_type,display_name,id",(event_id,)).fetchall()
            actors=c.execute("""SELECT p.account_id,a.display_name,ar.canonical_role_name,s.canonical_name AS stage_name,w.canonical_name AS work_name
                FROM participations p JOIN accounts a ON a.id=p.account_id JOIN actor_requirements ar ON ar.id=p.actor_requirement_id
                JOIN stages s ON s.id=p.stage_id JOIN work_items w ON w.id=p.work_id WHERE p.event_id=%s AND p.status='ACCEPTED' ORDER BY p.account_id""",(event_id,)).fetchall()
        actor_by_id={x['account_id']:x for x in actors};resources={x.get('name'):x for x in (setup['resource_needs'] if setup else [])};supports={x.get('name'):x for x in (setup['sponsors_support'] if setup else []) if x.get('visibility_enabled')}
        markers=[]
        for row in rows:
            kind=row['entity_type'];entity=row['entity_id'];role=organization=profession=resource_type=None
            if kind=='ACTOR':
                actor=actor_by_id.get(entity)
                if not setup or not setup['map_enabled'] or not setup['show_actor_tree'] or not actor or row['location_precision']=='EXACT':continue
                role=actor['canonical_role_name']
            elif kind=='RESOURCE':
                resource=resources.get(row['display_name'])
                if not setup or not setup['map_enabled'] or not setup['show_resources'] or not resource:continue
                resource_type=resource.get('category')
            elif kind in ('SPONSOR','SUPPORT_PARTNER'):
                support=supports.get(row['display_name'])
                if not setup or not setup['map_enabled'] or not setup['show_sponsors'] or not support or support.get('type')!=kind:continue
            elif kind!='EVENT' and (not setup or not setup['map_enabled']):continue
            metadata={k:v for k,v in (row['metadata'] or {}).items() if k in SAFE_METADATA}
            markers.append(MapMarker(id=row['id'],event_id=event_id,entity_type=kind,entity_id=entity,display_name=row['display_name'],latitude=row['latitude'],longitude=row['longitude'],area_label=row['area_label'],location_precision=row['location_precision'],role=role,organization=organization,profession=profession,resource_type=resource_type,status=row['status'],visible=True,metadata=metadata,created_at=row['created_at'],updated_at=row['updated_at']))
        filters={key:sorted({str(getattr(x,key)) for x in markers if getattr(x,key)}) for key in ('area_label','role','organization','profession','resource_type')}
        filters['marker_type']=sorted({x.entity_type.value for x in markers})
        return MapReadModel(event={k:event[k] for k in ('id','name','location_description','starts_at','ends_at','timezone')},markers=markers,available_filters=filters,map_settings={'enabled':bool(setup and setup['map_enabled']),'default_view':setup['default_view'] if setup else None,'participation_dimensions':setup['participation_dimensions'] if setup else [],'event_visibility':visibility})
