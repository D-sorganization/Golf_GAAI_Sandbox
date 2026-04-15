"""Unit tests for helpers extracted from ``run_adam_optimization`` (issue #142).

These tests focus on pure-input / pure-output properties of the
helpers added when decomposing the oversized ``run_adam_optimization``
function.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from src.shared.python.upstream_drift_tools.process_calculators import optimization
from src.shared.python.upstream_drift_tools.process_calculators.optimization import (
    OptimizationHistoryEntry,
    _AdamState,
    _build_optimization_results,
    _compute_finite_difference_gradient,
    _run_adam_loop,
)


def _make_state(values: list[float]) -> _AdamState:
    """Build a minimal ``_AdamState`` for testing helpers."""
    arr = np.array(values, dtype=float)
    names = [f"p{i}" for i in range(len(values))]
    return _AdamState(
        parameter_names=names,
        lower_bounds=np.zeros_like(arr),
        upper_bounds=np.ones_like(arr) * 10.0,
        values=arr.copy(),
        m=np.zeros_like(arr),
        v=np.zeros_like(arr),
        best_output=float("-inf"),
        best_parameters={},
        best_state={},
        best_composition={},
        history=[],
        previous_values=arr.copy(),
        base_params={},
        output_name="Temperature",
    )


class TestComputeFiniteDifferenceGradient:
    """Tests for ``_compute_finite_difference_gradient``."""

    def test_non_finite_objective_returns_zero_vector(self) -> None:
        st = _make_state([1.0, 2.0, 3.0])
        grad = _compute_finite_difference_gradient(
            st,
            objective=float("nan"),
            parameter_configs=[
                {"name": "p0", "min": 0.0, "max": 10.0, "initial": 1.0},
                {"name": "p1", "min": 0.0, "max": 10.0, "initial": 2.0},
                {"name": "p2", "min": 0.0, "max": 10.0, "initial": 3.0},
            ],
            gradient_step=0.1,
            engine=None,
            manual_hhv=100.0,
        )
        np.testing.assert_array_equal(grad, np.zeros(3))

    def test_returns_shape_matches_values(self) -> None:
        st = _make_state([1.0, 2.0])
        grad = _compute_finite_difference_gradient(
            st,
            objective=float("inf"),
            parameter_configs=[
                {"name": "p0", "min": 0.0, "max": 10.0, "initial": 1.0},
                {"name": "p1", "min": 0.0, "max": 10.0, "initial": 2.0},
            ],
            gradient_step=0.1,
            engine=None,
            manual_hhv=100.0,
        )
        assert grad.shape == st.values.shape

    def test_delegates_component_wise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[int] = []

        def fake_component(idx, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(idx)
            return float(idx + 1)

        monkeypatch.setattr(optimization, "_compute_gradient_component", fake_component)

        st = _make_state([0.0, 0.0, 0.0])
        configs = [
            {"name": "p0", "min": 0.0, "max": 10.0, "initial": 1.0},
            {"name": "p1", "min": 0.0, "max": 10.0, "initial": 2.0},
            {"name": "p2", "min": 0.0, "max": 10.0, "initial": 3.0},
        ]
        grad = _compute_finite_difference_gradient(
            st,
            objective=1.0,
            parameter_configs=configs,
            gradient_step=0.1,
            engine=None,
            manual_hhv=100.0,
        )
        assert calls == [0, 1, 2]
        np.testing.assert_array_equal(grad, np.array([1.0, 2.0, 3.0]))


class TestBuildOptimizationResults:
    """Tests for ``_build_optimization_results``."""

    def test_populated_state_returns_expected_fields(self) -> None:
        st = _make_state([1.0, 2.0])
        st.best_output = 42.0
        st.best_parameters = {"Temperature": 1.0}
        st.best_state = {"foo": 0.5}
        st.best_composition = {"H2O": 0.1}
        st.history.append(
            OptimizationHistoryEntry(iteration=1, objective=42.0, parameters={})
        )

        results = _build_optimization_results(st)

        assert results["best_output"] == 42.0
        assert results["best_parameters"] == {"Temperature": 1.0}
        assert results["best_state"] == {"foo": 0.5}
        assert results["best_composition"] == {"H2O": 0.1}
        assert results["iterations"] == 1

    def test_final_parameters_derived_from_values(self) -> None:
        st = _make_state([5.0, 6.0])
        st.parameter_names = ["Temperature", "Pressure"]
        results = _build_optimization_results(st)
        assert results["final_parameters"] == {"Temperature": 5.0, "Pressure": 6.0}

    def test_empty_history_zero_iterations(self) -> None:
        st = _make_state([1.0])
        results = _build_optimization_results(st)
        assert results["iterations"] == 0


class TestRunAdamLoop:
    """Tests for ``_run_adam_loop`` termination semantics."""

    def test_zero_gradient_terminates_first_iteration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        iterations_seen: list[int] = []

        def fake_evaluate(
            st: _AdamState,
            iteration: int,
            engine: Any,
            manual_hhv: float,
            maximize: bool,
        ) -> float:
            iterations_seen.append(iteration)
            st.history.append(
                OptimizationHistoryEntry(
                    iteration=iteration, objective=1.0, parameters={}
                )
            )
            return 1.0

        monkeypatch.setattr(optimization, "_evaluate_and_record", fake_evaluate)
        monkeypatch.setattr(
            optimization,
            "_compute_finite_difference_gradient",
            lambda *a, **k: np.zeros(2),
        )

        st = _make_state([1.0, 2.0])
        _run_adam_loop(
            st,
            engine=None,
            manual_hhv=100.0,
            parameter_configs=[
                {"name": "p0", "min": 0.0, "max": 10.0, "initial": 1.0},
                {"name": "p1", "min": 0.0, "max": 10.0, "initial": 2.0},
            ],
            maximize=True,
            learning_rate=0.1,
            beta1=0.9,
            beta2=0.999,
            epsilon=1e-8,
            gradient_step=0.1,
            max_iterations=5,
            tolerance=1e-6,
            gradient_tolerance=1e-6,
        )
        assert iterations_seen == [1]

    def test_respects_max_iterations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Runs the full budget when neither tolerance triggers.

        Use a large gradient (won't satisfy gradient tolerance) and a
        tiny learning rate (parameter delta below tolerance never holds
        for long because ``previous_values`` is updated each step, but
        we still need at least one iteration).
        """
        iterations_seen: list[int] = []

        def fake_evaluate(
            st: _AdamState,
            iteration: int,
            engine: Any,
            manual_hhv: float,
            maximize: bool,
        ) -> float:
            iterations_seen.append(iteration)
            return 1.0

        monkeypatch.setattr(optimization, "_evaluate_and_record", fake_evaluate)
        monkeypatch.setattr(
            optimization,
            "_compute_finite_difference_gradient",
            lambda *a, **k: np.array([10.0, 10.0]),
        )

        st = _make_state([0.0, 0.0])
        _run_adam_loop(
            st,
            engine=None,
            manual_hhv=100.0,
            parameter_configs=[
                {"name": "p0", "min": 0.0, "max": 10.0, "initial": 0.0},
                {"name": "p1", "min": 0.0, "max": 10.0, "initial": 0.0},
            ],
            maximize=True,
            learning_rate=1.0,
            beta1=0.9,
            beta2=0.999,
            epsilon=1e-8,
            gradient_step=0.1,
            max_iterations=3,
            tolerance=0.0,  # never triggers param-delta break
            gradient_tolerance=0.001,  # gradient (~14) always exceeds
        )
        assert iterations_seen == [1, 2, 3]
