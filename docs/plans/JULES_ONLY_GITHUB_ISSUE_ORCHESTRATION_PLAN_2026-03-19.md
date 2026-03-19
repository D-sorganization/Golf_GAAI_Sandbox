# Jules-Only GitHub Issue Orchestration Plan

Date: 2026-03-19

## Purpose

This document proposes a GitHub-native, Jules-only automation architecture for tackling repository work through GitHub Issues, GitHub Actions, branches, and pull requests.

The design goal is to:

- avoid dependence on local resources
- keep orchestration durable and visible in GitHub
- allow safe parallel agent work
- reduce branch and PR chaos
- keep the codebase clean while automation scales

This plan assumes Jules is the sole execution backend for autonomous code work in the initial rollout.

## Why a Jules-Only First Architecture Makes Sense

For this repository, a Jules-only first phase is the cleanest path to operational stability.

### Advantages

- cloud-based execution avoids local machine bottlenecks
- issue and PR automation already exists in this repo
- GitHub becomes the natural source of truth
- there is no need to solve multi-backend routing before the task model is stable
- existing workflows already demonstrate viable patterns for queueing, repair, and PR management

### Tradeoff

This is not the most flexible long-term architecture, but it is likely the fastest route to a reliable autonomous workflow.

The right strategy is:

- standardize Jules-first orchestration now
- keep the architecture backend-aware in naming and policy
- add other backends later only after the GitHub task contract is stable

## Existing Patterns To Build On

The repository already contains the foundations of a Jules-only control plane:

- `Jules-Control-Tower` routes events to worker workflows
- `Jules-Issue-Resolver` gathers priority issues and launches code-fix sessions
- `Jules-Hotfix-Creator` responds to CI failure on important branches
- `PR-Comment-Responder` queues review comments instead of creating workflow cascades
- `Jules-Comment-Processor` processes queued comments in batches
- `Jules-PR-Compiler` consolidates multiple PRs into a cleaner review surface
- `Jules-Auto-Assign-Issues` already uses issue labels and comments to bring Jules in

These workflows suggest the right core ideas:

- event routing should be centralized
- noisy work should be queued and batched
- agent work should be bounded by branch and task scope
- there should be explicit safeguards against loops and duplicate work
- cleanup and consolidation should be first-class concerns

## Architectural Objective

Create a Jules operating system for GitHub Issues with these properties:

1. every automated task starts from or maps to a GitHub Issue
2. every issue has explicit machine-readable routing metadata
3. every Jules run is auditable through issue comments, workflow runs, labels, and PR links
4. parallel work is allowed only when branch ownership and task boundaries are clear
5. PR sprawl is actively managed through compilation, reuse, and cleanup
6. automation can run continuously without making the repository messy

## Source of Truth

The recommended source-of-truth model is:

- GitHub Issues: work authorization and durable state
- GitHub Labels: routing, status, and policy signals
- GitHub Actions: scheduler, router, and dispatcher
- Pull Requests: change delivery
- `.jules/` checked-in artifacts: queueing, grouping, and intermediate orchestration state where needed

This plan does not require a local backlog manager for autonomous execution.

## Recommended Issue Model

Every issue intended for Jules automation should have a structured contract.

### Required fields

- objective
- scope
- acceptance criteria
- risk level
- task class
- allowed file or directory scope if bounded
- validation commands
- merge strategy

### Recommended issue sections

- `Objective`
- `Why This Matters`
- `Scope`
- `Out of Scope`
- `Acceptance Criteria`
- `Validation`
- `Risk Level`
- `Suggested Task Class`
- `Notes For Jules`

### Suggested task classes

- `issue:triage`
- `issue:ci-repair`
- `issue:docs`
- `issue:review-followup`
- `issue:refactor`
- `issue:test-generation`
- `issue:cleanup`
- `issue:feature`

The task class should drive both prompt shape and branch policy.

## Recommended Label Taxonomy

The current repo already uses labels informally in several workflows. The next step is to normalize them.

### Dispatch labels

- `jules:ready`
- `jules:queued`
- `jules:assigned`
- `jules:blocked`
- `jules:needs-human`
- `jules:done`

### Task-class labels

- `jules:triage`
- `jules:ci-repair`
- `jules:docs`
- `jules:review-fix`
- `jules:refactor`
- `jules:test-gen`
- `jules:cleanup`
- `jules:feature`

### Risk labels

- `risk:low`
- `risk:medium`
- `risk:high`

### Parallelism labels

- `parallel:allowed`
- `parallel:exclusive`

### Queue hygiene labels

- `queue:batched`
- `queue:deduplicated`
- `queue:superseded`

## Proposed Jules Workflow Topology

The repository currently has many Jules workflows. The medium-term design should consolidate them into a more regular topology.

### 1. One control tower

Use one top-level orchestrator as the only general router.

Recommended responsibilities:

- listen for issue events, PR events, workflow failures, schedules, and manual dispatch
- classify work items
- prevent duplicate dispatch
- assign work to the correct worker family
- enforce loop protection and retry limits

This should evolve from the current `Jules-Control-Tower`.

### 2. Worker families

Replace the long list of one-off specialist workflows over time with reusable worker families.

Recommended worker families:

- `jules-issue-worker`
- `jules-batch-comment-worker`
- `jules-ci-repair-worker`
- `jules-doc-worker`
- `jules-maintenance-worker`
- `jules-pr-compiler`

Each worker should accept inputs such as:

- issue number
- task class
- branch mode
- validation profile
- prompt template
- max scope

### 3. Shared utilities

Create shared patterns for:

- source lookup
- session creation
- polling
- workflow summary reporting
- branch creation and reuse
- PR creation and update
- retry and cooldown logic

This will reduce drift across current Jules workflows.

## Parallel Agent Strategy

Parallelism is useful, but only if it is disciplined.

### Rule 1: Parallelize by issue, not by intuition

Parallel Jules sessions should correspond to different issues or different explicitly partitioned work items.

Bad pattern:

- several sessions editing the same subsystem with overlapping scope

Good pattern:

- one issue for docs
- one issue for test generation
- one issue for a bounded refactor in a specific module

### Rule 2: Mark issues as parallel-safe or exclusive

Use labels and issue metadata to state whether an issue can run in parallel.

- `parallel:allowed` means branch-isolated, bounded work
- `parallel:exclusive` means only one active automation stream should touch the area

### Rule 3: Scope parallel workers tightly

Parallel Jules sessions should be constrained by:

- file list
- directory list
- issue acceptance criteria
- narrow prompt instructions

### Rule 4: Reuse PRs where appropriate

If an issue already has an open PR, subsequent Jules runs for that issue should update the same branch and PR where possible instead of opening a new one.

### Rule 5: Consolidate after fan-out

Parallelism should end with cleanup:

- merge compatible work
- close superseded PRs
- archive stale branches
- compile related PRs when review surface is too fragmented

The existing `Jules-PR-Compiler` is the right pattern to keep.

## Clean Codebase Rules

Parallel automation becomes dangerous when it floods the repo with branches, stale PRs, and partial fixes. The system should actively resist that.

### Branch discipline

Use predictable naming conventions:

- `jules/issue-<num>-<slug>`
- `jules/review-fix-<pr>-<timestamp>`
- `jules/ci-fix-<run-id>`
- `jules/compiled-<category>-<date>`

One issue should map to one primary working branch unless there is an explicit fan-out plan.

### PR discipline

Every automated PR should state:

- originating issue
- task class
- validation run
- whether it supersedes another PR

### Duplicate prevention

Before dispatching a new Jules task, the orchestrator should check:

- is there already an open PR for this issue
- is there already an active workflow run for this issue
- is the issue already labeled `jules:assigned` or `jules:queued`
- has the issue been marked superseded

### Queue hygiene

Batch and deduplicate where possible.

The current comment collector and comment processor already show the right idea:

- collect noisy micro-events
- deduplicate them
- process them as a batch

The same principle should apply to:

- issue triage
- review-followup tasks
- maintenance chores

### Cleanup policy

Every automation cycle should include cleanup behavior:

- close stale automation branches after merge
- label superseded issues and PRs
- compile fragmented related PRs
- stop creating new PRs when an existing PR can be reused

## Issue Lifecycle

The following state model should govern automated issue handling.

### 1. Intake

Issue is created or labeled for automation.

Expected labels:

- `jules:ready`
- one task-class label
- one risk label

### 2. Triage

The control tower determines:

- is the issue automatable
- should it be queued now
- is it parallel-safe
- does an existing branch or PR already exist

Possible outcomes:

- queue for Jules
- batch with related work
- mark `jules:needs-human`
- mark `parallel:exclusive`

### 3. Dispatch

The worker launches a Jules session and writes back:

- session started
- branch chosen
- workflow run URL
- expected validation profile

### 4. Execution

Jules works on the assigned branch with issue-bounded instructions.

### 5. Validation

Worker runs the required validation profile and reports results.

### 6. Delivery

Worker creates or updates a PR and links it back to the issue.

### 7. Consolidation

If multiple related PRs exist, the compiler decides whether to group them.

### 8. Closure

Issue is closed or relabeled based on outcome:

- `jules:done`
- `jules:blocked`
- `jules:needs-human`

## Batch-Oriented Operating Modes

Not all issue work should run immediately.

### Immediate mode

Use for:

- CI failures
- urgent regression fixes
- explicitly requested issue dispatch

### Scheduled batch mode

Use for:

- review comments
- docs hygiene
- cleanup
- low-priority issue sweeps
- tech debt clusters

### Overnight mode

Use for:

- larger issue sets
- refactoring clusters
- test generation
- PR compilation

The current repository already leans in this direction, and that is a good pattern to preserve.

## Recommended Worker Families

### Jules Issue Worker

Purpose:

- process one issue or one small issue bundle

Responsibilities:

- check labels and existing PR state
- create or reuse branch
- package issue context into prompt
- run validation
- create or update PR
- post structured issue summary

### Jules Batch Comment Worker

Purpose:

- process queued PR review comments in batches

Responsibilities:

- deduplicate comments
- group by PR
- reuse PR branch if possible
- apply only actionable code changes

### Jules CI Repair Worker

Purpose:

- fix CI failures from workflow runs

Responsibilities:

- pull failed logs
- create minimal repair branch
- apply bounded remediation
- stop after retry ceiling

### Jules Maintenance Worker

Purpose:

- run scheduled cleanup or hygiene work

Responsibilities:

- handle low-risk repetitive issue classes
- avoid creating unnecessary PR noise
- consolidate changes by category

### Jules PR Compiler

Purpose:

- reduce review fragmentation

Responsibilities:

- detect compatible automated PRs
- compile by category or issue family
- close or supersede fragmented PRs

## Prompting Strategy

Parallel automation stays cleaner when prompts are narrow and structured.

Each prompt should include:

- issue number and title
- exact scope
- acceptance criteria
- forbidden actions
- validation commands
- branch expectations
- PR expectations

Prompt rules:

- ask for minimal focused changes
- forbid unrelated refactors unless the task class is refactor
- require updating existing PRs when they exist
- require issue references in commit and PR text where appropriate

## Validation Profiles

Every task class should map to a validation profile.

### Profile A: docs and metadata

- markdown or docs checks as needed
- path and link sanity

### Profile B: bounded code cleanup

- formatter
- linter
- targeted tests

### Profile C: risky implementation

- formatter
- linter
- type checks
- targeted tests
- relevant integration tests if available

Workers should not guess validation. It should be configured by task class.

## Suggested Branch and PR Reuse Rules

### Reuse branch when

- the issue already has an open automation PR
- the new work is a continuation of the same issue
- review comments target the same PR

### Create a new branch when

- the issue is distinct
- the existing branch has drifted too far
- the new task is intentionally isolated

### Compile PRs when

- there are multiple open PRs in the same category
- review burden is too high
- branches are independent and merge-clean

### Do not compile when

- PRs solve unrelated issues
- the merge surface is risky
- one PR is awaiting focused human review

## Operational Metrics

Track these metrics in workflow summaries or dashboards:

- queue depth by task class
- active Jules sessions
- issue-to-PR conversion rate
- median time from issue ready to PR
- duplicate-dispatch rate
- superseded PR count
- merge conflict rate in compiled PRs
- ratio of immediate versus batched work

These metrics will tell you whether automation is helping or just generating churn.

## Rollout Phases

### Phase 0: Documentation and policy normalization

Deliverables:

- issue schema
- label taxonomy
- branch naming rules
- PR body conventions
- worker family map

### Phase 1: Issue-first routing

Deliverables:

- route issues through one control tower
- normalize `ready`, `assigned`, `blocked`, and `done` states
- add duplicate-dispatch checks

### Phase 2: Safe parallelism

Deliverables:

- `parallel:allowed` and `parallel:exclusive` model
- branch reuse policy
- issue-bound worker prompts

### Phase 3: Queue hygiene and batching

Deliverables:

- issue batching rules
- comment batching hardening
- stale queue cleanup
- supersede handling

### Phase 4: PR cleanliness

Deliverables:

- broader PR compiler policy
- stale branch cleanup
- one-issue-one-primary-PR guideline

### Phase 5: Metrics and hardening

Deliverables:

- dashboard or summary reports
- clearer retry and stop policies
- review of workflow sprawl

## Initial Backlog For This Approach

These are the first concrete planning or implementation issues I would create.

1. Define canonical Jules issue template for automatable work.
2. Define canonical Jules labels for status, task class, risk, and parallelism.
3. Refactor control tower design into a single issue-first router.
4. Create a reusable issue worker contract for Jules workflows.
5. Add duplicate-dispatch and existing-PR checks before every Jules launch.
6. Standardize branch naming and PR metadata for all Jules workflows.
7. Formalize comment batching and issue batching rules.
8. Expand PR compilation policy to reduce review fragmentation.
9. Define validation profiles by task class.
10. Add cleanup policies for stale automation branches, PRs, and superseded queue items.

## Recommended Near-Term Strategy

If the goal is to automate aggressively while keeping the codebase clean, the best next step is:

1. treat GitHub Issues as the only work queue for autonomous coding
2. standardize issue metadata and labels
3. route everything through one control tower
4. allow parallel Jules work only on bounded, label-approved issues
5. clean up aggressively through PR reuse, batching, and compilation

That gives you the benefits of autonomous parallel cloud execution without immediately inheriting the complexity of multi-backend orchestration.

## Appendix: Repository Workflows This Plan Builds On

- `/.github/workflows/Jules-Control-Tower.yml`
- `/.github/workflows/Jules-Issue-Resolver.yml`
- `/.github/workflows/Jules-Hotfix-Creator.yml`
- `/.github/workflows/Jules-Comment-Processor.yml`
- `/.github/workflows/PR-Comment-Responder.yml`
- `/.github/workflows/Jules-PR-Compiler.yml`
- `/.github/workflows/Jules-Auto-Assign-Issues.yml`
