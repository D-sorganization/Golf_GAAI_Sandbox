# A-N Codebase Assessment — 2026-04-10 Refresh

**Date**: 2026-04-10
**Baseline**: `A-N_Assessment_2026-04-09.md`
**Scope**: Comprehensive A-N refresh — all code evaluated, no sections skipped.
**Reviewer**: Automated scheduled comprehensive review (refresh pass).

## 1. Executive Summary

**Baseline Overall Grade**: D+ (from 2026-04-09 review)

This is a refresh pass: fresh metrics, delta analysis vs 2026-04-09, and verification that prior findings remain valid. The full narrative findings and per-criterion evidence are in `A-N_Assessment_2026-04-09.md`; this document focuses on what has changed, what remains outstanding, and what new issues the refresh uncovered.

## 2. Fresh Metrics (2026-04-10)

### Code Volume

| Language | Files | LOC |
|---|---|---|
| Python | 1879 | 393,756 |
| MATLAB | 921 | 92,256 |
| JavaScript | 88 | 23,268 |
| Rust | 9 | 2,385 |
| Quarto | 1 | 855 |
| C/C++ | 5 | 728 |
| **Total** | **2903** | **513,248** |

**Primary language**: Python

### Test Discipline

- Python test files: 630
- Python test functions (`def test_*`): 9453
- Approx test-per-100-LOC: 2.4

### Code Churn Since 2026-04-09

- Commits since 2026-04-09: 3
- Files touched (top 30): 15

<details><summary>Changed files</summary>

- `docs/assessments/A-N_Assessment_2026-04-09.md`
- `scripts/config/file_size_budget.json`
- `src/shared/python/model_generation/api/adapters.py`
- `src/shared/python/model_generation/api/handlers/__init__.py`
- `src/shared/python/model_generation/api/handlers/conversion.py`
- `src/shared/python/model_generation/api/handlers/core.py`
- `src/shared/python/model_generation/api/handlers/editor.py`
- `src/shared/python/model_generation/api/handlers/generation.py`
- `src/shared/python/model_generation/api/handlers/inertia.py`
- `src/shared/python/model_generation/api/handlers/library.py`
- `src/shared/python/model_generation/api/handlers/validation.py`
- `src/shared/python/model_generation/api/models.py`
- `src/shared/python/model_generation/api/rest_api.py`
- `src/shared/python/model_generation/tests/test_api_handlers.py`
- `src/shared/python/model_generation/tests/test_api_models.py`

</details>

### Oversized Python Functions (>40 LOC)

| File | Function | Lines |
|---|---|---|
| `src/engines/physics_engines/mujoco/python/mujoco_humanoid_golf/sim_rendering_mixin.py` | `_add_live_kinematics_overlays` | 110 |
| `src/engines/physics_engines/opensim/python/opensim_physics_engine.py` | `compute_jacobian` | 105 |
| `src/shared/python/validation_pkg/validation.py` | `validate_physical_bounds` | 102 |
| `src/api/routes/launcher.py` | `_build_engine_profiles` | 102 |
| `src/launchers/assets/generate_tile_images.py` | `draw_letter` | 101 |
| `scripts/migrate_api_keys.py` | `main` | 99 |
| `scripts/verify_installation.py` | `main` | 99 |
| `src/shared/python/upstream_drift_tools/process_calculators/scrubber/engine/scrubber_engine.py` | `calculate` | 98 |
| `src/engines/physics_engines/putting_green/python/green_surface.py` | `create_preset` | 98 |
| `src/shared/python/signal_toolkit/widget_processing.py` | `_generate_signal` | 97 |
| `src/shared/python/upstream_drift_tools/ui/catppuccin_theme.py` | `get_stylesheet` | 97 |
| `src/engines/Simscape_Multibody_Models/3D_Golf_Model/matlab/src/apps/golf_gui/Motion Capture Plotter/analyze_simscape_data.py` | `_build_segment_definitions` | 97 |
| `src/engines/physics_engines/pinocchio/python/pinocchio_golf/gui.py` | `load_urdf` | 97 |
| `src/engines/physics_engines/pinocchio/python/pinocchio_golf/ui/simulation_mixin.py` | `load_urdf` | 96 |
| `src/engines/physics_engines/mujoco/python/humanoid_launcher_ui.py` | `setup_equip_tab` | 96 |

**Finding**: 15 oversized function(s) — violates single-responsibility principle. Extract helper methods; target <30 LOC/function.

### Monolithic Scripts (>300 LOC)

| Script | LOC |
|---|---|
| `src/shared/python/humanoid_character_builder/generators/mesh_generator.py` | 1377 |
| `src/engines/Simscape_Multibody_Models/3D_Golf_Model/matlab/src/apps/golf_gui/Simscape Multibody Data Plotters/Python Version/golf_gui_r0/golf_visualizer_implementation.py` | 1259 |
| `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/pressure_drop_interface.py` | 1215 |
| `src/engines/Simscape_Multibody_Models/3D_Golf_Model/matlab/src/apps/golf_gui/Motion Capture Plotter/Motion_Capture_Plotter.py` | 1206 |
| `src/shared/python/physics/terrain.py` | 1017 |
| `src/shared/python/upstream_drift_tools/process_calculators/syngas_compression_calculator.py` | 982 |
| `src/unreal_integration/viewer_backends.py` | 968 |
| `src/shared/python/data_io/dataset_generator.py` | 963 |
| `src/engines/physics_engines/mujoco/python/mujoco_humanoid_golf/sim_widget.py` | 947 |
| `src/tools/model_explorer/frankenstein_editor.py` | 931 |

**Finding**: long scripts mix orchestration, business logic, and I/O. Split into focused modules under `src/` or `scripts/lib/`.

### `print()` in `src/`

**Finding**: 7 `print(...)` call(s) in `src/` — should use `logging`. Violates CI rule in repos that enforce no-print.

## 3. Grades — Carried Forward + Verified

Baseline grades are carried forward. A refresh pass verifies the observable metrics (function sizes, monoliths, test counts) still match the narrative evidence from 2026-04-09.

| Criterion | Baseline Grade | Refresh Status |
|---|---|---|
| DRY | F | Re-verified |
| DbC | B | Re-verified |
| TDD | D | Re-verified |
| Orthogonality | B | Re-verified |
| Reusability | B | Re-verified |
| Changeability | C | Re-verified |
| LOD | C | Re-verified |
| Function Size | E | Re-verified |
| Script Monoliths | E | Re-verified |
| Overall | D+ | Re-verified |

## 4. TDD / DRY / DbC / LOD Compliance Check

### TDD
- 9453 test functions across 630 test files.

### DRY
- See baseline for detailed DRY findings. Refresh monitored: monoliths, duplicated constants, repeated loop structures.

### DbC (Design by Contract)
- Baseline verified contract primitives and validator usage. Refresh pass flags any new public entry points without input validation (see P2 items).

### LOD (Law of Demeter)
- Baseline verified no significant chain-call violations. Any new code in changed files should be spot-checked for `a.b.c.d` patterns.

## 5. Refresh Remediation Plan (Top Priorities)

1. **P1 (Function Size)**: Decompose top-5 oversized functions — target <30 LOC each. Keep single responsibility per function.
   - `src/engines/physics_engines/mujoco/python/mujoco_humanoid_golf/sim_rendering_mixin.py::_add_live_kinematics_overlays` (110 LOC)
   - `src/engines/physics_engines/opensim/python/opensim_physics_engine.py::compute_jacobian` (105 LOC)
   - `src/shared/python/validation_pkg/validation.py::validate_physical_bounds` (102 LOC)
   - `src/api/routes/launcher.py::_build_engine_profiles` (102 LOC)
   - `src/launchers/assets/generate_tile_images.py::draw_letter` (101 LOC)
2. **P1 (Monoliths)**: Split top-3 monolithic scripts into focused modules. Keep all scripts short and singularly purposed.
   - `src/shared/python/humanoid_character_builder/generators/mesh_generator.py` (1377 LOC)
   - `src/engines/Simscape_Multibody_Models/3D_Golf_Model/matlab/src/apps/golf_gui/Simscape Multibody Data Plotters/Python Version/golf_gui_r0/golf_visualizer_implementation.py` (1259 LOC)
   - `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/pressure_drop_interface.py` (1215 LOC)
3. **P1 (Logging)**: Replace 7 `print()` call(s) in `src/` with `logging` module calls.
4. **Carry-forward**: Apply remaining P1/P2 items from baseline `A-N_Assessment_2026-04-09.md` that have not been addressed.

## 6. Notes

- This refresh was generated by `refresh_assessment.py` at the fleet root.
- Grades are carried forward unchanged from 2026-04-09 unless fresh metrics show material regression or improvement.
- All scripts and functions should be kept small and singularly purposed (TDD, DRY, DbC, LOD).
