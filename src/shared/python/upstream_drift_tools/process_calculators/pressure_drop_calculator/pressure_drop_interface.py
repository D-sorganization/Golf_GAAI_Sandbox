"""User-friendly Python interface for the advanced pressure drop calculator.

This module is the public API facade.  Implementation details live in:
  - :mod:`ui.display_helpers`  — human-readable output (tables, help text)
  - :mod:`validation_helpers`  — input validation logic
  - :mod:`unit_converters`     — temperature / pressure unit conversion
  - :mod:`calculation_helpers` — pipe-geometry, flow, fitting, and result helpers

QUICK START:
    >>> from pressure_drop_calculator import calculate_pressure_drop
    >>> result = calculate_pressure_drop(
    ...     pipe_size="4",
    ...     pipe_schedule="40",
    ...     pipe_length=100,
    ...     flow_rate=1000,
    ...     flow_unit='kg/h',
    ...     pressure=10,
    ...     temperature=500
    ... )
    >>> print(f"Pressure drop: {result['pressure_drop_bar']:.4f} bar")
"""

import logging
from typing import Any

from .calculation_helpers import (
    build_fitting_list,
    format_results,
    resolve_gas_and_flow,
    resolve_pipe_geometry,
)
from .engine.pressure_drop_calculation_engine import PressureDropCalculationEngine
from .models.pressure_drop_data_models import PressureDropInputs
from .ui.display_helpers import (
    compare_friction_methods,
    generate_recommendations,
    list_fittings,
    list_flow_units,
    list_gas_components,
    list_materials,
    list_pipe_sizes,
    print_results,
    show_help,
    wrap_text,
)
from .unit_converters import convert_pressure, convert_temperature
from .validation_helpers import (
    log_validation_report,
    validate_composition_and_fittings,
    validate_conditions,
    validate_flow_params,
    validate_inputs,
    validate_pipe_params,
)

logger = logging.getLogger(__name__)

__all__ = [
    "calculate_pressure_drop",
    "calculate_pressure_drop_custom_gas",
    "calculate_pressure_drop_syngas",
    "compare_friction_methods",
    "generate_recommendations",
    "list_fittings",
    "list_flow_units",
    "list_gas_components",
    "list_materials",
    "list_pipe_sizes",
    "log_validation_report",
    "print_results",
    "show_help",
    "validate_composition_and_fittings",
    "validate_conditions",
    "validate_flow_params",
    "validate_inputs",
    "validate_pipe_params",
    "wrap_text",
]


# ============================================================================
# PUBLIC API
# ============================================================================


def _assemble_inputs(
    pipe_diameter_m: float,
    pipe_length: float,
    roughness: float,
    elevation_change: float,
    mass_flow_kg_s: float,
    pressure_pa: float,
    temp_k: float,
    composition: Any,
    fitting_list: list,
    compressibility_correction: bool,
    friction_method: str,
) -> PressureDropInputs:
    """Assemble a PressureDropInputs dataclass from resolved parameters."""
    return PressureDropInputs(
        pipe_diameter=pipe_diameter_m,
        pipe_length=pipe_length,
        pipe_roughness=roughness,
        elevation_change=elevation_change,
        mass_flow_rate=mass_flow_kg_s,
        inlet_pressure=pressure_pa,
        inlet_temperature=temp_k,
        gas_composition=composition,
        fittings=fitting_list,
        compressibility_correction=compressibility_correction,
        friction_method=friction_method,
    )


def _run_calculation(
    pipe_size: str | None,
    pipe_schedule: str | None,
    pipe_diameter: float | None,
    pipe_length: float,
    pipe_material: str,
    pipe_roughness: float | None,
    elevation_change: float,
    flow_rate: float,
    flow_unit: str,
    pressure_pa: float,
    temp_k: float,
    gas_composition: dict[str, float] | None,
    fittings: list | None,
    friction_method: str,
    compressibility_correction: bool,
    standard_condition: str,
) -> dict[str, Any]:
    """Resolve all inputs, build the engine inputs object, and return results."""
    pipe_diameter_m, roughness = resolve_pipe_geometry(
        pipe_size, pipe_schedule, pipe_diameter, pipe_material, pipe_roughness
    )
    composition, mass_flow_kg_s = resolve_gas_and_flow(
        flow_rate,
        flow_unit,
        gas_composition,
        temp_k,
        pressure_pa,
        compressibility_correction,
        standard_condition,
    )
    inputs = _assemble_inputs(
        pipe_diameter_m,
        pipe_length,
        roughness,
        elevation_change,
        mass_flow_kg_s,
        pressure_pa,
        temp_k,
        composition,
        build_fitting_list(fittings),
        compressibility_correction,
        friction_method,
    )
    return format_results(PressureDropCalculationEngine().calculate(inputs))


def calculate_pressure_drop(
    pipe_size: str | None = None,
    pipe_schedule: str | None = None,
    pipe_diameter: float | None = None,
    pipe_length: float = 100.0,
    pipe_material: str = "Commercial Steel",
    pipe_roughness: float | None = None,
    elevation_change: float = 0.0,
    flow_rate: float = 1000.0,
    flow_unit: str = "kg/h",
    pressure: float = 1.0,
    pressure_unit: str = "bar",
    temperature: float = 288.15,
    temperature_unit: str = "K",
    gas_composition: dict[str, float] | None = None,
    fittings: list[dict[str, str | int | float]] | None = None,
    friction_method: str = "colebrook",
    compressibility_correction: bool = True,
    standard_condition: str = "STP",
) -> dict[str, Any]:
    """Calculate pressure drop with flexible unit inputs.

    See module docstring for full parameter documentation.

    Returns:
        Dictionary with pressure drop in Pa, bar, psi, kPa plus flow
        characteristics and safety metrics.
    """
    if pipe_length is None:
        raise ValueError("pipe_length must be provided")
    return _run_calculation(
        pipe_size,
        pipe_schedule,
        pipe_diameter,
        pipe_length,
        pipe_material,
        pipe_roughness,
        elevation_change,
        flow_rate,
        flow_unit,
        convert_pressure(pressure, pressure_unit, "Pa"),
        convert_temperature(temperature, temperature_unit, "K"),
        gas_composition,
        fittings,
        friction_method,
        compressibility_correction,
        standard_condition,
    )


def calculate_pressure_drop_custom_gas(
    pipe_diameter: float,
    pipe_length: float,
    gas_composition: dict[str, float],
    flow_rate: float,
    flow_unit: str,
    pressure: float,  # bar absolute
    temperature: float,  # K
    pipe_roughness: float = 0.000045,
    elevation_change: float = 0.0,
    fittings: list[dict[str, Any]] | None = None,
    friction_method: str = "colebrook",
) -> dict[str, Any]:
    """Simplified API for custom gas composition (pipe specified by diameter).

    Thin wrapper around :func:`calculate_pressure_drop` that fixes
    ``pressure_unit='bar'`` and ``temperature_unit='K'`` for convenience.

    Returns:
        Results dictionary (same schema as ``calculate_pressure_drop``).
    """
    return calculate_pressure_drop(
        pipe_diameter=pipe_diameter,
        pipe_length=pipe_length,
        pipe_roughness=pipe_roughness,
        elevation_change=elevation_change,
        flow_rate=flow_rate,
        flow_unit=flow_unit,
        pressure=pressure,
        pressure_unit="bar",
        temperature=temperature,
        temperature_unit="K",
        gas_composition=gas_composition,
        fittings=fittings,
        friction_method=friction_method,
    )


def _build_syngas_composition(
    H2: float, CO: float, CO2: float, N2: float, CH4: float
) -> dict[str, float]:
    """Return a normalised syngas mole-fraction dictionary."""
    raw = {"H2": H2, "CO": CO, "CO2": CO2, "N2": N2, "CH4": CH4}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def calculate_pressure_drop_syngas(
    pipe_size: str,
    pipe_schedule: str,
    pipe_length: float,
    flow_rate: float,
    flow_unit: str,
    pressure: float,  # bar
    temperature: float,  # K
    H2_fraction: float = 0.30,
    CO_fraction: float = 0.40,
    CO2_fraction: float = 0.15,
    N2_fraction: float = 0.10,
    CH4_fraction: float = 0.05,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convenience wrapper for typical syngas (H2/CO/CO2/N2/CH4) calculations.

    Mole fractions are auto-normalised to sum to 1.0.

    Returns:
        Results dictionary (same schema as ``calculate_pressure_drop``).
    """
    if pipe_size is None:
        raise ValueError("pipe_size must be provided")
    syngas = _build_syngas_composition(
        H2_fraction, CO_fraction, CO2_fraction, N2_fraction, CH4_fraction
    )
    return calculate_pressure_drop(
        pipe_size=pipe_size,
        pipe_schedule=pipe_schedule,
        pipe_length=pipe_length,
        flow_rate=flow_rate,
        flow_unit=flow_unit,
        pressure=pressure,
        temperature=temperature,
        gas_composition=syngas,
        **kwargs,
    )


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================


def main() -> None:
    """Command line interface for pressure drop calculator."""
    logger.info("\n" + "=" * 80)
    logger.info("ADVANCED PRESSURE DROP CALCULATOR".center(80))
    logger.info("For Combustion and Gasification Gases".center(80))
    logger.info("=" * 80)

    logger.info("\n" + "-" * 80)
    logger.info('Example 1: Air in 4" Schedule 40 pipe')
    logger.info("-" * 80)
    result = calculate_pressure_drop(
        pipe_size="4",
        pipe_schedule="40",
        pipe_length=100,
        flow_rate=1000,
        flow_unit="SCFM",
        pressure=5,
        pressure_unit="bar",
        temperature=400,
        temperature_unit="K",
        fittings=[
            {"type": "90_elbow_std", "quantity": 4},
            {"type": "gate_valve_open", "quantity": 2},
        ],
    )
    print_results(result, "Example 1: Air Flow")

    logger.info("\n" + "-" * 80)
    logger.info('Example 2: Syngas in 6" Schedule 40 pipe')
    logger.info("-" * 80)
    result = calculate_pressure_drop_syngas(
        pipe_size="6",
        pipe_schedule="40",
        pipe_length=50,
        flow_rate=2000,
        flow_unit="kg/h",
        pressure=25,
        temperature=800,
        fittings=[
            {"type": "90_elbow_std", "quantity": 2},
            {"type": "tee_through_run", "quantity": 1},
        ],
    )
    print_results(result, "Example 2: Syngas Flow")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
