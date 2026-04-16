"""Display and reporting helpers for the pressure drop calculator.

This module contains all human-readable output functions (table printing,
help text, reference listings, and result formatting).  Separating these
from the calculation logic keeps pressure_drop_interface.py focused on
validation and orchestration.
"""

from __future__ import annotations

import logging
from typing import Any

from ..engine.pressure_drop_calculation_engine import (
    friction_factor_churchill,
    friction_factor_colebrook,
    friction_factor_haaland,
    friction_factor_swamee_jain,
)
from ..utils.fitting_loss_coefficients import FITTING_K_FACTORS
from ..utils.flow_rate_converter import (
    MASS_FLOW_CONVERSIONS,
    MOLAR_FLOW_CONVERSIONS,
    STANDARD_CONDITIONS,
    VOLUMETRIC_FLOW_CONVERSIONS_TO_M3_S,
)
from ..utils.gas_properties import GAS_DATABASE
from ..utils.pipe_database import (
    MATERIAL_ROUGHNESS,
    list_available_sizes,
    list_schedules_for_size,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference / listing helpers
# ---------------------------------------------------------------------------

_HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║               ADVANCED PRESSURE DROP CALCULATOR - QUICK REFERENCE            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  BASIC USAGE:                                                                ║
║  ─────────────                                                               ║
║    result = calculate_pressure_drop(                                         ║
║        pipe_size="4", pipe_schedule="40",     # Use standard pipe OR         ║
║        pipe_diameter=0.1,                      # specify diameter (m)        ║
║        pipe_length=100,                        # meters                      ║
║        flow_rate=1000, flow_unit='kg/h',      # flow with units             ║
║        pressure=10, pressure_unit='bar',       # inlet pressure             ║
║        temperature=500, temperature_unit='K',  # inlet temperature          ║
║        gas_composition={'H2': 0.3, 'CO': 0.7}, # optional (default: air)    ║
║    )                                                                         ║
║                                                                              ║
║  AVAILABLE PIPE SIZES:                                                       ║
║    1/2, 3/4, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24 inches       ║
║                                                                              ║
║  AVAILABLE SCHEDULES:                                                        ║
║    5S, 10S, 40, STD, 80, XS, 120, 160, XXS                                   ║
║                                                                              ║
║  GAS COMPONENTS:                                                             ║
║    H2, CO, CO2, CH4, C2H6, C2H4, N2, O2, H2O, Ar, H2S, NH3, Air             ║
║                                                                              ║
║  FLOW RATE UNITS:                                                            ║
║    Mass:    kg/s, kg/h, lb/hr, ton/h, g/s                                   ║
║    Molar:   mol/s, kmol/h, lbmol/hr                                         ║
║    Volume:  m³/h, SCFM, CFM, Nm³/h, L/s, L/min, ft³/min                     ║
║                                                                              ║
║  FRICTION METHODS:                                                           ║
║    'colebrook'   - Most accurate (default)                                  ║
║    'swamee-jain' - Fast, ~1% of Colebrook                                   ║
║    'churchill'   - All flow regimes                                         ║
║    'haaland'     - Simple, ~1.5% accuracy                                   ║
║                                                                              ║
║  FITTING TYPES (examples):                                                   ║
║    90_elbow_std, 90_elbow_long, 45_elbow_std                                ║
║    tee_through_branch, tee_through_run                                       ║
║    gate_valve_open, globe_valve_open, ball_valve_open                       ║
║    check_valve_swing, butterfly_valve_open                                   ║
║    entrance_sharp, exit_sharp                                                ║
║                                                                              ║
║  HELPER FUNCTIONS:                                                           ║
║    show_help()           - Display this help                                ║
║    list_gas_components() - Show available gas components                    ║
║    list_fittings()       - Show available fittings with K-factors           ║
║    list_pipe_sizes()     - Show available pipe sizes                        ║
║    list_flow_units()     - Show available flow rate units                   ║
║    list_materials()      - Show pipe materials and roughness values         ║
║    compare_friction_methods() - Compare friction factor correlations        ║
║    validate_inputs()     - Validate inputs before calculation               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


def show_help() -> None:
    """Display comprehensive help with available options and examples."""
    logger.info(_HELP_TEXT)


def list_gas_components() -> dict[str, dict[str, Any]]:
    """List all available gas components with their properties.

    Returns:
        Dictionary of gas components with MW, Tc, Pc, and acentric factor
    """
    components = {}
    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                    AVAILABLE GAS COMPONENTS                        ║"
    )
    logger.info("╠═════════════╦═══════════╦══════════╦═══════════╦══════════════════╣")
    logger.info("║ Component   ║  MW       ║   Tc (K) ║  Pc (bar) ║ Acentric Factor  ║")
    logger.info("╠═════════════╬═══════════╬══════════╬═══════════╬══════════════════╣")

    for name, props in sorted(GAS_DATABASE.items()):
        logger.info(
            f"║ {name:11s} ║ {props.molecular_weight:9.3f} ║ {props.critical_temp:8.1f} ║"
            f" {props.critical_pressure / 1e5:9.2f} ║ {props.acentric_factor:16.3f} ║"
        )
        components[name] = {
            "molecular_weight": props.molecular_weight,
            "critical_temp": props.critical_temp,
            "critical_pressure": props.critical_pressure,
            "acentric_factor": props.acentric_factor,
        }

    logger.info("╚═════════════╩═══════════╩══════════╩═══════════╩══════════════════╝")
    return components


def list_fittings(category: str | None = None) -> dict[str, float]:
    """List available fittings with their K-factors.

    Args:
        category: Optional filter ('elbow', 'tee', 'valve', 'entrance', 'exit', 'bend')

    Returns:
        Dictionary of fitting types and K-factors
    """
    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                    AVAILABLE FITTINGS (K-factors)                  ║"
    )
    logger.info("╠══════════════════════════════════════════╦═════════╦══════════════╣")
    logger.info("║ Fitting Type                             ║ K-factor║  Category    ║")
    logger.info("╠══════════════════════════════════════════╬═════════╬══════════════╣")

    result = {}
    categories = {
        "elbow": ["elbow", "miter"],
        "tee": ["tee"],
        "valve": ["valve"],
        "entrance": ["entrance"],
        "exit": ["exit"],
        "bend": ["bend"],
        "reducer": ["reducer", "expander"],
    }

    for fitting_type, k_factor in sorted(FITTING_K_FACTORS.items()):
        cat = _classify_fitting(fitting_type, categories)
        if category and cat != category:
            continue

        result[fitting_type] = k_factor
        name = fitting_type.replace("_", " ").title()
        logger.info(f"║ {name:40s} ║ {k_factor:7.2f} ║ {cat:12s} ║")

    logger.info("╚══════════════════════════════════════════╩═════════╩══════════════╝")
    logger.info(
        "\nNote: K-factors are for fully turbulent flow in standard pipe sizes."
    )
    logger.info("      Use Two-K method for more accuracy in small pipes/low Re flows.")
    return result


def _classify_fitting(fitting_type: str, categories: dict[str, list[str]]) -> str:
    """Return the category label for a fitting type string."""
    for cat_name, keywords in categories.items():
        if any(kw in fitting_type for kw in keywords):
            return cat_name
    return "other"


def list_pipe_sizes() -> dict[str, list[str]]:
    """List available standard pipe sizes and schedules.

    Returns:
        Dictionary mapping pipe sizes to available schedules
    """
    sizes = list_available_sizes()
    result = {}

    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                    AVAILABLE PIPE SIZES (ASME B36.10M)             ║"
    )
    logger.info("╠═══════════════════════════════════════════════════════════════════╣")

    for size in sizes:
        schedules = list_schedules_for_size(size)
        result[size] = schedules
        sch_str = ", ".join(schedules)
        logger.info(f"║ NPS {size:5s} : {sch_str:56s}║")

    logger.info("╚═══════════════════════════════════════════════════════════════════╝")
    return result


def list_flow_units() -> dict[str, list[str]]:
    """List all available flow rate units.

    Returns:
        Dictionary of unit categories and available units
    """
    _log_flow_units_header()
    mass_units = list(MASS_FLOW_CONVERSIONS.keys())
    molar_units = list(MOLAR_FLOW_CONVERSIONS.keys())
    vol_units = _log_volumetric_units()
    _log_standard_conditions()
    logger.info("╚═══════════════════════════════════════════════════════════════════╝")

    return {
        "mass": mass_units,
        "molar": molar_units,
        "volumetric": vol_units,
        "standard_conditions": list(STANDARD_CONDITIONS.keys()),
    }


def _log_flow_units_header() -> None:
    """Log the flow units table header."""
    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                    AVAILABLE FLOW RATE UNITS                       ║"
    )
    logger.info("╠═══════════════════════════════════════════════════════════════════╣")

    logger.info(
        "║ MASS FLOW UNITS:                                                   ║"
    )
    mass_units = list(MASS_FLOW_CONVERSIONS.keys())
    logger.info(f"║   {', '.join(mass_units):63s}║")

    logger.info(
        "║                                                                    ║"
    )
    logger.info(
        "║ MOLAR FLOW UNITS:                                                  ║"
    )
    molar_units = list(MOLAR_FLOW_CONVERSIONS.keys())
    logger.info(f"║   {', '.join(molar_units):63s}║")


def _log_volumetric_units() -> list[str]:
    """Log the volumetric units rows and return the unit list."""
    logger.info(
        "║                                                                    ║"
    )
    logger.info(
        "║ VOLUMETRIC FLOW UNITS:                                             ║"
    )
    vol_units = list(VOLUMETRIC_FLOW_CONVERSIONS_TO_M3_S.keys())
    vol_str = ", ".join(vol_units)
    while len(vol_str) > 63:
        idx = vol_str[:63].rfind(",")
        logger.info(f"║   {vol_str[: idx + 1]:63s}║")
        vol_str = vol_str[idx + 2 :]
    logger.info(f"║   {vol_str:63s}║")
    return vol_units


def _log_standard_conditions() -> None:
    """Log the standard conditions rows."""
    logger.info(
        "║                                                                    ║"
    )
    logger.info(
        "║ STANDARD CONDITIONS FOR VOLUMETRIC FLOWS:                          ║"
    )
    for name, (T, P, desc) in STANDARD_CONDITIONS.items():
        logger.info(f"║   {name:6s}: T={T:.2f}K, P={P:.0f}Pa - {desc:34s}║")


def list_materials() -> dict[str, dict[str, float]]:
    """List available pipe materials with roughness values.

    Returns:
        Dictionary of materials with roughness values
    """
    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                    PIPE MATERIAL ROUGHNESS VALUES                  ║"
    )
    logger.info(
        "╠═══════════════════════════════════╦═════════════╦══════════════════╣"
    )
    logger.info(
        "║ Material                          ║  ε (mm)     ║  ε (m)           ║"
    )
    logger.info(
        "╠═══════════════════════════════════╬═════════════╬══════════════════╣"
    )

    result = {}
    for material, (roughness_mm, _roughness_ft, _desc) in sorted(
        MATERIAL_ROUGHNESS.items()
    ):
        result[material] = {
            "roughness_mm": roughness_mm,
            "roughness_m": roughness_mm / 1000,
        }
        logger.info(
            f"║ {material:33s} ║ {roughness_mm:11.4f} ║ {roughness_mm / 1000:16.6f} ║"
        )

    logger.info(
        "╚═══════════════════════════════════╩═════════════╩══════════════════╝"
    )
    return result


def _log_friction_rows(f_colebrook: float, re: float, eps: float) -> dict[str, float]:
    """Log all four friction-factor method rows and return their values."""
    results: dict[str, float] = {"colebrook": f_colebrook}
    logger.info(
        f"║ Colebrook-White (iterative)       ║ {f_colebrook:.6f}  ║ (reference)         ║"
    )
    for label, f_val in [
        ("Swamee-Jain (explicit)", friction_factor_swamee_jain(re, eps)),
        ("Churchill (all regimes)", friction_factor_churchill(re, eps)),
        ("Haaland (simplified)", friction_factor_haaland(re, eps)),
    ]:
        key = label.split()[0].lower()
        results[key] = f_val
        diff = (f_val / f_colebrook - 1) * 100
        logger.info(f"║ {label:33s} ║ {f_val:.6f}  ║ {diff:+.2f}%              ║")
    return results


def compare_friction_methods(
    reynolds_number: float,
    relative_roughness: float = 0.0001,
) -> dict[str, float]:
    """Compare friction factor correlations for given conditions.

    Args:
        reynolds_number: Reynolds number
        relative_roughness: ε/D ratio (default 0.0001)

    Returns:
        Dictionary of friction factors from each method

    Example:
        >>> compare_friction_methods(100000, 0.001)
    """
    if reynolds_number is None:
        raise ValueError("reynolds_number must be provided")
    _log_friction_comparison_header(reynolds_number, relative_roughness)
    f_colebrook = friction_factor_colebrook(reynolds_number, relative_roughness)
    results = _log_friction_rows(f_colebrook, reynolds_number, relative_roughness)
    logger.info(
        "╚═══════════════════════════════════╩═══════════╩═════════════════════╝"
    )
    _log_flow_regime(reynolds_number)
    return results


def _log_friction_comparison_header(
    reynolds_number: float, relative_roughness: float
) -> None:
    """Log the friction method comparison table header."""
    logger.info(
        "\n╔═══════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        "║                 FRICTION FACTOR METHOD COMPARISON                  ║"
    )
    logger.info(
        f"║  Re = {reynolds_number:.0f}, ε/D = {relative_roughness:.6f}".ljust(68) + "║"
    )
    logger.info(
        "╠═══════════════════════════════════╦═══════════╦═════════════════════╣"
    )
    logger.info(
        "║ Method                            ║ f         ║ Δ from Colebrook    ║"
    )
    logger.info(
        "╠═══════════════════════════════════╬═══════════╬═════════════════════╣"
    )


def _log_flow_regime(reynolds_number: float) -> None:
    """Log the flow regime classification and notes."""
    if reynolds_number < 2300:
        regime = "Laminar"
    elif reynolds_number < 4000:
        regime = "Transitional"
    else:
        regime = "Turbulent"
    logger.info(f"\nFlow regime: {regime}")
    if reynolds_number < 4000:
        logger.info("Note: For transitional flow, Churchill method is recommended.")


# ---------------------------------------------------------------------------
# Result printing helpers
# ---------------------------------------------------------------------------


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap text to specified width.

    Args:
        text: Text to wrap
        width: Maximum line width

    Returns:
        List of wrapped lines
    """
    if text is None:
        raise ValueError("text must be provided")
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= width:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines or [""]


def print_summary_section(results: dict[str, Any]) -> None:
    """Log the pressure-drop summary section."""
    logger.info("\n┌" + "─" * 78 + "┐")
    logger.info("│" + " SUMMARY ".center(78) + "│")
    logger.info("├" + "─" * 78 + "┤")
    logger.info(
        f"│  Total Pressure Drop:  {results['pressure_drop_bar']:10.4f} bar  "
        f"│  {results['pressure_drop_psi']:10.4f} psi  │  {results['pressure_drop_kpa']:10.2f} kPa  │"
    )
    logger.info(
        f"│  Outlet Pressure:      {results['outlet_pressure_bar']:10.4f} bar  "
        f"│  {results['outlet_pressure_psi']:10.4f} psi  │                 │"
    )
    logger.info("└" + "─" * 78 + "┘")


def print_breakdown_section(results: dict[str, Any]) -> None:
    """Log the pressure-drop breakdown by component."""

    def safe_percent(num: float, denom: float) -> float:
        return (num / denom * 100) if denom != 0 else 0.0

    logger.info("\n┌" + "─" * 78 + "┐")
    logger.info("│" + " PRESSURE DROP BREAKDOWN ".center(78) + "│")
    logger.info("├" + "─" * 38 + "┬" + "─" * 19 + "┬" + "─" * 19 + "┤")
    logger.info(
        "│  Component                           │     Value (bar)   │    Percentage   │"
    )
    logger.info("├" + "─" * 38 + "┼" + "─" * 19 + "┼" + "─" * 19 + "┤")

    dp_total = results["pressure_drop_pa"]
    friction_pct = safe_percent(results["friction_loss_pa"], dp_total)
    fitting_pct = safe_percent(results["fitting_loss_pa"], dp_total)
    elevation_pct = safe_percent(results["elevation_loss_pa"], dp_total)

    logger.info(
        f"│  Friction (pipe wall)                │ {results['friction_loss_bar']:17.6f} │ {friction_pct:15.1f}% │"
    )
    logger.info(
        f"│  Fittings & valves                   │ {results['fitting_loss_bar']:17.6f} │ {fitting_pct:15.1f}% │"
    )
    if abs(results["elevation_loss_pa"]) > 0.1:
        logger.info(
            f"│  Elevation change                    │ {results['elevation_loss_pa'] / 1e5:17.6f} │ {elevation_pct:15.1f}% │"
        )
    logger.info("└" + "─" * 38 + "┴" + "─" * 19 + "┴" + "─" * 19 + "┘")


def print_flow_and_gas_sections(results: dict[str, Any]) -> None:
    """Log flow characteristics and gas property sections."""
    logger.info("\n┌" + "─" * 78 + "┐")
    logger.info("│" + " FLOW CHARACTERISTICS ".center(78) + "│")
    logger.info("├" + "─" * 38 + "┬" + "─" * 39 + "┤")
    logger.info(
        f"│  Flow Velocity:     {results['flow_velocity_m_s']:10.2f} m/s   │  {results['flow_velocity_ft_s']:10.2f} ft/s                  │"
    )
    logger.info(
        f"│  Reynolds Number:   {results['reynolds_number']:10.0f}        │  Flow Regime: {results['flow_regime']:18s}   │"
    )
    logger.info(
        f"│  Mach Number:       {results['mach_number']:10.4f}        │  Friction Factor: {results['friction_factor']:14.6f}   │"
    )
    logger.info("└" + "─" * 38 + "┴" + "─" * 39 + "┘")

    logger.info("\n┌" + "─" * 78 + "┐")
    logger.info("│" + " GAS PROPERTIES ".center(78) + "│")
    logger.info("├" + "─" * 38 + "┬" + "─" * 39 + "┤")
    logger.info(
        f"│  Density:           {results['density_kg_m3']:10.4f} kg/m³  │  Molecular Weight: {results['molecular_weight']:12.2f} kg/kmol│"
    )
    logger.info(
        f"│  Viscosity:         {results['viscosity_pa_s'] * 1e6:10.4f} µPa·s  │  Compressibility (Z): {results['compressibility_factor']:10.4f}     │"
    )
    logger.info("└" + "─" * 38 + "┴" + "─" * 39 + "┘")


def print_safety_section(results: dict[str, Any]) -> None:
    """Log the safety metrics section."""
    logger.info("\n┌" + "─" * 78 + "┐")
    logger.info("│" + " SAFETY METRICS ".center(78) + "│")
    logger.info("├" + "─" * 38 + "┬" + "─" * 39 + "┤")

    erosion_ratio = results["erosion_ratio_percent"]
    erosion_status = _erosion_status_label(erosion_ratio)

    logger.info(
        f"│  Erosional Velocity: {results['erosional_velocity_m_s']:9.2f} m/s   │  Status: {erosion_status:26s}  │"
    )
    logger.info(
        f"│  Erosion Ratio:      {erosion_ratio:9.1f} %     │  (Velocity/Erosional limit)         │"
    )
    logger.info("└" + "─" * 38 + "┴" + "─" * 39 + "┘")


def _erosion_status_label(erosion_ratio_percent: float) -> str:
    """Return a human-readable erosion status label."""
    if erosion_ratio_percent < 50:
        return "✅ SAFE"
    if erosion_ratio_percent < 80:
        return "⚠️  CAUTION"
    return "❌ DANGER"


def print_warnings_and_recommendations(
    results: dict[str, Any], show_recommendations: bool
) -> None:
    """Log warnings and engineering recommendations."""
    if results is None:
        raise ValueError("results must be provided")
    if results.get("warnings"):
        warnings = results["warnings"]
        if isinstance(warnings, list) and len(warnings) > 0:
            logger.info("\n┌" + "─" * 78 + "┐")
            logger.warning("│" + " ⚠️  WARNINGS ".center(78) + "│")
            logger.info("├" + "─" * 78 + "┤")
            for warning in warnings:
                for line in wrap_text(warning, 74):
                    logger.info(f"│  {line:74s}  │")
            logger.info("└" + "─" * 78 + "┘")

    if show_recommendations:
        recommendations = generate_recommendations(results)
        if recommendations:
            logger.info("\n┌" + "─" * 78 + "┐")
            logger.info("│" + " 💡 RECOMMENDATIONS ".center(78) + "│")
            logger.info("├" + "─" * 78 + "┤")
            for rec in recommendations:
                for line in wrap_text(rec, 74):
                    logger.info(f"│  {line:74s}  │")
            logger.info("└" + "─" * 78 + "┘")


def print_results(
    results: dict[str, Any],
    title: str = "PRESSURE DROP CALCULATION RESULTS",
    show_recommendations: bool = True,
) -> None:
    """Print results in a beautifully formatted table with recommendations.

    Args:
        results: Results dictionary from calculate_pressure_drop
        title: Title for the output
        show_recommendations: Whether to show engineering recommendations
    """
    if results is None:
        raise ValueError("results must be provided")
    logger.info("\n" + "═" * 80)
    logger.info(f"  {title}  ".center(80, "═"))
    logger.info("═" * 80)

    print_summary_section(results)
    print_breakdown_section(results)
    print_flow_and_gas_sections(results)
    print_safety_section(results)
    print_warnings_and_recommendations(results, show_recommendations)

    logger.info("═" * 80 + "\n")


def _pressure_drop_recommendation(results: dict[str, Any]) -> str | None:
    """Return a recommendation if the pressure drop ratio is high, else None."""
    dp_ratio = results["pressure_drop_pa"] / (
        results["outlet_pressure_pa"] + results["pressure_drop_pa"]
    )
    if dp_ratio > 0.20:
        return (
            f"High pressure drop ({dp_ratio * 100:.0f}% of inlet). Consider: larger pipe "
            "diameter, shorter pipe run, or fewer fittings."
        )
    return None


def _erosion_recommendation(erosion_ratio: float) -> str | None:
    """Return an erosion recommendation string, or None if safe."""
    if erosion_ratio > 0.8:
        return (
            "Velocity exceeds 80% of erosional limit. Consider larger pipe diameter to "
            "reduce velocity and extend pipe life."
        )
    if erosion_ratio > 0.5:
        return (
            "Velocity is 50-80% of erosional limit. Monitor pipe condition and consider "
            "velocity reduction for longer service life."
        )
    return None


def generate_recommendations(results: dict[str, Any]) -> list[str]:
    """Generate engineering recommendations based on calculation results.

    Args:
        results: Results dictionary from calculate_pressure_drop

    Returns:
        List of recommendation strings
    """
    recs: list[str] = []

    if (r := _pressure_drop_recommendation(results)) is not None:
        recs.append(r)
    if (r := _erosion_recommendation(results["erosion_ratio"])) is not None:
        recs.append(r)
    if results["fitting_loss_pa"] > results["friction_loss_pa"]:
        recs.append(
            "Fitting losses exceed pipe friction. Consider using long-radius elbows, "
            "full-port valves, or reducing number of fittings."
        )
    if results["mach_number"] > 0.3:
        recs.append(
            f"High Mach number ({results['mach_number']:.3f}). Compressibility effects "
            "significant. Verify calculations and consider acoustic vibration analysis."
        )
    if results["reynolds_number"] < 4000:
        recs.append(
            f"Low Reynolds number ({results['reynolds_number']:.0f}). Flow may be transitional "
            "or laminar - friction factor has higher uncertainty in this regime."
        )
    if results["reynolds_number"] > 1e7:
        recs.append(
            f"Very high Reynolds number ({results['reynolds_number']:.0e}). Ensure turbulent "
            "flow correlations are valid. Consider CFD analysis for critical applications."
        )
    return recs


__all__ = [
    "compare_friction_methods",
    "generate_recommendations",
    "list_fittings",
    "list_flow_units",
    "list_gas_components",
    "list_materials",
    "list_pipe_sizes",
    "print_breakdown_section",
    "print_flow_and_gas_sections",
    "print_results",
    "print_safety_section",
    "print_summary_section",
    "print_warnings_and_recommendations",
    "show_help",
    "wrap_text",
]
