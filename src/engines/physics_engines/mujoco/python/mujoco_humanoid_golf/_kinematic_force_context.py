from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

import mujoco
import numpy as np

if TYPE_CHECKING:
    from types import TracebackType


def check_mujoco_version() -> None:
    """Validate MuJoCo version meets minimum requirements."""
    try:
        version_str = mujoco.__version__
        major, minor, *_ = map(int, version_str.split("."))

        if (major, minor) < (3, 3):
            msg = (
                f"MuJoCo {version_str} detected, but 3.3.0+ is required.\n"
                "The reshaped Jacobian API (mj_jacBody with 2D arrays) was "
                "introduced in MuJoCo 3.3. Earlier versions use flat arrays "
                "which can cause dimension alignment errors.\n"
                "Please upgrade: pip install 'mujoco>=3.3.0,<4.0.0'\n"
                "See Issue F-003 in Assessment C for details."
            )
            raise ImportError(msg)

        import logging

        logger = logging.getLogger(__name__)
        logger.info("MuJoCo version %s validated successfully", version_str)
    except (AttributeError, ValueError) as exc:
        warnings.warn(
            f"Could not validate MuJoCo version: {exc}. "
            "Proceeding with fallback Jacobian handling.",
            category=UserWarning,
            stacklevel=2,
        )


class MjDataContext:
    """Context manager for safe MuJoCo MjData state isolation."""

    def __init__(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        if model is None:
            raise ValueError("model must be provided")
        self.model = model
        self.data = data
        self.qpos_backup: np.ndarray | None = None
        self.qvel_backup: np.ndarray | None = None
        self.qacc_backup: np.ndarray | None = None
        self.ctrl_backup: np.ndarray | None = None
        self.time_backup: float = 0.0

    def __enter__(self) -> mujoco.MjData:
        self.qpos_backup = self.data.qpos.copy()
        self.qvel_backup = self.data.qvel.copy()
        self.qacc_backup = self.data.qacc.copy()
        self.ctrl_backup = self.data.ctrl.copy()
        self.time_backup = self.data.time
        return self.data

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.data.qpos[:] = self.qpos_backup
        self.data.qvel[:] = self.qvel_backup
        self.data.qacc[:] = self.qacc_backup
        self.data.ctrl[:] = self.ctrl_backup
        self.data.time = self.time_backup
        mujoco.mj_forward(self.model, self.data)


@dataclass
class KinematicForceData:
    """Container for kinematic-dependent forces at a single time point."""

    time: float
    coriolis_forces: np.ndarray
    gravity_forces: np.ndarray
    centrifugal_forces: np.ndarray | None = None
    velocity_coupling_forces: np.ndarray | None = None
    club_head_coriolis_force: np.ndarray | None = None
    club_head_centrifugal_force: np.ndarray | None = None
    club_head_apparent_force: np.ndarray | None = None
    coriolis_power: float = 0.0
    centrifugal_power: float = 0.0
    rotational_kinetic_energy: float = 0.0
    translational_kinetic_energy: float = 0.0
