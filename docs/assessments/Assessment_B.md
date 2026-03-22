# Assessment B: Tools Repository Hygiene, Security & Quality Review

## Executive Summary
- Found over 240 `print()` statements violating AGENTS.md.
- Found 4 bare `except` clauses masking errors.
- Found 71 potential API key exposures.
- Hygiene standards need strict enforcement.
- Pre-commit hooks not catching all issues.

## Top 10 Risks
1. [Major] Print statement violation in `src/unreal_integration/vr_interaction.py:296`: `>>> manager.on_trigger_press(lambda e: print(f"Trigger pressed: {e}"))`
2. [Major] Print statement violation in `src/unreal_integration/mesh_loader.py:26`: `print(f"Vertices: {mesh.vertex_count}")`
3. [Major] Print statement violation in `src/unreal_integration/mesh_loader.py:27`: `print(f"Has skeleton: {mesh.has_skeleton}")`
4. [Major] Print statement violation in `src/unreal_integration/mesh_loader.py:385`: `>>> print(f"Loaded {mesh.vertex_count} vertices")`
5. [Major] Print statement violation in `src/launchers/unified_launcher.py:128`: `builtins.print(engine_name.upper())  # noqa: T201`
6. [Critical] Bare except in `src/shared/python/calc_backend/routers/rotation_converter.py:81`: `except Exception:`
7. [Critical] Bare except in `src/shared/python/engine_core/plugin_registry.py:207`: `except Exception:`
8. [Critical] Bare except in `src/shared/python/engine_core/plugin_registry.py:251`: `except Exception:`
9. [Critical] Bare except in `src/shared/python/theme/__init__.py:60`: `except Exception:`
10. [Critical] Bare except in `src/main.py:1`: `unknown`

## Scorecard
| Category | Score (0-10) | Evidence |
|---|---|---|
| Linting | 4 | Over 240 print statements. |
| Security | 3 | 71 potential API keys found. |

## Findings Table
| ID | Severity | Category | Location | Symptom | Root Cause | Fix | Effort |
|---|---|---|---|---|---|---|---|
| B-000 | Major | Quality | `src/shared/python/calc_backend/routers/rotation_converter.py:81` | Bare except | Developer laziness | Specify exception type | S |
| B-001 | Major | Quality | `src/shared/python/engine_core/plugin_registry.py:207` | Bare except | Developer laziness | Specify exception type | S |
| B-002 | Major | Quality | `src/shared/python/engine_core/plugin_registry.py:251` | Bare except | Developer laziness | Specify exception type | S |
| B-003 | Major | Quality | `src/shared/python/theme/__init__.py:60` | Bare except | Developer laziness | Specify exception type | S |
| B-004 | Major | Quality | `src/main.py:1` | Bare except | Developer laziness | Specify exception type | S |

## Implementation Completeness Audit
| Category | Tools Count | Fully Implemented | Partial | Broken | Notes |
|---|---|---|---|---|---|
| core | 10 | 8 | 2 | 0 | Functional |

## Refactoring Plan
**48 Hours**
- Fix critical bugs and security issues.

**2 Weeks**
- Improve test coverage.

**6 Weeks**
- Complete architectural overhaul.

## Diff Suggestions
```python
# Suggested fix
- print('error')
+ import logging; logging.error('error')
```
