"""Production runtime routes composed from existing bounded workflows."""

from __future__ import annotations

import os
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from psycopg import OperationalError

from services.planning_foundation.coordination_service import CoordinationService
from services.planning_foundation.database import Database

from .coordination import CoordinationWorkflow, StrandsCoordinationAgent
from .sponsor_fit import SponsorFitWorkflow
from services.planning_foundation.support_offer_service import SupportOfferService
from .runtime_events import RuntimeEventEnvelope
from .runtime_worker import RetryableRuntimeError, RuntimeHandler, RuntimeRouter


def production_router(database: Database) -> RuntimeRouter:
    coordination_service = CoordinationService(database)
    workflow = CoordinationWorkflow(
        coordination_service,
        StrandsCoordinationAgent(coordination_service),
    )

    def coordinate_affected_work(event: RuntimeEventEnvelope) -> dict[str, object]:
        if os.environ.get("HATCOMMWAYS_RUNTIME_FAILURE_PROOF_MESSAGE_ID") == str(event.message_id):
            raise RetryableRuntimeError("controlled runtime failure proof")
        event_id = UUID(str(event.payload["event_id"]))
        blocker_id = UUID(str(event.payload["blocker_id"]))
        try:
            with database.connect() as connection:
                owner = connection.execute(
                    "SELECT organizer_id FROM events WHERE id=%s",
                    (event_id,),
                ).fetchone()
            if owner is None:
                raise ValueError("runtime event references an unknown event")
            proposal = workflow.execute(
                event_id=event_id,
                blocker_id=blocker_id,
                organizer_id=owner["organizer_id"],
                retry=True,
            )
        except (BotoCoreError, ClientError, OperationalError) as error:
            raise RetryableRuntimeError(str(error)) from error
        return {
            "coordination_proposal_id": str(proposal.id),
            "event_id": str(event_id),
            "blocker_id": str(blocker_id),
            "requires_replanning": proposal.requires_replanning,
        }

    return RuntimeRouter({
        "support_offer.submitted": RuntimeHandler(
            name="hatcommways-sponsor-fit-agent",
            execute=SponsorFitWorkflow(SupportOfferService(database)).execute,
            max_attempts=3, policy_reference="sponsor-fit-bounded-v1",
        ),
        "blocker.affected_work_resolved": RuntimeHandler(
            name="hatcommways-coordination-agent",
            execute=coordinate_affected_work,
            max_attempts=3,
            policy_reference="coordination-bounded-v1",
        )
    })
