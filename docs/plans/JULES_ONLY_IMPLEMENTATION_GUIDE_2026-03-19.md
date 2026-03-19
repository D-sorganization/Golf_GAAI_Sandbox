# Jules-Only Orchestration Implementation Guide

Date: 2026-03-19

## Purpose

This guide translates the Jules-only orchestration plan into implementation instructions detailed enough for agents to execute consistently across repositories.

It answers four practical questions:

1. What do we version-control?
2. How do we trigger the workflows?
3. How do we pause, resume, and operate them safely?
4. How do we keep Jules-managed PRs moving toward green CI without creating unsafe automation loops?

## Implementation Goal

Stand up a reusable GitHub-native Jules automation layer that can be copied repo to repo and controlled primarily through:

- checked-in workflow files
- checked-in policy/config files
- GitHub labels
- issue templates
- workflow dispatch inputs
- repository variables and secrets

The design should require no local daemon and minimal operator intervention once configured.

## What Must Be Version-Controlled

These parts of the system should be committed to every participating repository:

### Workflow entrypoints

- top-level control tower workflow
- issue worker workflow
- CI repair workflow
- PR shepherd workflow
- comment batching workflow
- PR compiler workflow
- cleanup workflow

### Workflow policy files

- task-class to validation-profile mapping
- branch naming rules
- pause/resume behavior
- retry ceilings
- schedule defaults
- label names and meanings

### GitHub-facing contract

- issue template for automatable work
- pull request body fragments or template text
- slash command policy
- operator runbook

### Suggested repository paths

- `.github/workflows/jules-control-tower.yml`
- `.github/workflows/jules-issue-worker.yml`
- `.github/workflows/jules-ci-repair.yml`
- `.github/workflows/jules-pr-shepherd.yml`
- `.github/workflows/jules-comment-collector.yml`
- `.github/workflows/jules-comment-processor.yml`
- `.github/workflows/jules-pr-compiler.yml`
- `.github/workflows/jules-cleanup.yml`
- `.github/ISSUE_TEMPLATE/jules_task.yml`
- `.github/jules/policy.yml`
- `.github/jules/task_classes.yml`
- `.github/jules/validation_profiles.yml`
- `docs/operations/jules-orchestration-runbook.md`

### What should not be version-controlled

- `JULES_API_KEY`
- bot tokens
- temporary provider credentials
- live workflow runtime state that belongs in GitHub issues, PRs, or workflow metadata instead

## Required GitHub Secrets And Variables

### Secrets

- `JULES_API_KEY`
- `GITHUB_TOKEN` for standard repo operations
- optional elevated bot token if cross-repo or restricted operations require it

### Variables

- `JULES_AUTOMATION_ENABLED`
- `JULES_AUTOMATION_PAUSED`
- `JULES_MAX_PARALLEL_ISSUES`
- `JULES_MAX_PR_REPAIR_ATTEMPTS`
- `JULES_ALLOWED_SCHEDULES`
- `JULES_DEFAULT_BRANCH`

Recommended defaults:

- `JULES_AUTOMATION_ENABLED=true`
- `JULES_AUTOMATION_PAUSED=false`
- `JULES_MAX_PARALLEL_ISSUES=3`
- `JULES_MAX_PR_REPAIR_ATTEMPTS=3`

## Triggering Model

The orchestration layer should support four trigger families.

### 1. Automatic issue triggers

Use when:

- a new issue is created from an automation workflow
- an issue is labeled `jules:ready`
- an issue is labeled with a task class and risk level

Recommended events:

- `issues: opened`
- `issues: labeled`
- `issues: reopened`

Recommended behavior:

- validate issue metadata
- reject or relabel malformed issues
- queue valid issues for the control tower

### 2. Scheduled triggers

Use when:

- you want regular triage or batch processing
- you want predictable overnight work windows
- you want a PR shepherd sweep to catch stalled automation

Recommended schedules:

- every 15 or 30 minutes for queue sweeps if load is light
- hourly or every few hours for maintenance clusters
- overnight batches for lower-priority cleanup and refactor work
- periodic PR shepherd sweep in addition to event-driven CI monitoring

### 3. Manual triggers

Use when:

- an operator wants to run the queue now
- an operator wants to force a specific issue or PR through a worker
- an operator wants to retry, compile, or clean up immediately

Recommended support:

- `workflow_dispatch` with explicit inputs
- issue comment commands such as `/jules-run`
- issue comment commands such as `/jules-retry`
- PR comment commands such as `/jules-fix-ci`
- manual `target` choices in the control tower

### 4. CI event triggers

Use when:

- a workflow run fails on a Jules-managed PR
- a protected branch CI failure needs urgent action
- a Jules PR becomes mergeable or blocked

Recommended events:

- `workflow_run: completed`
- optional `check_suite: completed`

Recommended behavior:

- inspect whether the PR or branch is Jules-managed
- apply retry ceilings and cooldown windows
- route to PR shepherd or CI repair worker as appropriate

## Manual Shortcuts For Operators

The system should provide predictable manual shortcuts that avoid editing workflow files or relabeling by hand.

### Recommended issue commands

- `/jules-run`
- `/jules-retry`
- `/jules-pause`
- `/jules-resume`
- `/jules-status`
- `/jules-batch-now`

### Recommended PR commands

- `/jules-fix-ci`
- `/jules-address-comments`
- `/jules-retry-validation`
- `/jules-stop`

These commands should be handled by a lightweight comment-command router workflow that:

- authenticates actor permissions
- translates commands into labels or `workflow_dispatch`
- records the command invocation visibly in issue or PR comments

## Pause, Resume, And Safe Stop Design

Yes, the system should support pausing.

Pausing is important for:

- high-risk incidents
- branch protection changes
- CI outages
- provider issues
- noisy or unsafe automation behavior

### Global pause

Implement via repository variable:

- `JULES_AUTOMATION_PAUSED=true`

Control-tower behavior when paused:

- do not dispatch new work
- allow in-flight workflows to finish unless the worker is explicitly stop-capable
- comment or summarize that the repo is paused

### Scoped pause

Implement via labels or variable subsets:

- `pause:jules-ci-repair`
- `pause:jules-issue-worker`
- `pause:jules-pr-shepherd`

This allows you to pause one automation class without freezing the entire system.

### Per-issue pause

Implement via issue label:

- `jules:blocked`

or command:

- `/jules-pause`

### Resume behavior

On resume:

- the control tower should sweep queued items
- stale in-progress state should be reconciled
- no issue should be dispatched twice

## Detailed Workflow Set

### 1. Control Tower

Purpose:

- central routing and gating layer

Triggers:

- issues opened, labeled, reopened
- issue comment commands
- workflow_run completed
- schedule
- workflow_dispatch

Responsibilities:

- check repo pause state
- validate issue or PR eligibility
- prevent duplicate dispatch
- select worker family
- enforce max parallel limit
- write status labels or comments

### 2. Issue Worker

Purpose:

- process one automatable issue

Inputs:

- issue number
- task class
- validation profile
- branch mode
- max scope

Responsibilities:

- gather issue context
- find or create working branch
- reuse an open PR if present
- dispatch Jules session
- poll for result
- run validation
- create or update PR
- post structured completion report

### 3. Comment Collector And Processor

Purpose:

- collect noisy review comments and address them in batches

Collector responsibilities:

- capture actionable comments
- ignore bots and closed PRs
- queue comments into checked-in or transient structured storage

Processor responsibilities:

- deduplicate comments
- group by PR
- reuse PR branch
- dispatch a bounded Jules session
- avoid opening new PRs unnecessarily

### 4. CI Repair Worker

Purpose:

- repair failed CI on Jules-managed branches or critical branches

Responsibilities:

- fetch failed logs
- decide whether failure class is automatable
- create or reuse repair branch
- dispatch minimal Jules repair prompt
- stop after retry ceiling

### 5. PR Shepherd

Purpose:

- keep open Jules-managed PRs moving toward green CI and review completion

This is the missing piece that answers your question about iterating on open PRs until they pass CI/CD.

Yes, you can create one, but it must be careful and bounded.

## PR Shepherd Design

Jules is not naturally a continuous monitor, so the workflow should be event-driven and sweep-based rather than trying to keep a long-running watch process.

### Trigger conditions

Use two trigger modes:

- `workflow_run: completed` for relevant CI workflows
- scheduled sweep every few hours for open Jules-managed PRs

### Eligibility rules

Only act if all are true:

- PR author or labels mark it as Jules-managed
- PR is open
- PR is not draft unless explicitly allowed
- PR is not labeled `jules:needs-human`
- PR has not exceeded repair ceiling
- repo is not paused

### What the shepherd should do

1. inspect the latest CI results
2. classify whether the failures are automatable
3. if automatable, dispatch a bounded fix attempt on the same branch
4. post a structured progress comment
5. increment repair-attempt count
6. stop and escalate if attempts exceed configured ceiling

### What the shepherd must not do

- loop forever on the same PR
- create a new PR for every repair attempt
- repair failures on human-owned PRs unless explicitly labeled
- keep retrying when the failures are flaky, infrastructural, or ambiguous

### Retry policy

Recommended defaults:

- maximum 3 repair attempts per PR per 24 hours
- cooldown of at least 15 to 30 minutes between attempts
- immediate stop if failure class is not confidently automatable

### Failure classes suitable for automatic repair

- formatting
- import ordering
- obvious lint violations
- missing type imports
- straightforward test breakages tied to the PR changes

### Failure classes that should escalate instead

- flaky infrastructure
- unrelated baseline breakage
- merge conflicts
- heavy integration failures
- security-sensitive changes
- broad architectural regressions

## Scheduling Recommendations

Yes, scheduling should be part of the design.

Recommended schedule families:

### Fast loop

- queue sweep every 15 to 30 minutes
- command router every few minutes if needed

### Business-hours support

- PR shepherd every 1 to 3 hours
- CI repair immediately on workflow completion

### Overnight batch

- issue cleanup
- comment processing
- PR compilation
- docs and tech debt clusters

### Weekly hygiene

- stale PR cleanup
- stale issue reconciliation
- automation metrics summary

## Cross-Repository Rollout Strategy

To support this pattern across all repos, treat the orchestration layer as a reusable package of policy and workflow files.

### Recommended rollout order

1. create the standard docs and policy files
2. create the standard labels
3. add the control tower and issue worker
4. add comment batching
5. add PR shepherd
6. add cleanup and compiler workflows

### Repo onboarding checklist

Each repo should have:

- Jules API secret configured
- standard labels installed
- issue template installed
- baseline CI workflow names mapped
- pause variable configured
- allowed schedules reviewed
- maintainer owner list defined for command authorization

### Merge strategy across repos

For each repo:

- create a dedicated orchestration branch
- open one setup PR
- validate workflow syntax and permissions
- merge only after CI and dry-run validation pass

Do not roll out the full active automation set to every repo at once. Start with:

- labels
- issue template
- control tower in report-only or dry-run mode
- issue worker on explicitly labeled issues only

## Suggested Dry-Run And Safety Modes

Every major workflow should support a dry-run mode.

### Dry-run behavior

- analyze targets
- summarize planned action
- do not dispatch Jules
- do not create PRs
- do not mutate branches

### Limited-launch mode

Recommended initial flag:

- only dispatch on issues labeled `jules:ready`

This prevents accidental repository-wide activation during rollout.

## Detailed Implementation Backlog

These are the first implementation issues I recommend creating.

### Epic

- Stand up a reusable Jules-only GitHub issue orchestration control plane for this repository.

### Issue 1

- Define the canonical label taxonomy, issue template, and policy files.

Expected outputs:

- standard labels
- issue template
- `.github/jules/*.yml` policy files

### Issue 2

- Build `jules-control-tower.yml` v2 with pause checks, duplicate-dispatch protection, and manual dispatch inputs.

Expected outputs:

- central router
- dry-run mode
- schedule support
- command routing support

### Issue 3

- Build `jules-issue-worker.yml` with branch reuse, PR reuse, validation profiles, and structured issue reporting.

Expected outputs:

- one issue to one branch/PR pattern
- bounded session dispatch
- post-run summary comments

### Issue 4

- Build comment collection and batch-processing workflows with deduplication and safe PR reuse.

Expected outputs:

- stable queue structure
- grouped PR comment handling
- no PR cascades

### Issue 5

- Build `jules-pr-shepherd.yml` to iterate carefully on open Jules-managed PRs until they pass CI or hit bounded stop conditions.

Expected outputs:

- event-driven CI monitoring
- scheduled sweep
- retry ceiling
- cooldown handling
- escalation comments

### Issue 6

- Build cleanup and PR compiler workflows to reduce branch and PR sprawl.

Expected outputs:

- stale branch cleanup
- stale automation PR policy
- compiled PR creation rules

### Issue 7

- Write the operator runbook covering trigger methods, pause/resume, failure handling, and cross-repo rollout.

Expected outputs:

- `docs/operations` runbook
- troubleshooting and safety procedures

## Agent Execution Instructions

When agents implement this system, they should follow these rules:

1. Do not introduce auto-dispatch for all issues at once.
2. Start with explicit labels and dry-run support.
3. Reuse branches and PRs whenever possible.
4. Do not create infinite repair or retry loops.
5. Keep workflow logic centralized where possible.
6. Prefer report-only mode before mutation mode.
7. Every workflow must write enough structured output for a human to audit what happened.
8. Every workflow must have clear stop conditions.
9. Every new workflow must document required labels, variables, and secrets.
10. Roll out one repo at a time until the pattern is proven stable.

## Recommended Near-Term Decision

The next implementation step should be:

1. merge the planning and implementation docs
2. create the epic and first implementation issues
3. build the version-controlled policy layer first
4. then build the control tower and issue worker
5. then add PR shepherding carefully after the issue pipeline is stable

That sequence gives you a version-controlled foundation, clean operator control, and a path toward automated PR convergence without trying to solve all workflow classes at once.
