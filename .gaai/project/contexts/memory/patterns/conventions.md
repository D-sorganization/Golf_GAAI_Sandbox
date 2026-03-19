---
type: memory
category: patterns
id: PATTERNS-001
tags:
  - patterns
  - conventions
  - procedural
created_at: 2026-03-18
updated_at: 2026-03-18
---

# Patterns & Conventions

> Procedural memory: how things are done in this project.
> Agent-maintained. Updated when durable patterns are confirmed.
> The Delivery Agent loads this before every implementation task.

---

## Code Patterns

- **Logging:** Always `import logging; logger = logging.getLogger(__name__)` at module top. Never use `print()`.
- **Shared logger factory:** Use `from src.shared.python.logging_pkg.logging_config import get_logger` if available in the module's package.
- **Engine availability guard:** Use `src.shared.python.engine_core.engine_availability` to check if an engine is installed before importing it.
- **Lazy engine import:** Inside a function/method only, not at module top level:
  ```python
  def _load_engine():
      import mujoco  # deferred — only when needed
      return mujoco
  ```
- **DbC precondition pattern:**
  ```python
  def compute_kinematics(joint_angles: np.ndarray) -> np.ndarray:
      """Compute forward kinematics.

      Preconditions:
          joint_angles must be 1D array of floats.
      """
      if not isinstance(joint_angles, np.ndarray) or joint_angles.ndim != 1:
          raise ValueError(f"joint_angles must be 1D ndarray, got {type(joint_angles)}")
      ...
  ```

---

## Test Patterns

- **TDD cycle:** Write failing test → minimal implementation → refactor. No production code without a failing test first.
- **Marker for engine tests:** `@pytest.mark.live_simulation` on any test requiring a running physics engine.
- **Fixture for optional engines:** Use `pytest.importorskip("pinocchio")` at top of test module for optional-dep tests.
- **Test file naming:** `tests/` mirrors `src/` — `src/engines/pinocchio/adapter.py` → `tests/engines/pinocchio/test_adapter.py`.
- **Cross-engine consistency:** Tests that must pass identically for all engines go in `tests/engines/test_cross_engine_*.py`.

---

## Architecture Patterns

- **Tri-engine validation:** MuJoCo, Drake, Pinocchio all implement the same interface/protocol. Tests run against the protocol, not engine-specific APIs.
- **Shared physics logic:** If a computation appears in 2+ engine adapters, extract to `src/shared/python/physics/`.
- **GUI decoupling:** Launchers use `QtCore.QTimer.singleShot` or `QThread` for deferred engine initialization — never block the UI thread.
- **Config externalization:** No hardcoded paths or URLs. Use `src/config/` or `.env` loaded via `python-dotenv`.

---

## Anti-Patterns (Avoid)

- `print()` in source — causes AGENTS.md violation. Use `logger.info/debug/warning/error`.
- `type: ignore` — fix the underlying type issue instead. Only add with a detailed comment explaining why.
- Wildcard imports (`from module import *`) — always explicit.
- `sys.path` hacks — use proper packaging.
- Bare `except:` — always catch specific exceptions.
- Circular imports between `src/engines/` and `src/launchers/` — use dependency injection.
