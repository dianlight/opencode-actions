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
    B --> C{"Enough info?"}
    C -- No --> D["Post clarifying questions"]
    D --> E["Set opencode:awaiting-response"]
    E --> F["Human replies with more info"]
    F --> B
    C -- Yes --> G["Post structured proposal"]
    G --> H["Set opencode:awaiting-response"]
    H --> I{"Human response"}
    I -- "New instruction / feedback" --> B
    I -- "Approved (comment)" --> J["Post acknowledgment"]
    J --> K["Set opencode:approved-for-implementation"]
    K --> L["opencode-implement.yaml"]
    L --> M["Create branch from default branch"]
    M --> N["Implement + commit + push"]
    N --> O["Open PR with 'Closes #N'"]
```

### Workflow state labels

| Label | Meaning | Set by |
|-------|---------|--------|
| `opencode:awaiting-response` | Waiting for human input | triage-issue |
| `opencode:approved-for-implementation` | Ready to implement | triage-issue |

### Files involved

| Workflow | File | Trigger |
|----------|------|---------|
| **Triage (issue)** | `.github/workflows/opencode-triage-issue.yaml` | `issue_comment` containing `/oc` or label `opencode:awaiting-response` present |
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
    D --> E["opencode-triage-pr.yaml"]
    E --> F{"Enough info?"}
    F -- No --> G["Submit review with inline questions"]
    G --> H["Set opencode:awaiting-response"]
    H --> I["Human responds"]
    I --> E
    F -- Yes --> J["Submit proposal as PR review with suggestions"]
    J --> K["Set opencode:awaiting-response"]
    K --> L{"Human action"}
    L -- "Discussion / changes requested" --> E
    L -- "Approved (Approve review)" --> M["Submit acknowledgment review"]
    M --> N["Set opencode:approved-for-implementation"]
    N --> O["opencode-implement.yaml"]
    O --> P["Checkout existing PR branch"]
    P --> Q["Implement + commit + push"]
```

### Workflow state labels

| Label | Meaning | Set by |
|-------|---------|--------|
| `opencode:awaiting-response` | Waiting for human input | triage-pr |
| `opencode:approved-for-implementation` | Ready to implement | triage-pr |

### Files involved

| Workflow | File | Trigger |
|----------|------|---------|
| **Review** | `.github/workflows/opencode-review.yaml` | `pull_request: [opened, synchronize, reopened, ready_for_review]` |
| **Triage (PR)** | `.github/workflows/opencode-triage-pr.yaml` | `pull_request_review_comment` or `pull_request_review` containing `/oc` or label `opencode:awaiting-response` present |
| **Implement** | `.github/workflows/opencode-implement.yaml` | `pull_request: [labeled]` with `opencode:approved-for-implementation` |

---

## Implement workflow behaviour

The `opencode-implement.yaml` workflow handles both trigger sources by
inspecting which event payload is present:

| Trigger | Action |
|---------|--------|
| **Issue** (`github.event.issue` present) | Creates a new feature branch from the default branch, implements, commits, pushes, and opens a PR referencing the issue with `Closes #N` |
| **Pull request** (`github.event.pull_request` present) | Checkouts the existing PR branch via `gh pr checkout`, implements, commits, and pushes to that same branch |

## Token strategy

- **triage-issue** and **triage-pr** use the OpenCode GitHub App token (via OIDC
  exchange, `use_github_token: false`) so that label changes trigger downstream
  workflow events.
- **review** and **implement** use the built-in `GITHUB_TOKEN`
  (`use_github_token: true`) since they do not need to chain further workflow
  events.
