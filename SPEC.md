# SPEC.md - Repository Specification Document

## 1. Identity

| Field | Value |
| --- | --- |
| Repository Name | `Golf_GAAI_Sandbox` |
| GitHub URL | `https://github.com/D-sorganization/Golf_GAAI_Sandbox` |
| Owner | D-sorganization |
| Primary Language(s) | Python 3.10+, Rust, TypeScript, MATLAB |
| License | MIT |
| Current Version | `2.1.0` |
| Spec Version | `1.0.14` |
| Last Spec Update | `2026-04-15` |

## 2. Purpose

Golf_GAAI_Sandbox is a multi-surface golf modeling and analysis workspace. The maintained codebase combines a Python simulation/API layer, a React/Tauri desktop UI, a Rust physics core, and a large set of legacy MATLAB and Simscape model assets for golf and biomechanics workflows.

## 3. Scope And Boundaries

### In Scope

- Python package code under `src/`
- Test code under `tests/`
- Root launchers and setup scripts
- React/Tauri UI under `ui/`
- Rust physics core under `rust_core/upstream-physics/`
- Repository documentation under `docs/`

### Out Of Scope

- Treating generated outputs in `output/` and report artifacts in `reports/` as source code
- Refactoring legacy model trees unless a task explicitly targets them
- Editing unrelated merge-conflict files that already exist in the working tree

## 4. Architecture Overview

The repository is organized around a Python application core with multiple front ends and integration surfaces:

- `src/api/` provides the HTTP API, route registry, auth, middleware, models, services, and utility modules.
- `launch_golf_suite.py` is the main Python launcher entrypoint and routes to web UI, classic UI, or API-only modes.
- `start_api_server.py` and `setup_golf_suite.py` are supporting root-level operational entrypoints.
- `ui/` contains the React front end and Tauri desktop wrapper.
- `rust_core/upstream-physics/` contains the Rust physics library used by the desktop/application stack.
- `src/deployment/` holds deployment, realtime, safety, and teleoperation support modules.
- `src/config/` holds configuration loading and launcher manifest data.
- `src/engines/` contains model and engine-specific implementations, including the large Simscape Multibody tree and engine-specific Python packages.
- `src/shared/` and `shared/` provide reusable code and model assets used across the repo.

## 5. Current Layout

| Area | Path | Notes |
| --- | --- | --- |
| Python package root | `src/` | Main application package and supporting modules |
| API service | `src/api/` | Routes, services, auth, middleware, and server wiring |
| Configuration | `src/config/` | Launcher manifests, model data, and config helpers |
| Deployment helpers | `src/deployment/` | Realtime, safety, and teleoperation support |
| Shared code | `src/shared/`, `shared/` | Common helpers and shared model assets |
| Engine/model trees | `src/engines/` | Physics-engine integrations and legacy model content |
| Python launchers | `launch_golf_suite.py`, `start_api_server.py`, `setup_golf_suite.py` | Root-level entrypoints and setup helpers |
| Desktop UI | `ui/` | React app plus Tauri shell and build configuration |
| Rust core | `rust_core/upstream-physics/` | Rust physics library and Python packaging metadata |
| Tests | `tests/` | Unit, integration, benchmark, security, and specialized suites |
| Documentation | `docs/` | User, development, assessment, and technical docs |

## 6. Entry Points

### Python

- `upstream-drift` console entrypoint maps to `launch_golf_suite:main`
- `python launch_golf_suite.py` starts the unified launcher directly
- `python start_api_server.py` starts the API server path
- `python setup_golf_suite.py` prepares the runtime environment

### UI

- `ui/src/main.tsx` is the React application entrypoint
- `ui/src-tauri/src/main.rs` is the Tauri runtime entrypoint

### Rust

- `rust_core/upstream-physics/src/lib.rs` is the Rust library root

## 7. Data And Configuration

- Runtime configuration is primarily loaded from Python config modules, launcher manifests, environment variables, and repo-local YAML/JSON assets.
- `pyproject.toml` defines the package metadata, editable-install entrypoint, dependency groups, linting, mypy, pytest, and coverage settings.
- `ui/package.json` defines the JavaScript build, test, and type-check scripts for the front end.
- Legacy MATLAB and Simscape assets remain checked in under `src/engines/Simscape_Multibody_Models/`.

## 8. Testing And Validation

### Python Validation

- `pytest` is the primary test runner.
- The root `conftest.py` imports `mujoco` early to avoid Windows DLL initialization issues during collection.
- `pyproject.toml` enables strict pytest config, xdist parallelism, and a coverage floor of 45%.
- Developer convenience targets in `Makefile` include `make lint`, `make format`, `make test`, and `make check`.

### Frontend And Desktop Validation

- `ui/` is validated with npm scripts and Tauri build checks.
- The desktop build workflow exercises TypeScript checks, Rust formatting, clippy, and cargo checks when UI work changes.

### Coverage Expectations

- Python source is expected to stay compatible with the repo's existing pytest and coverage configuration.
- Legacy model and artifact directories are intentionally excluded from several lint and coverage paths.

## 9. CI Expectations

- Python changes are expected to pass `ruff`, `mypy`, and the relevant `pytest` selection used by CI.
- UI changes are expected to pass the front-end type and build checks, plus the Tauri/Rust validation path.
- Root documentation changes should keep the spec truthful without introducing additional runtime behavior.

## 10. Maintenance Rules

- Keep the spec aligned with the actual repository structure, especially entrypoints, major packages, and validation paths.
- Do not treat generated outputs, caches, or reports as maintained source unless a task explicitly says otherwise.
- Preserve existing public entrypoints unless an issue explicitly requires a behavioral change.
- Update this spec when repository structure or supported workflows change.

## 11. Open Issues And Legacy Surface

- The repository still carries large legacy model trees and generated artifacts that are part of the maintained workspace but are not all active application code.
- Several workflows and helper scripts in the repo are already in a conflicted or partially edited state in the working tree; this spec does not attempt to resolve them.

## 12. Change Log

| Date | Version | Changes |
| --- | --- | --- |
| 2026-04-15 | 1.0.14 | Marked the advanced putting-green simulator scenarios as slow so stochastic multi-ball scatter simulations stay out of the default core CI lane while lighter putting-green coverage remains active. |
| 2026-04-15 | 1.0.13 | Hardened the cross-engine validator CI step with the same Xvfb plugin disable flags and serial pytest execution used by the core Python lane, preventing worker-level Xvfb startup failures after the main suite passes. |
| 2026-04-15 | 1.0.12 | Marked the legacy performance benchmark module with the benchmark marker so the core CI lane skips timing-sensitive assertions, and made telemetry export tests tolerate unrelated process-log writes while still asserting the intended export open call occurred. |
| 2026-04-15 | 1.0.8 | Stabilized the required Python test lane by disabling xdist for serial execution, avoiding late worker crashes and cancellation while preserving per-job coverage isolation and test timeouts. |
| 2026-04-15 | 1.0.7 | Stabilized the standard Python test lane by using a per-job runner-temp coverage data file and bounding self-hosted xdist fanout so full-suite runs do not overload runners or reuse stale coverage databases. |
| 2026-04-15 | 1.0.6 | Disabled both pytest Xvfb plugin entrypoint names in the CI standard test lanes so the `xvfb-run` wrapper remains the only X server provider on self-hosted runners. |
| 2026-04-14 | 1.0.5 | Disabled the `pytest_xvfb` plugin in the CI standard workflow so the `xvfb-run`-wrapped test lanes do not try to start a second Xvfb instance. |
| 2026-04-11 | 1.0.4 | Decomposed the 5 largest Python functions into private helpers (issue #146): `_add_live_kinematics_overlays`, `compute_jacobian`, `validate_physical_bounds`, `_build_engine_profiles`, and `draw_letter`. Public signatures unchanged. |
| 2026-04-11 | 1.0.3 | Removed 7 `print()` call violations from `src/` to satisfy the `no-print-in-src` pre-commit rule (issue #148): converted subprocess check code to `sys.stdout.write`, switched a MakeHuman script template warning to `sys.stderr.write`, and reformatted doctest examples in `mesh_loader.py`. |
| 2026-04-06 | 1.0.2 | Split the MuJoCo kinematic-forces helper surfaces into smaller internal modules and standardized examples on module-style execution without inline `sys.path` shims. |
| 2026-04-06 | 1.0.1 | Corrected the repository URL and tightened the root-spec identity block. |
| 2026-04-06 | 1.0.0 | Initial root spec for `Golf_GAAI_Sandbox` documenting the current Python, UI, Rust, and legacy model layout. |
