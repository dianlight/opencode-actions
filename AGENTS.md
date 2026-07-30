# AGENTS.md

## Repository purpose

This repo distributes GitHub Actions workflows to multiple downstream repositories. It is **not** an application — it is a workflow distribution hub.

## Active vs deprecated workflows

- **Active (3 files):** `opencode-pr-review.yml`, `opencode-pr-comment.yml`, `opencode-issue-handler.yml`. These implement the 6-process automation pipeline.
- **Deprecated (6 files):** `opencode.yml`, `opencode-triage*.yaml`, `opencode-implement.yaml`, `opencode-review.yaml`. These are **no-op stubs** synced to downstream repos to prevent stale triggers. Do not add real logic to them.
- Do not add new workflow files without also adding them to `.github/sync.yml`.

## Commands

```bash
# Python env (uses mise)
mise install                  # installs python 3.14 + yamllint, pip installs requirements.txt

# Lint YAML (also runs in CI via opencode-maintenance)
mise run lint-yaml

# Lint Python with ruff (also runs in CI via opencode-maintenance)
mise run lint-python

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

### Shared script

`.github/scripts/auth.sh` parses `/oc` commands and outputs `IS_OC_COMMAND`, `SUBCOMMAND`, and `TASK_ARGS` via `GITHUB_OUTPUT`.

### Sync system

`.github/sync.yml` defines 4 downstream repos and files to sync. The `sync-actions.yml` workflow uses `BetaHuhn/repo-file-sync-action`. Requires a `GH_PAT` secret.

### Maintenance

`scripts/opencode_maintenance.py` fetches model catalogs (OpenCode Zen/Go + LiveBench), classifies workflows by task type, scores models, updates `README.md` tables, and saves results to `data/*.json`. Runs on a schedule and on pushes to `opencode-maintenance.yaml`.

## Config files

- `.mise.toml` — tool versions (Python 3.14, yamllint 1.38) and task shortcuts
- `.yamllint` — 180-char line limit for GitHub Actions expressions, 2-space indent, truthy rule relaxed
- `config/task-types.yaml` — task type definitions with signal keywords and priority subscores
- `config/workflow-task-map.yaml` — workflow→task type mapping with job-level overrides
- `config/model-scores.yaml` — static fallback scores for models not on LiveBench (also includes `token_multipliers` config)
- `ruff.toml` — ruff linter configuration (Python)

## Workflow conventions

- All OpenCode steps pin the action: `anomalyco/opencode/github@<sha>`
- Concurrency groups are keyed by issue/PR number with `cancel-in-progress: false`
- Every process step uses `continue-on-error: true` followed by reaction-on-success/failure steps
- Issue titles are passed via `env:` (not inline substitution) to prevent shell injection
- Multi-line strings in `run: |` blocks must be consistently indented — all content lines must share the same indentation as the first content line; use temp-file patterns (`echo ... > /tmp/file`) instead of inline `--body "..."` for long comment bodies

## Validation

- **Always run `mise run lint-yaml` after editing any YAML file** — the CI lints YAML and a `syntax error: could not find expected ':'` usually means a `|` block line broke out of the correct indent level
- **Always run `mise run lint-python` after editing any Python file** — the CI checks Python with ruff
- Verify with `bash -n .github/scripts/auth.sh` after changing the shared auth script

## Renovate

`.github/renovate.json` auto-updates GitHub Actions every Monday with automerge enabled.
