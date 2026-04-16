"""Unit tests for shared generated-mesh invariant checks."""

from __future__ import annotations

import numpy as np
import pytest
from humanoid_character_builder.generators.mesh_invariants import (
    MeshInvariantPolicy,
    validate_mesh_invariants,
)


class _FakeMesh:
    def __init__(
        self,
        *,
        vertices: np.ndarray,
        faces: np.ndarray,
        is_watertight: bool = True,
        is_self_intersecting: bool = False,
    ) -> None:
        self.vertices = vertices
        self.faces = faces
        self.is_watertight = is_watertight
        self.is_self_intersecting = is_self_intersecting


def test_valid_mesh_passes_default_policy() -> None:
    mesh = _FakeMesh(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]]),
    )

    validate_mesh_invariants(mesh, context="unit")


def test_self_intersection_is_rejected() -> None:
    mesh = _FakeMesh(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]]),
        is_self_intersecting=True,
    )

    with pytest.raises(ValueError, match="self-intersect"):
        validate_mesh_invariants(mesh, context="unit")


def test_manifold_policy_rejects_open_mesh() -> None:
    mesh = _FakeMesh(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]]),
        is_watertight=False,
    )

    with pytest.raises(ValueError, match="manifold"):
        validate_mesh_invariants(
            mesh,
            context="unit",
            policy=MeshInvariantPolicy(require_manifold=True),
        )
