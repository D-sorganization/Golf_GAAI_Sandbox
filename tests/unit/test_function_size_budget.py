"""Unit tests for the per-function size budget CI check script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_script():
    """Load check_function_size_budget as a module for direct testing."""
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "check_function_size_budget.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_function_size_budget", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def script():
    """Return the loaded script module."""
    return _load_script()


class TestMeasureFunctions:
    """Tests for _measure_functions."""

    def test_returns_empty_for_file_with_no_functions(self, script, tmp_path):
        py_file = tmp_path / "empty.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        result = script._measure_functions(py_file)

        assert result == []

    def test_detects_short_function(self, script, tmp_path):
        py_file = tmp_path / "short.py"
        py_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        result = script._measure_functions(py_file)

        assert len(result) == 1
        name, lineno, length = result[0]
        assert name == "foo"
        assert lineno == 1
        assert length == 2

    def test_detects_long_function(self, script, tmp_path):
        lines = ["def big():\n"] + ["    x = 1\n"] * 60 + ["\n"]
        py_file = tmp_path / "big.py"
        py_file.write_text("".join(lines), encoding="utf-8")

        result = script._measure_functions(py_file)

        assert len(result) == 1
        name, lineno, length = result[0]
        assert name == "big"
        assert length >= 61

    def test_returns_empty_on_syntax_error(self, script, tmp_path):
        py_file = tmp_path / "broken.py"
        py_file.write_text("def (\n", encoding="utf-8")

        result = script._measure_functions(py_file)

        assert result == []

    def test_handles_async_functions(self, script, tmp_path):
        py_file = tmp_path / "async_fn.py"
        py_file.write_text("async def fetch():\n    return 1\n", encoding="utf-8")

        result = script._measure_functions(py_file)

        assert any(name == "fetch" for name, _, _ in result)


class TestCheckFile:
    """Tests for _check_file."""

    def test_no_violation_for_short_function(self, script, tmp_path):
        py_file = tmp_path / "ok.py"
        py_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        violations = script._check_file(py_file, {}, max_lines=50, repo_root=tmp_path)

        assert violations == []

    def test_reports_new_violation_when_not_in_baseline(self, script, tmp_path):
        lines = ["def huge():\n"] + ["    x = 1\n"] * 60
        py_file = tmp_path / "big.py"
        py_file.write_text("".join(lines), encoding="utf-8")

        violations = script._check_file(py_file, {}, max_lines=50, repo_root=tmp_path)

        assert len(violations) == 1
        assert "new violation" in violations[0]
        assert "huge" in violations[0]

    def test_no_violation_when_function_matches_baseline(self, script, tmp_path):
        lines = ["def big():\n"] + ["    x = 1\n"] * 60
        py_file = tmp_path / "big.py"
        py_file.write_text("".join(lines), encoding="utf-8")
        rel = "big.py"
        baseline = {f"{rel}:1:big": 61}

        violations = script._check_file(
            py_file, baseline, max_lines=50, repo_root=tmp_path
        )

        assert violations == []

    def test_violation_when_function_grows_beyond_baseline(self, script, tmp_path):
        lines = ["def big():\n"] + ["    x = 1\n"] * 80
        py_file = tmp_path / "big.py"
        py_file.write_text("".join(lines), encoding="utf-8")
        rel = "big.py"
        baseline = {f"{rel}:1:big": 60}

        violations = script._check_file(
            py_file, baseline, max_lines=50, repo_root=tmp_path
        )

        assert len(violations) == 1
        assert "grew beyond baseline" in violations[0]

    def test_handles_multiple_functions_independently(self, script, tmp_path):
        source = "def ok():\n    pass\n\ndef bad():\n" + "    x = 1\n" * 60
        py_file = tmp_path / "mixed.py"
        py_file.write_text(source, encoding="utf-8")

        violations = script._check_file(py_file, {}, max_lines=50, repo_root=tmp_path)

        assert len(violations) == 1
        assert "bad" in violations[0]


class TestLoadBaseline:
    """Tests for _load_baseline."""

    def test_returns_empty_dict_when_file_missing(self, script, tmp_path):
        missing = tmp_path / "missing.json"
        result = script._load_baseline(missing)
        assert result == {}

    def test_loads_valid_baseline(self, script, tmp_path):
        data = {"src/foo.py:10:bar": 75}
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text(json.dumps(data), encoding="utf-8")

        result = script._load_baseline(baseline_file)

        assert result == {"src/foo.py:10:bar": 75}


class TestShouldSkip:
    """Tests for _should_skip."""

    def test_skips_vendor_paths(self, script):
        assert script._should_skip(Path("vendor/some/module.py")) is True

    def test_skips_test_paths(self, script):
        assert script._should_skip(Path("tests/unit/test_foo.py")) is True

    def test_does_not_skip_src_paths(self, script):
        assert script._should_skip(Path("src/api/local_server.py")) is False

    def test_skips_pycache(self, script):
        assert script._should_skip(Path("src/__pycache__/foo.cpython-311.pyc")) is True
