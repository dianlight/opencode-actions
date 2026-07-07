# OpenCode Workflow Flows

This repository contains five GitHub Actions workflows that implement two
end-to-end automation pipelines: one for **issues** (triage → PR creation →
sequential task implementation) and one for **pull requests** (review → triage →
implementation).

## Issue Flow

Triggered when a collaborator posts `/oc` (or `/opencode`) on an issue. The
workflow triages the request, iterates with the reporter, and — once approved —
creates a new pull request with a CHANGELOG entry and the full task list in the
body. Each task is then implemented sequentially against that PR branch.

```mermaid
flowchart TD
    A["/oc instruction on issue"] --> B["opencode-triage-issue.yaml"]
    B --> C{"`opencode:awaiting-response` label present?"}
    C -- No --> D{"Enough info?"}
    C -- Yes --> E{"Quick approval match?"}
    E -- "approved / LGTM / go ahead / :+1:" --> F["Post acknowledgment + update labels + dispatch new-pr"]
    E -- Other reply --> D
    D -- No --> G["Post clarifying questions"]
    G --> H["Set opencode:awaiting-response"]
    H --> I["Human replies with more info"]
    I --> B
    D -- Yes --> J["Post structured proposal as task list"]
    J --> K["Set opencode:awaiting-response"]
    K --> L{"Human response"}
    L -- "New instruction / feedback" --> B
    L -- "Approved (comment)" --> M["Post acknowledgment"]
    M --> N["Set opencode:approved-for-implementation"]
    N --> O["Dispatch opencode-new-pr.yaml"]
    O --> P["opencode-new-pr.yaml"]
    P --> Q["Create/update CHANGELOG.md"]
    Q --> R["Create feature branch"]
    R --> S["Open PR with task list in body"]

    F --> P

    S --> T{"For each task (sequentially)"}
    T --> U["Dispatch opencode-implement.yaml"]
    U --> V["Checkout existing PR branch"]
    V --> W["Implement task + commit + push"]
    W --> T
```

### Workflow state labels

| Label | Meaning | Set by |
|-------|---------|--------|
| `opencode:awaiting-response` | Waiting for human input | triage-issue |
| `opencode:approved-for-implementation` | Ready to implement | triage-issue |

### Files involved

| Workflow | File | Trigger |
|----------|------|---------|
| **Triage (issue)** | `.github/workflows/opencode-triage-issue.yaml` | `issue_comment` containing `/oc`, or label `opencode:awaiting-response` present. Quick approval matched by shell keyword check (no AI). |
| **Orchestrator** | `.github/workflows/opencode-new-pr.yaml` | `workflow_dispatch` with `issue-number` from triage approval |
| **Implement** | `.github/workflows/opencode-implement.yaml` | `pull_request: [labeled]` with `opencode:approved-for-implementation`, or `workflow_dispatch` with `pull-request-number` (per-task from orchestrator) |

---

## PR Flow

Triggered when a PR is opened or updated. The code review workflow reviews the
diff. If the author responds with `/oc` (or a review finding needs discussion),
the triage workflow analyses the PR and submits a proposal as a formal PR review
with inline suggestions. Once accepted, the implementation workflow pushes
commits directly to the existing PR branch.

```mermaid
flowchart TD
    A["PR opened / updated"] --> B["opencode-review.yaml"]
    B --> C["Submit formal code review"]
    C --> D["/oc instruction or review finding"]
    D --> E{"`opencode:awaiting-response` label present?"}
    E -- No --> F{"Enough info?"}
    E -- Yes --> G{"Quick approval match?"}
    G -- "Approved / LGTM / go ahead / :+1:" --> H["Post acknowledgment review + update labels + dispatch implement"]
    G -- Other reply --> F
    F -- No --> I["Submit review with inline questions"]
    I --> J["Set opencode:awaiting-response"]
    J --> K["Human responds"]
    K --> E
    F -- Yes --> L["Submit proposal as PR review with suggestions"]
    L --> M["Set opencode:awaiting-response"]
    M --> N{"Human action"}
    N -- "Discussion / changes requested" --> E
    N -- "Approved (Approve review)" --> O["Submit acknowledgment review"]
    O --> P["Set opencode:approved-for-implementation"]
    P --> Q["opencode-implement.yaml"]
    Q --> R["Checkout existing PR branch"]
    R --> S["Implement + commit + push"]

    H --> Q
```

### Workflow state labels

| Label | Meaning | Set by |
|-------|---------|--------|
| `opencode:awaiting-response` | Waiting for human input | triage-pr |
| `opencode:approved-for-implementation` | Ready to implement | triage-pr |

### Files involved

| Workflow | File | Trigger |
|----------|------|---------|
| **Review** | `.github/workflows/opencode-review.yaml` | `pull_request: [opened, synchronize, reopened, ready_for_review]`. Skips draft PRs. |
| **Triage (PR)** | `.github/workflows/opencode-triage-pr.yaml` | `pull_request_review_comment` or `pull_request_review` containing `/oc`, or label `opencode:awaiting-response` present. Quick approval matched by shell keyword check or "Approve" review state (no AI). |
| **Implement** | `.github/workflows/opencode-implement.yaml` | `pull_request: [labeled]` with `opencode:approved-for-implementation` |

---

## Workflow behaviours

### `opencode-new-pr.yaml` — Issue PR orchestrator

Triggered by `workflow_dispatch` with an `issue-number` from the triage workflow
after approval. This workflow replaces the old behaviour where
`opencode-implement.yaml` directly handled issue triggers. It has two jobs:

| Job | Action |
|-----|--------|
| **create-pr** | Fetches the approved proposal comment from the issue, extracts the markdown task list (`- [ ]` items), creates/updates `CHANGELOG.md` with the issue summary and task list, creates a feature branch, and opens a PR with the task list as checkboxes in the body — all links back to the issue with `Closes #N`. |
| **execute-tasks** | Iterates through each task sequentially. For each task, dispatches `opencode-implement.yaml` with `pull-request-number` and `task-description`, then waits for that run to complete before moving to the next task. Fails fast if any task fails. |

### `opencode-implement.yaml` — PR-only implementation

This workflow now only handles pull request triggers:

| Trigger | Action |
|---------|--------|
| **Pull request label** (`pull_request: [labeled]` with `opencode:approved-for-implementation`) | Checkouts the existing PR branch via `gh pr checkout`, implements the full approved proposal, commits, and pushes to that same branch |
| **Workflow dispatch** (from `opencode-new-pr.yaml` with `pull-request-number` + `task-description`) | Checkouts the PR branch and implements only the specific task described by `task-description` |

## Token strategy

- **triage-issue** and **triage-pr** use the OpenCode GitHub App token (via OIDC
  exchange, `use_github_token: false`) so that label changes trigger downstream
  workflow events.
- **triage-issue** and **triage-pr** also have a pre-step that uses
  `GITHUB_TOKEN` for quick approval detection via shell keyword matching — this
  bypasses the AI entirely for simple approvals and dispatches the orchestrator
  or implement workflow directly via `workflow_dispatch`.
- **opencode-new-pr** uses `GITHUB_TOKEN` for API calls (branch creation, PR
  creation, commenting) and the OpenCode API key for CHANGELOG creation.
- **review** and **implement** use the built-in `GITHUB_TOKEN`
  (`use_github_token: true`) since they do not need to chain further workflow
  events.

## Optimizations

### Quick approval pre-step

Both triage workflows include a shell-based pre-step that runs only when the
`opencode:awaiting-response` label is present. It checks for explicit approval
keywords (`approved`, `LGTM`, `go ahead`, `:+1:`) or, in the PR workflow, an
"Approve" review verdict. If matched, the pre-step:

1. Posts an acknowledgment (issue comment or PR review)
2. Updates labels (for documentation — via `GITHUB_TOKEN`)
3. Dispatches the downstream workflow:
   - **Issue flow:** dispatches `opencode-new-pr.yaml` (orchestrator)
   - **PR flow:** dispatches `opencode-implement.yaml` directly

This completely bypasses the AI, saving one full triage run per approval cycle.

### Sequential task execution

The `opencode-new-pr.yaml` orchestrator runs tasks one at a time. Each task is
dispatched to `opencode-implement.yaml`, and the orchestrator waits for that run
to complete before proceeding. If a task fails, execution stops immediately —
subsequent tasks are not attempted.

### Draft PR skip

The `opencode-review.yaml` workflow skips draft pull requests
(`!github.event.pull_request.draft`), preventing unnecessary AI reviews on
work-in-progress code.

### Large PR skip

The `opencode-review.yaml` workflow also skips PRs with 50+ changed files or
3000+ additions (`github.event.pull_request.changed_files < 50` and
`github.event.pull_request.additions < 3000`), where AI review quality degrades
and token costs spike.

### Trivial-only skip

A pre-step in `opencode-review.yaml` inspects the diff against the base branch.
If only documentation, config, lock files, images, or other non-code files are
changed (no `.js`, `.ts`, `.py`, `.rs`, `.go`, `.c`, `.cpp`, `.h`, `.css`,
`.sh`, `.sql`, etc.), the AI review is skipped entirely.

### Minimum instruction length

Both triage workflows require instruction text to be longer than 10 characters
when triggered by `/oc` or `/opencode`. A bare command with no context is
rejected without AI processing. Follow-up responses triggered by the
`opencode:awaiting-response` label bypass this check.
