"""Aerodynamics module for golf ball flight simulation.

This module provides sophisticated, tunable aerodynamic models that can be
toggled on/off for comparing trajectories with and without air resistance.

Design Principles (Pragmatic Programmer):
- Reversible: All effects can be toggled on/off at runtime
- Reusable: Modular components that compose well together
- DRY: Shared calculations extracted into helper functions
- Orthogonal: Independent components with no hidden coupling

The implementation is split across focused submodules and re-exported here
so existing ``from src.shared.python.physics.aerodynamics import ...`` call
sites keep working without modification:

- :mod:`.aerodynamics_config` — :class:`AerodynamicsConfig`, :class:`WindConfig`,
  :class:`RandomizationConfig`
- :mod:`.aerodynamics_forces` — :class:`DragModel`, :class:`LiftModel`,
  :class:`MagnusModel`
- :mod:`.aerodynamics_wind` — :class:`WindGust`, :class:`TurbulenceModel`,
  :class:`WindModel`
- :mod:`.aerodynamics_environment` — :class:`EnvironmentRandomizer`,
  :class:`EnvironmentSnapshot`

:class:`AerodynamicsEngine` remains here as the unified orchestrator.

References:
    - Bearman, P.W. & Harvey, J.K. (1976). Golf ball aerodynamics.
    - Smits, A.J. & Ogg, S. (2004). Golf ball aerodynamics. Physics Today.
    - Jorgensen, T. (1999). The Physics of Golf. Springer.
"""

from __future__ import annotations

import math

import numpy as np

from src.shared.python.core.contracts import precondition
from src.shared.python.core.physics_constants import AIR_DENSITY_SEA_LEVEL_KG_M3
from src.shared.python.physics.aerodynamics_config import (
    AerodynamicsConfig,
    RandomizationConfig,
    WindConfig,
)
from src.shared.python.physics.aerodynamics_environment import (
    EnvironmentRandomizer,
    EnvironmentSnapshot,
)
from src.shared.python.physics.aerodynamics_forces import (
    DragModel,
    LiftModel,
    MagnusModel,
)
from src.shared.python.physics.aerodynamics_wind import (
    TurbulenceModel,
    WindGust,
    WindModel,
)


class AerodynamicsEngine:
    """Unified aerodynamics calculation engine.

    Combines all aerodynamic force models with optional wind and
    environment randomization. All effects can be toggled on/off.

    Example:
        >>> config = AerodynamicsConfig(drag_enabled=True, lift_enabled=True)
        >>> engine = AerodynamicsEngine(config)
        >>> forces = engine.compute_forces(velocity, spin)
        >>> print(forces['total'])
    """

    def __init__(
        self,
        config: AerodynamicsConfig | None = None,
        wind_model: WindModel | None = None,
        randomization: EnvironmentRandomizer | None = None,
        air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
    ) -> None:
        """Initialize aerodynamics engine.

        Args:
            config: Aerodynamics configuration
            wind_model: Wind model for variable wind
            randomization: Environment randomizer
            air_density: Base air density [kg/m^3]
        """
        if air_density is None:
            raise ValueError("air_density must be provided")
        self.config = config or AerodynamicsConfig()
        self.wind_model = wind_model
        self.randomization = randomization
        self._base_air_density = air_density
        self._current_air_density = air_density

        # Initialize force models
        self._drag = DragModel(
            base_coefficient=self.config.drag_coefficient,
            ball_area=self.config.ball_area,
            ball_radius=self.config.ball_radius,
            reynolds_correction=self.config.reynolds_correction_enabled,
        )
        self._lift = LiftModel(
            base_coefficient=self.config.lift_coefficient,
            ball_area=self.config.ball_area,
            ball_radius=self.config.ball_radius,
        )
        self._magnus = MagnusModel(
            coefficient=self.config.magnus_coefficient,
            ball_area=self.config.ball_area,
            ball_radius=self.config.ball_radius,
        )

    @precondition(
        lambda self, velocity, spin, t=0.0, position=None, resample=False: (
            np.ndim(velocity) == 1 and len(velocity) == 3
        ),
        "velocity must be a 1-D array of length 3",
    )
    @precondition(
        lambda self, velocity, spin, t=0.0, position=None, resample=False: (
            np.ndim(spin) == 1 and len(spin) == 3
        ),
        "spin must be a 1-D array of length 3",
    )
    def compute_forces(
        self,
        velocity: np.ndarray,
        spin: np.ndarray,
        t: float = 0.0,
        position: np.ndarray | None = None,
        resample: bool = False,
    ) -> dict[str, np.ndarray]:
        """Compute all aerodynamic forces.

        Args:
            velocity: Ball velocity [m/s]
            spin: Angular velocity [rad/s]
            t: Current time [s] (for wind variation)
            position: Current position [m] (for wind gradient)
            resample: Resample random environment

        Returns:
            Dictionary with 'drag', 'lift', 'magnus', and 'total' forces [N]
        """
        if position is None:
            position = np.zeros(3)

        # Resample air density if randomization enabled
        if resample and self.randomization:
            self._current_air_density = self.randomization.randomize_air_density(
                self._base_air_density
            )

        # Get wind velocity
        wind = np.zeros(3)
        if self.wind_model:
            wind = self.wind_model.get_wind_at(t, position)

        # Relative velocity (ball velocity minus wind)
        rel_velocity = velocity - wind

        # Initialize forces
        drag = np.zeros(3)
        lift = np.zeros(3)
        magnus = np.zeros(3)

        # Compute active forces
        if self.config.is_drag_active():
            drag = self._drag.calculate(rel_velocity, self._current_air_density)

        if self.config.is_lift_active():
            lift = self._lift.calculate(rel_velocity, spin, self._current_air_density)

        if self.config.is_magnus_active():
            magnus = self._magnus.calculate(
                rel_velocity, spin, self._current_air_density
            )

        total = drag + lift + magnus

        return {
            "drag": drag,
            "lift": lift,
            "magnus": magnus,
            "total": total,
        }

    @precondition(
        lambda self, velocity, spin, mass, t=0.0, position=None, resample=False: (
            mass > 0
        ),
        "mass must be positive (non-zero, non-negative) to avoid ZeroDivisionError",
    )
    def compute_acceleration(
        self,
        velocity: np.ndarray,
        spin: np.ndarray,
        mass: float,
        t: float = 0.0,
        position: np.ndarray | None = None,
        resample: bool = False,
    ) -> np.ndarray:
        """Compute acceleration from aerodynamic forces.

        Args:
            velocity: Ball velocity [m/s]
            spin: Angular velocity [rad/s]
            mass: Ball mass [kg] — must be positive
            t: Current time [s]
            position: Current position [m]
            resample: Resample random environment

        Returns:
            Acceleration vector [m/s^2]

        Raises:
            PreconditionError: If mass <= 0
        """
        forces = self.compute_forces(velocity, spin, t, position, resample)
        return forces["total"] / mass

    def compute_spin_decay(
        self,
        spin: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """Compute spin decay over time step.

        Spin decays exponentially due to air resistance.

        Args:
            spin: Current angular velocity [rad/s]
            dt: Time step [s]

        Returns:
            Updated spin after decay [rad/s]
        """
        if spin is None:
            raise ValueError("spin must be provided")
        decay_factor = math.exp(-self.config.spin_decay_rate * dt)
        return spin * decay_factor


__all__ = [
    "AerodynamicsConfig",
    "AerodynamicsEngine",
    "DragModel",
    "EnvironmentRandomizer",
    "EnvironmentSnapshot",
    "LiftModel",
    "MagnusModel",
    "RandomizationConfig",
    "TurbulenceModel",
    "WindConfig",
    "WindGust",
    "WindModel",
]
