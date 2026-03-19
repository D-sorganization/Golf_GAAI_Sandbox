---
type: rules
category: project
id: RULES-PROJECT-001
tags:
  - project-specific
  - sandbox
  - safety
created_at: 2026-03-18
updated_at: 2026-03-18
---

# Golf GAAI Sandbox — Project Rules

These rules extend and override base GAAI rules for this specific project.

---

## Sandbox Safety Rules

1. **Staging-only.** All AI work happens on the `staging` branch. Never commit directly to `main`. Story branches target `staging` for PRs.
2. **No auto-merge.** The Delivery Agent creates PRs but NEVER merges them. Merging is a human-only action.
3. **No destructive history operations.** Do NOT run `git filter-branch`, `git rebase -i`, or `BFG Repo Cleaner`. Issues #1894, #1899, #1900 (git history scrub) are explicitly OUT OF SCOPE for autonomous delivery.
4. **No secret commits.** Never commit `.env` files, API keys, credentials, or private keys.
5. **No large binary files.** Never add files >10MB. The upstream repo already has one large CSV (50MB) — do not add more.

---

## Code Quality Gates (enforced before PR creation)

6. **ruff check must pass** on all modified Python files before creating a PR: `ruff check src tests`
7. **No new print() calls** introduced in `src/` — check with `grep -rn "print(" src/` on modified files
8. **No new type: ignore** introduced without an explanatory comment
9. **TDD required** for all new Python modules and functions in `src/`

---

## Branch Naming

10. Story branches follow GAAI convention: `story/{story-id}` (e.g., `story/E01S01`)
11. Never reuse a branch name for a different story

---

## Escalation Triggers (stop and create PR comment instead of proceeding)

12. Any story that requires modifying `.github/workflows/ci-standard.yml` in a way that could break all CI — escalate first
13. Any story that requires a database migration or schema change — escalate first
14. Any story that touches `src/shared/python/engine_core/` in a way that could affect all engines — escalate first

---

## Upstream Reference

15. This sandbox is forked from `D-sorganization/Golf_Modeling_Suite`. Do NOT open PRs against the upstream repo — only against `D-sorganization/Golf_GAAI_Sandbox`.
