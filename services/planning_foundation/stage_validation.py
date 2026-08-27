"""Deterministic validation for Event Planning Agent proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from .dependency_validation import validate_acyclic_dependencies
from .errors import ValidationError
from .models import EventSnapshot, StagePlanProposal


_UNVERIFIED_CONFIRMATION = re.compile(
    r"\b(?:confirmed|verified)\s+"
    r"(?:venue|permission|resource|resources|participant|participants|"
    r"volunteer|volunteers|sponsor|sponsors)\b",
    re.IGNORECASE,
)


class StagePlanValidator:
    def parse(self, payload: Mapping[str, Any]) -> StagePlanProposal:
        try:
            return StagePlanProposal.model_validate(payload)
        except PydanticValidationError as error:
            raise ValidationError(str(error)) from error

    def validate(
        self,
        proposal: StagePlanProposal,
        event: EventSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> StagePlanProposal:
        if expected_proposal_id is not None and proposal.proposal_id != expected_proposal_id:
            raise ValidationError("proposal_id does not match the requested proposal")
        if proposal.event_id != event.id:
            raise ValidationError("proposal targets a different event")
        if proposal.base_event_version != event.version:
            raise ValidationError("proposal base event version is not current")
        if proposal.approval_required is not True:
            raise ValidationError("stage plans always require organizer approval")
        if not proposal.proposed_stages:
            raise ValidationError("at least one stage is required")

        refs = [stage.temporary_stage_ref for stage in proposal.proposed_stages]
        if len(refs) != len(set(refs)):
            raise ValidationError("temporary stage references must be unique")

        orders = [stage.proposed_order for stage in proposal.proposed_stages]
        expected_orders = list(range(1, len(proposal.proposed_stages) + 1))
        if sorted(orders) != expected_orders:
            raise ValidationError("stage order must be unique and contiguous from 1")

        dependency_graph: dict[str, set[str]] = {}
        for stage in proposal.proposed_stages:
            if stage.proposed_start.tzinfo is None or stage.proposed_end.tzinfo is None:
                raise ValidationError("stage timestamps must be timezone-aware")
            if stage.proposed_end <= stage.proposed_start:
                raise ValidationError("stage end must be after stage start")
            if stage.proposed_start < event.starts_at or stage.proposed_end > event.ends_at:
                raise ValidationError("stage must remain inside the event window")
            dependency_graph[stage.temporary_stage_ref] = set(stage.dependencies)

        validate_acyclic_dependencies(dependency_graph)
        self._reject_unverified_confirmations(proposal)
        return proposal

    def parse_and_validate(
        self,
        payload: Mapping[str, Any],
        event: EventSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> StagePlanProposal:
        return self.validate(
            self.parse(payload), event, expected_proposal_id=expected_proposal_id
        )

    @staticmethod
    def _reject_unverified_confirmations(proposal: StagePlanProposal) -> None:
        texts = [proposal.concise_rationale, *proposal.assumptions]
        for stage in proposal.proposed_stages:
            texts.extend((stage.canonical_name, stage.purpose))
        if any(_UNVERIFIED_CONFIRMATION.search(text) for text in texts):
            raise ValidationError(
                "proposal claims a confirmed real-world fact unavailable in scoped event facts"
            )
