"""
Unit tests for the extracted PrimitiveMeshGenerator.

See issue #136 — decompose ``mesh_generator.py``.  These tests cover the
happy path plus a few edge cases of the primitive backend after the
extraction into ``primitive_mesh_generator.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from humanoid_character_builder.core.body_parameters import BodyParameters

# Importing via both paths verifies the backward-compat re-export still works.
from humanoid_character_builder.generators.mesh_generator import (
    PrimitiveMeshGenerator as ReexportedPrimitive,
)
from humanoid_character_builder.generators.primitive_mesh_generator import (
    PrimitiveMeshGenerator,
)


def _default_params(**overrides: Any) -> BodyParameters:
    kwargs: dict[str, Any] = {"height_m": 1.80, "mass_kg": 80.0}
    kwargs.update(overrides)
    return BodyParameters(**kwargs)


class TestPrimitiveMeshGeneratorContract:
    """Static properties of the backend that do not require trimesh."""

    def test_backend_name_is_primitive(self) -> None:
        gen = PrimitiveMeshGenerator()
        assert gen.backend_name == "primitive"

    def test_reexport_is_same_class(self) -> None:
        # Backward-compat re-export from mesh_generator must resolve to the
        # extracted class (preserves isinstance checks in downstream code).
        assert ReexportedPrimitive is PrimitiveMeshGenerator

    def test_get_supported_segments_nonempty(self) -> None:
        segments = PrimitiveMeshGenerator().get_supported_segments()
        assert isinstance(segments, list)
        assert len(segments) > 0
        assert all(isinstance(s, str) for s in segments)


class TestPrimitiveMeshGeneratorGenerate:
    """Exercise the generate() path with trimesh mocked."""

    def test_generate_returns_failure_when_trimesh_unavailable(
        self, tmp_path: Path
    ) -> None:
        gen = PrimitiveMeshGenerator()
        # Force the availability check to report False without touching sys.modules
        with patch.object(
            PrimitiveMeshGenerator, "is_available", property(lambda self: False)
        ):
            result = gen.generate(_default_params(), tmp_path)
        assert result.success is False
        assert result.error_message is not None
        assert "trimesh" in result.error_message

    def test_generate_happy_path_with_mocked_trimesh(self, tmp_path: Path) -> None:
        gen = PrimitiveMeshGenerator()

        fake_mesh = MagicMock()
        fake_mesh.export = MagicMock()
        fake_mesh.convex_hull = MagicMock()
        fake_mesh.convex_hull.export = MagicMock()

        fake_trimesh = MagicMock()
        fake_trimesh.creation.icosphere.return_value = fake_mesh
        fake_trimesh.creation.cylinder.return_value = fake_mesh
        fake_trimesh.creation.capsule.return_value = fake_mesh
        fake_trimesh.creation.box.return_value = fake_mesh

        with (
            patch.dict("sys.modules", {"trimesh": fake_trimesh}),
            patch.object(
                PrimitiveMeshGenerator,
                "is_available",
                property(lambda self: True),
            ),
        ):
            result = gen.generate(_default_params(), tmp_path)

        assert result.success is True
        assert result.metadata["backend"] == "primitive"
        assert len(result.mesh_paths) > 0
        assert len(result.collision_paths) == len(result.mesh_paths)
        # Output directories should have been created
        assert (tmp_path / "visual").is_dir()
        assert (tmp_path / "collision").is_dir()
        # Every reported path should live under the expected dir and be .stl
        for seg, path in result.mesh_paths.items():
            assert path.parent == tmp_path / "visual"
            assert path.suffix == ".stl"
            assert path.name.startswith(seg)

    def test_generate_rejects_none_params(self, tmp_path: Path) -> None:
        gen = PrimitiveMeshGenerator()
        with pytest.raises(AssertionError):
            gen.generate(None, tmp_path)  # type: ignore[arg-type]
