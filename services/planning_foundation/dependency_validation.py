"""Pure structural validation for future Level 1 dependency graphs."""

from __future__ import annotations

from collections.abc import Mapping, Set
from typing import Hashable

from .errors import ValidationError


def validate_acyclic_dependencies(
    dependencies: Mapping[Hashable, Set[Hashable]],
) -> None:
    """Reject missing references, self-dependencies, and directed cycles."""

    nodes = set(dependencies)
    for node, prerequisites in dependencies.items():
        if node in prerequisites:
            raise ValidationError(f"self-dependency is not allowed: {node}")
        missing = set(prerequisites) - nodes
        if missing:
            raise ValidationError(f"dependency references missing nodes: {missing}")

    visiting: set[Hashable] = set()
    visited: set[Hashable] = set()

    def visit(node: Hashable) -> None:
        if node in visiting:
            raise ValidationError("dependency graph contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for prerequisite in dependencies[node]:
            visit(prerequisite)
        visiting.remove(node)
        visited.add(node)

    for node in nodes:
        visit(node)
