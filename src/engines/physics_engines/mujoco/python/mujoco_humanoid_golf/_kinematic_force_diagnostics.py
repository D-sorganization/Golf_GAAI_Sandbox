from __future__ import annotations

import warnings

import numpy as np

from src.shared.python.core.numerical_constants import EPSILON_SINGULARITY_DETECTION


def validate_effective_mass_direction(direction: np.ndarray) -> np.ndarray:
    """Return a normalized direction vector for effective-mass calculations."""
    direction_norm = np.linalg.norm(direction)
    if direction_norm < EPSILON_SINGULARITY_DETECTION:
        raise ValueError(
            f"Direction vector has near-zero magnitude: {direction_norm:.2e}. "
            "Cannot compute effective mass for zero-length direction."
        )
    return direction / direction_norm


def check_mass_matrix_conditioning(M: np.ndarray) -> None:
    """Warn or fail when the mass matrix is numerically unsafe."""
    M_cond = np.linalg.cond(M)
    if M_cond > 1e6:
        warnings.warn(
            f"Mass matrix is ill-conditioned: k(M) = {M_cond:.2e} > 1e6. "
            "Effective mass computation may be numerically unstable. "
            "This often indicates the robot is near a kinematic singularity.",
            category=UserWarning,
            stacklevel=2,
        )

    eigenvalues = np.linalg.eigvalsh(M)
    if np.any(eigenvalues <= 0):
        raise ValueError(
            "Mass matrix is not positive definite. "
            f"Minimum eigenvalue: {eigenvalues.min():.2e}. "
            "This indicates a modeling error or numerical instability."
        )


def check_jacobian_rank(jacp: np.ndarray) -> None:
    """Warn when the translational Jacobian loses rank."""
    jacobian_rank = np.linalg.matrix_rank(jacp)
    if jacobian_rank < 3:
        warnings.warn(
            f"Jacobian is rank deficient: rank={jacobian_rank} < 3. "
            "Robot has lost mobility in some directions. "
            "Effective mass may not be well-defined.",
            category=RuntimeWarning,
            stacklevel=2,
        )


def compute_effective_mass_value(
    direction: np.ndarray,
    jacp: np.ndarray,
    mass_matrix: np.ndarray,
) -> float:
    """Compute scalar effective mass along a normalized direction."""
    directed_jacobian = direction @ jacp
    mass_matrix_inverse = np.linalg.inv(mass_matrix)
    denominator = (
        directed_jacobian @ mass_matrix_inverse @ directed_jacobian.T
        + EPSILON_SINGULARITY_DETECTION
    )

    if abs(denominator) < 1e-8:
        warnings.warn(
            f"Effective mass denominator near zero: {denominator:.2e}. "
            "Robot is at or very close to a kinematic singularity in the "
            f"specified direction {direction}. Effective mass is extremely large.",
            category=UserWarning,
            stacklevel=2,
        )

    effective_mass = 1.0 / denominator

    if effective_mass < 0:
        raise ValueError(
            f"Computed negative effective mass: {effective_mass:.2e} kg. "
            "This indicates a numerical error or modeling issue."
        )

    if not np.isfinite(effective_mass):
        warnings.warn(
            f"Effective mass is non-finite: {effective_mass}. "
            "Robot is at a kinematic singularity. "
            "Returning large finite value instead.",
            category=UserWarning,
            stacklevel=2,
        )
        effective_mass = 1e10

    return float(effective_mass)
