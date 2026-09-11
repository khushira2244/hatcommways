"""Deterministic human reports and blockers. No agents or plan mutations."""
from uuid import UUID, uuid4

from .database import Database
from .errors import AuthorizationError, NotFoundError, ValidationError, StaleVersionError, IdempotencyConflictError
from .human_update_models import (
    BlockerCreate,
    BlockerPatch,
    BlockerSnapshot,
    HumanUpdateCreate,
    HumanUpdateInterpretationSnapshot,
    HumanUpdateSnapshot,
)


class HumanUpdateService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _event(connection, event_id, account_id, *, write=False):
        event = connection.execute(
            'SELECT * FROM events WHERE id=%s' + (' FOR UPDATE' if write else ''), (event_id,)
        ).fetchone()
        if event is None:
            raise NotFoundError('event not found')
        account = connection.execute("SELECT id FROM accounts WHERE id=%s AND status='ACTIVE'", (account_id,)).fetchone()
        if account is None:
            raise AuthorizationError('active account required')
        return event

    @staticmethod
    def _is_organizer(connection, event, account_id):
        membership = connection.execute(
            """SELECT 1 FROM event_memberships WHERE event_id=%s AND account_id=%s
               AND role='ORGANIZER' AND status='ACTIVE' FOR SHARE""", (event['id'], account_id)
        ).fetchone()
        return event['organizer_id'] == account_id and membership is not None

    def _require_organizer(self, connection, event, account_id):
        if not self._is_organizer(connection, event, account_id):
            raise AuthorizationError('active organizer membership is required')

    @staticmethod
    def _scope(connection, event_id, *, stage_id=None, work_id=None, actor_requirement_id=None, participation_id=None):
        scope = dict(stage_id=stage_id, work_id=work_id, actor_requirement_id=actor_requirement_id, participation_id=participation_id)
        # Resolve the most specific reference first, rejecting conflicting parents.
        for key, table, parents in (
            ('participation_id', 'participations', ('actor_requirement_id', 'work_id', 'stage_id')),
            ('actor_requirement_id', 'actor_requirements', ('work_id', 'stage_id')),
            ('work_id', 'work_items', ('stage_id',)),
            ('stage_id', 'stages', ()),
        ):
            if scope[key] is None:
                continue
            row = connection.execute(f'SELECT * FROM {table} WHERE id=%s AND event_id=%s', (scope[key], event_id)).fetchone()
            if row is None:
                raise ValidationError('linked context does not belong to this event')
            for parent in parents:
                if scope[parent] is not None and scope[parent] != row[parent]:
                    raise ValidationError('linked stage, work, role and participation must agree')
                scope[parent] = row[parent]
        return scope

    @staticmethod
    def _report(row):
        payload = {
            key: row[key]
            for key in HumanUpdateSnapshot.model_fields
            if key in row and key != "interpretation"
        }
        interpretation = row.get("interpretation")
        if interpretation:
            payload["interpretation"] = HumanUpdateInterpretationSnapshot.model_validate(
                {
                    "update_id": interpretation["human_update_id"],
                    **{
                        key: interpretation[key]
                        for key in HumanUpdateInterpretationSnapshot.model_fields
                        if key != "update_id"
                    },
                }
            )
        return HumanUpdateSnapshot.model_validate(payload)

    def submit(self, event_id: UUID, account_id: UUID, body: HumanUpdateCreate) -> HumanUpdateSnapshot:
        with self.database.connect() as c:
            event = self._event(c, event_id, account_id, write=True)
            organizer = self._is_organizer(c, event, account_id)
            accepted = []
            if not organizer:
                accepted = c.execute(
                    """SELECT * FROM participations WHERE event_id=%s AND account_id=%s
                       AND status='ACCEPTED' FOR SHARE""", (event_id, account_id)
                ).fetchall()
                if not accepted:
                    raise AuthorizationError('accepted participation is required')
            scope = self._scope(c, event_id, stage_id=body.stage_id, work_id=body.work_id,
                                actor_requirement_id=body.actor_requirement_id, participation_id=body.participation_id)
            if not organizer and not any(
                all(value is None or (item['id'] if key == 'participation_id' else item[key]) == value
                    for key, value in scope.items()) for item in accepted
            ):
                raise AuthorizationError('report context must match your accepted participation')
            values = dict(event_id=event_id, reporter_account_id=account_id,
                          source_type='ORGANIZER' if organizer else 'ACTOR', original_text=body.text, **scope)
            if body.idempotency_key is not None:
                existing = c.execute(
                    'SELECT * FROM human_updates WHERE event_id=%s AND reporter_account_id=%s AND idempotency_key=%s',
                    (event_id, account_id, body.idempotency_key),
                ).fetchone()
                if existing:
                    if any(existing[key] != value for key, value in values.items()):
                        raise IdempotencyConflictError('human update idempotency key has different content')
                    return self._report(existing)
            row = c.execute(
                """INSERT INTO human_updates(id,event_id,reporter_account_id,source_type,original_text,
                       stage_id,work_id,actor_requirement_id,participation_id,idempotency_key)
                   VALUES(%(id)s,%(event_id)s,%(reporter_account_id)s,%(source_type)s,%(original_text)s,
                       %(stage_id)s,%(work_id)s,%(actor_requirement_id)s,%(participation_id)s,%(idempotency_key)s)
                   RETURNING *""", dict(id=uuid4(), idempotency_key=body.idempotency_key, **values),
            ).fetchone()
            return self._report(row)

    def list_updates(self, event_id: UUID, account_id: UUID) -> list[HumanUpdateSnapshot]:
        with self.database.connect() as c:
            event = self._event(c, event_id, account_id)
            organizer = self._is_organizer(c, event, account_id)
            if not organizer:
                accepted = c.execute(
                    """SELECT 1 FROM participations WHERE event_id=%s AND account_id=%s
                       AND status='ACCEPTED' LIMIT 1""", (event_id, account_id)
                ).fetchone()
                if not accepted:
                    raise AuthorizationError('accepted participation is required')
            rows = c.execute(
                """SELECT h.*,to_jsonb(i) AS interpretation FROM human_updates h
                   LEFT JOIN human_update_interpretations i ON i.human_update_id=h.id
                   WHERE h.event_id=%s""" + ("" if organizer else " AND h.reporter_account_id=%s") +
                   " ORDER BY h.created_at DESC,h.id",
                (event_id,) if organizer else (event_id, account_id),
            ).fetchall()
            return [self._report(row) for row in rows]

    @staticmethod
    def _blocker_rows(connection, event_id, blocker_id=None):
        rows = connection.execute(
            """SELECT b.*,to_jsonb(h) AS source_human_update,s.canonical_name AS stage_name,
                      w.canonical_name AS work_name,a.display_name AS reported_by_display_name
               FROM blockers b JOIN human_updates h ON h.id=b.source_human_update_id AND h.event_id=b.event_id
               JOIN accounts a ON a.id=b.reported_by_account_id
               LEFT JOIN stages s ON s.id=b.stage_id AND s.event_id=b.event_id
               LEFT JOIN work_items w ON w.id=b.work_id AND w.event_id=b.event_id
               WHERE b.event_id=%s""" + (' AND b.id=%s' if blocker_id else '') + ' ORDER BY b.created_at DESC,b.id',
            (event_id, blocker_id) if blocker_id else (event_id,),
        ).fetchall()
        results = []
        for row in rows:
            payload = {key: row[key] for key in BlockerSnapshot.model_fields}
            payload['source_human_update'] = HumanUpdateService._report(row['source_human_update'])
            results.append(BlockerSnapshot.model_validate(payload))
        return results

    def create_blocker(self, event_id: UUID, account_id: UUID, body: BlockerCreate) -> BlockerSnapshot:
        with self.database.connect() as c:
            return self._create_blocker(
                c, event_id, account_id, body, reuse_existing_source=False
            )

    def _create_blocker(
        self,
        connection,
        event_id: UUID,
        account_id: UUID,
        body: BlockerCreate,
        *,
        reuse_existing_source: bool,
    ) -> BlockerSnapshot:
        """Deterministic blocker boundary, reusable inside a caller's transaction."""
        event = self._event(connection, event_id, account_id, write=True)
        self._require_organizer(connection, event, account_id)
        source = connection.execute(
            'SELECT * FROM human_updates WHERE id=%s AND event_id=%s',
            (body.human_update_id, event_id),
        ).fetchone()
        if source is None:
            raise ValidationError('source human update must belong to this event')
        stage_id, work_id = body.stage_id, body.work_id
        if stage_id is None and work_id is None:
            stage_id, work_id = source['stage_id'], source['work_id']
        scope = self._scope(connection, event_id, stage_id=stage_id, work_id=work_id)
        values = dict(
            event_id=event_id,
            source_human_update_id=body.human_update_id,
            stage_id=scope['stage_id'],
            work_id=scope['work_id'],
            title=body.title,
            summary=body.summary,
            category=body.category,
        )
        existing = connection.execute(
            """SELECT * FROM blockers WHERE event_id=%s AND
               (source_human_update_id=%s OR (idempotency_key IS NOT NULL AND idempotency_key=%s))""",
            (event_id, body.human_update_id, body.idempotency_key),
        ).fetchall()
        if existing:
            if reuse_existing_source and len(existing) == 1 and (
                existing[0]['source_human_update_id'] == body.human_update_id
            ):
                return self._blocker_rows(connection, event_id, existing[0]['id'])[0]
            if (
                len(existing) != 1
                or any(existing[0][key] != value for key, value in values.items())
                or (
                    body.idempotency_key is not None
                    and existing[0]['idempotency_key'] != body.idempotency_key
                )
            ):
                raise IdempotencyConflictError(
                    'source update or idempotency key already has a different blocker'
                )
            return self._blocker_rows(connection, event_id, existing[0]['id'])[0]
        row = connection.execute(
            """INSERT INTO blockers(id,event_id,source_human_update_id,reported_by_account_id,
                   created_by_account_id,stage_id,work_id,title,summary,category,idempotency_key)
               VALUES(%(id)s,%(event_id)s,%(source_human_update_id)s,%(reported_by_account_id)s,
                   %(created_by_account_id)s,%(stage_id)s,%(work_id)s,%(title)s,%(summary)s,%(category)s,%(idempotency_key)s)
               RETURNING id""",
            dict(
                id=uuid4(),
                reported_by_account_id=source['reporter_account_id'],
                created_by_account_id=account_id,
                idempotency_key=body.idempotency_key,
                **values,
            ),
        ).fetchone()
        return self._blocker_rows(connection, event_id, row['id'])[0]

    def list_blockers(self, event_id: UUID, account_id: UUID) -> list[BlockerSnapshot]:
        with self.database.connect() as c:
            event = self._event(c, event_id, account_id)
            self._require_organizer(c, event, account_id)
            return self._blocker_rows(c, event_id)

    def update_blocker(self, event_id: UUID, blocker_id: UUID, account_id: UUID, body: BlockerPatch) -> BlockerSnapshot:
        with self.database.connect() as c:
            event = self._event(c, event_id, account_id, write=True)
            self._require_organizer(c, event, account_id)
            row = c.execute('SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE', (blocker_id, event_id)).fetchone()
            if row is None:
                raise NotFoundError('blocker not found in this event')
            if row['version'] != body.expected_version:
                raise StaleVersionError('blocker version is stale')
            handling = body.handling_state.value if body.handling_state else row['handling_state']
            condition = body.condition_state.value if body.condition_state else row['condition_state']
            if handling != row['handling_state'] or condition != row['condition_state']:
                c.execute(
                    """UPDATE blockers SET handling_state=%s,condition_state=%s,
                       cleared_at=CASE WHEN %s='OPEN' THEN NULL ELSE COALESCE(cleared_at,now()) END,
                       version=version+1,updated_at=now() WHERE id=%s""", (handling, condition, condition, blocker_id),
                )
            return self._blocker_rows(c, event_id, blocker_id)[0]
