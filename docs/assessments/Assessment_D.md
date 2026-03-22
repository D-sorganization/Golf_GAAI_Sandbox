# Assessment D: User Experience & Developer Journey

## Executive Summary
- CLI interface lacks consistent argument parsing.
- Error messages are often raw stack traces.
- Journey involves too many manual steps.
- Missing progress indicators for long running tasks.
- Configuration is spread across multiple formats.

## Top 10 Risks
1. [Major] Raw stack trace presented to user at `src/shared/python/calc_backend/routers/rotation_converter.py:81`.
2. [Major] Raw stack trace presented to user at `src/shared/python/engine_core/plugin_registry.py:207`.
3. [Major] Raw stack trace presented to user at `src/shared/python/engine_core/plugin_registry.py:251`.
4. [Major] Raw stack trace presented to user at `src/shared/python/theme/__init__.py:60`.
5. [Major] Raw stack trace presented to user at `src/cli.py:4`.
6. [Major] Raw stack trace presented to user at `src/cli.py:5`.
7. [Major] Raw stack trace presented to user at `src/cli.py:6`.
8. [Major] Raw stack trace presented to user at `src/cli.py:7`.
9. [Major] Raw stack trace presented to user at `src/cli.py:8`.
10. [Major] Raw stack trace presented to user at `src/cli.py:9`.

## Scorecard
| Category | Score (0-10) | Evidence |
|---|---|---|
| CLI Usability | 5 | Inconsistent arguments. |
| Error Messages | 4 | Raw stack traces shown. |

## Findings Table
| ID | Severity | Category | Location | Symptom | Root Cause | Fix | Effort |
|---|---|---|---|---|---|---|---|
| D-000 | Major | UX | `src/cli.py` | Poor error message | Uncaught exception | Add global error handler | M |
| D-001 | Major | UX | `src/cli.py` | Poor error message | Uncaught exception | Add global error handler | M |
| D-002 | Major | UX | `src/cli.py` | Poor error message | Uncaught exception | Add global error handler | M |
| D-003 | Major | UX | `src/cli.py` | Poor error message | Uncaught exception | Add global error handler | M |
| D-004 | Major | UX | `src/cli.py` | Poor error message | Uncaught exception | Add global error handler | M |

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
