---
type: memory
category: project
id: PROJECT-001
tags:
  - architecture
  - stack
  - purpose
created_at: 2026-03-18
updated_at: 2026-03-18
---

# Golf Modeling Suite — Project Context

## Project Overview

**Name:** Golf Modeling Suite (GAAI Sandbox)

**Purpose:** A multi-engine golf biomechanics and physics simulation platform that models golf swings, ball flight, and robot motion planning using multiple physics backends (MuJoCo, Drake, Pinocchio, OpenSim, MyoSuite). Used for research, biomechanics analysis, and autonomous robotics development. This repo is a sandboxed GAAI-driven fork of `D-sorganization/Golf_Modeling_Suite`.

**Target Users:** Researchers, engineers, and automated AI development agents working on golf physics simulation and robot planning.

---

## Repository Info

- **Upstream:** `D-sorganization/Golf_Modeling_Suite`
- **This sandbox:** `D-sorganization/Golf_GAAI_Sandbox`
- **GAAI branch:** `staging` (AI works here; PRs target staging; main is protected)
- **Local path:** `/c/Users/diete/Repositories/Golf_GAAI_Sandbox_local`

---

## Core Problems Being Solved

- Pinocchio engine lags behind MuJoCo and Drake in feature/diagnostic parity
- Test coverage at ~50% (target 70%); 526 source modules have no test file
- 310 pytest.skip calls mask untested functionality; no live_simulation marker
- 1,227 type:ignore comments and 109 print() calls violate code standards
- GUI launcher may eagerly load heavy physics engines on startup
- Examples/notebooks are stale after major architectural refactoring
- CI has action version mismatches and missing heavy-integration workflow

---

## Success Metrics

- Test coverage ≥ 70%
- Zero print() calls in production source
- type:ignore count < 200
- Pinocchio passes all cross-engine consistency tests
- CI green on staging for all stories delivered overnight

---

## Tech Stack & Conventions

- **Language:** Python (primary), Rust (physics kernel via PyO3)
- **Physics engines:** MuJoCo, Drake, Pinocchio, OpenSim, MyoSuite
- **Testing:** pytest, pytest-cov; markers: live_simulation (to be added), heavy_integration
- **Linting:** ruff (isort + format), mypy
- **CI:** GitHub Actions (.github/workflows/ci-standard.yml, nightly-cross-engine.yml)
- **Packaging:** pyproject.toml
- **Key conventions:** TDD mandatory, DbC at boundaries, DRY, no print(), type hints required, max 400-line files, max 50-line functions

---

## Architectural Boundaries

- `src/shared/python/` — shared utilities; engines must not duplicate logic from here
- `src/engines/physics_engines/` — one subfolder per engine (drake, mujoco, pinocchio, opensim, myosuite)
- `src/launchers/` — GUI; must use lazy imports for engine packages
- `rust_core/` — Rust physics kernel; Python bindings via PyO3
- `tests/` — mirrors src/ structure; every source module should have a corresponding test file

---

## Known Constraints

- All AI work happens on `staging`; never push directly to `main`
- Engine-specific packages (mujoco, pinocchio, drake) may not be installed in CI standard — use guards/lazy imports
- No secrets, no API keys committed
- Rust toolchain required for rust_core builds
- This is a sandbox: no production traffic, no user data

---

## Out of Scope (Permanent)

- Changes to `main` branch directly
- Modifications to upstream `Golf_Modeling_Suite` from this sandbox
- Any MATLAB model changes (legacy, read-only)
- New physics engine integrations beyond the current five
