import pytest


def test_headless_plotting_import():
    """Test that plotting_core can be imported without PyQt6.

    Note: The plotting_core module was removed from the codebase.
    This test is skipped because the module no longer exists.
    """
    pytest.skip(
        "src.shared.python.plotting_core was removed; "
        "plotting functionality has been reorganized"
        # DEFERRED: Rewrite test to cover new plotting module location, or delete — see issue #1951
    )
