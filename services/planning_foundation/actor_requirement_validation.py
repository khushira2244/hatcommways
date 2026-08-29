"""Deterministic validation for Actor Requirement proposals."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from .errors import ValidationError
from .models import (
    ActorRequirementProposal,
    EventSnapshot,
    StageSnapshot,
    WorkSnapshot,
)


ROLE_CATEGORIES = frozenset(
    {
        "OWNERSHIP",
        "PLANNING",
        "COORDINATION",
        "EXECUTION",
        "SPECIALIST",
        "REVIEW_VALIDATION",
        "ORGANIZATION_REPRESENTATION",
        "SUPPORT_SPONSORSHIP",
        "EVENT_OPERATION",
        "COMMUNICATION_OUTREACH",
        "APPROVAL_AUTHORITY",
        "ADVISORY_GUIDANCE",
    }
)

FORBIDDEN_PROTECTED_TRAITS = (
    "gender", "sex", "race", "ethnicity", "religion", "caste", "disability",
    "sexual orientation", "age", "pregnancy", "nationality",
)
FORBIDDEN_PERSON_FIELDS = {
    "participant_id", "participant_ids", "person_id", "person_ids", "actor_id",
    "actor_ids", "assigned_person", "assigned_people", "participant_assignment",
    "participant_assignments", "person_score", "capability_score", "efficiency_score",
}
FORBIDDEN_MUTATION_FIELDS = {
    "work_mutation", "stage_mutation", "event_mutation", "work_updates",
    "stage_updates", "event_updates",
}


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for nested in value.values() for key in _walk_keys(nested)}
    if isinstance(value, list):
        return {key for nested in value for key in _walk_keys(nested)}
    return set()


class ActorRequirementValidator:
    def parse(self, payload: dict[str, Any]) -> ActorRequirementProposal:
        forbidden = _walk_keys(payload) & (FORBIDDEN_PERSON_FIELDS | FORBIDDEN_MUTATION_FIELDS)
        if forbidden:
            raise ValidationError(
                f"actor requirement proposal contains forbidden fields: {sorted(forbidden)}"
            )
        try:
            return ActorRequirementProposal.model_validate(payload)
        except PydanticValidationError as error:
            raise ValidationError(str(error)) from error

    def parse_and_validate(
        self,
        payload: dict[str, Any],
        event: EventSnapshot,
        stage: StageSnapshot,
        work: WorkSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> ActorRequirementProposal:
        proposal = self.parse(payload)
        self.validate(
            proposal, event, stage, work, expected_proposal_id=expected_proposal_id
        )
        return proposal

    def validate(
        self,
        proposal: ActorRequirementProposal,
        event: EventSnapshot,
        stage: StageSnapshot,
        work: WorkSnapshot,
        *,
        expected_proposal_id: UUID | None = None,
    ) -> None:
        if expected_proposal_id is not None and proposal.proposal_id != expected_proposal_id:
            raise ValidationError("proposal_id does not match the allocated proposal")
        if proposal.event_id != event.id or proposal.stage_id != stage.id:
            raise ValidationError("proposal must target the work event and stage")
        if proposal.work_id != work.id or work.stage_id != stage.id or stage.event_id != event.id:
            raise ValidationError("proposal must target exactly one current work item")
        if proposal.base_event_version != event.version:
            raise ValidationError("actor requirement proposal event version is stale")
        if proposal.base_stage_version != stage.version:
            raise ValidationError("actor requirement proposal stage version is stale")
        if proposal.base_work_version != work.version:
            raise ValidationError("actor requirement proposal work version is stale")
        if proposal.approval_required is not True:
            raise ValidationError("actor requirements require organizer approval")

        identities: set[tuple[str, str]] = set()
        for requirement in proposal.proposed_requirements:
            category = requirement.role_category.strip().upper()
            if category not in ROLE_CATEGORIES:
                raise ValidationError(f"invalid actor role category: {requirement.role_category}")
            identity = (category, requirement.canonical_role_name.casefold())
            if identity in identities:
                raise ValidationError("actor requirements must have unique category/name pairs")
            identities.add(identity)
            searchable = " ".join(
                [
                    requirement.canonical_role_name,
                    requirement.responsibility_summary,
                    *requirement.relevant_capabilities,
                    requirement.rough_effort_expectation,
                    requirement.rationale,
                ]
            ).casefold()
            trait = next(
                (
                    term
                    for term in FORBIDDEN_PROTECTED_TRAITS
                    if re.search(rf"\b{re.escape(term)}\b", searchable)
                ),
                None,
            )
            if trait:
                raise ValidationError(
                    f"protected-trait reasoning is forbidden in actor requirements: {trait}"
                )
