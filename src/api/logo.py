"""Animated startup logo and terminal status helpers for the local server.

Extracted from local_server.py to isolate presentation/CLI concerns from
server wiring logic.  All output goes through the logger rather than print()
so it respects the project's logging configuration.
"""

from __future__ import annotations

import sys
import time

from src.shared.python.logging_pkg.logging_config import get_logger

logger = get_logger(__name__)

# ANSI colour codes used by the startup display
_ORANGE: str = "\033[38;5;208m"
_GREEN: str = "\033[38;5;46m"  # Matrix bright green
_CYAN: str = "\033[38;5;51m"
_RESET: str = "\033[0m"

_LOGO_LINES: tuple[str, ...] = (
    r"██╗   ██╗██████╗ ███████╗████████╗██████╗ ███████╗ █████╗ ███╗   ███╗",
    r"██║   ██║██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔══██╗████╗ ████║",
    r"██║   ██║██████╔╝███████╗   ██║   ██████╔╝█████╗  ███████║██╔████╔██║",
    r"██║   ██║██╔═══╝ ╚════██║   ██║   ██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║",
    r"╚██████╔╝██║     ███████║   ██║   ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║",
    r" ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
    r"",
    r"██████╗ ██████╗ ██╗███████╗████████╗",
    r"██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝",
    r"██║  ██║██████╔╝██║█████╗     ██║   ",
    r"██║  ██║██╔══██╗██║██╔══╝     ██║   ",
    r"██████╔╝██║  ██║██║██║        ██║   ",
    r"╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝        ╚═╝   ",
)

_SCROLL_DELAY_SECONDS: float = 0.03  # Delay between logo lines for scroll effect


def print_logo_animated() -> None:
    """Print the Upstream Drift logo with a scroll animation effect.

    Outputs each line via the logger with a short sleep between lines to
    create a terminal scroll effect.  Falls back to a plain text banner on
    ``UnicodeEncodeError`` (e.g. Windows consoles without UTF-8 support).
    """
    logger.info("")
    try:
        for line in _LOGO_LINES:
            logger.info("    %s%s%s", _ORANGE, line, _RESET)
            sys.stdout.flush()
            time.sleep(_SCROLL_DELAY_SECONDS)
    except UnicodeEncodeError:
        logger.info("    %sUPSTREAM DRIFT%s", _ORANGE, _RESET)
    logger.info("")


def print_matrix_status(message: str, indent: int = 4) -> None:
    """Log a status line styled in matrix green.

    Args:
        message: The status message to display.
        indent: Number of leading spaces before the arrow indicator.

    Raises:
        ValueError: If *message* is None.
    """
    if message is None:
        raise ValueError("message must be provided")
    logger.info(
        "%s%s>%s %s%s%s",
        " " * indent,
        _GREEN,
        _RESET,
        _GREEN,
        message,
        _RESET,
    )


def print_server_info(host: str, port: int) -> None:
    """Log the server info box showing the running URL and API docs link.

    Args:
        host: Hostname or IP the server is bound to.
        port: Port number the server is listening on.

    Raises:
        ValueError: If *host* is None.
    """
    if host is None:
        raise ValueError("host must be provided")
    try:
        logger.info(
            "\n%s"
            "    ┌─────────────────────────────────────────────────────────┐\n"
            "    │              Golf Modeling Suite - Local Server         │\n"
            "    ├─────────────────────────────────────────────────────────┤\n"
            "    │  Running at: http://%s:%-5s                       │\n"
            "    │  API Docs:   http://%s:%s/api/docs               │\n"
            "    │                                                         │\n"
            "    │  Mode: LOCAL (no auth required)                         │\n"
            "    │  Press Ctrl+C to stop.                                  │\n"
            "    └─────────────────────────────────────────────────────────┘%s\n",
            _CYAN,
            host,
            port,
            host,
            port,
            _RESET,
        )
    except UnicodeEncodeError:
        logger.info("\n    Golf Modeling Suite - Local Server")
        logger.info("    Running at: http://%s:%s", host, port)
        logger.info("    API Docs:   http://%s:%s/api/docs", host, port)
        logger.info("    Mode: LOCAL (no auth required)")
        logger.info("    Press Ctrl+C to stop.\n")
