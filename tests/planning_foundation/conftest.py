from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.planning_foundation import Database, PlanningService
from services.planning_foundation.models import EventCreate, ProposalCreate


TEST_DSN = os.environ.get("HATCOMMWAYS_TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def database() -> Database:
    if not TEST_DSN:
        pytest.fail("HATCOMMWAYS_TEST_DATABASE_URL is required for PostgreSQL tests")
    database = Database(TEST_DSN)
    database.apply_schema()
    return database


@pytest.fixture(autouse=True)
def clean_database(database: Database) -> None:
    with database.connect() as connection:
        connection.execute(
            """TRUNCATE event_setup_updates, event_setups,
               event_memberships, auth_sessions, accounts,
               actor_requirements, actor_requirement_requests,
               work_dependencies, work_items, work_design_requests,
               stage_dependencies, stages, event_planning_requests,
               proposal_decisions, domain_outbox, proposals, events CASCADE"""
        )


@pytest.fixture
def service(database: Database) -> PlanningService:
    return PlanningService(database)


@pytest.fixture
def organizer_id():
    return uuid4()


def make_event_command(organizer_id, **changes) -> EventCreate:
    values = {
        "organizer_id": organizer_id,
        "name": "Hyderabad Lake Cleanup",
        "purpose": "Clean and restore a community lakefront",
        "event_type": "community_cleanup",
        "starts_at": datetime(2026, 9, 5, 8, tzinfo=timezone.utc),
        "ends_at": datetime(2026, 9, 5, 16, tzinfo=timezone.utc),
        "timezone": "Asia/Kolkata",
        "location_description": "Hyderabad lakefront",
    }
    values.update(changes)
    return EventCreate(**values)


def create_event(service, organizer_id):
    return service.create_event(
        make_event_command(organizer_id), idempotency_key=f"event-{uuid4()}"
    )


def store_update(service, event, **changes):
    return service.store_proposal(
        ProposalCreate(
            proposal_type="EVENT_UPDATE",
            target_type="EVENT",
            target_id=event.id,
            created_by="future-agent:test",
            base_versions={"event": event.version},
            payload=changes or {"purpose": "Updated community purpose"},
            idempotency_key=f"proposal-{uuid4()}",
        )
    )
