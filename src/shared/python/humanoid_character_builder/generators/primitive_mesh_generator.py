"""
Primitive mesh generator for humanoid character builder.

Extracted from ``mesh_generator.py`` as part of issue #136.  This module
contains the :class:`PrimitiveMeshGenerator` backend, which produces
simple geometric primitives (spheres, cylinders, capsules, boxes) for
each humanoid body segment and is the zero-dependency fallback backend.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from humanoid_character_builder.core.body_parameters import BodyParameters
from humanoid_character_builder.generators.mesh_generator import (
    GeneratedMeshResult,
    MeshGeneratorInterface,
)

logger = logging.getLogger(__name__)


class PrimitiveMeshGenerator(MeshGeneratorInterface):
    """
    Generate primitive shape meshes (built-in, no external dependencies).

    This is the fallback generator that creates simple geometric shapes
    for each body segment.
    """

    @property
    def backend_name(self) -> str:
        return "primitive"

    @property
    def is_available(self) -> bool:
        # Check if trimesh is available for mesh creation
        try:
            import trimesh  # noqa: F401

            return True
        except ImportError:
            return False

    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate primitive meshes for body segments."""
        assert params is not None, "params must be provided"
        if not self.is_available:
            return GeneratedMeshResult(
                success=False,
                error_message="trimesh not available for primitive mesh generation",
            )

        visual_dir, collision_dir = self._prepare_output_dirs(output_dir)
        mesh_paths = {}
        collision_paths = {}
        dimensions = self._estimate_dimensions(params)

        from humanoid_character_builder.core.segment_definitions import (
            HUMANOID_SEGMENTS,
        )

        for segment_name, segment_def in HUMANOID_SEGMENTS.items():
            mesh_pair = self._generate_segment_mesh(
                segment_name,
                segment_def.visual_geometry.geometry_type,
                dimensions,
                visual_dir,
                collision_dir,
            )
            if mesh_pair is None:
                continue
            mesh_paths[segment_name], collision_paths[segment_name] = mesh_pair

        return GeneratedMeshResult(
            success=len(mesh_paths) > 0,
            mesh_paths=mesh_paths,
            collision_paths=collision_paths,
            metadata={"backend": "primitive"},
        )

    @staticmethod
    def _prepare_output_dirs(output_dir: Path) -> tuple[Path, Path]:
        output_dir = Path(output_dir)
        visual_dir = output_dir / "visual"
        collision_dir = output_dir / "collision"
        visual_dir.mkdir(parents=True, exist_ok=True)
        collision_dir.mkdir(parents=True, exist_ok=True)
        return visual_dir, collision_dir

    @staticmethod
    def _estimate_dimensions(params: BodyParameters) -> dict[str, dict[str, float]]:
        from humanoid_character_builder.core.anthropometry import (
            estimate_segment_dimensions,
        )

        gender_factor = params.get_effective_gender_factor()
        return estimate_segment_dimensions(params.height_m, gender_factor)

    def _generate_segment_mesh(
        self,
        segment_name: str,
        geom_type: Any,
        dimensions: dict[str, dict[str, float]],
        visual_dir: Path,
        collision_dir: Path,
    ) -> tuple[Path, Path] | None:
        try:
            dims = dimensions.get(
                segment_name, {"length": 0.1, "width": 0.05, "depth": 0.05}
            )
            mesh = self._create_mesh(geom_type, dims)
            visual_path = visual_dir / f"{segment_name}.stl"
            mesh.export(str(visual_path))
            collision_path = collision_dir / f"{segment_name}.stl"
            mesh.convex_hull.export(str(collision_path))
            return visual_path, collision_path
        except (ValueError, ZeroDivisionError, OverflowError, TypeError) as e:
            logger.warning(f"Failed to generate mesh for {segment_name}: {e}")
            return None

    @staticmethod
    def _create_mesh(geom_type: Any, dims: dict[str, float]) -> Any:
        import trimesh
        from humanoid_character_builder.core.segment_definitions import GeometryType

        length = dims["length"]
        width = dims["width"]
        depth = dims["depth"]

        if geom_type == GeometryType.SPHERE:
            return trimesh.creation.icosphere(radius=length / 2, subdivisions=2)
        if geom_type == GeometryType.CYLINDER:
            radius = (width + depth) / 4
            return trimesh.creation.cylinder(radius=radius, height=length, sections=16)
        if geom_type == GeometryType.CAPSULE:
            radius = (width + depth) / 4
            cyl_height = max(0.01, length - 2 * radius)
            return trimesh.creation.capsule(
                radius=radius, height=cyl_height, count=[8, 8]
            )
        return trimesh.creation.box(extents=(width, depth, length))

    def get_supported_segments(self) -> list[str]:
        from humanoid_character_builder.core.segment_definitions import (
            HUMANOID_SEGMENTS,
        )

        return list(HUMANOID_SEGMENTS.keys())
