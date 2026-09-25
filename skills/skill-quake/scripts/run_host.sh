#!/bin/bash
# run_host.sh — dispatch one headless run to a host agent.
# Usage: run_host.sh <kimi|claude|codex> <prompt_file> <workdir> <out_file> [extra_read_dir]
# The prompt file must contain the full neutral prompt (see SKILL.md template).
# extra_read_dir (claude only): additional directory to grant tool access to,
# e.g. the mutated skill copy that lives outside the writable workdir.
set -uo pipefail

host="$1"; prompt_file="$2"; workdir="$3"; out="$4"; adddir="${5:-}"
prompt="$(cat "$prompt_file")"

case "$host" in
  kimi)
    (cd "$workdir" && kimi -p "$prompt" --output-format text) > "$out" 2>&1
    ;;
  claude)
    # acceptEdits covers file writes; if your flow needs bash commands beyond
    # your allowlist, add --dangerously-skip-permissions at your own risk.
    extra=()
    [ -n "$adddir" ] && extra=(--add-dir "$adddir")
    (cd "$workdir" && claude -p "$prompt" --output-format text --permission-mode acceptEdits "${extra[@]}") > "$out" 2>&1
    ;;
  codex)
    # codex has no skill-loading convention; the neutral prompt points at the
    # skill path directly (documented as prompt-injection mode).
    # Provider/model override via env: CODEX_PROVIDER=kimi CODEX_MODEL=kimi-for-coding
    args=(--skip-git-repo-check --sandbox workspace-write)
    [ -n "${CODEX_PROVIDER:-}" ] && args+=(-c model_provider="$CODEX_PROVIDER")
    [ -n "${CODEX_MODEL:-}" ] && args+=(-m "$CODEX_MODEL")
    (cd "$workdir" && codex exec "${args[@]}" "$prompt" < /dev/null) > "$out" 2>&1
    ;;
  *)
    echo "run_host: unknown host '$host'" >&2; exit 2;;
esac
rc=$?
echo "$rc" > "$out.exitcode"
echo "run_host: $host exit=$rc -> $out"
