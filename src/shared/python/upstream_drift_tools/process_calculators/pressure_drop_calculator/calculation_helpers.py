"""Internal calculation helpers for the pressure drop interface.

Extracts pipe-geometry resolution, gas-and-flow normalisation, fitting list
building, and result formatting so that pressure_drop_interface.py can stay
focused on the public API contract.
"""

from __future__ import annotations

import logging
from typing import Any

from .models.pressure_drop_data_models import (
    GasComposition,
    PipeFitting,
)
from .utils.fitting_loss_coefficients import FITTING_K_FACTORS
from .utils.flow_rate_converter import convert_flow_rate_to_mass
from .utils.gas_properties import calculate_mixture_molecular_weight
from .utils.pipe_database import get_pipe_spec, get_roughness

logger = logging.getLogger(__name__)


def resolve_pipe_geometry(
    pipe_size: str | None,
    pipe_schedule: str | None,
    pipe_diameter: float | None,
    pipe_material: str,
    pipe_roughness: float | None,
) -> tuple[float, float]:
    """Resolve pipe internal diameter and roughness from user-supplied parameters.

    Args:
        pipe_size: Nominal pipe size string, or None if pipe_diameter supplied
        pipe_schedule: Pipe schedule string, or None if pipe_diameter supplied
        pipe_diameter: Explicit pipe ID in metres, or None
        pipe_material: Pipe material name (used to look up default roughness)
        pipe_roughness: Explicit roughness override in metres, or None

    Returns:
        Tuple of (diameter_m, roughness_m).
    """
    if pipe_material is None:
        raise ValueError("pipe_material must be provided")
    if pipe_diameter is None:
        if pipe_size is None or pipe_schedule is None:
            raise ValueError(
                "Either provide pipe_diameter or both pipe_size and pipe_schedule"
            )
        pipe_spec = get_pipe_spec(pipe_size, pipe_schedule, pipe_material)
        pipe_diameter = pipe_spec.get_id_meters()
        logger.info(
            f'Using {pipe_size}" Schedule {pipe_schedule}: ID = {pipe_diameter * 1000:.2f} mm'
        )

    roughness = (
        pipe_roughness
        if pipe_roughness is not None
        else get_roughness(pipe_material, "m")
    )
    return pipe_diameter, roughness


def _normalise_composition(
    gas_composition: dict[str, float] | None,
) -> GasComposition:
    """Return a normalised GasComposition, defaulting to pure Air."""
    if gas_composition is None:
        gas_composition = {"Air": 1.0}
        logger.info("Using default gas composition: Air")
    composition = GasComposition(components=gas_composition)
    composition.normalize()
    return composition


def resolve_gas_and_flow(
    flow_rate: float,
    flow_unit: str,
    gas_composition: dict[str, float] | None,
    temp_k: float,
    pressure_pa: float,
    compressibility_correction: bool,
    standard_condition: str,
) -> tuple[GasComposition, float]:
    """Normalise gas composition and convert flow rate to kg/s.

    Returns:
        Tuple of (normalised GasComposition, mass_flow_kg_s).
    """
    if flow_rate is None:
        raise ValueError("flow_rate must be provided")
    composition = _normalise_composition(gas_composition)
    molecular_weight = calculate_mixture_molecular_weight(composition.components)

    if flow_unit.upper() in ["ACFM", "CFM"]:
        mass_flow_kg_s = _convert_actual_volumetric(
            flow_rate,
            flow_unit,
            composition,
            temp_k,
            pressure_pa,
            compressibility_correction,
        )
    else:
        mass_flow_kg_s = convert_flow_rate_to_mass(
            flow_rate,
            flow_unit,
            molecular_weight,
            temperature=temp_k,
            pressure=pressure_pa,
            standard=standard_condition,
        )

    logger.info(f"Mass flow rate: {mass_flow_kg_s:.4f} kg/s ({flow_rate} {flow_unit})")
    return composition, mass_flow_kg_s


def _convert_actual_volumetric(
    flow_rate: float,
    flow_unit: str,
    composition: GasComposition,
    temp_k: float,
    pressure_pa: float,
    compressibility_correction: bool,
) -> float:
    """Convert actual volumetric flow (ACFM/CFM) to kg/s."""
    from .utils.flow_rate_converter import volumetric_actual_to_mass
    from .utils.gas_properties import calculate_gas_properties

    props = calculate_gas_properties(
        composition.components, temp_k, pressure_pa, compressibility_correction
    )
    return volumetric_actual_to_mass(flow_rate, flow_unit, props["density"], "kg/s")


def build_fitting_list(
    fittings: list[dict[str, str | int | float]] | None,
) -> list[PipeFitting]:
    """Convert raw fitting specification dicts into PipeFitting objects.

    Args:
        fittings: Optional list of dicts with 'type', 'quantity', and
                  optional 'k_factor' keys

    Returns:
        List of PipeFitting instances.
    """
    fitting_list: list[PipeFitting] = []
    if fittings:
        for fitting_dict in fittings:
            fitting_type = str(fitting_dict.get("type", ""))
            quantity = int(fitting_dict.get("quantity", 1))
            k_factor = float(
                fitting_dict.get("k_factor", FITTING_K_FACTORS.get(fitting_type, 0.0))
            )
            fitting_list.append(
                PipeFitting(
                    fitting_type=fitting_type, quantity=quantity, k_factor=k_factor
                )
            )
    return fitting_list


def format_results(results: Any) -> dict[str, Any]:
    """Format engine results into a comprehensive output dictionary.

    Args:
        results: PressureDropResults object from the calculation engine

    Returns:
        Dictionary of pressure drop values in multiple unit systems plus
        flow characteristics and safety metrics.
    """
    return {
        "pressure_drop_pa": results.total_pressure_drop,
        "pressure_drop_bar": results.total_pressure_drop / 1e5,
        "pressure_drop_psi": results.total_pressure_drop / 6894.76,
        "pressure_drop_kpa": results.total_pressure_drop / 1000.0,
        "friction_loss_pa": results.friction_pressure_drop,
        "friction_loss_bar": results.friction_pressure_drop / 1e5,
        "fitting_loss_pa": results.fitting_pressure_drop,
        "fitting_loss_bar": results.fitting_pressure_drop / 1e5,
        "elevation_loss_pa": results.elevation_pressure_drop,
        "outlet_pressure_pa": results.outlet_pressure,
        "outlet_pressure_bar": results.outlet_pressure / 1e5,
        "outlet_pressure_psi": results.outlet_pressure / 6894.76,
        "friction_factor": results.friction_factor,
        "reynolds_number": results.flow_properties.reynolds_number,
        "flow_velocity_m_s": results.flow_properties.velocity,
        "flow_velocity_ft_s": results.flow_properties.velocity * 3.28084,
        "mach_number": results.flow_properties.mach_number,
        "flow_regime": results.flow_regime,
        "density_kg_m3": results.flow_properties.density,
        "viscosity_pa_s": results.flow_properties.viscosity,
        "compressibility_factor": results.flow_properties.compressibility_factor,
        "molecular_weight": results.flow_properties.molecular_weight,
        "erosional_velocity_m_s": results.erosional_velocity,
        "erosion_ratio": results.erosion_ratio,
        "erosion_ratio_percent": results.erosion_ratio * 100,
        "pressure_drop_per_100ft_pa": results.pressure_drop_per_100ft,
        "velocity_pressure_pa": results.velocity_pressure,
        "warnings": results.warnings,
    }


__all__ = [
    "build_fitting_list",
    "format_results",
    "resolve_gas_and_flow",
    "resolve_pipe_geometry",
]
