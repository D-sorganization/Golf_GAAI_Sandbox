"""Wind and turbulence models for aerodynamics.

Layered wind model used by :class:`~src.shared.python.physics.aerodynamics.AerodynamicsEngine`:

- :class:`WindGust` — a single Poisson-spawned gust with a sin^2 envelope
- :class:`TurbulenceModel` — Perlin-like small-scale turbulence (sum of sinusoids)
- :class:`WindModel` — base wind + altitude gradient + gusts + turbulence

Reproducible via an optional ``seed`` argument on each stochastic component.
"""

from __future__ import annotations

import math

import numpy as np

from src.shared.python.physics.aerodynamics_config import WindConfig


class WindGust:
    """Single wind gust event with smooth envelope.

    A gust ramps up, holds at peak, then ramps down using
    a sinusoidal envelope for smooth transitions.
    """

    def __init__(
        self,
        start_time: float,
        duration: float,
        peak_velocity: np.ndarray,
    ) -> None:
        """Initialize gust event.

        Args:
            start_time: When gust begins [s]
            duration: Total gust duration [s]
            peak_velocity: Maximum gust velocity [m/s]
        """
        if start_time is None:
            raise ValueError("start_time must be provided")
        self.start_time = start_time
        self.duration = duration
        self.peak_velocity = peak_velocity

    @property
    def end_time(self) -> float:
        """Get gust end time."""
        return self.start_time + self.duration

    def get_velocity_at(self, t: float) -> np.ndarray:
        """Get gust velocity at time t.

        Uses a sinusoidal envelope for smooth transitions.

        Args:
            t: Time [s]

        Returns:
            Gust velocity at time t [m/s]
        """
        if t is None:
            raise ValueError("t must be provided")
        if t < self.start_time or t > self.end_time:
            return np.zeros(3)

        # Normalized time within gust (0 to 1)
        tau = (t - self.start_time) / self.duration

        # Sinusoidal envelope: sin^2 for smooth ramp up/down
        envelope = math.sin(math.pi * tau) ** 2

        return self.peak_velocity * envelope


class TurbulenceModel:
    """Small-scale atmospheric turbulence model.

    Uses Perlin-like noise for smooth, continuous turbulence.
    """

    def __init__(
        self,
        intensity: float = 0.5,
        seed: int | None = None,
    ) -> None:
        """Initialize turbulence model.

        Args:
            intensity: Turbulence intensity scale [m/s]
            seed: Random seed for reproducibility
        """
        if intensity is None:
            raise ValueError("intensity must be provided")
        self.intensity = intensity
        self._rng = np.random.default_rng(seed)
        # Pre-generate noise coefficients for smooth interpolation
        self._coeffs = self._rng.standard_normal((3, 10))
        self._phases = self._rng.uniform(0, 2 * np.pi, (3, 10))
        self._freqs = self._rng.uniform(0.1, 2.0, 10)

    def get_perturbation(
        self,
        t: float,
        position: np.ndarray,
    ) -> np.ndarray:
        """Get turbulence perturbation at given time and position.

        Args:
            t: Time [s]
            position: Position [m]

        Returns:
            Turbulence velocity perturbation [m/s]
        """
        if t is None:
            raise ValueError("t must be provided")
        if self.intensity < 1e-10:
            return np.zeros(3)

        # Sum of sinusoids at different frequencies (poor man's Perlin noise)
        perturbation = np.zeros(3)
        for i in range(3):
            for j, freq in enumerate(self._freqs):
                perturbation[i] += self._coeffs[i, j] * math.sin(
                    freq * t + self._phases[i, j]
                )

        # Normalize and scale
        perturbation = perturbation / len(self._freqs) * self.intensity  # type: ignore[assignment]

        return perturbation


class WindModel:
    """Sophisticated wind model with gusts and turbulence.

    Features:
    - Constant base wind
    - Random gusts with configurable intensity and frequency
    - Small-scale turbulence
    - Altitude-dependent wind gradient (wind shear)
    - Reproducible with seed
    """

    def __init__(
        self,
        config: WindConfig | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize wind model.

        Args:
            config: Wind configuration
            seed: Random seed for reproducibility
        """
        self.config = config or WindConfig()
        self._rng = np.random.default_rng(seed)
        self._gusts: list[WindGust] = []
        self._turbulence = TurbulenceModel(
            intensity=self.config.turbulence_intensity,
            seed=seed,
        )
        self._last_gust_time = -float("inf")
        self._last_check_time = -float("inf")
        self._dt_accumulator = 0.0  # Accumulate time for probabilistic spawning

    def get_wind_at(
        self,
        t: float,
        position: np.ndarray,
    ) -> np.ndarray:
        """Get wind velocity at given time and position.

        Args:
            t: Time [s]
            position: Position [m]

        Returns:
            Wind velocity [m/s]
        """
        # Start with base wind
        if t is None:
            raise ValueError("t must be provided")
        wind = self.config.base_velocity.copy()

        # Apply altitude gradient
        if self.config.altitude_gradient:
            altitude = max(0.0, position[2])
            gradient_multiplier = 1.0 + self.config.gradient_factor * (altitude / 10.0)
            wind = wind * gradient_multiplier

        # Add gusts
        if self.config.gusts_enabled:
            wind = wind + self._get_gust_contribution(t)

        # Add turbulence
        wind = wind + self._turbulence.get_perturbation(t, position)

        return wind

    def _get_gust_contribution(self, t: float) -> np.ndarray:
        """Get contribution from active gusts and possibly spawn new ones.

        Args:
            t: Time [s]

        Returns:
            Total gust velocity [m/s]
        """
        # Maybe spawn new gust
        if t is None:
            raise ValueError("t must be provided")
        self._maybe_spawn_gust(t)

        # Sum contributions from active gusts
        total = np.zeros(3)
        for gust in self._gusts:
            total = total + gust.get_velocity_at(t)

        # Clean up expired gusts
        self._gusts = [g for g in self._gusts if g.end_time > t]

        return total

    def _maybe_spawn_gust(self, t: float) -> None:
        """Possibly spawn a new gust event.

        Uses a Poisson process: expected gusts = frequency * time_elapsed.
        Accumulated time is used to properly handle irregular sampling.

        Args:
            t: Current time [s]
        """
        # Compute time since last check
        if t is None:
            raise ValueError("t must be provided")
        if self._last_check_time < 0:
            self._last_check_time = t
            dt = 0.1  # Initial time step assumption
        else:
            dt = t - self._last_check_time
            self._last_check_time = t

        if dt <= 0:
            return

        # Accumulate time for probabilistic spawning
        self._dt_accumulator += dt

        # Check spawning probability based on accumulated time
        # Expected gusts in accumulated time = frequency * accumulated_time
        spawn_probability = self.config.gust_frequency * self._dt_accumulator

        if self._rng.random() < spawn_probability:
            # Reset accumulator after spawn attempt
            self._dt_accumulator = 0.0

            # Generate random gust
            duration = self._rng.exponential(self.config.gust_duration_mean)
            duration = max(0.5, min(duration, 10.0))  # Clamp

            # Random direction perturbation
            base_speed = self.config.speed
            gust_speed = (
                base_speed * self.config.gust_intensity * self._rng.uniform(0.5, 1.5)
            )

            # Gust direction: mostly aligned with base wind, some random deviation
            base_dir = self.config.direction
            random_perturb = self._rng.standard_normal(3) * 0.3
            gust_dir = base_dir + random_perturb
            gust_dir = gust_dir / (np.linalg.norm(gust_dir) + 1e-10)

            gust = WindGust(
                start_time=t,
                duration=duration,
                peak_velocity=gust_dir * gust_speed,
            )
            self._gusts.append(gust)
            self._last_gust_time = t
        elif spawn_probability > 1.0:
            # If probability exceeds 1, reset to prevent unbounded growth
            self._dt_accumulator = 0.0


__all__ = ["TurbulenceModel", "WindGust", "WindModel"]
