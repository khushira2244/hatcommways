"""Deterministic validation and Work Share math for work proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from .dependency_validation import validate_acyclic_dependencies
from .errors import ValidationError
from .models import EventSnapshot, StageSnapshot, WorkDecompositionProposal


# Proposals may express shares as whole percentages. A correctly rounded whole
# percentage can differ from the exact effort ratio by at most 0.5 points.
WORK_SHARE_ITEM_TOLERANCE = Decimal("0.51")
WORK_SHARE_TOTAL_TOLERANCE = Decimal("0.20")


def calculate_work_shares(
    proposal: WorkDecompositionProposal,
) -> WorkDecompositionProposal:
    """Derive the frozen effort percentage from proposed person-hour estimates."""
    if not proposal.proposed_work:
        return proposal
    efforts = [Decimal(str(item.estimated_person_hours)) for item in proposal.proposed_work]
    total_effort = sum(efforts)
    if total_effort <= 0:
        return proposal
    shares = [
        (effort / total_effort * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for effort in efforts
    ]
    shares[-1] += Decimal("100") - sum(shares)
    return proposal.model_copy(
        update={
            "proposed_work": [
                item.model_copy(update={"work_share": float(share)})
                for item, share in zip(proposal.proposed_work, shares, strict=True)
            ]
        }
    )
_UNVERIFIED_CONFIRMATION = re.compile(
    r"\b(?:confirmed|verified)\s+"
    r"(?:resource|resources|equipment|material|materials|venue|permission|"
    r"participant|participants|volunteer|volunteers|sponsor|sponsors)\b",
    re.IGNORECASE,
)


class WorkDecompositionValidator:
    def parse(self, payload: Mapping[str, Any]) -> WorkDecompositionProposal:
        try:
            return WorkDecompositionProposal.model_validate(payload)
        except PydanticValidationError as error:
            raise ValidationError(str(error)) from error

    def validate(
        self,
        proposal: WorkDecompositionProposal,
        event: EventSnapshot,
        stage: StageSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> WorkDecompositionProposal:
        if expected_proposal_id is not None and proposal.proposal_id != expected_proposal_id:
            raise ValidationError("proposal_id does not match the requested proposal")
        if proposal.event_id != event.id or proposal.stage_id != stage.id:
            raise ValidationError("work proposal must target exactly the scoped stage")
        if stage.event_id != event.id:
            raise ValidationError("target stage does not belong to the event")
        if proposal.base_event_version != event.version:
            raise ValidationError("proposal base event version is not current")
        if proposal.base_stage_version != stage.version:
            raise ValidationError("proposal base stage version is not current")
        if proposal.approval_required is not True:
            raise ValidationError("work decomposition always requires organizer approval")
        if not proposal.proposed_work:
            raise ValidationError("at least one work item is required")

        refs = [work.temporary_work_ref for work in proposal.proposed_work]
        if len(refs) != len(set(refs)):
            raise ValidationError("temporary work references must be unique")

        dependency_graph: dict[str, set[str]] = {}
        total_hours = sum(
            (Decimal(str(work.estimated_person_hours)) for work in proposal.proposed_work),
            Decimal("0"),
        )
        total_share = Decimal("0")
        for work in proposal.proposed_work:
            if work.proposed_start.tzinfo is None or work.proposed_end.tzinfo is None:
                raise ValidationError("work timestamps must be timezone-aware")
            if work.proposed_end <= work.proposed_start:
                raise ValidationError("work end must be after work start")
            if work.proposed_start < stage.starts_at or work.proposed_end > stage.ends_at:
                raise ValidationError("work must remain inside the approved stage window")
            dependency_graph[work.temporary_work_ref] = set(work.dependencies)
            actual_share = Decimal(str(work.work_share))
            expected_share = (
                Decimal(str(work.estimated_person_hours)) / total_hours * Decimal("100")
            )
            if abs(actual_share - expected_share) > WORK_SHARE_ITEM_TOLERANCE:
                raise ValidationError(
                    "work_share must equal estimated person-hours divided by total "
                    "stage person-hours times 100"
                )
            total_share += actual_share

        if abs(total_share - Decimal("100")) > WORK_SHARE_TOTAL_TOLERANCE:
            raise ValidationError("work shares must total approximately 100 percent")
        validate_acyclic_dependencies(dependency_graph)
        self._reject_unverified_confirmations(proposal)
        return proposal

    def parse_and_validate(
        self,
        payload: Mapping[str, Any],
        event: EventSnapshot,
        stage: StageSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> WorkDecompositionProposal:
        return self.validate(
            self.parse(payload),
            event,
            stage,
            expected_proposal_id=expected_proposal_id,
        )

    @staticmethod
    def _reject_unverified_confirmations(
        proposal: WorkDecompositionProposal,
    ) -> None:
        texts = [proposal.concise_rationale, *proposal.assumptions]
        for work in proposal.proposed_work:
            texts.extend((work.canonical_name, work.purpose))
        if any(_UNVERIFIED_CONFIRMATION.search(text) for text in texts):
            raise ValidationError(
                "proposal claims a confirmed real-world fact unavailable in scoped stage facts"
            )
