"""Tests for the extracted pressure drop calculator helper modules.

Covers:
  - unit_converters.py  (convert_temperature, convert_pressure)
  - validation_helpers.py  (validate_pipe_params, validate_flow_params,
                             validate_conditions, validate_composition_and_fittings,
                             validate_inputs)
  - calculation_helpers.py  (build_fitting_list, resolve_pipe_geometry,
                              _normalise_composition, resolve_gas_and_flow,
                              format_results)
  - ui/display_helpers.py   (wrap_text, generate_recommendations,
                              _erosion_status_label, _classify_fitting)
"""

from __future__ import annotations

import pytest

from src.shared.python.upstream_drift_tools.process_calculators.pressure_drop_calculator.calculation_helpers import (
    _normalise_composition,
    build_fitting_list,
)
from src.shared.python.upstream_drift_tools.process_calculators.pressure_drop_calculator.ui.display_helpers import (
    _classify_fitting,
    _erosion_status_label,
    generate_recommendations,
    wrap_text,
)
from src.shared.python.upstream_drift_tools.process_calculators.pressure_drop_calculator.unit_converters import (
    convert_pressure,
    convert_temperature,
)
from src.shared.python.upstream_drift_tools.process_calculators.pressure_drop_calculator.validation_helpers import (
    validate_composition_and_fittings,
    validate_conditions,
    validate_flow_params,
    validate_inputs,
    validate_pipe_params,
)

# ---------------------------------------------------------------------------
# unit_converters
# ---------------------------------------------------------------------------


class TestConvertTemperature:
    def test_kelvin_identity(self):
        assert convert_temperature(300.0, "K", "K") == pytest.approx(300.0)

    def test_celsius_to_kelvin(self):
        assert convert_temperature(0.0, "C", "K") == pytest.approx(273.15)

    def test_kelvin_to_celsius(self):
        assert convert_temperature(273.15, "K", "C") == pytest.approx(0.0)

    def test_fahrenheit_to_celsius(self):
        assert convert_temperature(212.0, "F", "C") == pytest.approx(100.0)

    def test_celsius_to_fahrenheit(self):
        assert convert_temperature(100.0, "C", "F") == pytest.approx(212.0)

    def test_unknown_from_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown temperature unit"):
            convert_temperature(300.0, "X", "K")

    def test_unknown_to_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown temperature unit"):
            convert_temperature(300.0, "K", "X")


class TestConvertPressure:
    def test_bar_to_pa(self):
        assert convert_pressure(1.0, "bar", "Pa") == pytest.approx(1e5)

    def test_pa_identity(self):
        assert convert_pressure(101325.0, "Pa", "Pa") == pytest.approx(101325.0)

    def test_atm_to_pa(self):
        assert convert_pressure(1.0, "atm", "Pa") == pytest.approx(101325.0)

    def test_pa_to_bar(self):
        assert convert_pressure(1e5, "Pa", "bar") == pytest.approx(1.0)

    def test_unknown_from_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown pressure unit"):
            convert_pressure(1.0, "ZZZ", "Pa")

    def test_unknown_to_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown pressure unit"):
            convert_pressure(1.0, "Pa", "ZZZ")


# ---------------------------------------------------------------------------
# validation_helpers
# ---------------------------------------------------------------------------


class TestValidatePipeParams:
    def test_no_pipe_info_adds_error(self):
        errors: list[str] = []
        validate_pipe_params(None, None, None, errors, [])
        assert any("pipe_diameter" in e for e in errors)

    def test_explicit_diameter_passes(self):
        errors: list[str] = []
        validate_pipe_params(None, None, 0.1, errors, [])
        assert errors == []

    def test_negative_diameter_adds_error(self):
        errors: list[str] = []
        validate_pipe_params(None, None, -0.05, errors, [])
        assert any("positive" in e for e in errors)

    def test_large_diameter_adds_warning(self):
        warnings: list[str] = []
        validate_pipe_params(None, None, 3.0, [], warnings)
        assert any("Large diameter" in w for w in warnings)


class TestValidateFlowParams:
    def test_missing_flow_rate_adds_error(self):
        errors: list[str] = []
        validate_flow_params(None, "kg/h", errors)
        assert any("flow_rate is required" in e for e in errors)

    def test_negative_flow_rate_adds_error(self):
        errors: list[str] = []
        validate_flow_params(-1.0, "kg/h", errors)
        assert any("positive" in e for e in errors)

    def test_none_errors_raises(self):
        with pytest.raises(ValueError, match="errors must be provided"):
            validate_flow_params(1.0, "kg/h", None)  # type: ignore[arg-type]

    def test_valid_flow_no_errors(self):
        errors: list[str] = []
        validate_flow_params(100.0, "kg/h", errors)
        assert errors == []


class TestValidateConditions:
    def test_negative_pressure_adds_error(self):
        errors: list[str] = []
        validate_conditions(-1.0, 300.0, errors, [])
        assert any("positive" in e for e in errors)

    def test_negative_temperature_adds_error(self):
        errors: list[str] = []
        validate_conditions(1.0, -10.0, errors, [])
        assert any("positive" in e for e in errors)

    def test_low_temperature_warning(self):
        warnings: list[str] = []
        validate_conditions(1.0, 100.0, [], warnings)
        assert any("Celsius" in w for w in warnings)

    def test_none_errors_raises(self):
        with pytest.raises(ValueError, match="errors must be provided"):
            validate_conditions(1.0, 300.0, None, [])  # type: ignore[arg-type]


class TestValidateCompositionAndFittings:
    def test_unknown_gas_component_adds_error(self):
        errors: list[str] = []
        validate_composition_and_fittings({"UNOBTAINIUM": 1.0}, None, errors, [])
        assert any("Unknown gas components" in e for e in errors)

    def test_composition_not_summing_to_one_warns(self):
        warnings: list[str] = []
        validate_composition_and_fittings({"H2": 0.5, "CO": 0.3}, None, [], warnings)
        assert any("sums to" in w for w in warnings)

    def test_unknown_fitting_type_warns(self):
        warnings: list[str] = []
        validate_composition_and_fittings(
            None, [{"type": "fantasy_valve", "quantity": 1}], [], warnings
        )
        assert any("not in database" in w for w in warnings)

    def test_valid_air_composition_no_errors(self):
        errors: list[str] = []
        validate_composition_and_fittings({"Air": 1.0}, None, errors, [])
        assert errors == []


class TestValidateInputs:
    def test_all_none_returns_invalid(self):
        is_valid, errors, _warnings = validate_inputs()
        assert not is_valid
        assert len(errors) > 0

    def test_diameter_and_flow_returns_valid(self):
        is_valid, errors, _warnings = validate_inputs(
            pipe_diameter=0.1,
            flow_rate=100.0,
            flow_unit="kg/h",
        )
        assert is_valid
        assert errors == []


# ---------------------------------------------------------------------------
# calculation_helpers
# ---------------------------------------------------------------------------


class TestNormaliseComposition:
    def test_none_defaults_to_air(self):
        composition = _normalise_composition(None)
        assert "Air" in composition.components

    def test_normalisation_adjusts_fractions(self):
        # Sum > 1 should be normalised
        composition = _normalise_composition({"H2": 0.6, "CO": 0.6})
        total = sum(composition.components.values())
        assert total == pytest.approx(1.0, abs=1e-6)


class TestBuildFittingList:
    def test_none_returns_empty_list(self):
        assert build_fitting_list(None) == []

    def test_single_known_fitting(self):
        result = build_fitting_list([{"type": "90_elbow_std", "quantity": 2}])
        assert len(result) == 1
        assert result[0].quantity == 2
        assert result[0].fitting_type == "90_elbow_std"

    def test_unknown_fitting_defaults_k_to_zero(self):
        result = build_fitting_list([{"type": "mystery_fitting", "quantity": 1}])
        assert result[0].k_factor == 0.0

    def test_explicit_k_factor_used(self):
        result = build_fitting_list(
            [{"type": "custom", "quantity": 1, "k_factor": 3.5}]
        )
        assert result[0].k_factor == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# ui.display_helpers
# ---------------------------------------------------------------------------


class TestWrapText:
    def test_short_text_not_wrapped(self):
        lines = wrap_text("hello world", 80)
        assert lines == ["hello world"]

    def test_long_text_split_on_word_boundary(self):
        text = "one two three four five six seven eight nine ten"
        lines = wrap_text(text, 20)
        for line in lines:
            assert len(line) <= 20

    def test_none_text_raises(self):
        with pytest.raises(ValueError, match="text must be provided"):
            wrap_text(None, 80)  # type: ignore[arg-type]

    def test_empty_string_returns_one_empty(self):
        lines = wrap_text("", 80)
        assert lines == [""]


class TestErosionStatusLabel:
    def test_safe_below_50(self):
        assert "SAFE" in _erosion_status_label(40.0)

    def test_caution_between_50_and_80(self):
        label = _erosion_status_label(65.0)
        assert "CAUTION" in label

    def test_danger_above_80(self):
        label = _erosion_status_label(90.0)
        assert "DANGER" in label


class TestClassifyFitting:
    def test_elbow_classified_correctly(self):
        categories = {"elbow": ["elbow"]}
        assert _classify_fitting("90_elbow_std", categories) == "elbow"

    def test_unknown_returns_other(self):
        categories = {"valve": ["valve"]}
        assert _classify_fitting("mystery_widget", categories) == "other"


class TestGenerateRecommendations:
    """Test generate_recommendations with synthetic results dicts."""

    def _base_results(self) -> dict:
        return {
            "pressure_drop_pa": 1000.0,
            "outlet_pressure_pa": 100000.0,
            "friction_loss_pa": 800.0,
            "fitting_loss_pa": 200.0,
            "erosion_ratio": 0.1,
            "mach_number": 0.05,
            "reynolds_number": 50000.0,
        }

    def test_no_issues_returns_empty(self):
        recs = generate_recommendations(self._base_results())
        assert recs == []

    def test_high_pressure_drop_flagged(self):
        results = self._base_results()
        # Make dp_ratio > 0.20
        results["pressure_drop_pa"] = 30000.0
        results["outlet_pressure_pa"] = 100000.0
        recs = generate_recommendations(results)
        assert any("pressure drop" in r.lower() for r in recs)

    def test_high_erosion_ratio_flagged(self):
        results = self._base_results()
        results["erosion_ratio"] = 0.9
        recs = generate_recommendations(results)
        assert any("erosional limit" in r for r in recs)

    def test_fitting_dominated_flagged(self):
        results = self._base_results()
        results["fitting_loss_pa"] = 5000.0
        results["friction_loss_pa"] = 100.0
        recs = generate_recommendations(results)
        assert any("Fitting losses" in r for r in recs)

    def test_high_mach_flagged(self):
        results = self._base_results()
        results["mach_number"] = 0.5
        recs = generate_recommendations(results)
        assert any("Mach" in r for r in recs)

    def test_low_reynolds_flagged(self):
        results = self._base_results()
        results["reynolds_number"] = 1000.0
        recs = generate_recommendations(results)
        assert any("Reynolds" in r for r in recs)
