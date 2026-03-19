# Jules Orchestration Runbook

Date: 2026-03-19

## Purpose

This runbook explains how to operate the Jules-only GitHub issue orchestration workflows introduced in this repository.

## Entry Points

The orchestration layer supports four main entry points:

- issue labels and issue creation using the `Jules Task` template
- manual `workflow_dispatch` on the control tower and worker workflows
- issue and PR comment commands
- scheduled queue and PR sweeps
- scheduled cleanup and PR compilation sweeps

## Required Secrets And Variables

Secrets:

- `JULES_API_KEY`

Variables:

- `JULES_AUTOMATION_ENABLED`
- `JULES_AUTOMATION_PAUSED`
- `JULES_MAX_PARALLEL_ISSUES`
- `JULES_MAX_PR_REPAIR_ATTEMPTS`
- `JULES_DEFAULT_BRANCH`

## Triggering Work

### Issue-driven

Use the `Jules Task` issue template, apply a task-class label, risk label, and parallelism label, then add `jules:ready`.

### Manual

Use `workflow_dispatch` on:

- `jules-control-tower-v2.yml`
- `jules-issue-worker.yml`
- `jules-pr-shepherd.yml`
- `jules-pr-compiler.yml`
- `jules-cleanup.yml`

### Comment commands

Supported issue commands:

- `/jules-run`
- `/jules-retry`
- `/jules-pause`
- `/jules-resume`
- `/jules-status`

Supported PR commands:

- `/jules-fix-ci`
- `/jules-address-comments`
- `/jules-compile`
- `/jules-stop`

## Pause And Resume

### Global pause

Set `JULES_AUTOMATION_PAUSED=true`.

This prevents new dispatches while allowing maintainers to inspect the queue and in-flight state.

### Per-item pause

Apply `jules:blocked` to an issue or PR, or use `/jules-pause`.

### Resume

Remove `jules:blocked` or use `/jules-resume`.

## PR Shepherd Guardrails

The PR shepherd is deliberately conservative.

- It only acts on Jules-managed PRs.
- It only retries bounded, automatable failure classes.
- It obeys a cooldown window.
- It stops after the configured repair-attempt ceiling.
- It labels or comments for human escalation when a failure is not suitable for automated repair.

## PR Compiler Guardrails

The PR compiler is opt-in and should stay conservative.

- It only compiles PRs labeled `queue:compile-candidate`.
- It only compiles `parallel:allowed` Jules-managed PRs.
- It only compiles bounded task classes such as docs, cleanup, review-fix, and test-gen.
- It creates a draft compiled PR so maintainers can review the integration batch before merge.
- It skips branches that do not merge cleanly and reports those conflicts in the compiled PR body.

## Cleanup Guardrails

The cleanup workflow is report-first by default.

- Scheduled cleanup runs should stay in dry-run mode first.
- Stale Jules-managed PRs are marked `jules:needs-human` before any closure is considered.
- Stale issue state is reconciled by removing `jules:queued` or `jules:assigned` and escalating to human review.
- Stale branch deletion must remain an explicit manual choice.

## Suggested Rollout Order

1. Sync labels from `.github/jules/labels.yml`.
2. Merge policy files and issue template.
3. Enable the control tower in dry-run mode first.
4. Enable issue worker dispatch for explicitly labeled issues only.
5. Enable PR shepherd after validating issue-worker behavior.
6. Enable cleanup in dry-run mode and review summaries.
7. Enable PR compiler only for explicit compile-candidate labels.

## Cross-Repository Adoption

When copying this model to another repository:

1. copy `.github/jules/`
2. copy the workflow files
3. copy the issue template
4. review CI workflow names referenced by PR shepherd
5. review stale cleanup thresholds and compile policy
6. set repo variables and secrets
7. start in dry-run mode
