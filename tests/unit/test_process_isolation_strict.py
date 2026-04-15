"""Process isolation tests for strict unit-level physics engine adapters.

This module executes mock-driven Drake and Pinocchio adapter tests in separate
Python processes to avoid 'numpy' corruption caused by incompatible
C-extension mocking/reloading within a single pytest session (Issue #496).
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Paths to the isolated unit test files
ISOLATED_TESTS_DIR = Path(__file__).parent / "isolated"
TEST_DRAKE_STRICT = ISOLATED_TESTS_DIR / "test_drake_strict.py"
TEST_PINOCCHIO_STRICT = ISOLATED_TESTS_DIR / "test_pinocchio_strict.py"


class TestProcessIsolationStrict:
    """Run specific strict unit tests in isolated subprocesses."""

    def run_isolated_test(self, test_file: Path) -> None:
        """Helper to run pytest on a single file in a subprocess."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            str(test_file),
            "-v",
        ]

        import os

        env = os.environ.copy()
        env.pop("MUJOCO_GL", None)

        # Capture output to help debugging if it fails
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # We check returncode manually for better error reporting
                env=env,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            pytest.fail(
                f"Isolated test {test_file.name} timed out after {exc.timeout}s.\n"
                f"--- STDOUT ---\n{exc.stdout or ''}\n"
                f"--- STDERR ---\n{exc.stderr or ''}"
            )

        if result.returncode != 0:
            pytest.fail(
                f"Isolated test {test_file.name} failed with exit code {result.returncode}.\n"
                f"--- STDOUT ---\n{result.stdout}\n"
                f"--- STDERR ---\n{result.stderr}"
            )

    def test_drake_strict_isolated(self):
        """Run Drake strict tests in an isolated process to prevent numpy corruption."""
        if not TEST_DRAKE_STRICT.exists():
            pytest.fail(f"Test file not found: {TEST_DRAKE_STRICT}")
        self.run_isolated_test(TEST_DRAKE_STRICT)

    def test_pinocchio_strict_isolated(self):
        """Run Pinocchio strict tests in an isolated process to prevent numpy corruption."""
        if not TEST_PINOCCHIO_STRICT.exists():
            pytest.fail(f"Test file not found: {TEST_PINOCCHIO_STRICT}")
        self.run_isolated_test(TEST_PINOCCHIO_STRICT)
