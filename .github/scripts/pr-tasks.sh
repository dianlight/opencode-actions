#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# .github/scripts/pr-tasks.sh
# Deterministic git-plumbing helpers for OpenCode workflows.
# Replaces tasks that were previously delegated to the AI model.
#
# Subcommands:
#   slug       <title>              — sanitize a title into a branch slug
#   check-task <pr#> [needle]       — flip first matching - [ ] → - [x]
#   changelog  <issue#> <message>  — append Unreleased/Added entry
#
# Environment variables consumed:
#   GH_TOKEN   — required for check-task and changelog
# ─────────────────────────────────────────────────────────────────────

SUBCMD="${1:-}"

# ── slug ─────────────────────────────────────────────────────────────
# Usage: pr-tasks.sh slug <title>
# Prints a lowercase, hyphen-separated, 40-char-max slug suitable for
# a branch name. Mirrors the transform from the Process 5 prompt.
# ─────────────────────────────────────────────────────────────────────
if [[ "$SUBCMD" == "slug" ]]; then
  TITLE="${2:-}"
  SLUG=$(echo "$TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]/-/g' \
    | sed 's/--*/-/g' \
    | sed 's/^-//;s/-$//' \
    | cut -c1-40)
  # Strip trailing hyphen that cut can leave (e.g. if char-40 is mid-run)
  SLUG="${SLUG%-}"
  echo "$SLUG"
  exit 0
fi

# ── check-task ───────────────────────────────────────────────────────
# Usage: pr-tasks.sh check-task <pr#> [needle]
# Fetches the current PR body, flips the first uncompleted task that
# matches <needle> (or just the very first - [ ] if no needle is given),
# then updates the PR body via `gh pr edit`.
# Outputs the completed task description to stdout.
# Requires: GH_TOKEN env, gh CLI in PATH.
# ─────────────────────────────────────────────────────────────────────
if [[ "$SUBCMD" == "check-task" ]]; then
  PR_NUMBER="${2:-}"
  NEEDLE="${3:-}"

  if [[ -z "$PR_NUMBER" ]]; then
    echo "::error::check-task: PR number required" >&2
    exit 1
  fi

  # Fetch the current PR body
  PR_BODY=$(gh pr view "$PR_NUMBER" --json body -q .body)

  # Find the first uncompleted task that matches the needle
  if [[ -n "$NEEDLE" ]]; then
    MATCH=$(printf '%s\n' "$PR_BODY" \
      | grep '^- \[ \]' \
      | grep -F -m1 -- "$NEEDLE" || true)
  else
    MATCH=$(echo "$PR_BODY" | grep -m1 '^- \[ \]' || true)
  fi

  if [[ -z "$MATCH" ]]; then
    echo "::warning::check-task: no uncompleted task found (needle='${NEEDLE}')" >&2
    exit 0
  fi

  # Build the checked version of that exact line
  CHECKED="${MATCH/- \[ \]/- [x]}"

  # Replace first occurrence only (sed: break after first substitution)
  UPDATED=$(echo "$PR_BODY" | awk -v old="$MATCH" -v new="$CHECKED" '
    !done && $0 == old { print new; done=1; next }
    { print }
  ')

  # Write updated body back
  echo "$UPDATED" | gh pr edit "$PR_NUMBER" --body-file -

  # Report what was checked
  TASK_DESC=$(echo "$MATCH" | sed 's/^- \[ \] *//')
  echo "$TASK_DESC"
  exit 0
fi

# ── changelog ────────────────────────────────────────────────────────
# Usage: pr-tasks.sh changelog <issue#> <message>
# Appends an entry to the ## [Unreleased] / ### Added section of
# CHANGELOG.md. Creates the section if it doesn't exist.
# Commit is the caller's responsibility (the workflow steps handles it).
# ─────────────────────────────────────────────────────────────────────
if [[ "$SUBCMD" == "changelog" ]]; then
  ISSUE_NUMBER="${2:-}"
  MESSAGE="${3:-}"
  CHANGELOG="${CHANGELOG_PATH:-CHANGELOG.md}"

  if [[ -z "$ISSUE_NUMBER" || -z "$MESSAGE" ]]; then
    echo "::error::changelog: issue# and message required" >&2
    exit 1
  fi

  ENTRY="- ${MESSAGE} (Resolves #${ISSUE_NUMBER})"

  if [[ ! -f "$CHANGELOG" ]]; then
    # Bootstrap a minimal CHANGELOG
    cat > "$CHANGELOG" <<'CLEOF'
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
CLEOF
    echo "$ENTRY" >> "$CHANGELOG"
    echo "::notice::changelog: created $CHANGELOG with first entry"
    exit 0
  fi

  # If the file already has ## [Unreleased] / ### Added, insert after that line
  if grep -q '^## \[Unreleased\]' "$CHANGELOG"; then
    if grep -q '^### Added' "$CHANGELOG"; then
      # Insert after the first ### Added line
  TMP_CHANGELOG=$(mktemp)
  trap 'rm -f "$TMP_CHANGELOG"' EXIT

      awk -v entry="$ENTRY" '
        !done && /^### Added/ { print; print entry; done=1; next }
        { print }
      ' "$CHANGELOG" > "$TMP_CHANGELOG"
    else
      # Insert ### Added section right after ## [Unreleased]
      awk -v entry="$ENTRY" '
        !done && /^## \[Unreleased\]/ { print; print ""; print "### Added"; print entry; done=1; next }
        { print }
      ' "$CHANGELOG" > "$TMP_CHANGELOG"
    fi
  else
    # Prepend a full ## [Unreleased] block before the first ## [version]
    awk -v entry="$ENTRY" '
      !done && /^## \[/ {
        print "## [Unreleased]"
        print ""
        print "### Added"
        print entry
        print ""
        done=1
      }
      { print }
    ' "$CHANGELOG" > "$TMP_CHANGELOG"
  fi

  mv "$TMP_CHANGELOG" "$CHANGELOG"
  trap - EXIT
  echo "::notice::changelog: appended entry for issue #${ISSUE_NUMBER}"
  exit 0
fi

# ── unknown subcommand ────────────────────────────────────────────────
echo "::error::pr-tasks.sh: unknown subcommand '${SUBCMD}'" >&2
echo "Available subcommands: slug, check-task, changelog" >&2
exit 1
