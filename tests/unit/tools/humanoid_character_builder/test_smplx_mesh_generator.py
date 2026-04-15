"""
Unit tests for the extracted SMPLXMeshGenerator.

See issue #136 - decompose ``mesh_generator.py``.  These tests focus on
behaviour that is unique to this extraction (backend name / re-export
identity / availability gating / parameter-validation guards) plus a
mocked happy path.  The broader behavioural coverage for this backend
lives in ``test_mesh_generators.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from humanoid_character_builder.core.body_parameters import BodyParameters

# Importing via both paths verifies the backward-compat re-export still works.
from humanoid_character_builder.generators.mesh_generator import (
    SMPLXMeshGenerator as ReexportedSMPLX,
)
from humanoid_character_builder.generators.smplx_mesh_generator import (
    SMPLXMeshGenerator,
)


def _default_params(**overrides: Any) -> BodyParameters:
    kwargs: dict[str, Any] = {"height_m": 1.80, "mass_kg": 80.0}
    kwargs.update(overrides)
    return BodyParameters(**kwargs)


class TestSMPLXMeshGeneratorContract:
    """Static properties of the backend that do not require smplx or trimesh."""

    def test_backend_name_is_smplx(self) -> None:
        gen = SMPLXMeshGenerator()
        assert gen.backend_name == "smplx"

    def test_reexport_is_same_class(self) -> None:
        # Backward-compat re-export from mesh_generator must resolve to the
        # extracted class (preserves isinstance checks in downstream code).
        assert ReexportedSMPLX is SMPLXMeshGenerator

    def test_get_supported_segments_matches_vertex_ranges(self) -> None:
        segments = SMPLXMeshGenerator().get_supported_segments()
        assert isinstance(segments, list)
        assert len(segments) == len(SMPLXMeshGenerator.SMPLX_SEGMENT_VERTEX_RANGES)
        # A representative sample of expected segments.
        for name in ("head", "torso", "left_hand", "right_foot"):
            assert name in segments


class TestSMPLXMeshGeneratorAvailability:
    """is_available should gate on smplx package presence and model_dir existence."""

    def test_unavailable_when_smplx_missing(self) -> None:
        gen = SMPLXMeshGenerator(model_dir="/tmp")
        with patch(
            "humanoid_character_builder.generators.mesh_generator.SMPLX_AVAILABLE",
            False,
        ):
            assert gen.is_available is False

    def test_unavailable_when_model_dir_missing(self) -> None:
        # A nonexistent explicit model_dir should make is_available False even
        # when smplx itself is importable.
        gen = SMPLXMeshGenerator(model_dir="/definitely/does/not/exist")
        with patch(
            "humanoid_character_builder.generators.mesh_generator.SMPLX_AVAILABLE",
            True,
        ):
            assert gen.is_available is False


class TestSMPLXMeshGeneratorGenerate:
    """Exercise the generate() path with smplx/trimesh mocked."""

    def test_generate_returns_failure_when_smplx_unavailable(
        self, tmp_path: Path
    ) -> None:
        gen = SMPLXMeshGenerator(model_dir=tmp_path)
        with patch(
            "humanoid_character_builder.generators.mesh_generator.SMPLX_AVAILABLE",
            False,
        ):
            result = gen.generate(_default_params(), tmp_path)
        assert result.success is False
        assert result.error_message is not None
        assert "smplx" in result.error_message.lower()

    def test_generate_returns_failure_when_trimesh_unavailable(
        self, tmp_path: Path
    ) -> None:
        gen = SMPLXMeshGenerator(model_dir=tmp_path)
        with (
            patch(
                "humanoid_character_builder.generators.mesh_generator.SMPLX_AVAILABLE",
                True,
            ),
            patch(
                "humanoid_character_builder.generators.mesh_generator.TRIMESH_AVAILABLE",
                False,
            ),
        ):
            result = gen.generate(_default_params(), tmp_path)
        assert result.success is False
        assert result.error_message is not None
        assert "trimesh" in result.error_message.lower()

    def test_generate_rejects_none_params(self, tmp_path: Path) -> None:
        gen = SMPLXMeshGenerator(model_dir=tmp_path)
        with pytest.raises(AssertionError):
            gen.generate(None, tmp_path)  # type: ignore[arg-type]

    def test_generate_happy_path_with_mocks(self, tmp_path: Path) -> None:
        """Mock both smplx and trimesh and verify per-segment STL export."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        gen = SMPLXMeshGenerator(model_dir=model_dir)

        # Fake smplx output: vertices (N, 3) and faces (M, 3) with body height > 0.
        # 120 vertices is enough for every range in SMPLX_SEGMENT_VERTEX_RANGES.
        num_verts = 120
        verts = np.zeros((num_verts, 3), dtype=np.float32)
        verts[:, 1] = np.linspace(0.0, 1.75, num_verts)  # Y-up body
        faces = np.array(
            [[i, (i + 1) % num_verts, (i + 2) % num_verts] for i in range(num_verts)],
            dtype=np.int64,
        )

        fake_output = MagicMock()
        fake_output.vertices.detach.return_value.cpu.return_value.numpy.return_value.squeeze.return_value = verts

        fake_model = MagicMock()
        fake_model.return_value = fake_output
        fake_model.faces = faces
        # Force the LBS-weights path to fail so the fallback vertex-range path runs
        # deterministically without needing a real torch tensor.
        del fake_model.lbs_weights

        fake_smplx = MagicMock()
        fake_smplx.create.return_value = fake_model

        exported: list[str] = []

        class FakeTrimesh:
            def __init__(self, vertices: Any = None, faces: Any = None) -> None:
                self.vertices = vertices
                self.faces = faces

            def export(self, path: str) -> None:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).touch()
                exported.append(path)

            @property
            def convex_hull(self) -> FakeTrimesh:
                return self

        fake_trimesh = MagicMock()
        fake_trimesh.Trimesh = FakeTrimesh

        with (
            patch(
                "humanoid_character_builder.generators.mesh_generator.SMPLX_AVAILABLE",
                True,
            ),
            patch(
                "humanoid_character_builder.generators.mesh_generator.TRIMESH_AVAILABLE",
                True,
            ),
            patch(
                "humanoid_character_builder.generators.mesh_generator._smplx_module",
                fake_smplx,
            ),
            patch(
                "humanoid_character_builder.generators.mesh_generator._trimesh_module",
                fake_trimesh,
            ),
        ):
            result = gen.generate(_default_params(), tmp_path / "out")

        assert result.success is True
        assert result.metadata["backend"] == "smplx"
        assert len(result.mesh_paths) > 0
        assert len(result.collision_paths) == len(result.mesh_paths)
        assert (tmp_path / "out" / "visual").is_dir()
        assert (tmp_path / "out" / "collision").is_dir()
