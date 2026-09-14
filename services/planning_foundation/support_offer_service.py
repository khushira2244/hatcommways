"""Authoritative offers; only an organizer decision creates a contribution."""
import hashlib
import json
from decimal import Decimal
from uuid import UUID, uuid4, uuid5

from psycopg.types.json import Jsonb

from .errors import AuthorizationError, NotFoundError, StaleVersionError, ValidationError
from .services import PlanningService


def need_id(event_id, need):
    # Existing setup needs are value objects. An edited need is a new reference;
    # old offers must never silently attach to a different need or another event.
    return uuid5(UUID(str(event_id)), json.dumps(need, sort_keys=True, separators=(",", ":")))


class SupportOfferService:
    def __init__(self, database):
        self.database = database

    def _scope(self, c, event_id, account_id):
        event = PlanningService._lock_event(c, event_id)
        setup = c.execute("SELECT * FROM event_setups WHERE event_id=%s", (event_id,)).fetchone()
        if not setup:
            raise ValidationError("Event setup is not available")
        if event['organizer_id'] != account_id and setup['event_visibility'] == 'PRIVATE':
            member = c.execute("SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s AND status='ACTIVE'", (event_id, account_id)).fetchone()
            if not member:
                raise AuthorizationError("This event is private")
        return event, setup

    def _needs(self, event_id, setup):
        needs, occurrences = {}, {}
        for need in setup['resource_needs']:
            base_id = need_id(event_id, need)
            occurrence = occurrences.get(base_id, 0)
            resource_id = base_id if occurrence == 0 else uuid5(base_id, str(occurrence))
            occurrences[base_id] = occurrence + 1
            needs[str(resource_id)] = need
        return needs

    def _need(self, event_id, setup, resource_id):
        if resource_id is None:
            return None
        need = self._needs(event_id, setup).get(str(resource_id))
        if need is None:
            raise ValidationError("Resource need is no longer valid for this event")
        return need

    def _pledged(self, c, event_id, resource_id):
        return c.execute("SELECT coalesce(sum(quantity),0) AS total FROM support_offers WHERE event_id=%s AND resource_need_id=%s AND status='APPROVED'", (event_id, resource_id)).fetchone()['total']

    def _validate_quantity(self, c, event_id, resource_id, need, quantity):
        if quantity is None:
            return
        if not need or need.get('quantity') is None:
            raise ValidationError("This need has no quantity requirement; submit descriptive support instead")
        remaining = Decimal(str(need['quantity'])) - self._pledged(c, event_id, resource_id)
        if quantity > remaining:
            raise ValidationError(f"Offered quantity exceeds the remaining need ({max(0, remaining)})")

    def submit(self, event_id, account_id, body):
        payload = body.model_dump(mode='json', exclude={'idempotency_key'})
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.database.connect() as c:
            event, setup = self._scope(c, event_id, account_id)
            if event['organizer_id'] == account_id:
                raise AuthorizationError("Organizers cannot submit offers to their own event")
            c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"support-offer:{account_id}:{body.idempotency_key}",))
            replay = c.execute("SELECT * FROM support_offers WHERE sponsor_account_id=%s AND idempotency_key=%s", (account_id, body.idempotency_key)).fetchone()
            if replay:
                if replay['event_id'] != event_id or replay['request_fingerprint'] != fingerprint:
                    raise ValidationError("Idempotency key already used for another offer")
                return replay
            need = self._need(event_id, setup, body.resource_need_id)
            self._validate_quantity(c, event_id, body.resource_need_id, need, body.quantity)
            offer_id, correlation_id = uuid4(), uuid4()
            row = c.execute("""INSERT INTO support_offers(id,event_id,sponsor_account_id,resource_need_id,resource_snapshot,support_type,quantity,availability_start,availability_end,comment,idempotency_key,request_fingerprint,correlation_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (offer_id,event_id,account_id,body.resource_need_id,Jsonb(need),body.support_type,body.quantity,body.availability_start,body.availability_end,body.comment,body.idempotency_key,fingerprint,correlation_id)).fetchone()
            c.execute("INSERT INTO event_notifications(id,account_id,event_id,notification_type,support_offer_id) VALUES(%s,%s,%s,'SPONSOR_OFFER',%s)", (uuid4(),event['organizer_id'],event_id,offer_id))
            PlanningService._enqueue_outbox(c,event_type='support_offer.submitted',aggregate_type='SUPPORT_OFFER',aggregate_id=offer_id,aggregate_version=1,payload={'event_id':str(event_id),'offer_id':str(offer_id)},correlation_id=correlation_id)
            return row

    def workspace(self, event_id, account_id):
        with self.database.connect() as c:
            event, setup = self._scope(c, event_id, account_id)
            organizer = event['organizer_id'] == account_id
            offers = c.execute("""SELECT o.*,a.display_name AS sponsor_name,f.result AS fit,f.provenance AS fit_provenance,
                (SELECT r.status FROM runtime_agent_runs r JOIN domain_outbox d ON d.id=r.message_id
                 WHERE d.aggregate_id=o.id AND d.event_type='support_offer.submitted' AND r.handler_name='hatcommways-sponsor-fit-agent'
                 ORDER BY r.started_at DESC LIMIT 1) AS fit_runtime_status
                FROM support_offers o JOIN accounts a ON a.id=o.sponsor_account_id
                LEFT JOIN sponsor_fit_results f ON f.offer_id=o.id
                WHERE o.event_id=%s AND (%s OR o.sponsor_account_id=%s) ORDER BY o.created_at DESC""", (event_id,organizer,account_id)).fetchall()
            needs = [dict(n, id=rid, pledged=self._pledged(c,event_id,UUID(rid))) for rid,n in self._needs(event_id,setup).items()] if organizer or setup['show_resources'] else []
            for n in needs:
                n['remaining'] = max(Decimal(0),Decimal(str(n['quantity']))-n['pledged']) if n.get('quantity') is not None else None
            approved = c.execute("""SELECT o.id,o.sponsor_account_id,o.support_type,o.quantity,o.resource_snapshot,a.display_name AS sponsor_name,o.status
                FROM support_offers o JOIN accounts a ON a.id=o.sponsor_account_id WHERE o.event_id=%s AND o.status='APPROVED' ORDER BY o.reviewed_at""", (event_id,)).fetchall() if organizer or setup['show_sponsors'] else []
            return {'offers':offers,'needs':needs,'approved':approved}

    def notifications(self, event_id, account_id):
        with self.database.connect() as c:
            event, _ = self._scope(c,event_id,account_id)
            PlanningService._require_organizer(event,account_id)
            return c.execute("""SELECT n.id,n.event_id,n.support_offer_id AS offer_id,n.is_read,n.created_at,a.display_name AS sponsor_name,o.support_type,o.status
                FROM event_notifications n JOIN support_offers o ON o.id=n.support_offer_id JOIN accounts a ON a.id=o.sponsor_account_id
                WHERE n.account_id=%s AND n.event_id=%s AND n.notification_type='SPONSOR_OFFER' ORDER BY n.created_at DESC""", (account_id,event_id)).fetchall()

    def decide(self, event_id, offer_id, account_id, body):
        with self.database.connect() as c:
            event, setup = self._scope(c,event_id,account_id)
            PlanningService._require_organizer(event,account_id)
            offer = c.execute("SELECT * FROM support_offers WHERE id=%s AND event_id=%s FOR UPDATE", (offer_id,event_id)).fetchone()
            if not offer:
                raise NotFoundError("Offer not found in this event")
            if offer['status'] != 'PENDING' or offer['version'] != body.expected_version:
                raise StaleVersionError("Offer already reviewed or changed; refresh before deciding")
            if body.decision == 'APPROVED':
                need = self._need(event_id,setup,offer['resource_need_id'])
                self._validate_quantity(c,event_id,offer['resource_need_id'],need,offer['quantity'])
            row = c.execute("UPDATE support_offers SET status=%s,reviewed_by=%s,reviewed_at=now(),updated_at=now(),version=version+1 WHERE id=%s RETURNING *", (body.decision,account_id,offer_id)).fetchone()
            # APPROVED rows are the contribution ledger. Read models aggregate them;
            # no parallel mutable pledged counter can drift or double count.
            c.execute("UPDATE event_notifications SET is_read=true WHERE support_offer_id=%s AND account_id=%s", (offer_id,account_id))
            return row

    def fit_context(self, event_id, offer_id):
        with self.database.connect() as c:
            offer = c.execute("SELECT * FROM support_offers WHERE id=%s AND event_id=%s", (offer_id,event_id)).fetchone()
            if not offer:
                raise NotFoundError("Offer not found in runtime event scope")
            event = c.execute("SELECT id,name,purpose,starts_at,ends_at,timezone FROM events WHERE id=%s", (event_id,)).fetchone()
            setup = c.execute("SELECT resource_needs FROM event_setups WHERE event_id=%s", (event_id,)).fetchone()
            need = self._needs(event_id,setup).get(str(offer['resource_need_id']))
            approved = c.execute("SELECT quantity,support_type FROM support_offers WHERE event_id=%s AND resource_need_id=%s AND status='APPROVED'", (event_id,offer['resource_need_id'])).fetchall()
            remaining = max(Decimal(0),Decimal(str(need['quantity']))-sum((r['quantity'] or 0 for r in approved),Decimal(0))) if need and need.get('quantity') is not None else None
            sponsor = c.execute("SELECT display_name FROM accounts WHERE id=%s", (offer['sponsor_account_id'],)).fetchone()
            return {'support_offer':{k:offer[k] for k in ('id','support_type','quantity','availability_start','availability_end','comment')},'event':event,'selected_resource_need':need,'approved_contributions':approved,'remaining_gap':remaining,'sponsor_profile':sponsor}

    def existing_fit(self, event_id, offer_id):
        with self.database.connect() as c:
            return c.execute("SELECT f.* FROM sponsor_fit_results f JOIN support_offers o ON o.id=f.offer_id WHERE o.id=%s AND o.event_id=%s", (offer_id,event_id)).fetchone()

    def store_fit(self, event_id, offer_id, result, provenance):
        with self.database.connect() as c:
            if not c.execute("SELECT id FROM support_offers WHERE id=%s AND event_id=%s", (offer_id,event_id)).fetchone():
                raise NotFoundError("Offer outside runtime scope")
            c.execute("INSERT INTO sponsor_fit_results(offer_id,result,provenance) VALUES(%s,%s,%s) ON CONFLICT(offer_id) DO NOTHING", (offer_id,Jsonb(result.model_dump()),Jsonb(provenance)))
        return self.existing_fit(event_id,offer_id)

    def sponsor_dashboard(self, sponsor_id, viewer_id):
        """Explicit public projection; private offers are queried only for their owner."""
        with self.database.connect() as c:
            sponsor = c.execute("SELECT id,display_name,account_type FROM accounts WHERE id=%s AND status='ACTIVE' AND account_type='ORGANIZATION'", (sponsor_id,)).fetchone()
            if not sponsor:
                raise NotFoundError("Sponsor organization not found")
            public = c.execute("""SELECT e.id AS event_id,e.name,e.category,e.location_description,
                e.starts_at,s.event_latitude AS latitude,s.event_longitude AS longitude,
                s.cover_image_data_url AS image,o.support_type,o.reviewed_at
                FROM support_offers o JOIN events e ON e.id=o.event_id
                JOIN event_setups s ON s.event_id=e.id
                WHERE o.sponsor_account_id=%s AND o.status='APPROVED'
                AND s.event_visibility='PUBLIC' AND s.show_sponsors=true
                ORDER BY o.reviewed_at DESC,o.id""", (sponsor_id,)).fetchall()
            result = {'sponsor':sponsor,'is_owner':sponsor_id==viewer_id,'contributions':public}
            if sponsor_id==viewer_id:
                result['offers'] = c.execute("""SELECT o.id,o.event_id,e.name,e.location_description,
                    o.support_type,o.comment,o.quantity,o.status,o.created_at,o.updated_at
                    FROM support_offers o JOIN events e ON e.id=o.event_id
                    WHERE o.sponsor_account_id=%s ORDER BY o.updated_at DESC,o.id""", (sponsor_id,)).fetchall()
            return result
