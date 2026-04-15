"""Aerodynamic force models for golf ball flight.

Three orthogonal models — each computes exactly one force:

- :class:`DragModel` — air resistance with optional Reynolds-number correction
- :class:`LiftModel` — spin-induced lift (backspin effect)
- :class:`MagnusModel` — spin-induced lateral force (hook/slice)

All models accept SI units (m/s, rad/s, kg/m^3) and return N.
"""

from __future__ import annotations

import math

import numpy as np

from src.shared.python.core.physics_constants import (
    AIR_DENSITY_SEA_LEVEL_KG_M3,
    AIR_VISCOSITY_KG_M_S,
    GOLF_BALL_CROSS_SECTIONAL_AREA_M2,
    GOLF_BALL_DRAG_COEFFICIENT,
    GOLF_BALL_LIFT_COEFFICIENT,
    GOLF_BALL_RADIUS_M,
    MAGNUS_COEFFICIENT,
)


class DragModel:
    """Model for aerodynamic drag force.

    Drag opposes motion and scales with v^2:
        F_drag = -0.5 * rho * Cd * A * |v| * v

    The drag coefficient can optionally be corrected for Reynolds number,
    which accounts for the transition from laminar to turbulent flow
    around the golf ball's dimpled surface.
    """

    def __init__(
        self,
        base_coefficient: float = float(GOLF_BALL_DRAG_COEFFICIENT),
        ball_area: float = float(GOLF_BALL_CROSS_SECTIONAL_AREA_M2),
        ball_radius: float = float(GOLF_BALL_RADIUS_M),
        reynolds_correction: bool = True,
    ) -> None:
        """Initialize drag model.

        Args:
            base_coefficient: Base drag coefficient
            ball_area: Cross-sectional area [m^2]
            ball_radius: Ball radius [m]
            reynolds_correction: Apply Reynolds number correction
        """
        if base_coefficient is None:
            raise ValueError("base_coefficient must be provided")
        self.base_coefficient = base_coefficient
        self.ball_area = ball_area
        self.ball_radius = ball_radius
        self.reynolds_correction = reynolds_correction

    def calculate(
        self,
        velocity: np.ndarray,
        air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
    ) -> np.ndarray:
        """Calculate drag force.

        Args:
            velocity: Ball velocity relative to air [m/s]
            air_density: Air density [kg/m^3]

        Returns:
            Drag force vector [N]
        """
        if velocity is None:
            raise ValueError("velocity must be provided")
        speed = float(np.linalg.norm(velocity))
        if speed < 1e-10:
            return np.zeros(3)

        cd = self.get_effective_coefficient(velocity, air_density)
        force_magnitude = 0.5 * air_density * cd * self.ball_area * speed**2

        # Drag opposes velocity
        return -force_magnitude * velocity / speed

    def get_effective_coefficient(
        self,
        velocity: np.ndarray,
        air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
    ) -> float:
        """Get drag coefficient, optionally corrected for Reynolds number.

        The Reynolds correction modifies the base coefficient based on flow regime:
        - Laminar flow (low Re): higher effective Cd
        - Turbulent flow (high Re): base coefficient applies
        - Transition: smooth interpolation

        Args:
            velocity: Ball velocity [m/s]
            air_density: Air density [kg/m^3]

        Returns:
            Effective drag coefficient
        """
        if velocity is None:
            raise ValueError("velocity must be provided")
        if not self.reynolds_correction:
            return self.base_coefficient

        speed = float(np.linalg.norm(velocity))
        if speed < 1e-10:
            return self.base_coefficient

        # Reynolds number
        viscosity = float(AIR_VISCOSITY_KG_M_S)
        diameter = 2 * self.ball_radius
        re = air_density * speed * diameter / viscosity

        # Golf ball Cd variation with Re (empirical)
        # The base_coefficient is used as the turbulent value, with
        # higher values at lower Reynolds numbers (laminar flow)
        laminar_cd = 0.5  # Laminar flow coefficient
        turbulent_cd = self.base_coefficient  # User-specified turbulent coefficient

        if re < 8e4:
            return laminar_cd  # Laminar flow
        if re < 2e5:
            # Transition region - interpolate between laminar and turbulent
            fraction = (re - 8e4) / (2e5 - 8e4)
            return laminar_cd - fraction * (laminar_cd - turbulent_cd)
        return turbulent_cd  # Fully turbulent


class LiftModel:
    """Model for spin-induced lift force.

    Lift from backspin acts perpendicular to velocity in the
    plane defined by the spin axis and velocity vector.

        F_lift = 0.5 * rho * Cl * A * v^2 * lift_direction

    where lift_direction = normalize(spin_axis x velocity)
    """

    def __init__(
        self,
        base_coefficient: float = float(GOLF_BALL_LIFT_COEFFICIENT),
        ball_area: float = float(GOLF_BALL_CROSS_SECTIONAL_AREA_M2),
        ball_radius: float = float(GOLF_BALL_RADIUS_M),
        max_coefficient: float = 0.4,
    ) -> None:
        """Initialize lift model.

        Args:
            base_coefficient: Base lift coefficient
            ball_area: Cross-sectional area [m^2]
            ball_radius: Ball radius [m]
            max_coefficient: Maximum lift coefficient (saturation)
        """
        if base_coefficient is None:
            raise ValueError("base_coefficient must be provided")
        self.base_coefficient = base_coefficient
        self.ball_area = ball_area
        self.ball_radius = ball_radius
        self.max_coefficient = max_coefficient

    def calculate(
        self,
        velocity: np.ndarray,
        spin: np.ndarray,
        air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
    ) -> np.ndarray:
        """Calculate lift force from spin.

        Args:
            velocity: Ball velocity [m/s]
            spin: Angular velocity [rad/s]
            air_density: Air density [kg/m^3]

        Returns:
            Lift force vector [N]
        """
        if velocity is None:
            raise ValueError("velocity must be provided")
        speed = float(np.linalg.norm(velocity))
        spin_magnitude = float(np.linalg.norm(spin))

        if speed < 1e-10 or spin_magnitude < 1e-10:
            return np.zeros(3)

        # Lift direction: perpendicular to velocity, in spin plane
        spin_axis = spin / spin_magnitude
        lift_dir = np.cross(spin_axis, velocity)
        lift_norm = float(np.linalg.norm(lift_dir))

        if lift_norm < 1e-10:
            return np.zeros(3)

        lift_dir = lift_dir / lift_norm

        # Effective lift coefficient based on spin ratio
        spin_ratio = self.ball_radius * spin_magnitude / speed
        cl = self._compute_lift_coefficient(spin_ratio)

        # Lift magnitude
        force_magnitude = 0.5 * air_density * cl * self.ball_area * speed**2

        return force_magnitude * lift_dir

    def _compute_lift_coefficient(self, spin_ratio: float) -> float:
        """Compute lift coefficient based on spin ratio.

        Args:
            spin_ratio: Dimensionless spin parameter (omega*R/v)

        Returns:
            Lift coefficient
        """
        # Empirical relationship: Cl saturates at high spin
        if spin_ratio is None:
            raise ValueError("spin_ratio must be provided")
        cl = self.max_coefficient * (1 - math.exp(-spin_ratio / 0.1))
        return min(cl, self.max_coefficient)


class MagnusModel:
    """Model for Magnus force from spin.

    The Magnus effect creates a force perpendicular to both velocity
    and spin axis, causing hook/slice for sidespin.

        F_magnus = 0.5 * rho * Cm * A * v^2 * (spin x velocity) / |spin x velocity|
    """

    def __init__(
        self,
        coefficient: float = float(MAGNUS_COEFFICIENT),
        ball_area: float = float(GOLF_BALL_CROSS_SECTIONAL_AREA_M2),
        ball_radius: float = float(GOLF_BALL_RADIUS_M),
    ) -> None:
        """Initialize Magnus model.

        Args:
            coefficient: Magnus coefficient
            ball_area: Cross-sectional area [m^2]
            ball_radius: Ball radius [m]
        """
        if coefficient is None:
            raise ValueError("coefficient must be provided")
        self.coefficient = coefficient
        self.ball_area = ball_area
        self.ball_radius = ball_radius

    def calculate(
        self,
        velocity: np.ndarray,
        spin: np.ndarray,
        air_density: float = float(AIR_DENSITY_SEA_LEVEL_KG_M3),
    ) -> np.ndarray:
        """Calculate Magnus force.

        Args:
            velocity: Ball velocity [m/s]
            spin: Angular velocity [rad/s]
            air_density: Air density [kg/m^3]

        Returns:
            Magnus force vector [N]
        """
        if velocity is None:
            raise ValueError("velocity must be provided")
        speed = float(np.linalg.norm(velocity))
        spin_magnitude = float(np.linalg.norm(spin))

        if speed < 1e-10 or spin_magnitude < 1e-10:
            return np.zeros(3)

        # Magnus direction: spin x velocity
        magnus_dir = np.cross(spin, velocity)
        magnus_norm = float(np.linalg.norm(magnus_dir))

        if magnus_norm < 1e-10:
            return np.zeros(3)

        magnus_dir = magnus_dir / magnus_norm

        # Effective coefficient based on spin parameter
        spin_param = self.ball_radius * spin_magnitude / speed
        cm = self._compute_magnus_coefficient(spin_param)

        # Force magnitude
        force_magnitude = 0.5 * air_density * cm * self.ball_area * speed**2

        return force_magnitude * magnus_dir

    def _compute_magnus_coefficient(self, spin_param: float) -> float:
        """Compute Magnus coefficient based on spin parameter.

        Args:
            spin_param: Dimensionless spin parameter (omega*R/v)

        Returns:
            Magnus coefficient
        """
        # Approximately linear for small spin_param, saturates for large
        return self.coefficient * min(spin_param / 0.2, 1.0)


__all__ = ["DragModel", "LiftModel", "MagnusModel"]
