"""Deterministic affected-work resolution over the confirmed planning graph."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from .affected_work_models import AffectedWorkResolution
from .database import Database
from .errors import NotFoundError, StaleVersionError, ValidationError
from .human_update_service import HumanUpdateService
from .services import PlanningService


class AffectedWorkService:
    """Resolve one assessed blocker without invoking an agent or mutating the plan."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.human_updates = HumanUpdateService(database)

    @staticmethod
    def _resolution(row: dict[str, Any]) -> AffectedWorkResolution:
        return AffectedWorkResolution.model_validate(row)

    def get_resolution(
        self, event_id: UUID, blocker_id: UUID, organizer_id: UUID
    ) -> AffectedWorkResolution | None:
        with self.database.connect() as connection:
            event = self.human_updates._event(connection, event_id, organizer_id)
            self.human_updates._require_organizer(connection, event, organizer_id)
            blocker = connection.execute(
                "SELECT 1 FROM blockers WHERE id=%s AND event_id=%s",
                (blocker_id, event_id),
            ).fetchone()
            if blocker is None:
                raise NotFoundError("blocker not found in this event")
            row = connection.execute(
                "SELECT * FROM affected_work_resolutions WHERE blocker_id=%s AND event_id=%s",
                (blocker_id, event_id),
            ).fetchone()
            return self._resolution(row) if row else None

    def resolve(
        self, event_id: UUID, blocker_id: UUID, organizer_id: UUID
    ) -> AffectedWorkResolution:
        correlation_id = uuid4()
        with self.database.connect() as connection:
            event = self.human_updates._event(
                connection, event_id, organizer_id, write=True
            )
            self.human_updates._require_organizer(connection, event, organizer_id)
            blocker = connection.execute(
                "SELECT * FROM blockers WHERE id=%s AND event_id=%s FOR UPDATE",
                (blocker_id, event_id),
            ).fetchone()
            if blocker is None:
                raise NotFoundError("blocker not found in this event")
            assessment = connection.execute(
                """SELECT * FROM blocker_assessments
                   WHERE event_id=%s AND authoritative_blocker_id=%s""",
                (event_id, blocker_id),
            ).fetchone()
            if assessment is None:
                raise ValidationError(
                    "blocker requires a persisted blocking assessment before affected work can be resolved"
                )
            if not assessment["is_execution_blocker"] or assessment["requires_clarification"]:
                raise ValidationError("assessment is not eligible for affected-work resolution")

            existing = connection.execute(
                "SELECT * FROM affected_work_resolutions WHERE blocker_id=%s",
                (blocker_id,),
            ).fetchone()
            if blocker["condition_state"] == "CLEARED":
                if existing:
                    return self._resolution(existing)
                raise ValidationError("a cleared blocker cannot receive a new affected-work resolution")

            assessed_event_version = assessment["assessed_event_version"]
            if assessed_event_version is None:
                raise StaleVersionError(
                    "blocker assessment predates graph version snapshots and must be reassessed"
                )
            if event["version"] != assessed_event_version:
                raise StaleVersionError("confirmed planning graph changed after blocker assessment")

            graph = self._load_confirmed_graph(connection, event_id, event["version"])
            direct_work_id = assessment["directly_referenced_work_id"]
            direct_stage_id = assessment["directly_referenced_stage_id"]
            if direct_work_id is None and direct_stage_id is None:
                raise ValidationError("blocking assessment has no direct stage or work scope")

            stages = graph["stages"]
            work = graph["work"]
            if direct_stage_id is not None and direct_stage_id not in stages:
                raise ValidationError("directly referenced stage is not confirmed authoritative planning data")
            if direct_work_id is not None:
                direct = work.get(direct_work_id)
                if direct is None:
                    raise ValidationError("directly referenced work is not confirmed authoritative planning data")
                if direct_stage_id is not None and direct["stage_id"] != direct_stage_id:
                    raise ValidationError("direct work and stage references do not agree")
                direct_stage_id = direct["stage_id"]
                if (
                    assessment["assessed_work_version"] is not None
                    and direct["version"] != assessment["assessed_work_version"]
                ):
                    raise StaleVersionError("directly referenced work changed after blocker assessment")
            if (
                direct_stage_id is not None
                and assessment["assessed_stage_version"] is not None
                and stages[direct_stage_id]["version"] != assessment["assessed_stage_version"]
            ):
                raise StaleVersionError("directly referenced stage changed after blocker assessment")

            self._assert_acyclic(work.keys(), graph["work_edges"])
            self._assert_acyclic(stages.keys(), graph["stage_edges"])

            directly_affected: list[UUID] = []
            downstream: list[UUID] = []
            if direct_work_id is not None:
                directly_affected = [direct_work_id]
                downstream_set = self._downstream({direct_work_id}, graph["work_edges"])
                downstream = sorted(downstream_set, key=lambda item: self._work_key(work[item], stages))
                reason = (
                    "Direct work from the persisted blocker assessment plus every confirmed work item "
                    "reachable through prerequisite-to-dependent edges."
                )
            else:
                reason = (
                    "Stage-level blocker retained at stage scope; work impact is not inferred without "
                    "a directly referenced confirmed work item."
                )

            affected_stage_set = {direct_stage_id} if direct_stage_id is not None else set()
            affected_stage_set.update(work[item]["stage_id"] for item in directly_affected)
            affected_stage_set.update(work[item]["stage_id"] for item in downstream)
            affected_stages = sorted(
                affected_stage_set,
                key=lambda item: (stages[item]["stage_order"], str(item)),
            )

            fingerprint = graph["fingerprint"]
            if existing:
                if existing["graph_fingerprint"] != fingerprint:
                    raise StaleVersionError("stored affected-work resolution uses a different planning graph")
                return self._resolution(existing)

            row = connection.execute(
                """INSERT INTO affected_work_resolutions(
                       id,event_id,blocker_id,blocker_assessment_id,
                       directly_affected_work_ids,downstream_affected_work_ids,
                       affected_stage_ids,deterministic_reason,graph_fingerprint,
                       assessed_event_version,resolved_event_version,source_versions)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING *""",
                (
                    uuid4(), event_id, blocker_id, assessment["id"], directly_affected,
                    downstream, affected_stages, reason, fingerprint,
                    assessed_event_version, event["version"], Jsonb(graph["source_versions"]),
                ),
            ).fetchone()
            PlanningService._enqueue_outbox(
                connection,
                event_type="blocker.affected_work_resolved",
                aggregate_type="BLOCKER",
                aggregate_id=blocker_id,
                aggregate_version=blocker["version"],
                payload={
                    "event_id": str(event_id),
                    "blocker_id": str(blocker_id),
                    "blocker_assessment_id": str(assessment["id"]),
                    "resolution_id": str(row["id"]),
                    "directly_affected_work_ids": [str(item) for item in directly_affected],
                    "downstream_affected_work_ids": [str(item) for item in downstream],
                    "affected_stage_ids": [str(item) for item in affected_stages],
                    "graph_fingerprint": fingerprint,
                },
                correlation_id=correlation_id,
            )
            return self._resolution(row)

    @staticmethod
    def _work_key(row: dict[str, Any], stages: dict[UUID, dict[str, Any]]) -> tuple[int, int, str]:
        return stages[row["stage_id"]]["stage_order"], row["work_order"], str(row["id"])

    @staticmethod
    def _downstream(seeds: set[UUID], edges: Iterable[tuple[UUID, UUID]]) -> set[UUID]:
        dependents: dict[UUID, set[UUID]] = defaultdict(set)
        for dependent, prerequisite in edges:
            dependents[prerequisite].add(dependent)
        found: set[UUID] = set()
        pending = list(sorted(seeds, key=str, reverse=True))
        while pending:
            current = pending.pop()
            for dependent in sorted(dependents.get(current, ()), key=str, reverse=True):
                if dependent not in seeds and dependent not in found:
                    found.add(dependent)
                    pending.append(dependent)
        return found

    @staticmethod
    def _assert_acyclic(nodes: Iterable[UUID], edges: Iterable[tuple[UUID, UUID]]) -> None:
        prerequisites: dict[UUID, set[UUID]] = defaultdict(set)
        for dependent, prerequisite in edges:
            prerequisites[dependent].add(prerequisite)
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def visit(node: UUID) -> None:
            if node in visiting:
                raise ValidationError("confirmed dependency graph contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for prerequisite in sorted(prerequisites.get(node, ()), key=str):
                visit(prerequisite)
            visiting.remove(node)
            visited.add(node)

        for node in sorted(set(nodes), key=str):
            visit(node)

    def _load_confirmed_graph(self, connection, event_id: UUID, event_version: int) -> dict[str, Any]:
        stage_rows = connection.execute(
            """SELECT s.* FROM stages s
               JOIN proposals p ON p.id=s.source_proposal_id
               WHERE s.event_id=%s AND p.proposal_type='STAGE_PLAN' AND p.status='APPROVED'""",
            (event_id,),
        ).fetchall()
        stages = {row["id"]: dict(row) for row in stage_rows}
        work_rows = connection.execute(
            """SELECT w.* FROM work_items w
               JOIN stages s ON s.id=w.stage_id AND s.event_id=w.event_id
               JOIN proposals wp ON wp.id=w.source_proposal_id
               JOIN proposals sp ON sp.id=s.source_proposal_id
               WHERE w.event_id=%s
                 AND wp.proposal_type='WORK_DECOMPOSITION' AND wp.status='APPROVED'
                 AND sp.proposal_type='STAGE_PLAN' AND sp.status='APPROVED'""",
            (event_id,),
        ).fetchall()
        work = {row["id"]: dict(row) for row in work_rows}

        all_event_stage_ids = {
            row["id"] for row in connection.execute("SELECT id FROM stages WHERE event_id=%s", (event_id,)).fetchall()
        }
        all_event_work_ids = {
            row["id"] for row in connection.execute("SELECT id FROM work_items WHERE event_id=%s", (event_id,)).fetchall()
        }
        stage_edges: list[tuple[UUID, UUID]] = []
        for row in connection.execute(
            """SELECT d.stage_id,d.depends_on_stage_id,s.event_id AS stage_event_id,
                      p.event_id AS prerequisite_event_id
               FROM stage_dependencies d
               JOIN stages s ON s.id=d.stage_id
               JOIN stages p ON p.id=d.depends_on_stage_id
               WHERE s.event_id=%s OR p.event_id=%s""",
            (event_id, event_id),
        ).fetchall():
            pair = (row["stage_id"], row["depends_on_stage_id"])
            if row["stage_event_id"] != event_id or row["prerequisite_event_id"] != event_id:
                raise ValidationError("stage dependency crosses event boundaries")
            if pair[0] not in stages or pair[1] not in stages:
                raise ValidationError("stage dependency references unconfirmed planning data")
            stage_edges.append(pair)
        work_edges: list[tuple[UUID, UUID]] = []
        for row in connection.execute(
            """SELECT d.work_id,d.depends_on_work_id,w.event_id AS work_event_id,
                      p.event_id AS prerequisite_event_id
               FROM work_dependencies d
               JOIN work_items w ON w.id=d.work_id
               JOIN work_items p ON p.id=d.depends_on_work_id
               WHERE w.event_id=%s OR p.event_id=%s""",
            (event_id, event_id),
        ).fetchall():
            pair = (row["work_id"], row["depends_on_work_id"])
            if row["work_event_id"] != event_id or row["prerequisite_event_id"] != event_id:
                raise ValidationError("work dependency crosses event boundaries")
            if pair[0] not in work or pair[1] not in work:
                raise ValidationError("work dependency references unconfirmed planning data")
            work_edges.append(pair)

        # If rows exist but are absent from the approved graph, keep them outside traversal.
        # A direct assessment of one is rejected above; an edge touching one is rejected here.
        source_versions = {
            "event": event_version,
            "stages": {str(item): stages[item]["version"] for item in sorted(stages, key=str)},
            "work": {str(item): work[item]["version"] for item in sorted(work, key=str)},
        }
        canonical = {
            "event_id": str(event_id),
            "event_version": event_version,
            "stages": [
                [str(item), stages[item]["version"], str(stages[item]["source_proposal_id"])]
                for item in sorted(stages, key=str)
            ],
            "work": [
                [str(item), str(work[item]["stage_id"]), work[item]["version"], str(work[item]["source_proposal_id"])]
                for item in sorted(work, key=str)
            ],
            "stage_edges": [[str(a), str(b)] for a, b in sorted(set(stage_edges), key=lambda pair: (str(pair[0]), str(pair[1])))],
            "work_edges": [[str(a), str(b)] for a, b in sorted(set(work_edges), key=lambda pair: (str(pair[0]), str(pair[1])))],
        }
        fingerprint = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "stages": stages,
            "work": work,
            "stage_edges": list(set(stage_edges)),
            "work_edges": list(set(work_edges)),
            "source_versions": source_versions,
            "fingerprint": fingerprint,
            "all_event_stage_ids": all_event_stage_ids,
            "all_event_work_ids": all_event_work_ids,
        }
