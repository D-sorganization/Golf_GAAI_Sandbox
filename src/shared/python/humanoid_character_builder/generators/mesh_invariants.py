"""Mesh invariant checks shared by humanoid mesh generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class MeshInvariantPolicy:
    """Controls which generated mesh invariants are enforced."""

    require_manifold: bool = False
    require_no_self_intersections: bool = True


DEFAULT_SEGMENT_POLICY = MeshInvariantPolicy()


def validate_mesh_invariants(
    mesh: Any,
    *,
    context: str,
    policy: MeshInvariantPolicy = DEFAULT_SEGMENT_POLICY,
) -> None:
    """Validate mesh invariants before export.

    Preconditions:
        mesh exposes finite vertices and triangular faces when those
        attributes are available.

    Postconditions:
        Detectable manifold and self-intersection invariants are honored
        according to *policy*.
    """
    if mesh is None:
        raise ValueError(f"{context}: mesh must be provided")
    _validate_vertices(mesh, context)
    _validate_faces(mesh, context)
    _validate_manifold(mesh, context, policy)
    _validate_self_intersection(mesh, context, policy)


def _validate_vertices(mesh: Any, context: str) -> None:
    vertices = getattr(mesh, "vertices", None)
    if vertices is None:
        return
    vertices_arr = np.asarray(vertices)
    if vertices_arr.size == 0:
        raise ValueError(f"{context}: mesh has no vertices")
    if vertices_arr.ndim != 2 or vertices_arr.shape[1] != 3:
        raise ValueError(f"{context}: vertices must have shape (N, 3)")
    if not np.isfinite(vertices_arr).all():
        raise ValueError(f"{context}: vertices must be finite")


def _validate_faces(mesh: Any, context: str) -> None:
    faces = getattr(mesh, "faces", None)
    vertices = getattr(mesh, "vertices", None)
    if faces is None or vertices is None:
        return
    faces_arr = np.asarray(faces)
    if faces_arr.size == 0:
        raise ValueError(f"{context}: mesh has no faces")
    if faces_arr.ndim != 2 or faces_arr.shape[1] != 3:
        raise ValueError(f"{context}: faces must have shape (M, 3)")
    vertex_count = len(vertices)
    if faces_arr.min() < 0 or faces_arr.max() >= vertex_count:
        raise ValueError(f"{context}: face indices are outside vertex range")


def _validate_manifold(
    mesh: Any,
    context: str,
    policy: MeshInvariantPolicy,
) -> None:
    is_watertight = getattr(mesh, "is_watertight", None)
    if policy.require_manifold and is_watertight is False:
        raise ValueError(f"{context}: mesh must be manifold/watertight")


def _validate_self_intersection(
    mesh: Any,
    context: str,
    policy: MeshInvariantPolicy,
) -> None:
    if not policy.require_no_self_intersections:
        return
    intersects = getattr(mesh, "is_self_intersecting", None)
    if intersects is True:
        raise ValueError(f"{context}: mesh must not self-intersect")
