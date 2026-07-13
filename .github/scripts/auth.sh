#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
# .github/scripts/auth.sh
# Shared command-parsing gate for OpenCode workflows.
#
# Usage:
#   .github/scripts/auth.sh <comment_body>
#
# Outputs (via GITHUB_OUTPUT):
#   IS_OC_COMMAND=true|false
#   SUBCOMMAND=review|implement|task|discuss|none
#   TASK_ARGS=<text after the subcommand, flags removed>
#   FLAG_MODEL=<value of --model=…, or empty>
#   FLAG_DRAFT=true|false          (from --draft)
#   FLAG_NO_CHANGELOG=true|false   (from --no-changelog)
#
# Flags may appear anywhere after the subcommand. Recognized flags are
# stripped from TASK_ARGS so the AI receives clean task text. Unknown
# --flags are left in place and reported via a ::warning:: annotation.
# ─────────────────────────────────────────────────────────────────────

COMMENT_BODY="${1:-}"

# Normalize: trim leading/trailing whitespace
TRIMMED=$(echo "$COMMENT_BODY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

IS_OC="false"
SUBCOMMAND="none"
TASK_ARGS=""

if [[ "$TRIMMED" =~ ^/oc ]]; then
  IS_OC="true"

  if [[ "$TRIMMED" =~ ^/oc[[:space:]]+implement[[:space:]]+(.*) ]]; then
    SUBCOMMAND="implement"
    TASK_ARGS="${BASH_REMATCH[1]}"
  elif [[ "$TRIMMED" =~ ^/oc[[:space:]]+task[[:space:]]+(.*) ]]; then
    SUBCOMMAND="task"
    TASK_ARGS="${BASH_REMATCH[1]}"
  elif [[ "$TRIMMED" =~ ^/oc[[:space:]]+task[[:space:]]*$ ]]; then
    SUBCOMMAND="task"
  elif [[ "$TRIMMED" =~ ^/oc[[:space:]]+review($|[[:space:]]) ]]; then
    SUBCOMMAND="review"
  elif [[ "$TRIMMED" =~ ^/oc[[:space:]]*$ ]] || [[ "$TRIMMED" =~ ^/oc$ ]]; then
    SUBCOMMAND="discuss"
  else
    # /oc with unrecognized subcommand — default to discuss
    SUBCOMMAND="discuss"
  fi
fi

# ─── Flag extraction ─────────────────────────────────────────────────
# Only the first line of TASK_ARGS is scanned for flags, so a --flag that
# appears inside a multi-line task description body is left untouched.
FLAG_MODEL=""
FLAG_DRAFT="false"
FLAG_NO_CHANGELOG="false"

if [[ -n "$TASK_ARGS" ]]; then
  FIRST_LINE="${TASK_ARGS%%$'\n'*}"
  REST_LINES=""
  if [[ "$TASK_ARGS" == *$'\n'* ]]; then
    REST_LINES=$'\n'"${TASK_ARGS#*$'\n'}"
  fi

  # --model=<value>
  if [[ "$FIRST_LINE" =~ (^|[[:space:]])--model=([^[:space:]]+) ]]; then
    FLAG_MODEL="${BASH_REMATCH[2]}"
    FIRST_LINE=$(echo "$FIRST_LINE" | sed -E 's/(^|[[:space:]])--model=[^[:space:]]+//')
  fi

  # --draft
  if [[ "$FIRST_LINE" =~ (^|[[:space:]])--draft($|[[:space:]]) ]]; then
    FLAG_DRAFT="true"
    FIRST_LINE=$(echo "$FIRST_LINE" | sed -E 's/(^|[[:space:]])--draft($|[[:space:]])/\2/')
  fi

  # --no-changelog
  if [[ "$FIRST_LINE" =~ (^|[[:space:]])--no-changelog($|[[:space:]]) ]]; then
    FLAG_NO_CHANGELOG="true"
    FIRST_LINE=$(echo "$FIRST_LINE" | sed -E 's/(^|[[:space:]])--no-changelog($|[[:space:]])/\2/')
  fi

  # Warn on any remaining unknown --flags on the first line
  if [[ "$FIRST_LINE" =~ (^|[[:space:]])(--[a-zA-Z0-9-]+) ]]; then
    echo "::warning::Unknown flag '${BASH_REMATCH[2]}' ignored by auth.sh"
  fi

  # Re-trim the first line after flag removal and reassemble TASK_ARGS
  FIRST_LINE=$(echo "$FIRST_LINE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  TASK_ARGS="${FIRST_LINE}${REST_LINES}"
fi

echo "IS_OC_COMMAND=$IS_OC" >> "$GITHUB_OUTPUT"
echo "SUBCOMMAND=$SUBCOMMAND" >> "$GITHUB_OUTPUT"
echo "FLAG_MODEL=$FLAG_MODEL" >> "$GITHUB_OUTPUT"
echo "FLAG_DRAFT=$FLAG_DRAFT" >> "$GITHUB_OUTPUT"
echo "FLAG_NO_CHANGELOG=$FLAG_NO_CHANGELOG" >> "$GITHUB_OUTPUT"

# Multi-line args via heredoc delimiter
if [[ -n "$TASK_ARGS" ]]; then
  {
    echo "TASK_ARGS<<OCAUTH_EOF"
    echo "$TASK_ARGS"
    echo "OCAUTH_EOF"
  } >> "$GITHUB_OUTPUT"
else
  echo "TASK_ARGS=" >> "$GITHUB_OUTPUT"
fi
