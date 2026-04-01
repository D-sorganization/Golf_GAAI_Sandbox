"""Unit tests for src.api.templates — HTML template loader."""

from __future__ import annotations

import pytest

templates = pytest.importorskip("src.api.templates")


class TestLoadTemplate:
    """Tests for load_template."""

    def test_loads_ui_not_built_html(self) -> None:
        """load_template should return a non-empty string for ui_not_built.html."""
        content = templates.load_template("ui_not_built.html")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_ui_not_built_html_is_valid_html(self) -> None:
        """The ui_not_built template should contain key HTML markers."""
        content = templates.load_template("ui_not_built.html")
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

    def test_ui_not_built_html_contains_setup_instructions(self) -> None:
        """The ui_not_built template should mention npm build commands."""
        content = templates.load_template("ui_not_built.html")
        assert "npm install" in content
        assert "npm run build" in content

    def test_raises_file_not_found_for_missing_template(self) -> None:
        """load_template should raise FileNotFoundError for unknown templates."""
        with pytest.raises(FileNotFoundError, match="Template not found"):
            templates.load_template("nonexistent_template.html")
