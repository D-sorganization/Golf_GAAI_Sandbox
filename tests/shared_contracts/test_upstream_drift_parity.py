"""Drift guard for Golf's vendored copies of UpstreamDrift shared packages.

Tracks issue #138 — "Resolve overlap with UpstreamDrift repository (DRY at
fleet level)". Two directories in Golf's ``src/shared/python`` tree currently
duplicate content owned by the UpstreamDrift repository:

* ``src/shared/python/upstream_drift_tools/``
* ``src/shared/python/humanoid_character_builder/``

The long-term plan (see issue #138) is to pick a single source-of-truth and
remove the duplication. Until that refactor lands, this module locks in the
subset of files that are byte-identical between the two repos today. Any
drift against those locked files should fail loudly so we know when a fix in
one repo has been silently forked in the other.

Behaviour:

* If a UpstreamDrift checkout is discoverable (via ``UPSTREAM_DRIFT_REPO``
  env var, or a sibling ``../UpstreamDrift`` directory, or an existing
  ``vendor/upstream_drift`` / ``_tools_dep`` path that contains the UD
  source tree), we compare hashes and fail on mismatch.
* If no UD checkout is available (the common CI path today), the test is
  skipped rather than failing. This keeps the guard honest without coupling
  Golf's CI to a UD working tree.

Manifest of currently-identical files lives in
``tests/shared_contracts/ud_drift_manifest.json`` and was generated from a
clean clone of each repo on 2026-04-15. Regenerate by re-running the audit
from issue #138 once a follow-up PR removes the duplication.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLF_SHARED_PY = REPO_ROOT / "src" / "shared" / "python"
MANIFEST_PATH = Path(__file__).with_name("ud_drift_manifest.json")


def _load_manifest() -> dict[str, dict[str, str]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _candidate_ud_roots() -> list[Path]:
    """Return likely locations of an UpstreamDrift checkout, in priority order."""
    env = os.environ.get("UPSTREAM_DRIFT_REPO")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            REPO_ROOT.parent / "UpstreamDrift",
            REPO_ROOT / "vendor" / "upstream_drift",
            REPO_ROOT / "_tools_dep",
            REPO_ROOT / "vendor" / "ud-tools",
        ]
    )
    out: list[Path] = []
    for c in candidates:
        try:
            if c and c.exists() and (c / "src" / "shared" / "python").exists():
                out.append(c.resolve())
        except OSError:
            continue
    return out


def _find_ud_root() -> Path | None:
    roots = _candidate_ud_roots()
    return roots[0] if roots else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_manifest_entries() -> list[tuple[str, str, str]]:
    manifest = _load_manifest()
    entries: list[tuple[str, str, str]] = []
    for subdir, files in manifest.items():
        for rel, digest in files.items():
            entries.append((subdir, rel, digest))
    return entries


MANIFEST_ENTRIES = _iter_manifest_entries()


def test_manifest_is_non_empty() -> None:
    """The manifest must list something or the guard silently protects nothing."""
    assert MANIFEST_ENTRIES, (
        f"{MANIFEST_PATH.name} is empty; regenerate from issue #138 audit."
    )


@pytest.mark.parametrize(
    ("subdir", "rel", "expected_sha"),
    MANIFEST_ENTRIES,
    ids=[f"{sd}/{rel}" for sd, rel, _ in MANIFEST_ENTRIES],
)
def test_golf_copy_matches_manifest(subdir: str, rel: str, expected_sha: str) -> None:
    """Golf's local copy must match the recorded hash from the audit."""
    path = GOLF_SHARED_PY / subdir / rel
    assert path.exists(), (
        f"Expected Golf file missing: {path}. If this file was intentionally "
        f"removed as part of resolving issue #138, update "
        f"{MANIFEST_PATH.name}."
    )
    actual = _sha256(path)
    assert actual == expected_sha, (
        f"Golf's {subdir}/{rel} has drifted from the recorded UpstreamDrift "
        f"parity hash.\n"
        f"  expected: {expected_sha}\n"
        f"  actual:   {actual}\n"
        f"Either sync the change with UpstreamDrift and regenerate "
        f"{MANIFEST_PATH.name}, or (preferred) finish issue #138 by removing "
        f"the duplicated file in favour of the UpstreamDrift source-of-truth."
    )


@pytest.mark.parametrize(
    ("subdir", "rel", "expected_sha"),
    MANIFEST_ENTRIES,
    ids=[f"{sd}/{rel}" for sd, rel, _ in MANIFEST_ENTRIES],
)
def test_upstream_drift_copy_matches_manifest(
    subdir: str, rel: str, expected_sha: str
) -> None:
    """If a UD checkout is reachable, its copy must also match the manifest."""
    ud_root = _find_ud_root()
    if ud_root is None:
        pytest.skip(
            "No UpstreamDrift checkout found (set UPSTREAM_DRIFT_REPO or place "
            "one at ../UpstreamDrift to enable cross-repo drift checking)."
        )
    path = ud_root / "src" / "shared" / "python" / subdir / rel
    if not path.exists():
        pytest.skip(
            f"UpstreamDrift checkout at {ud_root} is missing {subdir}/{rel}; "
            f"likely a version skew — refresh the checkout or regenerate the "
            f"manifest."
        )
    actual = _sha256(path)
    assert actual == expected_sha, (
        f"UpstreamDrift's {subdir}/{rel} has drifted from the recorded parity "
        f"hash.\n"
        f"  expected: {expected_sha}\n"
        f"  actual:   {actual}\n"
        f"Regenerate {MANIFEST_PATH.name} from a fresh clone of both repos, "
        f"or land the matching change in Golf."
    )
