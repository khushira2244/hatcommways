from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from psycopg.types.json import Jsonb

from .database import Database
from .errors import StaleProposalError, ValidationError
from .event_setup_models import EventSetupSettings, EventSetupSnapshot, EventSetupUpdateRequest
from .services import PlanningService


class EventSetupService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, event_id: UUID, organizer_id: UUID) -> EventSetupSnapshot:
        with self.database.connect() as connection:
            event = PlanningService._lock_event(connection, event_id)
            PlanningService._require_organizer(event, organizer_id)
            row = connection.execute(
                "SELECT * FROM event_setups WHERE event_id=%s", (event_id,)
            ).fetchone()
        return self._snapshot(event_id, row)

    def update(
        self, event_id: UUID, organizer_id: UUID, command: EventSetupUpdateRequest
    ) -> EventSetupSnapshot:
        settings = EventSetupSettings.model_validate(
            command.model_dump(exclude={"expected_version", "idempotency_key"})
        )
        canonical = json.dumps(settings.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self.database.connect() as connection:
            event = PlanningService._lock_event(connection, event_id)
            PlanningService._require_organizer(event, organizer_id)
            replay = connection.execute(
                "SELECT * FROM event_setup_updates WHERE idempotency_key=%s",
                (command.idempotency_key,),
            ).fetchone()
            if replay is not None:
                if replay["event_id"] != event_id or replay["request_fingerprint"] != fingerprint:
                    raise ValidationError("idempotency key was already used for a different setup update")
                return EventSetupSnapshot.model_validate(replay["result"])

            current = connection.execute(
                "SELECT * FROM event_setups WHERE event_id=%s FOR UPDATE", (event_id,)
            ).fetchone()
            current_version = current["version"] if current is not None else 0
            if command.expected_version != current_version:
                raise StaleProposalError("event setup version is stale")
            values = settings.model_dump(mode="json")
            if current is None:
                row = connection.execute(
                    """
                    INSERT INTO event_setups (
                        event_id,initial_invites,sponsors_support,resource_needs,
                        contribution_links,event_media,cover_image_data_url,map_enabled,default_view,event_latitude,event_longitude,map_area_label,participation_dimensions,
                        event_visibility,show_participant_counts,show_actor_tree,
                        show_sponsors,show_resources,show_payment_links
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING *
                    """,
                    self._parameters(event_id, values),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    UPDATE event_setups SET
                        initial_invites=%s,sponsors_support=%s,resource_needs=%s,
                        contribution_links=%s,event_media=%s,cover_image_data_url=%s,map_enabled=%s,default_view=%s,event_latitude=%s,event_longitude=%s,map_area_label=%s,
                        participation_dimensions=%s,event_visibility=%s,
                        show_participant_counts=%s,show_actor_tree=%s,show_sponsors=%s,
                        show_resources=%s,show_payment_links=%s,
                        version=version+1,updated_at=now()
                    WHERE event_id=%s RETURNING *
                    """,
                    self._parameters(event_id, values)[1:] + (event_id,),
                ).fetchone()
            maps = values["map_settings"]
            marker_id = uuid5(NAMESPACE_URL, f"hatcommways:event-map:{event_id}")
            if maps.get("event_latitude") is not None:
                connection.execute(
                    """INSERT INTO map_locations(id,event_id,entity_type,entity_id,display_name,latitude,longitude,area_label,location_precision,status,visible,metadata)
                       VALUES(%s,%s,'EVENT',%s,%s,%s,%s,%s,'ZONE','ACTIVE',%s,%s)
                       ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,latitude=excluded.latitude,longitude=excluded.longitude,
                         area_label=excluded.area_label,visible=excluded.visible,updated_at=now()""",
                    (marker_id,event_id,event_id,event["name"],maps["event_latitude"],maps["event_longitude"],maps.get("area_label") or event["location_description"],maps["map_enabled"],Jsonb({"source_label":"Organizer approximate event location"})),
                )
            elif not maps["map_enabled"]:
                connection.execute("UPDATE map_locations SET visible=false,updated_at=now() WHERE id=%s",(marker_id,))
            snapshot = self._snapshot(event_id, row)
            correlation_id = uuid4()
            connection.execute(
                """
                INSERT INTO event_setup_updates (
                    id,event_id,organizer_id,idempotency_key,request_fingerprint,
                    applied_version,result,correlation_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    uuid4(), event_id, organizer_id, command.idempotency_key,
                    fingerprint, snapshot.version,
                    Jsonb(snapshot.model_dump(mode="json")), correlation_id,
                ),
            )
            PlanningService._enqueue_outbox(
                connection,
                event_type="event.setup_saved",
                aggregate_type="EVENT_SETUP",
                aggregate_id=event_id,
                aggregate_version=snapshot.version,
                payload={"event_id": str(event_id), "setup_version": snapshot.version},
                correlation_id=correlation_id,
                causation_id=None,
            )
        return snapshot

    @staticmethod
    def _parameters(event_id: UUID, values: dict):
        maps = values["map_settings"]
        privacy = values["privacy_settings"]
        return (
            event_id,
            Jsonb(values["initial_invites"]),
            Jsonb(values["sponsors_support"]),
            Jsonb(values["resources"]),
            Jsonb(values["contribution_links"]),
            Jsonb(values["event_media"]),
            values["cover_image_data_url"],
            maps["map_enabled"], maps["default_view"], maps["event_latitude"], maps["event_longitude"], maps["area_label"], Jsonb(maps["participation_dimensions"]),
            privacy["event_visibility"], privacy["show_participant_counts"],
            privacy["show_actor_tree"], privacy["show_sponsors"],
            privacy["show_resources"], privacy["show_payment_links"],
        )

    @staticmethod
    def _snapshot(event_id: UUID, row) -> EventSetupSnapshot:
        if row is None:
            return EventSetupSnapshot(event_id=event_id, version=0)
        return EventSetupSnapshot(
            event_id=event_id,
            version=row["version"],
            initial_invites=row["initial_invites"],
            sponsors_support=row["sponsors_support"],
            resources=row["resource_needs"],
            contribution_links=row["contribution_links"],
            event_media=row.get("event_media") or [],
            cover_image_data_url=row.get("cover_image_data_url"),
            map_settings={
                "map_enabled": row["map_enabled"],
                "default_view": row["default_view"],
                "participation_dimensions": row["participation_dimensions"],
                "event_latitude": row.get("event_latitude"),
                "event_longitude": row.get("event_longitude"),
                "area_label": row.get("map_area_label"),
            },
            privacy_settings={
                "event_visibility": row["event_visibility"],
                "show_participant_counts": row["show_participant_counts"],
                "show_actor_tree": row["show_actor_tree"],
                "show_sponsors": row["show_sponsors"],
                "show_resources": row["show_resources"],
                "show_payment_links": row["show_payment_links"],
            },
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
