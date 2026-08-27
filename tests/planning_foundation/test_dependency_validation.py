import pytest

from services.planning_foundation.dependency_validation import (
    validate_acyclic_dependencies,
)
from services.planning_foundation.errors import ValidationError


def test_valid_dependency_graph():
    validate_acyclic_dependencies(
        {"stage-1": set(), "stage-2": {"stage-1"}, "stage-3": {"stage-1"}}
    )


@pytest.mark.parametrize(
    "graph",
    [
        {"stage-1": {"stage-1"}},
        {"stage-1": set(), "stage-2": {"missing"}},
        {"stage-1": {"stage-2"}, "stage-2": {"stage-1"}},
    ],
)
def test_invalid_dependency_graph(graph):
    with pytest.raises(ValidationError):
        validate_acyclic_dependencies(graph)
