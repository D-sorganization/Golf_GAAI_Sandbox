"""Unit tests for helpers extracted from ``BaghouseCalculator.calculate`` (issue #142).

These tests pin down the behaviour of the small helpers introduced
when the 102-line ``calculate`` method was decomposed.
"""

from __future__ import annotations

import pytest

from src.shared.python.upstream_drift_tools.process_calculators.baghouse_calculator import (
    BaghouseCalculator,
)


@pytest.fixture
def calculator() -> BaghouseCalculator:
    return BaghouseCalculator(thermo_calc=None)


class TestValidateCalculateInputs:
    def test_accepts_valid_inputs(self) -> None:
        BaghouseCalculator._validate_calculate_inputs(
            gas_flow_kg_s=1.0,
            inlet_temp_k=500.0,
            pressure_pa=101325.0,
            carbon_removal_efficiency=0.99,
            ash_removal_efficiency=0.95,
            drum_volume_m3=1.0,
            solid_density_kg_m3=500.0,
        )

    @pytest.mark.parametrize(
        "override",
        [
            {"gas_flow_kg_s": 0.0},
            {"inlet_temp_k": 0.0},
            {"pressure_pa": 0.0},
            {"carbon_removal_efficiency": 1.5},
            {"carbon_removal_efficiency": -0.1},
            {"ash_removal_efficiency": 1.5},
            {"drum_volume_m3": 0.0},
            {"solid_density_kg_m3": 0.0},
        ],
    )
    def test_rejects_invalid_inputs(self, override: dict[str, float]) -> None:
        defaults: dict[str, float] = {
            "gas_flow_kg_s": 1.0,
            "inlet_temp_k": 500.0,
            "pressure_pa": 101325.0,
            "carbon_removal_efficiency": 0.99,
            "ash_removal_efficiency": 0.95,
            "drum_volume_m3": 1.0,
            "solid_density_kg_m3": 500.0,
        }
        defaults.update(override)
        with pytest.raises(AssertionError):
            BaghouseCalculator._validate_calculate_inputs(**defaults)


class TestAshStreamComposition:
    def test_fractions_sum_to_one_when_nonzero(self) -> None:
        comp = BaghouseCalculator._compute_ash_stream_composition(
            carbon_removed=3.0, ash_removed=7.0, total_solids=10.0
        )
        assert comp["carbon_fraction"] == pytest.approx(0.3)
        assert comp["ash_fraction"] == pytest.approx(0.7)
        assert comp["carbon_fraction"] + comp["ash_fraction"] == pytest.approx(1.0)

    def test_zero_solids_returns_zero_fractions(self) -> None:
        comp = BaghouseCalculator._compute_ash_stream_composition(
            carbon_removed=0.0, ash_removed=0.0, total_solids=0.0
        )
        assert comp == {"carbon_fraction": 0.0, "ash_fraction": 0.0}


class TestAirToCloth:
    def test_positive_ratio(self) -> None:
        ratio = BaghouseCalculator._compute_air_to_cloth(
            flow_acfm=500.0, bag_area_ft2=100.0
        )
        assert ratio == pytest.approx(5.0)

    def test_zero_bag_area_returns_zero(self) -> None:
        ratio = BaghouseCalculator._compute_air_to_cloth(
            flow_acfm=500.0, bag_area_ft2=0.0
        )
        assert ratio == 0.0


class TestBuildBaghouseResult:
    def test_assembles_all_fields(self, calculator: BaghouseCalculator) -> None:
        drum_sizing = (
            10.0,  # carbon_removed
            20.0,  # ash_removed
            30.0,  # total_solids
            100.0,  # fill_hrs
            4.17,  # fill_days
            300.0,  # c_fill
            150.0,  # a_fill
        )
        result = calculator._build_baghouse_result(
            gas_flow_kg_s=1.0,
            bag_area_ft2=100.0,
            outlet_temp_c=200.0,
            flow_acfm=500.0,
            flow_scfm=400.0,
            drum_sizing=drum_sizing,
            carbon_removal_efficiency=0.99,
            ash_removal_efficiency=0.95,
        )
        assert result.carbon_removed_rate == 10.0
        assert result.ash_removed_rate == 20.0
        assert result.total_solids_removed_rate == 30.0
        assert result.drum_fill_time_hours == 100.0
        assert result.air_to_cloth_ratio == pytest.approx(5.0)
        assert result.outlet_temperature_c == 200.0
        assert result.flow_acfm == 500.0
        assert result.flow_scfm == 400.0
        assert result.removal_efficiency == {"carbon": 99.0, "ash": 95.0}
        assert result.ash_stream_composition["carbon_fraction"] == pytest.approx(
            10.0 / 30.0
        )


class TestCalculateEndToEnd:
    """Smoke test the full ``calculate`` method after decomposition."""

    def test_calculate_runs_end_to_end(self, calculator: BaghouseCalculator) -> None:
        composition = {
            "H2": 0.3,
            "CO": 0.3,
            "CO2": 0.2,
            "H2O": 0.1,
            "N2": 0.1,
        }
        result = calculator.calculate(
            gas_flow_kg_s=1.0,
            inlet_temp_k=800.0,
            pressure_pa=101325.0,
            composition=composition,
            solid_carbon_in_kg_hr=5.0,
            ash_in_kg_hr=2.0,
            carbon_removal_efficiency=0.99,
            ash_removal_efficiency=0.95,
            heat_loss_w=1000.0,
            drum_volume_m3=1.0,
            solid_density_kg_m3=500.0,
            bag_area_ft2=100.0,
        )
        assert result.carbon_removed_rate > 0
        assert result.ash_removed_rate > 0
        assert result.total_solids_removed_rate > 0
        assert result.air_to_cloth_ratio >= 0
        assert result.removal_efficiency["carbon"] == pytest.approx(99.0)
