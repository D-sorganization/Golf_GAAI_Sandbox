---
type: memory
category: decisions
id: DECISIONS-LOG
tags:
  - decisions
  - governance
created_at: 2026-03-18
updated_at: 2026-03-18
---

# Decision Log

> Append-only. Never delete or overwrite decisions.
> Only the Discovery Agent may add entries (or Bootstrap Agent during initialization).
> Format: one entry per decision, newest at top.
> For large projects, split by domain: `decisions/auth.md`, `decisions/api.md`, etc.

---

## Entry Template

```markdown
### DEC-YYYY-MM-DD-NN — [Decision Title]

**Context:** Why a decision was needed.
**Decision:** What was chosen.
**Rationale:** Why this option.
**Impact:** What it affects.
**Date:** YYYY-MM-DD
```

---

### DEC-2026-03-18-01 — GAAI Sandbox Strategy

**Context:** Need to test autonomous AI-driven development against an active project overnight without risk to the main repo.
**Decision:** Fork UpstreamDrift into Golf_GAAI_Sandbox and install GAAI framework. All autonomous work happens on `staging`; PRs are created but NOT auto-merged. Human reviews PRs.
**Rationale:** Sandboxed fork isolates risk. GAAI's "AI creates PRs, humans merge" model is appropriate for first overnight run.
**Impact:** All story branches target staging in Golf_GAAI_Sandbox, not UpstreamDrift.
**Date:** 2026-03-18

### DEC-2026-03-18-02 — Issue-to-Story Conversion

**Context:** GAAI requires a backlog of refined Stories with acceptance criteria. The source repo has well-defined GitHub issues.
**Decision:** Convert issues #1960, #1961, #1962, #1965 (CI fixes), #1964, #1963, #1951 (testing), #1950, #1957 (quality), #1956, #1955 (engines) into GAAI Stories E01S01–E04S02. Skip issues #1894, #1899, #1900 (git history scrub — risky for autonomous agent), #1744 (coverage epic — too broad for overnight run).
**Rationale:** Selected issues are well-scoped, have clear acceptance criteria, and are safe for autonomous implementation. Git history scrubs are destructive and require human oversight.
**Impact:** 11 refined stories in initial backlog.
**Date:** 2026-03-18

<!-- Add decisions above this line, newest first -->
