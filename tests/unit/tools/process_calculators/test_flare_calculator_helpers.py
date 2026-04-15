"""Unit tests for helpers extracted from ``calculate_flare_size`` (issue #142).

These tests exercise the pure-function helpers introduced when
``FlareCalculator.calculate_flare_size`` was decomposed into smaller
single-responsibility pieces.
"""

from __future__ import annotations

import math

import pytest

from src.shared.python.upstream_drift_tools.process_calculators.flare_calculator import (
    FlareCalculator,
    FlareDesign,
)


@pytest.fixture
def calculator() -> FlareCalculator:
    return FlareCalculator()


class TestNormalizeComposition:
    def test_already_normalized(self, calculator: FlareCalculator) -> None:
        comp = {"H2": 0.5, "CH4": 0.5}
        result = calculator._normalize_composition(comp)
        assert result == pytest.approx({"H2": 0.5, "CH4": 0.5})

    def test_sums_to_one_after_normalization(self, calculator: FlareCalculator) -> None:
        comp = {"H2": 50.0, "CH4": 50.0}
        result = calculator._normalize_composition(comp)
        assert sum(result.values()) == pytest.approx(1.0)
        assert result["H2"] == pytest.approx(0.5)

    def test_all_zero_input(self, calculator: FlareCalculator) -> None:
        comp = {"H2": 0.0, "CH4": 0.0}
        result = calculator._normalize_composition(comp)
        assert result == {"H2": 0.0, "CH4": 0.0}


class TestMixtureProperties:
    def test_pure_hydrogen(self, calculator: FlareCalculator) -> None:
        mw, hv = calculator._compute_mixture_properties({"H2": 1.0})
        assert mw == pytest.approx(calculator.gas_properties["H2"]["mw"])
        assert hv == pytest.approx(calculator.gas_properties["H2"]["hv"])

    def test_equal_blend(self, calculator: FlareCalculator) -> None:
        mw, hv = calculator._compute_mixture_properties({"H2": 0.5, "CH4": 0.5})
        expected_mw = 0.5 * (
            calculator.gas_properties["H2"]["mw"]
            + calculator.gas_properties["CH4"]["mw"]
        )
        assert mw == pytest.approx(expected_mw)
        assert hv > 0


class TestGasDensity:
    def test_density_is_positive_under_normal_conditions(
        self, calculator: FlareCalculator
    ) -> None:
        # CH4 at 298 K, 1.013 bar
        density = calculator._compute_gas_density(
            mix_mw=16.04, temperature=298.0, pressure=1.013
        )
        assert density > 0
        # methane density ~0.66 kg/m^3 at these conditions
        assert 0.5 < density < 1.0

    def test_fallback_when_temperature_nonpositive(
        self, calculator: FlareCalculator
    ) -> None:
        density = calculator._compute_gas_density(
            mix_mw=16.04, temperature=0.0, pressure=1.013
        )
        assert density == pytest.approx(1.0)


class TestFlareDiameter:
    def test_zero_density_returns_zero_diameter(
        self, calculator: FlareCalculator
    ) -> None:
        diameter = calculator._compute_flare_diameter(
            total_flow=1000.0, gas_density=0.0, target_velocity=170.0
        )
        assert diameter == 0.0

    def test_positive_diameter_with_valid_inputs(
        self, calculator: FlareCalculator
    ) -> None:
        diameter = calculator._compute_flare_diameter(
            total_flow=3600.0, gas_density=1.0, target_velocity=170.0
        )
        # mass flow = 1 kg/s, area = 1 / (1 * 170) m^2
        expected = math.sqrt(4 * (1.0 / 170.0) / math.pi)
        assert diameter == pytest.approx(expected)


class TestFlareHeight:
    def test_enforces_minimum_height(self, calculator: FlareCalculator) -> None:
        # Small heat release drives the computed height below the minimum.
        from src.shared.python.upstream_drift_tools.process_calculators.constants import (
            FLARE_MIN_HEIGHT,
        )

        height = calculator._compute_flare_height(
            heat_release=1.0, target_radiation=1.6
        )
        assert height >= FLARE_MIN_HEIGHT

    def test_target_radiation_zero_clamps_to_minimum(
        self, calculator: FlareCalculator
    ) -> None:
        from src.shared.python.upstream_drift_tools.process_calculators.constants import (
            FLARE_MIN_HEIGHT,
        )

        height = calculator._compute_flare_height(
            heat_release=1000.0, target_radiation=0.0
        )
        assert height == pytest.approx(FLARE_MIN_HEIGHT)


class TestValidation:
    def test_preconditions_allow_valid_inputs(
        self, calculator: FlareCalculator
    ) -> None:
        # should not raise
        calculator._validate_flare_inputs(
            total_flow=10.0,
            gas_composition={"H2": 1.0},
            temperature=300.0,
            pressure=1.0,
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"total_flow": 0.0},
            {"temperature": 0.0},
            {"pressure": 0.0},
            {"gas_composition": {}},
        ],
    )
    def test_preconditions_reject_bad_inputs(
        self, calculator: FlareCalculator, kwargs: dict[str, object]
    ) -> None:
        defaults: dict[str, object] = {
            "total_flow": 10.0,
            "gas_composition": {"H2": 1.0},
            "temperature": 300.0,
            "pressure": 1.0,
        }
        defaults.update(kwargs)
        with pytest.raises(AssertionError):
            calculator._validate_flare_inputs(**defaults)  # type: ignore[arg-type]

    def test_postcondition_rejects_negative_diameter(
        self, calculator: FlareCalculator
    ) -> None:
        bad = FlareDesign(
            height=10.0,
            diameter=-0.1,
            exit_velocity=170.0,
            heat_release=1.0,
            radiation_intensity=1.6,
        )
        with pytest.raises(AssertionError):
            calculator._validate_flare_result(bad)


class TestCalculateFlareSizeEndToEnd:
    """Ensure overall behaviour still matches after decomposition."""

    def test_produces_reasonable_design(self, calculator: FlareCalculator) -> None:
        design = calculator.calculate_flare_size(
            total_flow=10000.0,  # kg/hr
            gas_composition={"CH4": 90.0, "C2H6": 10.0},
            temperature=300.0,
            pressure=1.0,
        )
        assert design.height > 0
        assert design.diameter > 0
        assert design.exit_velocity > 0
        assert design.heat_release > 0
