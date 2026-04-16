"""MakeHuman mesh parsing and export helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from humanoid_character_builder.generators.mesh_invariants import (
    validate_mesh_invariants,
)

logger = logging.getLogger(__name__)

MAKEHUMAN_DEFAULT_HEIGHT_M = 1.68
MAKEHUMAN_SEARCH_PATHS = (
    Path("/usr/share/makehuman"),
    Path.home() / "makehuman",
    Path.home() / ".makehuman",
)
MAKEHUMAN_SEGMENT_GROUPS: dict[str, str] = {
    "head": "head",
    "neck": "neck",
    "torso": "torso",
    "upper_torso": "torso",
    "lower_torso": "pelvis",
    "pelvis": "pelvis",
    "left_upper_arm": "left_upper_arm",
    "right_upper_arm": "right_upper_arm",
    "left_forearm": "left_forearm",
    "right_forearm": "right_forearm",
    "left_hand": "left_hand",
    "right_hand": "right_hand",
    "left_thigh": "left_thigh",
    "right_thigh": "right_thigh",
    "left_shin": "left_shin",
    "right_shin": "right_shin",
    "left_foot": "left_foot",
    "right_foot": "right_foot",
}


def prepare_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    """Create and return visual/collision output directories."""
    output_dir = Path(output_dir)
    visual_dir = output_dir / "visual"
    collision_dir = output_dir / "collision"
    visual_dir.mkdir(parents=True, exist_ok=True)
    collision_dir.mkdir(parents=True, exist_ok=True)
    return visual_dir, collision_dir


def script_outputs(tmp: Path) -> tuple[Path, Path]:
    """Return the expected temporary MakeHuman OBJ and group JSON paths."""
    return tmp / "body.obj", tmp / "groups.json"


def load_vertex_groups(groups_json: Path) -> dict[str, list[int]]:
    """Load MakeHuman vertex groups from JSON when available."""
    if not groups_json.exists():
        return {}
    with open(groups_json, encoding="utf-8") as fh:
        loaded = json.load(fh)
    return loaded if isinstance(loaded, dict) else {}


def segment_by_index_range(
    vertices: np.ndarray,
    faces: np.ndarray,
    indices: list[int],
) -> tuple[np.ndarray, np.ndarray] | None:
    """Extract a segment using the smallest contiguous vertex range."""
    if not indices:
        return None
    in_range = (faces >= min(indices)) & (faces <= max(indices))
    segment_faces_global = faces[in_range.all(axis=1)]
    if len(segment_faces_global) == 0:
        return None
    unique_vertices, inverse = np.unique(segment_faces_global, return_inverse=True)
    return vertices[unique_vertices], inverse.reshape(-1, 3)


def valid_segments() -> Any:
    """Return canonical humanoid segment definitions."""
    from humanoid_character_builder.core.segment_definitions import HUMANOID_SEGMENTS

    return HUMANOID_SEGMENTS


def export_submesh(
    mesh: Any,
    vertex_indices: list[int],
    segment_name: str,
    visual_dir: Path,
    collision_dir: Path,
) -> None:
    """Export a submesh selected by vertex indices."""
    try:
        face_mask = mesh.faces_sparse.rows[vertex_indices].indices
        submesh = mesh.submesh([face_mask], append=True)
        export_mesh_pair(submesh, segment_name, visual_dir, collision_dir)
    except (AttributeError, TypeError, ValueError) as exc:
        logger.warning("Failed to extract %s: %s", segment_name, exc)


def export_mesh_pair(
    mesh: Any,
    segment_name: str,
    visual_dir: Path,
    collision_dir: Path,
) -> None:
    """Validate and export visual and convex-hull collision meshes."""
    validate_mesh_invariants(mesh, context=f"MakeHuman {segment_name}")
    mesh.export(str(visual_dir / f"{segment_name}.stl"))
    mesh.convex_hull.export(str(collision_dir / f"{segment_name}.stl"))


def slice_mesh_at_z(mesh: Any, z_low: float) -> Any | None:
    """Slice a mesh by normalized z coordinate."""
    bounds = mesh.bounds
    height = bounds[1][2] - bounds[0][2]
    z_min = bounds[0][2] + z_low * height
    try:
        submesh = mesh.slice_plane([0, 0, z_min], [0, 0, 1])
    except (AttributeError, TypeError, ValueError) as exc:
        logger.warning("Failed to slice mesh at z=%s: %s", z_min, exc)
        return None
    return submesh if submesh and len(submesh.vertices) > 0 else None


def segment_z_ranges() -> dict[str, float]:
    """Return normalized z cut points for geometry-only segmentation."""
    return {
        "head": 0.90,
        "neck": 0.85,
        "torso": 0.55,
        "pelvis": 0.45,
        "left_thigh": 0.25,
        "right_thigh": 0.25,
        "left_shin": 0.08,
        "right_shin": 0.08,
        "left_foot": 0.0,
        "right_foot": 0.0,
    }


def parse_group_line(
    raw_line: str,
    groups: dict[str, list[int]],
    current_group: str,
    vertex_index: int,
) -> tuple[str, int]:
    """Update OBJ vertex-group parser state for one line."""
    line = raw_line.strip()
    if line.startswith("g "):
        group_name = line[2:].strip()
        groups.setdefault(group_name, [])
        return group_name, vertex_index
    if line.startswith("v "):
        groups.setdefault(current_group, []).append(vertex_index)
        return current_group, vertex_index + 1
    return current_group, vertex_index


def parse_obj_line(
    raw_line: str,
    vertices: list[list[float]],
    faces: list[list[int]],
) -> None:
    """Parse one OBJ vertex or face line into mutable collections."""
    line = raw_line.strip()
    if line.startswith("v "):
        parts = line.split()
        vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
    elif line.startswith("f "):
        append_obj_faces(line.split()[1:], faces)


def append_obj_faces(parts: list[str], faces: list[list[int]]) -> None:
    """Append one OBJ face, triangulating polygons by fan."""
    indices = [int(part.split("/")[0]) - 1 for part in parts]
    if len(indices) == 3:
        faces.append(indices)
        return
    for index in range(1, len(indices) - 1):
        faces.append([indices[0], indices[index], indices[index + 1]])


def arrays_from_obj_parts(
    vertices: list[list[float]],
    faces: list[list[int]],
) -> tuple[np.ndarray, np.ndarray]:
    """Convert parsed OBJ lists into shaped numpy arrays."""
    vertex_array = (
        np.array(vertices, dtype=np.float64) if vertices else np.zeros((0, 3))
    )
    face_array = (
        np.array(faces, dtype=np.int64) if faces else np.zeros((0, 3), dtype=np.int64)
    )
    return vertex_array, face_array


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a float to a closed interval."""
    return float(min(maximum, max(minimum, value)))
