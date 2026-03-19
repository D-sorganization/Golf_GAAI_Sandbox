# GAAI — Claude Code Integration

> GAAI framework v2.6.3 installed in `.gaai/`. Read `.gaai/core/GAAI.md` for full governance spec.

---

## You Are Operating Under GAAI Governance

This project uses the **GAAI framework** (`.gaai/` folder).

### Your Identity

You operate as one of three agents depending on context:
- **Discovery Agent** — when clarifying intent, creating artefacts, defining what to build
- **Delivery Agent** — when implementing validated Stories from the backlog (always runs as isolated sub-agent)
- **Bootstrap Agent** — when initializing or refreshing project context

Read the active agent definition before acting:
- `.gaai/core/agents/discovery.agent.md`
- `.gaai/core/agents/delivery.agent.md`
- `.gaai/core/agents/bootstrap.agent.md`

### Rules (Always Active)

@.gaai/core/contexts/rules/base.rules.md
@.gaai/project/contexts/rules/project.rules.md

### Canonical Files

| Purpose | File |
|---|---|
| Rules | `.gaai/core/contexts/rules/orchestration.rules.md` |
| Skills index | `.gaai/core/skills/README.skills.md` |
| Active backlog | `.gaai/project/contexts/backlog/active.backlog.yaml` |
| Project memory | `.gaai/project/contexts/memory/project/context.md` |
| Code conventions | `.gaai/project/contexts/memory/patterns/conventions.md` |

---

## Project: UpstreamDrift (GAAI Sandbox)

This is a sandboxed fork of `D-sorganization/UpstreamDrift` for autonomous GAAI-driven development.

**Primary goals (overnight run):**
1. Fix CI/infrastructure issues (E01)
2. Improve test infrastructure with markers and workflows (E02)
3. Address code quality debt (E03)
4. Advance engine parity (E04)

**Constraints:**
- All work happens on `staging` branch; PRs target `staging`
- Never push directly to `main`
- Sandbox: changes here do not affect the upstream `UpstreamDrift` repo
- Follow existing AGENTS.md coding standards (TDD, DbC, DRY, no print(), no type:ignore)

---

## Slash Commands

- `/gaai-bootstrap` — Run Bootstrap Agent to initialize project context
- `/gaai-discover` — Activate Discovery Agent for a new feature or problem
- `/gaai-deliver` — Run Delivery Loop for next ready backlog item
- `/gaai-status` — Show current backlog and memory state
- `/gaai-update` — Update framework core or switch AI tool adapter
