"""Unit tests for helpers extracted from ``_render_o2_safety_tab`` (issue #142).

``_render_o2_safety_tab`` was decomposed into smaller pieces, of which the
pure-Python helpers (the sensitivity sweep and the highlight function) are
covered here. UI helpers that depend on ``streamlit`` are only smoke-tested.
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
pytest.importorskip("pandas")

import numpy as np
import pandas as pd

from src.shared.python.upstream_drift_tools.process_calculators.psa_package import (
    psa_webapp,
)


def _default_components() -> list[psa_webapp.ComponentData]:
    """Return a small valid PSA component list including O2."""
    return [
        psa_webapp.ComponentData(
            name="H2", feed_pct=60.0, stage1_removal_pct=20.0, stage2_removal_pct=15.0
        ),
        psa_webapp.ComponentData(
            name="CO", feed_pct=30.0, stage1_removal_pct=98.0, stage2_removal_pct=99.0
        ),
        psa_webapp.ComponentData(
            name="O2", feed_pct=1.0, stage1_removal_pct=80.0, stage2_removal_pct=99.0
        ),
        psa_webapp.ComponentData(
            name="N2", feed_pct=9.0, stage1_removal_pct=95.0, stage2_removal_pct=99.0
        ),
    ]


class TestComputeO2SensitivityTable:
    def test_table_shape(self) -> None:
        s1_range = np.linspace(50, 95, 5)
        inlets = [0.5, 1.0, 2.0, 5.0]
        df = psa_webapp._compute_o2_sensitivity_table(
            total_feed=1000.0,
            components=_default_components(),
            s1_removal_range=s1_range,
            inlet_o2_values=inlets,
        )
        assert isinstance(df, pd.DataFrame)
        # 5 rows (one per S1 removal) and 1 + 4 columns (the S1 axis + inlets)
        assert len(df) == 5
        assert list(df.columns) == [
            "S1 O2 Removal (%)",
            *[f"{v}% Inlet" for v in inlets],
        ]

    def test_values_are_numeric_and_finite(self) -> None:
        s1_range = np.linspace(50, 95, 3)
        df = psa_webapp._compute_o2_sensitivity_table(
            total_feed=1000.0,
            components=_default_components(),
            s1_removal_range=s1_range,
            inlet_o2_values=[1.0, 5.0],
        )
        for col in df.columns:
            assert df[col].dtype.kind in {"f", "i"}
            assert np.isfinite(df[col].to_numpy()).all()

    def test_higher_s1_removal_reduces_tail_o2(self) -> None:
        s1_range = np.array([50.0, 95.0])
        df = psa_webapp._compute_o2_sensitivity_table(
            total_feed=1000.0,
            components=_default_components(),
            s1_removal_range=s1_range,
            inlet_o2_values=[1.0],
        )
        first, second = df["1.0% Inlet"].iloc[0], df["1.0% Inlet"].iloc[1]
        # Increasing Stage-1 O2 removal must not increase tail O2.
        assert second <= first


class TestO2HighlightDanger:
    def test_above_2_percent_is_red(self) -> None:
        assert psa_webapp._o2_highlight_danger(2.5) == "background-color: #ffcccc"

    def test_between_1_5_and_2_is_yellow(self) -> None:
        assert psa_webapp._o2_highlight_danger(1.75) == "background-color: #ffffcc"

    def test_at_or_below_1_5_returns_empty(self) -> None:
        assert psa_webapp._o2_highlight_danger(1.5) == ""
        assert psa_webapp._o2_highlight_danger(0.0) == ""

    def test_non_numeric_returns_empty(self) -> None:
        # The helper is called with DataFrame cell values; strings / None must not raise.
        assert psa_webapp._o2_highlight_danger("N/A") == ""  # type: ignore[arg-type]


class TestRenderO2SafetyTab:
    def test_requires_total_feed(self) -> None:
        with pytest.raises(ValueError):
            psa_webapp._render_o2_safety_tab(
                total_feed=None, components=_default_components()
            )  # type: ignore[arg-type]
