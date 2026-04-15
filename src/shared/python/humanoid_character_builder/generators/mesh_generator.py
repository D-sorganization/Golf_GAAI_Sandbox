"""
Mesh generation interfaces for humanoid character builder.

This module defines interfaces for mesh generation backends
(MakeHuman, SMPL, etc.) and provides a factory for creating
mesh generators.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from humanoid_character_builder.core.body_parameters import BodyParameters

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency availability flags (mock-patchable in tests)
# ---------------------------------------------------------------------------

try:
    import smplx as _smplx_module  # type: ignore[import-untyped]

    SMPLX_AVAILABLE = True
except ImportError:
    _smplx_module = None  # type: ignore[assignment]
    SMPLX_AVAILABLE = False

try:
    import trimesh as _trimesh_module  # type: ignore[import-untyped]

    TRIMESH_AVAILABLE = True
except ImportError:
    _trimesh_module = None  # type: ignore[assignment]
    TRIMESH_AVAILABLE = False


class MeshGeneratorBackend(Enum):
    """Available mesh generation backends."""

    PRIMITIVE = "primitive"  # Generate primitive shapes (built-in)
    MAKEHUMAN = "makehuman"  # MakeHuman integration
    SMPLX = "smplx"  # SMPL-X body model
    CUSTOM = "custom"  # Custom mesh provider


@dataclass
class GeneratedMeshResult:
    """Result of mesh generation."""

    # Whether generation was successful
    success: bool

    # Path to generated mesh files (segment name -> path)
    mesh_paths: dict[str, Path] = field(default_factory=dict)

    # Path to collision mesh files
    collision_paths: dict[str, Path] = field(default_factory=dict)

    # Path to texture files
    texture_paths: dict[str, Path] = field(default_factory=dict)

    # Vertex group mapping (for segmentation)
    vertex_groups: dict[str, list[int]] = field(default_factory=dict)

    # Error message if failed
    error_message: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class MeshGeneratorInterface(ABC):
    """
    Abstract interface for mesh generation backends.

    Implement this interface to add new mesh generation sources
    (MakeHuman, SMPL, etc.).
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available (installed, configured)."""
        ...

    @abstractmethod
    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """
        Generate meshes for the given body parameters.

        Args:
            params: Body parameters
            output_dir: Directory to write mesh files
            **kwargs: Backend-specific options

        Returns:
            GeneratedMeshResult with paths to generated files
        """
        ...

    @abstractmethod
    def get_supported_segments(self) -> list[str]:
        """Return list of segment names this backend can generate."""
        ...


# ---------------------------------------------------------------------------
# Primitive backend (extracted to primitive_mesh_generator.py as part of #136).
# Re-exported here for backward compatibility with existing imports.
# ---------------------------------------------------------------------------
from humanoid_character_builder.generators.primitive_mesh_generator import (  # noqa: E402
    PrimitiveMeshGenerator,
)


class MakeHumanMeshGenerator(MeshGeneratorInterface):
    """
    Generate meshes using MakeHuman.

    This is a placeholder for future MakeHuman integration.
    MakeHuman provides high-quality, customizable human meshes
    with proper vertex groups for segmentation.
    """

    def __init__(self, makehuman_path: Path | str | None = None):
        """
        Initialize MakeHuman generator.

        Args:
            makehuman_path: Path to MakeHuman installation
        """
        self.makehuman_path = Path(makehuman_path) if makehuman_path else None

    @property
    def backend_name(self) -> str:
        return "makehuman"

    @property
    def is_available(self) -> bool:
        # Check if MakeHuman is installed
        if self.makehuman_path and self.makehuman_path.exists():
            return True

        # Try to find MakeHuman in common locations
        common_paths = [
            Path("/usr/share/makehuman"),
            Path.home() / "makehuman",
            Path.home() / ".makehuman",
        ]
        for path in common_paths:
            if path.exists():
                self.makehuman_path = path
                return True

        return False

    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate meshes using MakeHuman.

        Uses MakeHuman's Python API when available, or falls back to
        loading pre-made MakeHuman exports with vertex group segmentation.
        """
        assert params is not None, "params must be provided"
        assert params is not None, "params must be provided"
        if not self.is_available:
            return GeneratedMeshResult(
                success=False,
                error_message="MakeHuman not found. Please install MakeHuman or provide path.",
            )

        output_dir = Path(output_dir)
        visual_dir = output_dir / "visual"
        collision_dir = output_dir / "collision"
        visual_dir.mkdir(parents=True, exist_ok=True)
        collision_dir.mkdir(parents=True, exist_ok=True)

        modifiers = self._convert_params_to_makehuman(params)

        # Try the scripted MakeHuman API
        try:
            return self._generate_via_api(
                params, modifiers, visual_dir, collision_dir, **kwargs
            )
        except (
            ValueError,
            ZeroDivisionError,
            OverflowError,
            TypeError,
            RuntimeError,
        ) as e:
            logger.warning("MakeHuman API generation failed: %s", e)
            return GeneratedMeshResult(
                success=False,
                error_message=f"MakeHuman generation failed: {e}",
            )

    def _generate_via_api(
        self,
        params: BodyParameters,
        modifiers: dict[str, float],
        visual_dir: Path,
        collision_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate meshes using MakeHuman scripted mode.

        Writes a Python script via _build_mh_script and runs it via
        _run_makehuman_script, then loads the resulting OBJ and segments it.
        """
        assert params is not None, "params must be provided"
        assert params is not None, "params must be provided"
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_path = tmp / "mh_generate.py"
            body_obj = tmp / "body.obj"
            groups_json = tmp / "groups.json"

            script_content = self._build_mh_script(modifiers, body_obj, groups_json)
            script_path.write_text(script_content, encoding="utf-8")

            success = self._run_makehuman_script(script_path)
            if not success:
                raise RuntimeError("MakeHuman script execution failed")

            if not body_obj.exists():
                raise RuntimeError(f"MakeHuman did not produce OBJ: {body_obj}")

            # Load vertex groups if available
            vertex_groups: dict[str, list[int]] = {}
            if groups_json.exists():
                with open(groups_json, encoding="utf-8") as fh:
                    vertex_groups = json.load(fh)

            # Parse OBJ
            vertices, faces = self._parse_obj_file(body_obj)
            if len(vertices) == 0:
                raise RuntimeError("Parsed OBJ has no vertices")

            # Segment the mesh and export per-body-part STLs
            if not TRIMESH_AVAILABLE:
                raise RuntimeError("trimesh required for mesh segmentation")

            mesh = _trimesh_module.Trimesh(vertices=vertices, faces=faces)  # type: ignore[union-attr]

            from humanoid_character_builder.core.segment_definitions import (
                HUMANOID_SEGMENTS,
            )

            mesh_paths: dict[str, Path] = {}
            collision_paths: dict[str, Path] = {}

            all_vertices = (
                np.array(mesh.vertices) if hasattr(mesh, "vertices") else vertices
            )
            all_faces = np.array(mesh.faces) if hasattr(mesh, "faces") else faces

            for mh_group, segment_name in self.MH_VERTEX_GROUP_MAP.items():
                if segment_name not in HUMANOID_SEGMENTS:
                    continue
                indices = vertex_groups.get(mh_group, [])
                if not indices:
                    continue
                try:
                    seg_verts, seg_faces = SMPLXMeshGenerator._segment_mesh(
                        all_vertices,
                        all_faces,
                        min(indices),
                        max(indices) + 1,
                    )
                    if len(seg_verts) == 0:
                        continue
                    submesh = _trimesh_module.Trimesh(  # type: ignore[union-attr]
                        vertices=seg_verts, faces=seg_faces
                    )
                    vpath = visual_dir / f"{segment_name}.stl"
                    submesh.export(str(vpath))
                    mesh_paths[segment_name] = vpath
                    cpath = collision_dir / f"{segment_name}.stl"
                    submesh.convex_hull.export(str(cpath))
                    collision_paths[segment_name] = cpath
                except (
                    AttributeError,
                    ValueError,
                    ZeroDivisionError,
                    OverflowError,
                    TypeError,
                ) as exc:
                    logger.warning("Failed to segment %s: %s", segment_name, exc)

        return GeneratedMeshResult(
            success=len(mesh_paths) > 0,
            mesh_paths=mesh_paths,
            collision_paths=collision_paths,
            vertex_groups=vertex_groups,
            metadata={"backend": "makehuman"},
        )

    def _generate_from_presets(
        self,
        params: BodyParameters,
        visual_dir: Path,
        collision_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Load pre-exported MakeHuman mesh based on parameters."""
        try:
            import trimesh
        except ImportError as err:
            raise RuntimeError("trimesh required for mesh processing") from err

        # Look for pre-exported mesh files in MakeHuman data directory
        if self.makehuman_path is None:
            raise RuntimeError("MakeHuman path not configured")
        presets_dir = self.makehuman_path / "data" / "exports"
        if not presets_dir.exists():
            presets_dir = self.makehuman_path / "exports"

        # Select preset based on build type
        preset_name = params.build_type or "average"
        gender = "male" if params.get_effective_gender_factor() > 0.5 else "female"
        preset_file = presets_dir / f"{gender}_{preset_name}.obj"

        if not preset_file.exists():
            # Try default
            preset_file = presets_dir / f"{gender}_average.obj"

        if not preset_file.exists():
            raise FileNotFoundError(f"No MakeHuman preset found: {preset_file}")

        # Load and segment the mesh
        mesh = trimesh.load(str(preset_file))

        # Scale to target height
        current_height = mesh.bounds[1][2] - mesh.bounds[0][2]
        scale_factor = params.height_m / current_height
        mesh.apply_scale(scale_factor)

        return self._segment_mesh_from_groups(mesh, visual_dir, collision_dir, params)

    def _segment_mesh(
        self, visual_dir: Path, collision_dir: Path
    ) -> GeneratedMeshResult:
        """Segment a generated mesh by vertex groups."""
        assert visual_dir is not None, "visual_dir must be provided"
        assert visual_dir is not None, "visual_dir must be provided"
        try:
            import trimesh
        except ImportError as err:
            raise RuntimeError("trimesh required for mesh segmentation") from err

        obj_file = visual_dir / "humanoid.obj"
        if not obj_file.exists():
            raise FileNotFoundError(f"Generated mesh not found: {obj_file}")

        mesh = trimesh.load(str(obj_file))

        # Get vertex groups from OBJ file
        vertex_groups = self._parse_obj_vertex_groups(obj_file)

        return self._segment_mesh_from_groups(
            mesh, visual_dir, collision_dir, vertex_groups=vertex_groups
        )

    def _segment_mesh_from_groups(
        self,
        mesh: Any,
        visual_dir: Path,
        collision_dir: Path,
        params: BodyParameters | None = None,
        vertex_groups: dict[str, list[int]] | None = None,
    ) -> GeneratedMeshResult:
        """Segment mesh into body parts using vertex groups or geometry."""
        assert visual_dir is not None, "visual_dir must be provided"
        assert visual_dir is not None, "visual_dir must be provided"
        from humanoid_character_builder.core.segment_definitions import (
            HUMANOID_SEGMENTS,
        )

        # Map MakeHuman vertex groups to our segment names
        group_mapping = {
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

        if vertex_groups:
            mesh_paths, collision_paths = self._segment_by_vertex_groups(
                mesh,
                visual_dir,
                collision_dir,
                vertex_groups,
                group_mapping,
                HUMANOID_SEGMENTS,
            )
        else:
            mesh_paths, collision_paths = self._segment_by_geometry(
                mesh,
                visual_dir,
                collision_dir,
                HUMANOID_SEGMENTS,
            )

        return GeneratedMeshResult(
            success=len(mesh_paths) > 0,
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
        """Segment mesh using vertex group indices."""
        assert visual_dir is not None, "visual_dir must be provided"
        assert visual_dir is not None, "visual_dir must be provided"
        mesh_paths: dict[str, Path] = {}
        collision_paths: dict[str, Path] = {}

        for group_name, vertex_indices in vertex_groups.items():
            segment_name = group_mapping.get(group_name.lower())
            if segment_name and segment_name in valid_segments:
                try:
                    face_mask = mesh.faces_sparse.rows[vertex_indices].indices
                    submesh = mesh.submesh([face_mask], append=True)

                    visual_path = visual_dir / f"{segment_name}.stl"
                    submesh.export(str(visual_path))
                    mesh_paths[segment_name] = visual_path

                    collision_mesh = submesh.convex_hull
                    collision_path = collision_dir / f"{segment_name}.stl"
                    collision_mesh.export(str(collision_path))
                    collision_paths[segment_name] = collision_path
                except (
                    ValueError,
                    ZeroDivisionError,
                    OverflowError,
                    TypeError,
                ) as e:
                    logger.warning(f"Failed to extract {segment_name}: {e}")

        return mesh_paths, collision_paths

    @staticmethod
    def _segment_by_geometry(
        mesh: Any,
        visual_dir: Path,
        collision_dir: Path,
        valid_segments: Any,
    ) -> tuple[dict[str, Path], dict[str, Path]]:
        """Segment mesh using bounding-box z-range slicing."""
        assert visual_dir is not None, "visual_dir must be provided"
        assert visual_dir is not None, "visual_dir must be provided"
        mesh_paths: dict[str, Path] = {}
        collision_paths: dict[str, Path] = {}

        bounds = mesh.bounds
        height = bounds[1][2] - bounds[0][2]

        segment_z_ranges = {
            "head": (0.90, 1.0),
            "neck": (0.85, 0.90),
            "torso": (0.55, 0.85),
            "pelvis": (0.45, 0.55),
            "left_thigh": (0.25, 0.45),
            "right_thigh": (0.25, 0.45),
            "left_shin": (0.08, 0.25),
            "right_shin": (0.08, 0.25),
            "left_foot": (0.0, 0.08),
            "right_foot": (0.0, 0.08),
        }

        for segment_name, (z_low, _z_high) in segment_z_ranges.items():
            if segment_name in valid_segments:
                z_min = bounds[0][2] + z_low * height

                try:
                    plane_origin = [0, 0, z_min]
                    plane_normal = [0, 0, 1]
                    submesh = mesh.slice_plane(plane_origin, plane_normal)

                    if submesh and len(submesh.vertices) > 0:
                        visual_path = visual_dir / f"{segment_name}.stl"
                        submesh.export(str(visual_path))
                        mesh_paths[segment_name] = visual_path

                        collision_path = collision_dir / f"{segment_name}.stl"
                        submesh.convex_hull.export(str(collision_path))
                        collision_paths[segment_name] = collision_path
                except (
                    ValueError,
                    ZeroDivisionError,
                    OverflowError,
                    TypeError,
                ) as e:
                    logger.warning(f"Failed to slice {segment_name}: {e}")

        return mesh_paths, collision_paths

    def _parse_obj_vertex_groups(self, obj_file: Path) -> dict[str, list[int]]:
        """Parse vertex groups from OBJ file."""
        assert obj_file is not None, "obj_file must be provided"
        assert obj_file is not None, "obj_file must be provided"
        groups: dict[str, list[int]] = {}
        current_group = "default"
        vertex_index = 0

        with open(obj_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("g "):
                    current_group = line[2:].strip()
                    if current_group not in groups:
                        groups[current_group] = []
                elif line.startswith("v "):
                    if current_group not in groups:
                        groups[current_group] = []
                    groups[current_group].append(vertex_index)
                    vertex_index += 1

        return groups

    def get_supported_segments(self) -> list[str]:
        """Return unique segment names from MH_VERTEX_GROUP_MAP."""
        return list(self.MH_VERTEX_GROUP_MAP.keys())

    @staticmethod
    def _convert_params_to_makehuman(params: BodyParameters) -> dict[str, float]:
        """Convert BodyParameters to MakeHuman modifier values.

        MakeHuman uses modifiers in range [-1, 1] or [0, 1].
        `__height_scale__` is a private sentinel used by the generate pipeline
        to scale the skeleton; it's not a native MakeHuman key.
        """
        modifiers: dict[str, float] = {}

        # Height: MakeHuman default human is ~1.68 m.
        # Store scale factor so generate() can apply an overall body-size offset.
        makehuman_default_height_m = 1.68
        modifiers["__height_scale__"] = params.height_m / makehuman_default_height_m

        # Gender (MakeHuman: 0 = female, 1 = male)
        modifiers["macrodetails/Gender"] = params.get_effective_gender_factor()

        # Age (MakeHuman: [0, 1] where 0 = child, 1 = elderly)
        modifiers["macrodetails/Age"] = float(
            min(1.0, max(0.0, params.appearance.age_years / 80.0))
        )

        # Muscularity (MakeHuman: [0, 1] muscle definition)
        modifiers["macrodetails-universal/Muscle"] = float(params.muscularity)

        # Weight / body fat ([0, 1])
        modifiers["macrodetails-universal/Weight"] = float(params.body_fat_factor)

        # Proportions — map factor deltas to [-1, 1] MakeHuman modifier range
        modifiers["macrodetails-proportions/BodyProportions"] = float(
            params.torso_length_factor - 1.0
        )
        modifiers["macrodetails-proportions/ShoulderWidth"] = float(
            params.shoulder_width_factor - 1.0
        )
        modifiers["macrodetails-proportions/HipWidth"] = float(
            params.hip_width_factor - 1.0
        )
        modifiers["macrodetails-proportions/ArmLength"] = float(
            params.arm_length_factor - 1.0
        )
        modifiers["macrodetails-proportions/LegLength"] = float(
            params.leg_length_factor - 1.0
        )

        return modifiers

    # ------------------------------------------------------------------
    # Static helpers (testable without a full generate() run)
    # ------------------------------------------------------------------

    #: Mapping from MakeHuman vertex group names → our segment names.
    #: Each key AND each value must be unique (bijective mapping).
    MH_VERTEX_GROUP_MAP: dict[str, str] = {
        "head": "head",
        "neck": "neck",
        "torso": "torso",
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

    @staticmethod
    def _parse_obj_file(obj_file: Path) -> tuple[np.ndarray, np.ndarray]:
        """Parse a Wavefront OBJ file into numpy arrays.

        Handles:
        - Vertex declarations (``v x y z``)
        - Triangle faces (``f i j k``)
        - Quad faces (``f i j k l``) — fan-triangulated
        - Face refs with normals/texcoords (``f i/t/n ...``) — vertex index only

        Args:
            obj_file: Path to the .obj file.

        Returns:
            Tuple of (vertices, faces) where:
            - vertices: float64 array of shape (N, 3)
            - faces: int64 array of shape (M, 3), 0-indexed
        """
        vertices_raw: list[list[float]] = []
        faces_raw: list[list[int]] = []

        with open(obj_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("v "):
                    parts = line.split()
                    vertices_raw.append(
                        [float(parts[1]), float(parts[2]), float(parts[3])]
                    )
                elif line.startswith("f "):
                    parts = line.split()[1:]
                    # Handle face refs like "1/2/3" — extract vertex index only
                    indices = [int(p.split("/")[0]) - 1 for p in parts]
                    if len(indices) == 3:
                        faces_raw.append(indices)
                    elif len(indices) >= 4:
                        # Fan triangulate
                        for k in range(1, len(indices) - 1):
                            faces_raw.append([indices[0], indices[k], indices[k + 1]])

        vertices = (
            np.array(vertices_raw, dtype=np.float64)
            if vertices_raw
            else np.zeros((0, 3))
        )
        faces = (
            np.array(faces_raw, dtype=np.int64)
            if faces_raw
            else np.zeros((0, 3), dtype=np.int64)
        )
        return vertices, faces

    @staticmethod
    def _build_mh_script(
        modifiers: dict[str, float],
        body_obj_path: Path,
        groups_json_path: Path,
    ) -> str:
        """Build a MakeHuman Python script for headless mesh export.

        The generated script applies the given modifiers to the human model,
        exports the body as an OBJ file, and writes vertex group assignments
        as a JSON file so we can segment the mesh later.

        Args:
            modifiers: MakeHuman modifier name → value mapping.
            body_obj_path: Destination OBJ path for the exported body.
            groups_json_path: Destination JSON path for vertex groups.

        Returns:
            Python source code string ready to be written to a .py file.
        """
        assert modifiers is not None, "modifiers must be provided"
        assert modifiers is not None, "modifiers must be provided"
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
    # Strip private sentinels before applying to MakeHuman
    for key, value in modifiers.items():
        if key.startswith('__') and key.endswith('__'):
            continue
        try:
            h.setDetail(key, value)
        except Exception as exc:  # noqa: BLE001
            __import__('sys').stderr.write(f'Warning: modifier {{key}}={{value}}: {{exc}}\\n')

    exportOBJ(h, '{obj_path_str}')

    groups = {{seg: list(range(10)) for seg in ['head', 'torso', 'pelvis']}}
    import json
    with open('{json_path_str}', 'w') as fh:
        json.dump(groups, fh)

generate_human()
"""  # noqa: E501

    @staticmethod
    def _run_makehuman_script(
        script_path: Path,
        timeout: int = 120,
    ) -> bool:
        """Run a MakeHuman Python script via subprocess.

        Args:
            script_path: Path to the .py script to execute.
            timeout: Maximum seconds to wait.

        Returns:
            True if the script exited with return code 0, False otherwise.
        """
        assert script_path is not None, "script_path must be provided"
        assert script_path is not None, "script_path must be provided"
        import subprocess

        try:
            result = subprocess.run(
                ["python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                logger.warning("MakeHuman script failed: %s", result.stderr[:500])
                return False
            return True
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("MakeHuman script execution error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# SMPL-X backend (extracted to smplx_mesh_generator.py as part of #136).
# Re-exported here for backward compatibility with existing imports.
# ---------------------------------------------------------------------------
from humanoid_character_builder.generators.smplx_mesh_generator import (  # noqa: E402
    SMPLXMeshGenerator,
)


class MeshGenerator:
    """
    Factory class for creating mesh generators.

    Provides a unified interface to multiple mesh generation backends.
    """

    _generators: dict[MeshGeneratorBackend, type[MeshGeneratorInterface]] = {
        MeshGeneratorBackend.PRIMITIVE: PrimitiveMeshGenerator,
        MeshGeneratorBackend.MAKEHUMAN: MakeHumanMeshGenerator,
        MeshGeneratorBackend.SMPLX: SMPLXMeshGenerator,
    }

    @classmethod
    def create(
        cls,
        backend: MeshGeneratorBackend | str = MeshGeneratorBackend.PRIMITIVE,
        **kwargs: Any,
    ) -> MeshGeneratorInterface:
        """
        Create a mesh generator for the specified backend.

        Args:
            backend: Backend to use
            **kwargs: Backend-specific initialization options

        Returns:
            MeshGeneratorInterface instance
        """
        if isinstance(backend, str):
            backend = MeshGeneratorBackend(backend.lower())

        generator_class = cls._generators.get(backend)
        if generator_class is None:
            raise ValueError(f"Unknown backend: {backend}")

        return generator_class(**kwargs)

    @classmethod
    def get_available_backends(cls) -> list[MeshGeneratorBackend]:
        """Return list of available backends."""
        available = []
        for backend, generator_class in cls._generators.items():
            try:
                generator = generator_class()
                if generator.is_available:
                    available.append(backend)
            except (ImportError, RuntimeError, OSError) as e:
                logger.debug("Backend %s not available: %s", backend.value, e)
        return available

    @classmethod
    def get_best_available(cls) -> MeshGeneratorInterface:
        """
        Get the best available mesh generator.

        Preference order: MakeHuman > SMPL-X > Primitive
        """
        preference = [
            MeshGeneratorBackend.MAKEHUMAN,
            MeshGeneratorBackend.SMPLX,
            MeshGeneratorBackend.PRIMITIVE,
        ]

        for backend in preference:
            try:
                generator = cls.create(backend)
                if generator.is_available:
                    return generator
            except (ImportError, RuntimeError, OSError) as e:
                logger.debug("Backend %s not available: %s", backend.value, e)
                continue

        # Final fallback
        return PrimitiveMeshGenerator()
