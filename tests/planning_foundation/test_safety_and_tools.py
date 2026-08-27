from __future__ import annotations

from uuid import uuid4

import pytest

from services.planning_foundation import PlanningService
from services.planning_foundation.errors import (
    AuthorizationError,
    ProposalAlreadyDecidedError,
    StaleProposalError,
)
from services.planning_foundation.models import (
    ProposalDecision,
    ProposalDecisionCommand,
    ProposalStatus,
)
from services.planning_foundation.tools import ScopedPlanningReadTools
from tests.planning_foundation.conftest import create_event, store_update


def decide(proposal, organizer_id, value, *, key=None):
    return ProposalDecisionCommand(
        proposal_id=proposal.id,
        organizer_id=organizer_id,
        decision=value,
        decision_idempotency_key=key or f"decision-{uuid4()}",
    )


def test_stale_proposal_rejected_completely(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Stale name")
    service.update_event_direct(
        event_id=event.id,
        organizer_id=organizer_id,
        expected_version=1,
        changes={"purpose": "Newer authoritative purpose"},
    )
    result = service.decide_proposal(
        decide(proposal, organizer_id, ProposalDecision.APPROVE)
    )
    assert result.status == ProposalStatus.STALE
    assert service.get_event(event.id).name == event.name
    assert service.get_event(event.id).version == 2


def test_duplicate_approval_does_not_apply_twice(service, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Approved once")
    key = "same-decision-key"
    first = service.decide_proposal(
        decide(proposal, organizer_id, ProposalDecision.APPROVE, key=key)
    )
    second = service.decide_proposal(
        decide(proposal, organizer_id, ProposalDecision.APPROVE, key=key)
    )
    assert first.applied_event.version == 2
    assert second.applied_event.version == 2
    assert second.duplicate is True
    with pytest.raises(ProposalAlreadyDecidedError):
        service.decide_proposal(
            decide(proposal, organizer_id, ProposalDecision.APPROVE)
        )


def test_application_and_outbox_are_atomic(database, organizer_id, monkeypatch):
    service = PlanningService(database)
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Must roll back")

    def fail_before_outbox(connection):
        raise RuntimeError("simulated outbox boundary failure")

    monkeypatch.setattr(service, "_before_approval_outbox", fail_before_outbox)
    with pytest.raises(RuntimeError, match="simulated outbox"):
        service.decide_proposal(
            decide(proposal, organizer_id, ProposalDecision.APPROVE)
        )
    assert service.get_event(event.id).version == 1
    assert service.get_event(event.id).name == event.name
    assert service.get_proposal(proposal.id).status == ProposalStatus.PENDING


def test_approval_outbox_is_correlated(service, database, organizer_id):
    event = create_event(service, organizer_id)
    proposal = store_update(service, event, name="Correlated")
    service.decide_proposal(
        decide(proposal, organizer_id, ProposalDecision.APPROVE)
    )
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT event_type, aggregate_type, aggregate_id, aggregate_version,
                   correlation_id, causation_id, payload, published_at
            FROM domain_outbox
            WHERE correlation_id = %s
            ORDER BY occurred_at
            """,
            (proposal.correlation_id,),
        ).fetchall()
    assert [row["event_type"] for row in rows] == [
        "proposal.stored", "proposal.approved", "event.updated"
    ]
    assert rows[1]["causation_id"] == proposal.id
    assert rows[2]["aggregate_version"] == 2
    assert all(row["published_at"] is None for row in rows)


def test_scoped_read_tool_enforces_actor_and_version(service, organizer_id):
    event = create_event(service, organizer_id)
    tools = ScopedPlanningReadTools(service)
    brief = tools.get_event_brief(
        event_id=event.id, organizer_id=organizer_id, expected_version=1
    )
    assert brief.event_id == event.id
    assert not hasattr(brief, "organizer_id")
    with pytest.raises(AuthorizationError):
        tools.get_event_brief(
            event_id=event.id, organizer_id=uuid4(), expected_version=1
        )
    with pytest.raises(StaleProposalError):
        tools.get_event_brief(
            event_id=event.id, organizer_id=organizer_id, expected_version=2
        )
