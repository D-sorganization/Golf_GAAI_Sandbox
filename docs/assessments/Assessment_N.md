# Assessment N: Visualization & Export

## Executive Summary
- Matplotlib code is copy-pasted across scripts.
- Hardcoded color schemes lacking accessibility.
- Missing export to standardized formats (e.g., JSON, CSV).
- Slow rendering for large datasets.
- No interactive visualization options.

## Top 10 Risks
1. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/pipe_database.py:305`.
2. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:173`.
3. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:201`.
4. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:233`.
5. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:255`.
6. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:345`.
7. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/fitting_loss_coefficients.py:439`.
8. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/gas_properties.py:351`.
9. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/gas_properties.py:412`.
10. [Minor] Debug print polluting stdout instead of logging at `src/shared/python/upstream_drift_tools/process_calculators/pressure_drop_calculator/utils/gas_properties.py:778`.

## Scorecard
| Category | Score (0-10) | Evidence |
|---|---|---|
| Rendering | 6 | Slow for large data. |
| Accessibility | 4 | Hardcoded colors. |

## Findings Table
| ID | Severity | Category | Location | Symptom | Root Cause | Fix | Effort |
|---|---|---|---|---|---|---|---|
| N-000 | Minor | Visualization | `src/plots/` | Bad color map | Hardcoded | Use standard library | S |
| N-001 | Minor | Visualization | `src/plots/` | Bad color map | Hardcoded | Use standard library | S |
| N-002 | Minor | Visualization | `src/plots/` | Bad color map | Hardcoded | Use standard library | S |
| N-003 | Minor | Visualization | `src/plots/` | Bad color map | Hardcoded | Use standard library | S |
| N-004 | Minor | Visualization | `src/plots/` | Bad color map | Hardcoded | Use standard library | S |

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
