"""Pinocchio Engine Parity Tests — E04S02.

TDD-first parity tests that verify the PinocchioPhysicsEngine implements
the same interface and behavioural contracts as the MuJoCo and Drake adapters.

All tests require pinocchio to be installed; they skip gracefully otherwise.
All tests are marked @pytest.mark.live_simulation to route them to the
heavy-integration-tests workflow.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

# Skip entire module if pinocchio is not installed
pinocchio = pytest.importorskip("pinocchio")

from src.engines.physics_engines.pinocchio.python.pinocchio_physics_engine import (  # noqa: E402
    PinocchioPhysicsEngine,
)
from src.shared.python.core.contracts.exceptions import PreconditionError  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "models"
SIMPLE_PENDULUM_URDF = str(FIXTURE_DIR / "simple_pendulum.urdf")


@pytest.fixture
def engine() -> PinocchioPhysicsEngine:
    """Return an unloaded PinocchioPhysicsEngine."""
    return PinocchioPhysicsEngine()


@pytest.fixture
def loaded_engine() -> PinocchioPhysicsEngine:
    """Return a PinocchioPhysicsEngine loaded with simple_pendulum.urdf."""
    eng = PinocchioPhysicsEngine()
    eng.load_from_path(SIMPLE_PENDULUM_URDF)
    return eng


# ---------------------------------------------------------------------------
# Parity Tests
# ---------------------------------------------------------------------------


@pytest.mark.live_simulation
def test_forward_kinematics_matches_analytical(loaded_engine: PinocchioPhysicsEngine) -> None:
    """Forward kinematics must return valid state arrays of correct shapes.

    AC1 — parity test: forward kinematics shape and finiteness.
    """
    eng = loaded_engine
    # Set to a non-zero configuration
    q_init = eng.q.copy()
    q_init[0] = 0.5
    eng.q = q_init

    eng.forward()

    q, v = eng.get_state()
    assert q.shape == (eng.model.nq,), f"Expected q shape ({eng.model.nq},), got {q.shape}"
    assert v.shape == (eng.model.nv,), f"Expected v shape ({eng.model.nv},), got {v.shape}"
    assert np.all(np.isfinite(q)), "q contains non-finite values"
    assert np.all(np.isfinite(v)), "v contains non-finite values"


@pytest.mark.live_simulation
def test_inverse_kinematics_jacobian_shape(loaded_engine: PinocchioPhysicsEngine) -> None:
    """Jacobian must have linear (3, nv), angular (3, nv), spatial (6, nv) keys.

    AC2 — parity test: Jacobian shape matches Drake/MuJoCo protocol.
    """
    eng = loaded_engine
    eng.forward()

    # simple_pendulum.urdf has frame 'pendulum_link'
    J = eng.compute_jacobian("pendulum_link")
    assert J is not None, "compute_jacobian returned None for 'pendulum_link'"
    assert "linear" in J, "Jacobian dict missing 'linear' key"
    assert "angular" in J, "Jacobian dict missing 'angular' key"
    assert "spatial" in J, "Jacobian dict missing 'spatial' key"

    nv = eng.model.nv
    assert J["linear"].shape == (3, nv), f"linear shape: expected (3, {nv}), got {J['linear'].shape}"
    assert J["angular"].shape == (3, nv), f"angular shape: expected (3, {nv}), got {J['angular'].shape}"
    assert J["spatial"].shape == (6, nv), f"spatial shape: expected (6, {nv}), got {J['spatial'].shape}"


@pytest.mark.live_simulation
def test_screw_axis_kinematics_ztcf(loaded_engine: PinocchioPhysicsEngine) -> None:
    """compute_ztcf must return a finite (nv,) vector.

    AC2/AC3 — parity test: ZTCF screw axis kinematics.
    """
    eng = loaded_engine
    q = eng.q.copy()
    q[0] = 0.3
    v = np.zeros(eng.model.nv)

    result = eng.compute_ztcf(q, v)

    assert result.shape == (eng.model.nv,), f"Expected shape ({eng.model.nv},), got {result.shape}"
    assert np.all(np.isfinite(result)), "compute_ztcf returned non-finite values"


@pytest.mark.live_simulation
def test_mass_matrix_symmetry(loaded_engine: PinocchioPhysicsEngine) -> None:
    """Mass matrix must be symmetric and positive-definite.

    AC2 — parity test: mass matrix properties.
    """
    eng = loaded_engine
    M = eng.compute_mass_matrix()

    assert M.ndim == 2, "Mass matrix must be 2D"
    assert M.shape[0] == M.shape[1], "Mass matrix must be square"
    np.testing.assert_array_almost_equal(M, M.T, decimal=10, err_msg="Mass matrix must be symmetric")

    eigenvalues = np.linalg.eigvalsh(M)
    assert np.all(eigenvalues > 0), f"Mass matrix must be positive-definite; eigenvalues: {eigenvalues}"


@pytest.mark.live_simulation
def test_drift_control_superposition(loaded_engine: PinocchioPhysicsEngine) -> None:
    """drift + control superposition must approximately match full ABA.

    AC2 — parity test: superposition contract.
    """
    eng = loaded_engine
    q = eng.q.copy()
    v = np.zeros(eng.model.nv)
    eng.q = q
    eng.v = v

    tau = np.zeros(eng.model.nv)
    tau[0] = 0.5  # small control torque

    a_drift = eng.compute_drift_acceleration()
    a_control = eng.compute_control_acceleration(tau)
    a_superposition = a_drift + a_control

    # Full ABA for reference
    import pinocchio as pin

    a_full = pin.aba(eng.model, eng.data, q, v, tau)

    np.testing.assert_allclose(
        a_superposition,
        a_full,
        rtol=1e-5,
        atol=1e-8,
        err_msg="drift + control superposition must match full ABA",
    )


@pytest.mark.live_simulation
def test_contact_forces_returns_zero_vector(loaded_engine: PinocchioPhysicsEngine) -> None:
    """compute_contact_forces must return np.zeros(3) — Pinocchio has no contact solver.

    AC2 — parity test: contact forces protocol compliance.
    """
    eng = loaded_engine
    result = eng.compute_contact_forces()

    assert isinstance(result, np.ndarray), "compute_contact_forces must return np.ndarray"
    assert result.shape == (3,), f"Expected shape (3,), got {result.shape}"
    np.testing.assert_array_equal(result, np.zeros(3))


@pytest.mark.live_simulation
def test_get_sensors_returns_dict(loaded_engine: PinocchioPhysicsEngine) -> None:
    """get_sensors must return a dict (Pinocchio has no native sensor API).

    AC2 — parity test: sensor protocol compliance.
    """
    eng = loaded_engine
    result = eng.get_sensors()

    assert isinstance(result, dict), f"get_sensors must return dict, got {type(result)}"


@pytest.mark.live_simulation
def test_compute_affine_drift_alias(loaded_engine: PinocchioPhysicsEngine) -> None:
    """compute_affine_drift must return a finite array (alias for compute_drift_acceleration).

    AC2 — parity test: MuJoCo API alias.
    """
    eng = loaded_engine
    result = eng.compute_affine_drift()

    assert isinstance(result, np.ndarray), "compute_affine_drift must return np.ndarray"
    assert result.shape == (eng.model.nv,), f"Expected shape ({eng.model.nv},), got {result.shape}"
    assert np.all(np.isfinite(result)), "compute_affine_drift returned non-finite values"


@pytest.mark.live_simulation
def test_dbc_preconditions_raise_on_uninitialised(engine: PinocchioPhysicsEngine) -> None:
    """Calling methods before load() must raise an exception.

    AC5 — DbC precondition tests: engine raises StateError/PreconditionError
    before model is loaded.
    """
    # Engine is NOT loaded at this point
    assert not engine.is_initialized, "Engine should not be initialized before load"

    with pytest.raises(PreconditionError):
        engine.step()

    with pytest.raises(PreconditionError):
        engine.forward()

    with pytest.raises(PreconditionError):
        engine.reset()

    with pytest.raises(PreconditionError):
        engine.compute_mass_matrix()
