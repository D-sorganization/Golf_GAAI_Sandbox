"""Template loader for API HTML responses.

Provides a single function to load static HTML templates bundled
alongside this package, keeping template markup out of Python source.
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATES_DIR: Path = Path(__file__).parent


def load_template(name: str) -> str:
    """Load an HTML template by filename.

    Args:
        name: Template filename relative to the templates directory
              (e.g. ``"ui_not_built.html"``).

    Returns:
        The template content as a string.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    template_path = _TEMPLATES_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {name}")
    return template_path.read_text(encoding="utf-8")
