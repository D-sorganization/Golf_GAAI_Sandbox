"""Test that importing src.launchers.golf_launcher does NOT eagerly import
physics engine packages (mujoco, pinocchio) at module load time.

This test implements AC6 of E04S01: strict lazy-loading enforcement.

The test uses sys.modules inspection — as described in the story's
implementation notes — to confirm engine packages are NOT pulled in
by the launcher module import itself.

Strategy: capture sys.modules before and after importing the launcher,
then assert that no mujoco or pinocchio modules were *added* by the import.
Pre-existing mujoco/pinocchio entries (from previous tests or conftest)
are excluded from the check.
"""

from __future__ import annotations

import sys


def test_golf_launcher_does_not_import_mujoco_at_load_time() -> None:
    """Importing golf_launcher must not add mujoco to sys.modules.

    Captures sys.modules before and after the import and verifies no
    mujoco modules were *added* by the launcher module import.
    """
    # Snapshot BEFORE import
    modules_before = set(sys.modules.keys())

    # Remove any cached launcher so we get a fresh import
    launcher_keys = [k for k in sys.modules if k.startswith("src.launchers.golf_launcher")]
    saved_launcher = {k: sys.modules.pop(k) for k in launcher_keys}

    try:
        import src.launchers.golf_launcher  # noqa: F401  — side-effect import under test

        # Only check for mujoco modules that were NOT present before the import
        mujoco_added = [
            k for k in sys.modules
            if (k == "mujoco" or k.startswith("mujoco."))
            and k not in modules_before
        ]
        assert mujoco_added == [], (
            f"Eager mujoco import detected: {mujoco_added}. "
            "Engine packages must only be imported inside functions, not at module load time."
        )
    finally:
        # Restore state
        for k in list(sys.modules):
            if k.startswith("src.launchers.golf_launcher"):
                del sys.modules[k]
        sys.modules.update(saved_launcher)


def test_golf_launcher_does_not_import_pinocchio_at_load_time() -> None:
    """Importing golf_launcher must not add pinocchio to sys.modules."""
    # Snapshot BEFORE import
    modules_before = set(sys.modules.keys())

    # Remove any cached launcher so we get a fresh import
    launcher_keys = [k for k in sys.modules if k.startswith("src.launchers.golf_launcher")]
    saved_launcher = {k: sys.modules.pop(k) for k in launcher_keys}

    try:
        import src.launchers.golf_launcher  # noqa: F401  — side-effect import under test

        # Only check for pinocchio modules that were NOT present before the import
        pinocchio_added = [
            k for k in sys.modules
            if (k == "pinocchio" or k.startswith("pinocchio."))
            and k not in modules_before
        ]
        assert pinocchio_added == [], (
            f"Eager pinocchio import detected: {pinocchio_added}. "
            "Engine packages must only be imported inside functions, not at module load time."
        )
    finally:
        # Restore state
        for k in list(sys.modules):
            if k.startswith("src.launchers.golf_launcher"):
                del sys.modules[k]
        sys.modules.update(saved_launcher)
