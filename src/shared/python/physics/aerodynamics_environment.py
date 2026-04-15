"""Environment randomization for stochastic aerodynamics simulation.

Provides :class:`EnvironmentRandomizer` — Gaussian perturbation of air
density, temperature, and wind (speed + direction) — plus
:class:`EnvironmentSnapshot`, an immutable record of one randomized draw.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from src.shared.python.core.physics_constants import AIR_DENSITY_SEA_LEVEL_KG_M3
from src.shared.python.physics.aerodynamics_config import (
    RandomizationConfig,
    WindConfig,
)


@dataclass
class EnvironmentSnapshot:
    """Snapshot of randomized environment conditions.

    Provides consistent random values for a single simulation run.
    """

    air_density: float
    temperature: float
    wind_config: WindConfig | None = None


class EnvironmentRandomizer:
    """Randomize environment conditions for stochastic simulation.

    Provides reproducible randomization of:
    - Air density
    - Temperature
    - Wind speed and direction
    """

    def __init__(
        self,
        config: RandomizationConfig | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize randomizer.

        Args:
            config: Randomization configuration
            seed: Random seed for reproducibility
        """
        self.config = config or RandomizationConfig()
        self._rng = np.random.default_rng(seed)

    def randomize_air_density(self, base_density: float) -> float:
        """Randomize air density.

        Args:
            base_density: Base air density [kg/m^3]

        Returns:
            Randomized air density [kg/m^3]
        """
        if base_density is None:
            raise ValueError("base_density must be provided")
        if not self.config.enabled or self.config.air_density_variance <= 0:
            return base_density

        # Gaussian perturbation
        std = base_density * self.config.air_density_variance
        return float(self._rng.normal(base_density, std))

    def randomize_temperature(self, base_temperature: float) -> float:
        """Randomize temperature.

        Args:
            base_temperature: Base temperature [C]

        Returns:
            Randomized temperature [C]
        """
        if base_temperature is None:
            raise ValueError("base_temperature must be provided")
        if not self.config.enabled or self.config.temperature_variance <= 0:
            return base_temperature

        return float(
            self._rng.normal(base_temperature, self.config.temperature_variance)
        )

    def randomize_wind_config(self, base_config: WindConfig) -> WindConfig:
        """Randomize wind configuration.

        Args:
            base_config: Base wind configuration

        Returns:
            Randomized wind configuration
        """
        if base_config is None:
            raise ValueError("base_config must be provided")
        if not self.config.enabled:
            return base_config

        # Randomize speed
        base_speed = base_config.speed
        if self.config.wind_variance > 0 and base_speed > 0:
            speed_std = base_speed * self.config.wind_variance
            new_speed = float(self._rng.normal(base_speed, speed_std))
            new_speed = max(0.0, new_speed)  # Non-negative
        else:
            new_speed = base_speed

        # Randomize direction
        base_dir = base_config.direction
        if self.config.wind_direction_variance > 0:
            # Rotate by random angle
            angle = float(self._rng.normal(0, self.config.wind_direction_variance))
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            # Rotate in xy-plane
            new_dir = np.array(
                [
                    cos_a * base_dir[0] - sin_a * base_dir[1],
                    sin_a * base_dir[0] + cos_a * base_dir[1],
                    base_dir[2],
                ]
            )
        else:
            new_dir = base_dir

        new_velocity = new_dir * new_speed

        # Create new config with randomized velocity
        return WindConfig(
            base_velocity=new_velocity,
            gusts_enabled=base_config.gusts_enabled,
            gust_intensity=base_config.gust_intensity,
            gust_frequency=base_config.gust_frequency,
            gust_duration_mean=base_config.gust_duration_mean,
            turbulence_intensity=base_config.turbulence_intensity,
            altitude_gradient=base_config.altitude_gradient,
            gradient_factor=base_config.gradient_factor,
        )

    def create_snapshot(
        self,
        base_air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
        base_temperature: float = 15.0,
        base_wind_config: WindConfig | None = None,
    ) -> EnvironmentSnapshot:
        """Create a consistent randomized environment snapshot.

        Args:
            base_air_density: Base air density [kg/m^3]
            base_temperature: Base temperature [C]
            base_wind_config: Base wind configuration

        Returns:
            Randomized environment snapshot
        """
        return EnvironmentSnapshot(
            air_density=self.randomize_air_density(base_air_density),
            temperature=self.randomize_temperature(base_temperature),
            wind_config=(
                self.randomize_wind_config(base_wind_config)
                if base_wind_config
                else None
            ),
        )


__all__ = ["EnvironmentRandomizer", "EnvironmentSnapshot"]
