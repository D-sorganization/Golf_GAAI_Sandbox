"""Flare Calculator
===============

Core calculation engine for flare system design and analysis.
"""

import math
from dataclasses import dataclass
from typing import Final

from .constants import (
    BAR_TO_PA,
    FLARE_BASE_EFFICIENCY,
    FLARE_CO_EFFICIENCY_PENALTY,
    FLARE_CO_THRESHOLD,
    FLARE_COLD_TEMP_K,
    FLARE_COLD_TEMP_PENALTY,
    FLARE_FLAME_EMISSIVITY,
    FLARE_H2_EFFICIENCY_BOOST,
    FLARE_H2_THRESHOLD,
    FLARE_H2S_EFFICIENCY_PENALTY,
    FLARE_H2S_THRESHOLD,
    FLARE_HOT_TEMP_BOOST,
    FLARE_HOT_TEMP_K,
    FLARE_MAX_EFFICIENCY,
    FLARE_MAX_EXIT_VELOCITY,
    FLARE_MIN_EFFICIENCY,
    FLARE_MIN_HEIGHT,
    FLARE_SAFE_RADIATION_INTENSITY,
    G_MOL_TO_KG_MOL,
    R_UNIVERSAL,
    RADIATION_COMFORT,
    RADIATION_DAMAGE,
    RADIATION_LETHAL,
    RADIATION_SAFE,
    SECONDS_PER_HOUR,
)

# Standard Gas Properties (Molecular Weight [g/mol], Heating Value [kJ/kg], Cp [kJ/kg-K])
GAS_PROPERTIES: Final[dict[str, dict[str, float]]] = {
    "H2": {"mw": 2.016, "hv": 119930, "cp": 14.3},
    "CO": {"mw": 28.01, "hv": 10100, "cp": 1.04},
    "CH4": {"mw": 16.04, "hv": 50010, "cp": 2.22},
    "C2H6": {"mw": 30.07, "hv": 47520, "cp": 1.75},
    "C3H8": {"mw": 44.10, "hv": 46360, "cp": 1.67},
    "C4H10": {"mw": 58.12, "hv": 45720, "cp": 1.66},
    "H2S": {"mw": 34.08, "hv": 16500, "cp": 1.05},
    "N2": {"mw": 28.01, "hv": 0, "cp": 1.04},
    "CO2": {"mw": 44.01, "hv": 0, "cp": 0.84},
    "H2O": {"mw": 18.02, "hv": 0, "cp": 1.87},
}


@dataclass
class FlareDesign:
    """Flare design parameters."""

    height: float  # m
    diameter: float  # m
    exit_velocity: float  # m/s
    heat_release: float  # kW
    radiation_intensity: float  # kW/m²


class FlareCalculator:
    """Core flare calculation engine."""

    def __init__(self) -> None:
        """Initialize the flare calculator."""
        self.gas_properties = GAS_PROPERTIES

    def _normalize_composition(
        self, gas_composition: dict[str, float]
    ) -> dict[str, float]:
        """Normalize mole composition to fractions summing to 1 (or all zero)."""
        total_comp = sum(gas_composition.values())
        if total_comp == 0:
            return dict.fromkeys(gas_composition, 0.0)
        return {k: v / total_comp for k, v in gas_composition.items()}

    def _compute_mixture_properties(
        self, comp_fractions: dict[str, float]
    ) -> tuple[float, float]:
        """Compute mixture molecular weight (g/mol) and heating value (kJ/kg)."""
        mix_mw = sum(
            comp_fractions[gas] * self.gas_properties[gas]["mw"]
            for gas in comp_fractions
        )
        mix_hv = sum(
            comp_fractions[gas] * self.gas_properties[gas]["hv"]
            for gas in comp_fractions
        )
        return mix_mw, mix_hv

    def _compute_gas_density(
        self, mix_mw: float, temperature: float, pressure: float
    ) -> float:
        """Compute gas density [kg/m³] from Ideal Gas Law; fallback 1.0 if T<=0."""
        pressure_pa = pressure * BAR_TO_PA  # bar to Pa
        mix_mw_kg = mix_mw / G_MOL_TO_KG_MOL  # g/mol to kg/mol

        if temperature > 0:
            return pressure_pa / ((R_UNIVERSAL / mix_mw_kg) * temperature)
        return 1.0  # Fallback

    def _compute_flare_diameter(
        self, total_flow: float, gas_density: float, target_velocity: float
    ) -> float:
        """Compute flare stack diameter [m] from mass flow, density and exit velocity."""
        mass_flow_kg_s = total_flow / SECONDS_PER_HOUR
        if gas_density > 0 and target_velocity > 0:
            area = mass_flow_kg_s / (gas_density * target_velocity)
            return math.sqrt(4 * area / math.pi)
        return 0.0

    def _compute_flare_height(
        self, heat_release: float, target_radiation: float
    ) -> float:
        """Compute flare height [m] from point source radiation model,
        clamped to the configured minimum."""
        emissivity = FLARE_FLAME_EMISSIVITY  # Typical for clean hydrocarbon flames
        if target_radiation > 0:
            height = math.sqrt(
                emissivity * heat_release / (4 * math.pi * target_radiation)
            )
        else:
            height = 0.0
        return max(height, FLARE_MIN_HEIGHT)

    @staticmethod
    def _validate_flare_inputs(
        total_flow: float,
        gas_composition: dict[str, float],
        temperature: float,
        pressure: float,
    ) -> None:
        """Validate flare sizing preconditions (DbC)."""
        assert total_flow > 0, f"total_flow must be positive, got {total_flow}"
        assert temperature > 0, f"temperature must be positive (K), got {temperature}"
        assert pressure > 0, f"pressure must be positive (bar), got {pressure}"
        assert len(gas_composition) > 0, "gas_composition must not be empty"

    @staticmethod
    def _validate_flare_result(result: FlareDesign) -> None:
        """Validate flare sizing postconditions (DbC)."""
        assert result.height >= FLARE_MIN_HEIGHT, (
            f"Flare height must be >= minimum ({FLARE_MIN_HEIGHT}), got {result.height}"
        )
        assert result.diameter >= 0, (
            f"Flare diameter must be non-negative, got {result.diameter}"
        )

    def calculate_flare_size(
        self,
        total_flow: float,  # kg/hr
        gas_composition: dict[str, float],  # mol %
        temperature: float,  # K
        pressure: float,  # bar
    ) -> FlareDesign:
        """Calculate flare size based on flow conditions.

        Args:
            total_flow: Total gas flow rate (kg/hr)
            gas_composition: Gas composition (mol%)
            temperature: Gas temperature (K)
            pressure: Gas pressure (bar)

        Returns:
            FlareDesign object with calculated parameters
        """
        self._validate_flare_inputs(total_flow, gas_composition, temperature, pressure)

        comp_fractions = self._normalize_composition(gas_composition)
        mix_mw, mix_hv = self._compute_mixture_properties(comp_fractions)
        heat_release = total_flow * mix_hv / SECONDS_PER_HOUR
        gas_density = self._compute_gas_density(mix_mw, temperature, pressure)

        target_velocity = FLARE_MAX_EXIT_VELOCITY  # m/s
        target_radiation = FLARE_SAFE_RADIATION_INTENSITY  # kW/m²

        result = FlareDesign(
            height=self._compute_flare_height(heat_release, target_radiation),
            diameter=self._compute_flare_diameter(
                total_flow, gas_density, target_velocity
            ),
            exit_velocity=target_velocity,
            heat_release=heat_release,
            radiation_intensity=target_radiation,
        )
        self._validate_flare_result(result)
        return result

    def calculate_radiation_zones(self, flare_design: FlareDesign) -> dict[str, float]:
        """Calculate radiation zones around the flare.

        Args:
            flare_design: Flare design parameters

        Returns:
            Dictionary with zone distances (m)
        """
        assert flare_design is not None, "flare_design must be provided"
        assert flare_design is not None, "flare_design must be provided"
        zones = {
            "lethal": 0.0,  # 37.5 kW/m²
            "damage": 0.0,  # 12.5 kW/m²
            "safe": 0.0,  # 1.6 kW/m²
            "comfort": 0.0,  # 0.5 kW/m²
        }

        emissivity = FLARE_FLAME_EMISSIVITY
        heat_release = flare_design.heat_release

        # Calculate distances for each radiation level
        radiation_levels = {
            "lethal": RADIATION_LETHAL,
            "damage": RADIATION_DAMAGE,
            "safe": RADIATION_SAFE,
            "comfort": RADIATION_COMFORT,
        }

        for zone, level in radiation_levels.items():
            if level > 0:
                # Distance based on point source model
                distance = math.sqrt(emissivity * heat_release / (4 * math.pi * level))
                zones[zone] = distance

        return zones

    def calculate_combustion_efficiency(
        self,
        gas_composition: dict[str, float],
        temperature: float,
        pressure: float,
    ) -> float:
        """Calculate combustion efficiency.

        Args:
            gas_composition: Gas composition (mol%)
            temperature: Gas temperature (K)
            pressure: Gas pressure (bar)

        Returns:
            Combustion efficiency (0-1)
        """
        # Simplified efficiency calculation
        assert gas_composition is not None, "gas_composition must be provided"
        assert gas_composition is not None, "gas_composition must be provided"
        efficiency = FLARE_BASE_EFFICIENCY  # Base efficiency

        # Normalize factors
        total = sum(gas_composition.values()) or 1.0

        # Factors based on mole fractions
        h2_frac = gas_composition.get("H2", 0) / total
        co_frac = gas_composition.get("CO", 0) / total
        h2s_frac = gas_composition.get("H2S", 0) / total

        if h2_frac > FLARE_H2_THRESHOLD:
            efficiency += FLARE_H2_EFFICIENCY_BOOST

        if co_frac > FLARE_CO_THRESHOLD:
            efficiency -= FLARE_CO_EFFICIENCY_PENALTY

        if h2s_frac > FLARE_H2S_THRESHOLD:
            efficiency -= FLARE_H2S_EFFICIENCY_PENALTY

        # Temperature effects
        if temperature < FLARE_COLD_TEMP_K:
            efficiency -= FLARE_COLD_TEMP_PENALTY
        elif temperature > FLARE_HOT_TEMP_K:
            efficiency += FLARE_HOT_TEMP_BOOST

        return max(FLARE_MIN_EFFICIENCY, min(FLARE_MAX_EFFICIENCY, efficiency))
