"""Unit tests for the extracted MakeHumanMeshGenerator."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from humanoid_character_builder.core.body_parameters import BodyParameters
from humanoid_character_builder.generators.makehuman_mesh_generator import (
    MakeHumanMeshGenerator,
)
from humanoid_character_builder.generators.mesh_generator import (
    MakeHumanMeshGenerator as ReexportedMakeHuman,
)


def _default_params(**overrides: Any) -> BodyParameters:
    kwargs: dict[str, Any] = {"height_m": 1.80, "mass_kg": 80.0}
    kwargs.update(overrides)
    return BodyParameters(**kwargs)


class TestMakeHumanMeshGeneratorContract:
    """Static properties of the extracted backend."""

    def test_backend_name_is_makehuman(self) -> None:
        assert MakeHumanMeshGenerator().backend_name == "makehuman"

    def test_reexport_is_same_class(self) -> None:
        assert ReexportedMakeHuman is MakeHumanMeshGenerator

    def test_supported_segments_match_vertex_group_map(self) -> None:
        segments = MakeHumanMeshGenerator().get_supported_segments()
        assert len(segments) == len(MakeHumanMeshGenerator.MH_VERTEX_GROUP_MAP)
        assert "head" in segments
        assert "right_foot" in segments


class TestMakeHumanMeshGeneratorAvailability:
    """Availability behavior should remain compatible with the old module."""

    def test_unavailable_when_path_missing(self) -> None:
        gen = MakeHumanMeshGenerator(makehuman_path="/definitely/missing")
        assert gen.is_available is False

    def test_available_when_path_exists(self, tmp_path: Path) -> None:
        gen = MakeHumanMeshGenerator(makehuman_path=tmp_path)
        assert gen.is_available is True


class TestMakeHumanMeshGeneratorParsing:
    """Static OBJ helpers should keep existing behavior after extraction."""

    def test_parse_obj_with_quad_triangulation(self, tmp_path: Path) -> None:
        obj_file = tmp_path / "body.obj"
        obj_file.write_text(
            textwrap.dedent("""\
                v 0.0 0.0 0.0
                v 1.0 0.0 0.0
                v 1.0 1.0 0.0
                v 0.0 1.0 0.0
                f 1 2 3 4
                """),
            encoding="utf-8",
        )

        vertices, faces = MakeHumanMeshGenerator._parse_obj_file(obj_file)

        assert vertices.shape == (4, 3)
        assert faces.shape == (2, 3)

    def test_script_contains_expected_makehuman_operations(self) -> None:
        script = MakeHumanMeshGenerator._build_mh_script(
            {"macrodetails/Gender": 1.0},
            Path("body.obj"),
            Path("groups.json"),
        )
        assert "macrodetails/Gender" in script
        assert "exportOBJ" in script
        assert "json.dump" in script


class TestMakeHumanMeshGeneratorGenerate:
    """Exercise the generate path with subprocess and trimesh mocked."""

    def test_generate_rejects_none_params(self, tmp_path: Path) -> None:
        gen = MakeHumanMeshGenerator(makehuman_path=tmp_path)
        with pytest.raises(AssertionError):
            gen.generate(None, tmp_path / "out")  # type: ignore[arg-type]

    @patch(
        "humanoid_character_builder.generators.mesh_generator.TRIMESH_AVAILABLE", True
    )
    @patch("humanoid_character_builder.generators.mesh_generator._trimesh_module")
    def test_generate_happy_path_with_mocks(
        self,
        mock_trimesh: MagicMock,
        tmp_path: Path,
    ) -> None:
        gen = MakeHumanMeshGenerator(makehuman_path=tmp_path)
        mock_trimesh.Trimesh = _fake_trimesh_factory()

        def mock_run(script_path: Path, timeout: int = 120) -> bool:
            del timeout
            script_dir = script_path.parent
            _write_grouped_obj(script_dir / "body.obj")
            (script_dir / "groups.json").write_text(
                json.dumps({"head": [0, 1, 2]}),
                encoding="utf-8",
            )
            return True

        with patch.object(gen, "_run_makehuman_script", side_effect=mock_run):
            result = gen.generate(_default_params(), tmp_path / "out")

        assert result.success is True
        assert result.metadata["backend"] == "makehuman"
        assert result.mesh_paths["head"].suffix == ".stl"
        assert (tmp_path / "out" / "visual").is_dir()
        assert (tmp_path / "out" / "collision").is_dir()


def _fake_trimesh_factory() -> type:
    class FakeTrimesh:
        def __init__(self, vertices: Any = None, faces: Any = None) -> None:
            self.vertices = vertices
            self.faces = faces

        def export(self, path: str) -> None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).touch()

        @property
        def convex_hull(self) -> FakeTrimesh:
            return self

    return FakeTrimesh


def _write_grouped_obj(obj_file: Path) -> None:
    obj_file.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
        encoding="utf-8",
    )
