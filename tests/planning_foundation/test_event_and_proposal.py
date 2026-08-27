from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from services.planning_foundation.errors import AuthorizationError, ValidationError
from services.planning_foundation.models import (
    EventCreate,
    ProposalCreate,
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
)
from tests.planning_foundation.conftest import (
    create_event,
    make_event_command,
    store_update,
)


def decide(proposal, organizer_id, value, *, key=None, edited_payload=None):
    return ProposalDecisionCommand(
        proposal_id=proposal.id,
        organizer_id=organizer_id,
        decision=value,
        decision_idempotency_key=key or f"decision-{uuid4()}",
        edited_payload=edited_payload,
    )


def test_valid_event_creation_and_outbox(service, database, organizer_id):
    event = create_event(service, organizer_id)
    assert event.version == 1
    assert event.organizer_id == organizer_id
    with database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM domain_outbox WHERE aggregate_id = %s", (event.id,)
        ).fetchone()
    assert row["event_type"] == "event.created"
    assert row["aggregate_version"] == 1
    assert row["published_at"] is None


def test_missing_required_event_field():
    with pytest.raises(PydanticValidationError):
        EventCreate(
            organizer_id=uuid4(),
            purpose="purpose",
            event_type="cleanup",
            starts_at=datetime.now(timezone.utc),
            ends_at=datetime.now(timezone.utc).replace(year=2027),
            timezone="UTC",
            location_description="Somewhere",
        )


def test_invalid_time_range(organizer_id):
    starts = datetime.now(timezone.utc)
    with pytest.raises(PydanticValidationError):
        make_event_command(organizer_id, starts_at=starts, ends_at=starts)


def test_only_organizer_can_update_or_decide(service, organizer_id):
    event = create_event(service, organizer_id)
    with pytest.raises(AuthorizationError):
        service.update_event_direct(
            event_id=event.id,
            organizer_id=uuid4(),
            expected_version=1,
            changes={"name": "Unauthorized"},
        )
    proposal = store_update(service, event)
    with pytest.raises(AuthorizationError):
        service.decide_proposal(decide(proposal, uuid4(), ProposalDecision.APPROVE))


def test_event_version_increments(service, organizer_id):
    event = create_event(service, organizer_id)
    updated = service.update_event_direct(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_version=1,
        changes={"name": "Updated event"},
    )
    assert updated.version == 2


def test_proposal_storage_is_idempotent(service, organizer_id):
    event = create_event(service, organizer_id)
    command = ProposalCreate(
        proposal_type="EVENT_UPDATE",
        target_type="EVENT",
        target_id=event.id,
        created_by="future-agent:test",
        base_versions={"event": 1},
        payload={"name": "Proposed name"},
        idempotency_key="same-proposal-key",
    )
    first = service.store_proposal(command)
    second = service.store_proposal(command)
    assert first.id == second.id
    assert first.status == ProposalStatus.PENDING


def test_proposal_approval_applies_revalidated_edit(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Agent name")
    result = service.decide_proposal(
        decide(
            proposal,
            organizer_id,
            ProposalDecision.APPROVE,
            edited_payload={"name": "Organizer-approved name"},
        )
    )
    assert result.status == ProposalStatus.APPROVED
    assert result.applied_event.name == "Organizer-approved name"
    assert result.applied_event.version == 2


def test_invalid_organizer_edit_is_not_applied(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event)
    with pytest.raises(ValidationError):
        service.decide_proposal(
            decide(
                proposal,
                organizer_id,
                ProposalDecision.APPROVE,
                edited_payload={"ends_at": event.starts_at.isoformat()},
            )
        )
    assert service.get_event(event.id).version == 1
    assert service.get_proposal(proposal.id).status == ProposalStatus.PENDING


def test_empty_organizer_edit_is_revalidated(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event)
    with pytest.raises(ValidationError):
        service.decide_proposal(
            decide(
                proposal,
                organizer_id,
                ProposalDecision.APPROVE,
                edited_payload={},
            )
        )
    assert service.get_event(event.id).version == 1
    assert service.get_proposal(proposal.id).status == ProposalStatus.PENDING


def test_proposal_rejection_does_not_change_event(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Rejected name")
    result = service.decide_proposal(
        decide(proposal, organizer_id, ProposalDecision.REJECT)
    )
    assert result.status == ProposalStatus.REJECTED
    assert service.get_event(event.id).name == event.name
    assert service.get_event(event.id).version == 1
