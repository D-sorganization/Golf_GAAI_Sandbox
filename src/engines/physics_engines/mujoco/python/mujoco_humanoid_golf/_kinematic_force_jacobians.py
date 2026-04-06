from __future__ import annotations

import mujoco
import numpy as np


def find_body_id(model: mujoco.MjModel, name_pattern: str) -> int | None:
    """Find body ID by name pattern."""
    if not (name_pattern is not None):
        raise ValueError("name_pattern must be provided")
    for body_index in range(model.nbody):
        body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_index)
        if body_name and name_pattern.lower() in body_name.lower():
            return body_index
    return None


def initialize_jacobian_buffers(
    model: mujoco.MjModel, data: mujoco.MjData
) -> tuple[bool, np.ndarray, np.ndarray]:
    """Allocate Jacobian buffers matching the active MuJoCo API."""
    nv = model.nv
    try:
        jacp = np.zeros((3, nv))
        jacr = np.zeros((3, nv))
        mujoco.mj_jacBody(model, data, jacp, jacr, 0)
        return True, jacp, jacr
    except TypeError:
        return False, np.zeros(3 * nv), np.zeros(3 * nv)


def compute_body_jacobian(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_id: int,
    jacp_buffer: np.ndarray,
    jacr_buffer: np.ndarray,
    use_reshaped_arrays: bool,
    nv: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute a body's translational and rotational Jacobians."""
    if not (body_id is not None):
        raise ValueError("body_id must be provided")

    mujoco.mj_jacBody(model, data, jacp_buffer, jacr_buffer, body_id)
    if use_reshaped_arrays:
        return jacp_buffer, jacr_buffer
    return jacp_buffer.reshape(3, nv), jacr_buffer.reshape(3, nv)
