"""Unit tests for ``CollisionGeometryGenerator.generate`` helpers.

These tests exercise the pure-input / pure-output helpers extracted
during the decomposition of the oversized ``generate`` method (issue
#142).  They deliberately avoid requiring ``trimesh`` or VHACD.
"""

from __future__ import annotations

import pytest

from src.shared.python.humanoid_character_builder.mesh.collision_generator import (
    CollisionGeometryGenerator,
    CollisionGeometryResult,
    ComplexityLevel,
    SimplificationMethod,
)


@pytest.fixture
def generator() -> CollisionGeometryGenerator:
    """Return a fresh generator instance for each test."""
    return CollisionGeometryGenerator()


class TestResolveGenerateParameters:
    """Tests for ``_resolve_generate_parameters``."""

    def test_string_method_converted_to_enum(
        self, generator: CollisionGeometryGenerator
    ) -> None:
        method, _, _, _, _ = generator._resolve_generate_parameters(
            "vhacd", "balanced", None, None, None
        )
        assert method == SimplificationMethod.VHACD

    def test_string_complexity_converted_to_enum(
        self, generator: CollisionGeometryGenerator
    ) -> None:
        _, complexity, _, _, _ = generator._resolve_generate_parameters(
            "auto", "accurate", None, None, None
        )
        assert complexity == ComplexityLevel.ACCURATE

    def test_none_method_raises(self, generator: CollisionGeometryGenerator) -> None:
        with pytest.raises(ValueError, match="method"):
            generator._resolve_generate_parameters(None, "balanced", None, None, None)

    def test_preset_applied_when_overrides_absent(
        self, generator: CollisionGeometryGenerator
    ) -> None:
        _, _, max_p, max_t, max_h = generator._resolve_generate_parameters(
            "auto", "balanced", None, None, None
        )
        balanced = CollisionGeometryGenerator.COMPLEXITY_PRESETS[
            ComplexityLevel.BALANCED
        ]
        assert max_p == balanced["max_primitives"]
        assert max_t == balanced["max_triangles"]
        assert max_h == balanced["max_hulls"]

    def test_explicit_overrides_win(
        self, generator: CollisionGeometryGenerator
    ) -> None:
        _, _, max_p, max_t, max_h = generator._resolve_generate_parameters(
            "auto", "balanced", 7, 13, 19
        )
        assert (max_p, max_t, max_h) == (7, 13, 19)

    def test_enum_inputs_pass_through(
        self, generator: CollisionGeometryGenerator
    ) -> None:
        method, complexity, _, _, _ = generator._resolve_generate_parameters(
            SimplificationMethod.HYBRID, ComplexityLevel.MINIMAL, None, None, None
        )
        assert method == SimplificationMethod.HYBRID
        assert complexity == ComplexityLevel.MINIMAL


class TestBuildErrorResult:
    """Tests for ``_build_error_result``."""

    def test_success_is_false(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.VHACD, 42, "boom"
        )
        assert result.success is False

    def test_error_is_carried_through(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.VHACD, 42, "boom"
        )
        assert result.errors == ["boom"]

    def test_original_triangles_preserved(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.DECIMATION, 42, "boom"
        )
        assert result.original_triangles == 42

    def test_reduction_ratio_unit(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.CONVEX_HULL, 0, "err"
        )
        # No reduction achieved
        assert result.reduction_ratio == pytest.approx(1.0)

    def test_hausdorff_is_infinity(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.PRIMITIVES, 0, "err"
        )
        assert result.hausdorff_distance == float("inf")

    def test_method_preserved(self) -> None:
        result = CollisionGeometryGenerator._build_error_result(
            SimplificationMethod.HYBRID, 100, "err"
        )
        assert result.method_used == SimplificationMethod.HYBRID


class TestDispatchGeneration:
    """Tests for ``_dispatch_generation`` backend routing."""

    @staticmethod
    def _make_generator_with_recording() -> tuple[
        CollisionGeometryGenerator, dict[str, tuple]
    ]:
        """Return a generator whose backends record which one was called."""
        gen = CollisionGeometryGenerator()
        calls: dict[str, tuple] = {}

        def make_result() -> CollisionGeometryResult:
            return CollisionGeometryResult(
                success=True,
                method_used=SimplificationMethod.DECIMATION,
                components=[],
                original_triangles=0,
                final_triangles=0,
                reduction_ratio=0.0,
                volume_preservation=1.0,
                hausdorff_distance=0.0,
            )

        def _fake_vhacd(mesh, max_hulls, params):
            calls["vhacd"] = (mesh, max_hulls, params)
            return make_result()

        def _fake_primitives(mesh, max_primitives):
            calls["primitives"] = (mesh, max_primitives)
            return make_result()

        def _fake_decimated(mesh, max_triangles):
            calls["decimation"] = (mesh, max_triangles)
            return make_result()

        def _fake_convex_hull(mesh):
            calls["convex_hull"] = (mesh,)
            return make_result()

        def _fake_hybrid(mesh, max_primitives, max_triangles):
            calls["hybrid"] = (mesh, max_primitives, max_triangles)
            return make_result()

        gen._generate_vhacd = _fake_vhacd  # type: ignore[method-assign]
        gen._generate_primitives = _fake_primitives  # type: ignore[method-assign]
        gen._generate_decimated = _fake_decimated  # type: ignore[method-assign]
        gen._generate_convex_hull = _fake_convex_hull  # type: ignore[method-assign]
        gen._generate_hybrid = _fake_hybrid  # type: ignore[method-assign]
        return gen, calls

    def test_vhacd_dispatch(self) -> None:
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.VHACD, 4, 100, 8, None)
        assert "vhacd" in calls

    def test_primitives_dispatch(self) -> None:
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.PRIMITIVES, 4, 100, 8, None)
        assert "primitives" in calls

    def test_decimation_dispatch(self) -> None:
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.DECIMATION, 4, 100, 8, None)
        assert "decimation" in calls

    def test_convex_hull_dispatch(self) -> None:
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.CONVEX_HULL, 4, 100, 8, None)
        assert "convex_hull" in calls

    def test_hybrid_dispatch(self) -> None:
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.HYBRID, 4, 100, 8, None)
        assert "hybrid" in calls

    def test_auto_falls_back_to_decimation(self) -> None:
        # AUTO is resolved before _dispatch_generation is called in the
        # real flow, so reaching AUTO here must fall through to
        # decimation.
        gen, calls = self._make_generator_with_recording()
        gen._dispatch_generation("m", SimplificationMethod.AUTO, 4, 100, 8, None)
        assert "decimation" in calls
