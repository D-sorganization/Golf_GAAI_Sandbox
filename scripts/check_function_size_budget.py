#!/usr/bin/env python3
"""Ratcheting per-function size budget for Python source files.

Enforces that no *new* function exceeds the size limit, and that existing
over-budget functions do not grow beyond their recorded baseline.  Uses the
standard library ``ast`` module — no third-party dependencies required.

Usage::

    python scripts/check_function_size_budget.py           # full-repo scan
    python scripts/check_function_size_budget.py --changed # changed-files only

CI integration (add to quality-gate job)::

    - name: Function Size Budget Check
      run: python3 scripts/check_function_size_budget.py

Exit codes:
    0 — all checks passed
    1 — one or more violations detected
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FUNCTION_LINES: int = 50
DEFAULT_BASELINE: Path = Path("scripts/config/function_size_budget_baseline.json")
DEFAULT_INCLUDE: tuple[str, ...] = ("src",)
EXCLUDE_PARTS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "archive",
        "legacy",
        "experimental",
        "__pycache__",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
        "tests",
        "vendor",
        "opensim-models",
        "myosuite",
    }
)


def _should_skip(path: Path) -> bool:
    """Return True if the path contains an excluded path segment."""
    return any(part in EXCLUDE_PARTS for part in path.parts)


def _measure_functions(path: Path) -> list[tuple[str, int, int]]:
    """Return a list of (qualified_name, start_line, length) for all functions.

    Args:
        path: Python source file to analyse.

    Returns:
        List of (qualified_name, start_line, line_count) tuples.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    results: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end_line = getattr(node, "end_lineno", None)
        if end_line is None:
            continue
        length = end_line - node.lineno + 1
        results.append((node.name, node.lineno, length))
    return results


def _iter_python_files(include_roots: tuple[str, ...], repo_root: Path) -> list[Path]:
    """Yield all non-excluded Python files under the given roots."""
    files: list[Path] = []
    for root in include_roots:
        root_path = (repo_root / root).resolve()
        if not root_path.exists():
            continue
        for candidate in root_path.rglob("*.py"):
            if not _should_skip(candidate):
                files.append(candidate.resolve())
    return files


def _changed_python_files(base_ref: str) -> list[Path]:
    """Return Python files changed relative to *base_ref* that still exist."""
    repo_root = Path(__file__).resolve().parent.parent
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD", "--"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    paths = [
        (repo_root / p).resolve()
        for p in result.stdout.splitlines()
        if p.endswith(".py") and (repo_root / p).exists()
    ]
    return [p for p in paths if not _should_skip(p)]


def _load_baseline(baseline_path: Path) -> dict[str, int]:
    """Load baseline JSON mapping ``file:lineno:function`` → allowed line count."""
    if not baseline_path.exists():
        return {}
    raw: dict[str, int] = json.loads(baseline_path.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in raw.items()}


def _check_file(
    path: Path,
    baseline: dict[str, int],
    max_lines: int,
    repo_root: Path,
) -> list[str]:
    """Check a single file and return a list of violation messages."""
    rel = str(path.relative_to(repo_root)).replace("\\", "/")
    functions = _measure_functions(path)
    violations: list[str] = []
    for func_name, start_line, length in functions:
        if length <= max_lines:
            continue
        # Use file:lineno:name as key to handle same-named methods in diff classes
        key = f"{rel}:{start_line}:{func_name}"
        allowed = baseline.get(key)
        if allowed is None:
            violations.append(
                f"  {rel}:{start_line} {func_name}() - {length} lines "
                f"(budget={max_lines}, new violation)"
            )
        elif length > allowed:
            violations.append(
                f"  {rel}:{start_line} {func_name}() - {length} lines "
                f"(grew beyond baseline of {allowed})"
            )
    return violations


def main() -> int:
    """Entry point — returns 0 on success, 1 on violation."""
    parser = argparse.ArgumentParser(
        description="Enforce per-function line-count budget."
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=MAX_FUNCTION_LINES,
        help="Maximum allowed lines per function (default: 50).",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Path to the baseline JSON file (relative to repo root).",
    )
    parser.add_argument(
        "--include",
        nargs="+",
        default=list(DEFAULT_INCLUDE),
        help="Source directories to scan.",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Only check files changed relative to --base-ref.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Git base ref for changed-file detection (default: origin/main).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    repo_root = Path(__file__).resolve().parent.parent
    baseline = _load_baseline(repo_root / args.baseline)

    if args.changed:
        files = _changed_python_files(args.base_ref)
    else:
        files = _iter_python_files(tuple(args.include), repo_root)

    all_violations: list[str] = []
    for file_path in files:
        all_violations.extend(
            _check_file(file_path, baseline, args.max_lines, repo_root)
        )

    if all_violations:
        logger.error("FAIL: function size budget violations detected:\n")
        for violation in all_violations:
            logger.error("%s", violation)
        logger.error(
            "\nRefactor functions to ≤%d lines, or record them in %s.",
            args.max_lines,
            args.baseline,
        )
        return 1

    logger.info("OK: all functions are within the %d-line budget.", args.max_lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
