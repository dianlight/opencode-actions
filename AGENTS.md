# AGENTS.md

## Repository purpose

This repo distributes GitHub Actions workflows to multiple downstream repositories. It is **not** an application — it is a workflow distribution hub.

## Active vs deprecated workflows

- **Active (4 files):** `opencode-pr-review.yml`, `opencode-pr-comment.yml`, `opencode-issue-handler.yml`, `opencode-labels.yml`. The first three implement the 6-process automation pipeline; `opencode-labels.yml` is the event-driven label manager.
- **Deprecated (6 files):** `opencode.yml`, `opencode-triage*.yaml`, `opencode-implement.yaml`, `opencode-review.yaml`. These are **no-op stubs** synced to downstream repos to prevent stale triggers. Do not add real logic to them.
- Do not add new workflow files without also adding them to `.github/sync.yml`.

## Commands

```bash
# Python env (uses mise)
mise install                  # installs python 3.14 + yamllint, pip installs requirements.txt

# Lint YAML (also runs in CI via opencode-maintenance)
mise run lint-yaml

# Run the maintenance script (fetches models, updates README)
mise run maintenance
# or directly:
python scripts/opencode_maintenance.py
```

## Architecture

### 6-process pipeline

| Process | Workflow | Trigger |
|---------|----------|---------|
| 1 — PR Review | `opencode-pr-review.yml` | `/oc` or `/oc review` on a PR |
| 2 — Bot thread reply | `opencode-pr-comment.yml` | Reply in a bot-owned review thread (no `/oc` needed) |
| 3 — User thread takeover | `opencode-pr-comment.yml` | `/oc` in a human-owned review thread |
| 4 — Issue review | `opencode-issue-handler.yml` | `/oc` or `/oc review` on an issue |
| 5 — Issue implementation | `opencode-issue-handler.yml` | `/oc implement` on an issue |
| 6 — PR task execution | `opencode-pr-comment.yml` | `/oc task` on a PR |

Authorization gate: all workflows require `author_association` in `OWNER/MEMBER/COLLABORATOR`. Unknown users are silently skipped.

### Shared scripts

`.github/scripts/auth.sh` parses `/oc` commands and outputs `IS_OC_COMMAND`,
`SUBCOMMAND`, `TASK_ARGS`, and flag outputs via `GITHUB_OUTPUT`.

**Recognized flags** (trailing the subcommand on the first line):
- `--model=<id>` — override the AI model for this invocation (`FLAG_MODEL`)
- `--draft` — create PR as draft when applicable, e.g. `/oc implement ... --draft` (`FLAG_DRAFT`)
- `--no-changelog` — skip appending a CHANGELOG entry in Process 5 (`FLAG_NO_CHANGELOG`)

Unknown `--flags` are left in `TASK_ARGS` and reported via `::warning::`.

`.github/scripts/pr-tasks.sh` provides deterministic git-plumbing helpers
(replaces work previously delegated to the AI model):
- `slug <title>` — sanitize a title into a 40-char branch slug
- `check-task <pr#> [needle]` — flip first matching `- [ ]` → `- [x]` in PR body
- `changelog <issue#> <message>` — append `## [Unreleased] / ### Added` entry to CHANGELOG.md

### Shared composite action

`.github/actions/opencode-run/action.yml` owns the per-job lifecycle:
- **`do-ack: true`** — post 👀 (`eyes`) on the trigger comment, create a sticky
  "running" status comment, **and add GitHub labels** (`add-labels` input)
- **`do-success: true`** — post 🎉 (`hooray`), flip status comment to "✅ Done",
  **and remove labels** (`remove-labels` input)
- **`do-failure: true`** — post 👎 (`-1`), flip status comment to "❌ Failed",
  **and remove labels** (`remove-labels` input)

Label inputs (all optional — labels are created on demand with color `0075ca`):
- `issue-number` — issue or PR number for label operations
- `is-pull-request` — `'true'` to use the PR labels endpoint
- `add-labels` — space-separated labels to add at ack time
- `remove-labels` — space-separated labels to remove at success/failure

All workflows call this action by local path `uses: ./.github/actions/opencode-run`
**not** by `owner/repo@sha`. The action and `pr-tasks.sh` are both registered in
`.github/sync.yml` so downstream repos receive them automatically.

### Label-automation workflow (`opencode-labels.yml`)

Three event-driven jobs (no AI invoked):

| Job | Trigger | What it does |
|-----|---------|-------------|
| `inject-help-menu` | `issues/pull_request: labeled` where label = `ai:help` | Appends a checkboxes help menu to the body (idempotent) |
| `checkbox-proxy` | `issues/pull_request: edited` (body changed) | Authorized users checking a box in the menu get it proxied as `/oc comment` via `GH_PAT`; requires write permission on the repo |
| `clear-user-request-label` | `issue_comment: created` (authorized user) | Removes `ai:user_request` label when a human responds |

**Label lifecycle:**

| Label | Added by | Removed by |
|-------|----------|------------|
| `ai:working` | Composite action ack | Composite action success/failure |
| `ai:pr-review` | P1 ack | P1 success/failure |
| `ai:pr-comment` | P2/P3 ack | P2/P3 success/failure |
| `ai:pr-task` | P6 ack | P6 success/failure |
| `ai:issue-review` | P4 ack | P4 success/failure |
| `ai:issue-implement` | P5 ack | P5 success/failure |
| `ai:help` | Human | Not removed by bot (human removes when done) |
| `ai:user_request` | AI prompt instruction | `clear-user-request-label` job |

### Sync system

`.github/sync.yml` defines 4 downstream repos and files to sync. The `sync-actions.yml` workflow uses `BetaHuhn/repo-file-sync-action`. Requires a `GH_PAT` secret.

### Maintenance

`scripts/opencode_maintenance.py` fetches model catalogs (OpenCode Zen/Go + LiveBench), classifies workflows by task type, scores models, updates `README.md` tables, and saves results to `data/*.json`. Runs on a schedule and on pushes to `opencode-maintenance.yaml`.

## Config files

- `.mise.toml` — tool versions (Python 3.14, yamllint 1.38) and task shortcuts
- `.yamllint` — 180-char line limit for GitHub Actions expressions, 2-space indent, truthy rule relaxed
- `config/task-types.yaml` — task type definitions with signal keywords and priority subscores
- `config/workflow-task-map.yaml` — workflow→task type mapping with job-level overrides
- `config/model-scores.yaml` — static fallback scores for models not on LiveBench

## Workflow conventions

- All OpenCode steps pin the action: `anomalyco/opencode/github@<sha>`
- Concurrency groups are keyed by issue/PR number with `cancel-in-progress: false`
- Every process has: **Acknowledge** (ack step) → opencode invocation → one **retry** after 30s → terminal success/failure via the composite action
- Issue titles and comment bodies are passed via `env:` (not inline substitution) to prevent shell injection
- Timeouts: all PR-comment and issue-handler jobs have `timeout-minutes` (15 for review/discussion, 30 for implementation)
- The composite action (`opencode-run`) is the single source of truth for reactions and status comments; do not add bare `gh api .../reactions` calls to workflows

## Renovate

`.github/renovate.json` auto-updates GitHub Actions every Monday with automerge enabled.
