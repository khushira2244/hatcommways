"""Local ASGI entry point for the Hatcommways API."""

from __future__ import annotations

import os

from services.api.app import create_app
from services.planning_foundation.database import Database


database_url = os.environ.get("HATCOMMWAYS_DATABASE_URL")
if not database_url:
    raise RuntimeError("HATCOMMWAYS_DATABASE_URL is required")

database = Database(database_url)
database.apply_schema()
app = create_app(
    database,
    execute_planning_requests=True,
    google_maps_api_key=os.environ.get("HATCOMMWAYS_GOOGLE_MAPS_API_KEY"),
    google_maps_map_id=os.environ.get("HATCOMMWAYS_GOOGLE_MAPS_MAP_ID"),
)
