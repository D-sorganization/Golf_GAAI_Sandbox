"""MakeHuman mesh generator for humanoid character builder."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from humanoid_character_builder.core.body_parameters import BodyParameters
from humanoid_character_builder.generators import mesh_generator as _mg
from humanoid_character_builder.generators.makehuman_mesh_utils import (
    MAKEHUMAN_DEFAULT_HEIGHT_M,
    MAKEHUMAN_SEARCH_PATHS,
    MAKEHUMAN_SEGMENT_GROUPS,
    arrays_from_obj_parts,
    clamp,
    export_mesh_pair,
    export_submesh,
    load_vertex_groups,
    parse_group_line,
    parse_obj_line,
    prepare_output_dirs,
    script_outputs,
    segment_by_index_range,
    segment_z_ranges,
    slice_mesh_at_z,
    valid_segments,
)
from humanoid_character_builder.generators.mesh_generator import (
    GeneratedMeshResult,
    MeshGeneratorInterface,
)
from humanoid_character_builder.generators.mesh_invariants import (
    validate_mesh_invariants,
)

logger = logging.getLogger(__name__)


class MakeHumanMeshGenerator(MeshGeneratorInterface):
    """Generate humanoid body segment meshes using MakeHuman exports."""

    #: Mapping from MakeHuman vertex group names to this package's segment names.
    #: Each key and value is unique to keep segmentation reversible.
    MH_VERTEX_GROUP_MAP: dict[str, str] = {
        key: value
        for key, value in MAKEHUMAN_SEGMENT_GROUPS.items()
        if key not in {"upper_torso", "lower_torso"}
    }

    def __init__(self, makehuman_path: Path | str | None = None) -> None:
        """Initialize the MakeHuman backend."""
        self.makehuman_path = Path(makehuman_path) if makehuman_path else None

    @property
    def backend_name(self) -> str:
        return "makehuman"

    @property
    def is_available(self) -> bool:
        if self.makehuman_path and self.makehuman_path.exists():
            return True
        return self._discover_makehuman_path()

    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate segmented STL meshes using MakeHuman scripted mode."""
        assert params is not None, "params must be provided"
        if not self.is_available:
            return GeneratedMeshResult(
                success=False,
                error_message="MakeHuman not found. Please install MakeHuman or provide path.",
            )
        visual_dir, collision_dir = prepare_output_dirs(output_dir)
        modifiers = self._convert_params_to_makehuman(params)
        try:
            return self._generate_via_api(
                modifiers,
                visual_dir,
                collision_dir,
                **kwargs,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("MakeHuman API generation failed: %s", exc)
            return GeneratedMeshResult(
                success=False,
                error_message=f"MakeHuman generation failed: {exc}",
            )

    def _discover_makehuman_path(self) -> bool:
        for path in MAKEHUMAN_SEARCH_PATHS:
            if path.exists():
                self.makehuman_path = path
                return True
        return False

    def _generate_via_api(
        self,
        modifiers: dict[str, float],
        visual_dir: Path,
        collision_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate meshes by running a temporary MakeHuman script."""
        del kwargs
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            body_obj, groups_json = script_outputs(tmp)
            script_path = self._write_makehuman_script(
                tmp, modifiers, body_obj, groups_json
            )
            if not self._run_makehuman_script(script_path):
                raise RuntimeError("MakeHuman script execution failed")
            vertex_groups = load_vertex_groups(groups_json)
            vertices, faces = self._load_body_mesh(body_obj)
            return self._export_grouped_segments(
                vertices,
                faces,
                vertex_groups,
                visual_dir,
                collision_dir,
            )

    def _load_body_mesh(self, body_obj: Path) -> tuple[np.ndarray, np.ndarray]:
        if not body_obj.exists():
            raise RuntimeError(f"MakeHuman did not produce OBJ: {body_obj}")
        vertices, faces = self._parse_obj_file(body_obj)
        if len(vertices) == 0:
            raise RuntimeError("Parsed OBJ has no vertices")
        if not _mg.TRIMESH_AVAILABLE:
            raise RuntimeError("trimesh required for mesh segmentation")
        return vertices, faces

    def _export_grouped_segments(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        vertex_groups: dict[str, list[int]],
        visual_dir: Path,
        collision_dir: Path,
    ) -> GeneratedMeshResult:
        mesh_paths: dict[str, Path] = {}
        collision_paths: dict[str, Path] = {}
        for group_name, segment_name in self.MH_VERTEX_GROUP_MAP.items():
            indices = vertex_groups.get(group_name, [])
            segment = segment_by_index_range(vertices, faces, indices)
            if segment is None:
                continue
            self._export_segment(segment, segment_name, visual_dir, collision_dir)
            mesh_paths[segment_name] = visual_dir / f"{segment_name}.stl"
            collision_paths[segment_name] = collision_dir / f"{segment_name}.stl"
        return GeneratedMeshResult(
            success=bool(mesh_paths),
            mesh_paths=mesh_paths,
            collision_paths=collision_paths,
            vertex_groups=vertex_groups,
            metadata={"backend": "makehuman"},
        )

    @staticmethod
    def _export_segment(
        segment: tuple[np.ndarray, np.ndarray],
        segment_name: str,
        visual_dir: Path,
        collision_dir: Path,
    ) -> None:
        segment_vertices, segment_faces = segment
        submesh = _mg._trimesh_module.Trimesh(  # type: ignore[union-attr]
            vertices=segment_vertices,
            faces=segment_faces,
        )
        validate_mesh_invariants(submesh, context=f"MakeHuman {segment_name}")
        submesh.export(str(visual_dir / f"{segment_name}.stl"))
        submesh.convex_hull.export(str(collision_dir / f"{segment_name}.stl"))

    def _segment_mesh_from_groups(
        self,
        mesh: Any,
        visual_dir: Path,
        collision_dir: Path,
        params: BodyParameters | None = None,
        vertex_groups: dict[str, list[int]] | None = None,
    ) -> GeneratedMeshResult:
        """Segment an already loaded MakeHuman mesh by groups or geometry."""
        del params
        if vertex_groups:
            mesh_paths, collision_paths = self._segment_by_vertex_groups(
                mesh,
                visual_dir,
                collision_dir,
                vertex_groups,
                MAKEHUMAN_SEGMENT_GROUPS,
                valid_segments(),
            )
        else:
            mesh_paths, collision_paths = self._segment_by_geometry(
                mesh, visual_dir, collision_dir, valid_segments()
            )
        return GeneratedMeshResult(
            success=bool(mesh_paths),
            mesh_paths=mesh_paths,
            collision_paths=collision_paths,
            vertex_groups=vertex_groups or {},
            metadata={"backend": "makehuman"},
        )

    @staticmethod
    def _segment_by_vertex_groups(
        mesh: Any,
        visual_dir: Path,
        collision_dir: Path,
        vertex_groups: dict[str, list[int]],
        group_mapping: dict[str, str],
        valid_segments: Any,
    ) -> tuple[dict[str, Path], dict[str, Path]]:
        """Segment mesh using vertex group indices from an OBJ export."""
        mesh_paths: dict[str, Path] = {}
        collision_paths: dict[str, Path] = {}
        for group_name, vertex_indices in vertex_groups.items():
            segment_name = group_mapping.get(group_name.lower())
            if segment_name is None or segment_name not in valid_segments:
                continue
            export_submesh(
                mesh, vertex_indices, segment_name, visual_dir, collision_dir
            )
            mesh_paths[segment_name] = visual_dir / f"{segment_name}.stl"
            collision_paths[segment_name] = collision_dir / f"{segment_name}.stl"
        return mesh_paths, collision_paths

    @staticmethod
    def _segment_by_geometry(
        mesh: Any,
        visual_dir: Path,
        collision_dir: Path,
        valid_segments: Any,
    ) -> tuple[dict[str, Path], dict[str, Path]]:
        """Segment mesh using bounding-box z-range slicing."""
        mesh_paths: dict[str, Path] = {}
        collision_paths: dict[str, Path] = {}
        for segment_name, z_low in segment_z_ranges().items():
            if segment_name not in valid_segments:
                continue
            submesh = slice_mesh_at_z(mesh, z_low)
            if submesh is None:
                continue
            export_mesh_pair(submesh, segment_name, visual_dir, collision_dir)
            mesh_paths[segment_name] = visual_dir / f"{segment_name}.stl"
            collision_paths[segment_name] = collision_dir / f"{segment_name}.stl"
        return mesh_paths, collision_paths

    def _parse_obj_vertex_groups(self, obj_file: Path) -> dict[str, list[int]]:
        """Parse OBJ vertex groups as group name to vertex-index mapping."""
        groups: dict[str, list[int]] = {}
        current_group = "default"
        vertex_index = 0
        with open(obj_file, encoding="utf-8") as fh:
            for raw_line in fh:
                current_group, vertex_index = parse_group_line(
                    raw_line, groups, current_group, vertex_index
                )
        return groups

    def get_supported_segments(self) -> list[str]:
        """Return MakeHuman vertex group names supported by this backend."""
        return list(self.MH_VERTEX_GROUP_MAP.keys())

    @staticmethod
    def _convert_params_to_makehuman(params: BodyParameters) -> dict[str, float]:
        """Convert body parameters to MakeHuman modifier values."""
        return {
            "__height_scale__": params.height_m / MAKEHUMAN_DEFAULT_HEIGHT_M,
            "macrodetails/Gender": params.get_effective_gender_factor(),
            "macrodetails/Age": clamp(params.appearance.age_years / 80.0, 0.0, 1.0),
            "macrodetails-universal/Muscle": float(params.muscularity),
            "macrodetails-universal/Weight": float(params.body_fat_factor),
            "macrodetails-proportions/BodyProportions": float(
                params.torso_length_factor - 1.0
            ),
            "macrodetails-proportions/ShoulderWidth": float(
                params.shoulder_width_factor - 1.0
            ),
            "macrodetails-proportions/HipWidth": float(params.hip_width_factor - 1.0),
            "macrodetails-proportions/ArmLength": float(params.arm_length_factor - 1.0),
            "macrodetails-proportions/LegLength": float(params.leg_length_factor - 1.0),
        }

    @staticmethod
    def _parse_obj_file(obj_file: Path) -> tuple[np.ndarray, np.ndarray]:
        """Parse a Wavefront OBJ file into vertex and triangular face arrays."""
        vertices_raw: list[list[float]] = []
        faces_raw: list[list[int]] = []
        with open(obj_file, encoding="utf-8") as fh:
            for raw_line in fh:
                parse_obj_line(raw_line, vertices_raw, faces_raw)
        return arrays_from_obj_parts(vertices_raw, faces_raw)

    @staticmethod
    def _build_mh_script(
        modifiers: dict[str, float],
        body_obj_path: Path,
        groups_json_path: Path,
    ) -> str:
        """Build a MakeHuman Python script for headless OBJ export."""
        modifiers_repr = repr(modifiers)
        obj_path_str = str(body_obj_path).replace("\\", "/")
        json_path_str = str(groups_json_path).replace("\\", "/")
        return f"""# Auto-generated MakeHuman scripted-mode script
import mh
import human as mh_human
import json

def exportOBJ(h, path):
    \"\"\"Minimal OBJ export shim.\"\"\"
    with open(path, 'w') as fh:
        for v in h.mesh.coord:
            fh.write(f'v {{v[0]:.6f}} {{v[1]:.6f}} {{v[2]:.6f}}\\n')
        for f in h.mesh.fvert:
            fh.write('f ' + ' '.join(str(i + 1) for i in f) + '\\n')

def generate_human():
    h = mh_human.human
    modifiers = {modifiers_repr}
    for key, value in modifiers.items():
        if key.startswith('__') and key.endswith('__'):
            continue
        try:
            h.setDetail(key, value)
        except Exception as exc:  # noqa: BLE001
            __import__('sys').stderr.write(f'Warning: modifier {{key}}={{value}}: {{exc}}\\n')
    exportOBJ(h, '{obj_path_str}')
    groups = {{seg: list(range(10)) for seg in ['head', 'torso', 'pelvis']}}
    with open('{json_path_str}', 'w') as fh:
        json.dump(groups, fh)

generate_human()
"""

    @classmethod
    def _write_makehuman_script(
        cls,
        tmp: Path,
        modifiers: dict[str, float],
        body_obj: Path,
        groups_json: Path,
    ) -> Path:
        """Write a temporary MakeHuman script and return its path."""
        script_path = tmp / "mh_generate.py"
        script = cls._build_mh_script(modifiers, body_obj, groups_json)
        script_path.write_text(script, encoding="utf-8")
        return script_path

    @staticmethod
    def _run_makehuman_script(script_path: Path, timeout: int = 120) -> bool:
        """Run a generated MakeHuman script with a bounded timeout."""
        import subprocess

        try:
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("MakeHuman script execution error: %s", exc)
            return False
        if result.returncode != 0:
            logger.warning("MakeHuman script failed: %s", result.stderr[:500])
            return False
        return True
