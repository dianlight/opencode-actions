# OpenCode Workflow Flows

This repository contains four GitHub Actions workflows that implement two
end-to-end automation pipelines: one for **issues** (triage → implement) and one
for **pull requests** (review → triage → implement).

## Issue Flow

Triggered when a collaborator posts `/oc` (or `/opencode`) on an issue. The
workflow triages the request, iterates with the reporter, and — once approved —
creates a new pull request with the implementation.

```mermaid
flowchart TD
    A["/oc instruction on issue"] --> B["opencode-triage-issue.yaml"]
    B --> C{"`opencode:awaiting-response` label present?"}
    C -- No --> D{"Enough info?"}
    C -- Yes --> E{"Quick approval match?"}
    E -- "approved / LGTM / go ahead / :+1:" --> F["Post acknowledgment + update labels + dispatch implement"]
    E -- Other reply --> D
    D -- No --> G["Post clarifying questions"]
    G --> H["Set opencode:awaiting-response"]
    H --> I["Human replies with more info"]
    I --> B
    D -- Yes --> J["Post structured proposal"]
    J --> K["Set opencode:awaiting-response"]
    K --> L{"Human response"}
    L -- "New instruction / feedback" --> B
    L -- "Approved (comment)" --> M["Post acknowledgment"]
    M --> N["Set opencode:approved-for-implementation"]
    N --> O["opencode-implement.yaml"]
    O --> P["Create branch from default branch"]
    P --> Q["Implement + commit + push"]
    Q --> R["Open PR with 'Closes #N'"]
    
    F --> O
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
| **Implement** | `.github/workflows/opencode-implement.yaml` | `issues: [labeled]` with `opencode:approved-for-implementation` |

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

## Implement workflow behaviour

The `opencode-implement.yaml` workflow handles both trigger sources by
inspecting which event payload is present:

| Trigger | Action |
|---------|--------|
| **Issue** (`github.event.issue` present, or `workflow_dispatch` with `issue-number`) | Creates a new feature branch from the default branch, implements, commits, pushes, and opens a PR referencing the issue with `Closes #N` |
| **Pull request** (`github.event.pull_request` present, or `workflow_dispatch` with `pull-request-number`) | Checkouts the existing PR branch via `gh pr checkout`, implements, commits, and pushes to that same branch |

## Token strategy

- **triage-issue** and **triage-pr** use the OpenCode GitHub App token (via OIDC
  exchange, `use_github_token: false`) so that label changes trigger downstream
  workflow events.
- **triage-issue** and **triage-pr** also have a pre-step that uses
  `GITHUB_TOKEN` for quick approval detection via shell keyword matching — this
  bypasses the AI entirely for simple approvals and dispatches the implement
  workflow directly via `workflow_dispatch`.
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
3. Dispatches the implement workflow via `workflow_dispatch`

This completely bypasses the AI, saving one full triage run per approval cycle.

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
