"""Unit tests for src.api.logo — animated startup logo helpers."""

from __future__ import annotations

import pytest

logo = pytest.importorskip("src.api.logo")


class TestPrintMatrixStatus:
    """Tests for print_matrix_status."""

    def test_raises_on_none_message(self) -> None:
        """print_matrix_status should raise ValueError when message is None."""
        with pytest.raises(ValueError, match="message must be provided"):
            logo.print_matrix_status(None)  # type: ignore[arg-type]

    def test_logs_message(self, caplog) -> None:
        """print_matrix_status should emit a log record containing the message."""
        import logging

        with caplog.at_level(logging.INFO, logger="src.api.logo"):
            logo.print_matrix_status("test status")
        assert any("test status" in record.message for record in caplog.records)

    def test_custom_indent_accepted(self) -> None:
        """print_matrix_status should accept custom indent without raising."""
        logo.print_matrix_status("indented", indent=8)


class TestPrintServerInfo:
    """Tests for print_server_info."""

    def test_raises_on_none_host(self) -> None:
        """print_server_info should raise ValueError when host is None."""
        with pytest.raises(ValueError, match="host must be provided"):
            logo.print_server_info(None, 8000)  # type: ignore[arg-type]

    def test_logs_host_and_port(self, caplog) -> None:
        """print_server_info should emit a log record mentioning host and port."""
        import logging

        with caplog.at_level(logging.INFO, logger="src.api.logo"):
            logo.print_server_info("127.0.0.1", 8080)
        combined = " ".join(record.message for record in caplog.records)
        assert "127.0.0.1" in combined
        assert "8080" in combined


class TestPrintLogoAnimated:
    """Tests for print_logo_animated."""

    def test_runs_without_error(self, monkeypatch) -> None:
        """print_logo_animated should complete without raising."""
        # Skip actual sleep to keep test fast
        monkeypatch.setattr("src.api.logo.time.sleep", lambda _: None)
        logo.print_logo_animated()

    def test_emits_log_records(self, monkeypatch, caplog) -> None:
        """print_logo_animated should emit at least one log record."""
        import logging

        monkeypatch.setattr("src.api.logo.time.sleep", lambda _: None)
        with caplog.at_level(logging.INFO, logger="src.api.logo"):
            logo.print_logo_animated()
        assert len(caplog.records) > 0
