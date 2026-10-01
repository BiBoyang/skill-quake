#!/bin/bash
# matrix.sh — run one host x fault cell series: mutate copies, guard, dispatch.
# Usage: matrix.sh <src_skill> <results_dir> <prompt_template> <host> <faultspec> <N>
#   faultspec examples:  truncate-main:60 | truncate-attachment:references/x.md:50
#                        delete-ref:references/x.md | blank-frontmatter
# Run once per host. Grade afterwards (see references/grading-rubric.md), then collect.
set -euo pipefail

src="$1"; results="$2"; template="$3"; host="$4"; spec="$5"; n="$6"
here="$(cd "$(dirname "$0")" && pwd)"
# Resolve the guard witness: repo layout first, then PATH, then the install
# convention. A matrix without its witness is noise — fail fast, not silent.
if [ -f "$here/../../../bin/skill-guard" ]; then
  guard="$here/../../../bin/skill-guard"
elif command -v skill-guard >/dev/null 2>&1; then
  guard="$(command -v skill-guard)"
elif [ -f "$HOME/.agents/bin/skill-guard" ]; then
  guard="$HOME/.agents/bin/skill-guard"
else
  echo "matrix: skill-guard not found (checked repo bin/, PATH, ~/.agents/bin)" >&2
  exit 2
fi
# spec without a colon means a no-arg fault (blank-frontmatter): ${spec#*:}
# would keep the whole spec and pass it as a phantom argument, shifting
# every mutate.sh parameter by one (dst ends up as "./blank-frontmatter").
fault="${spec%%:*}"
args=""
[ "$fault" != "$spec" ] && args="${spec#*:}"

case "$fault" in
  truncate-main|truncate-attachment|delete-ref) cell="$host+$fault-${args//[\/:]/-}";;
  blank-frontmatter) cell="$host+$fault";;
  *) echo "matrix: unknown fault '$fault'" >&2; exit 2;;
esac

# C-style loop: BSD seq (macOS) counts DOWN for `seq 1 0`, which would run
# two unintended dispatch runs for N=0. `for ((...))` is portable and fork-free.
for ((i=1; i<=n; i++)); do
  run="$results/$cell/run-$i"
  mkdir -p "$run"
  # Opaque staging: paths visible to the host must never encode the fault type.
  stage_id=$(printf '%s' "$cell-$i-$(date +%s%N)" | shasum -a 256 | cut -c1-12)
  stage="$results/.stage/$stage_id"
  mkdir -p "$stage/work"
  [ -n "${TARGET:-}" ] && cp -R "$TARGET" "$stage/work/target"
  a=()
  [ -n "$args" ] && IFS=':' read -ra a <<< "$args"
  # ${a[@]+...} keeps an empty array safe under bash 3.2 + set -u (macOS ships 3.2).
  bash "$here/mutate.sh" "$src" "$fault" ${a[@]+"${a[@]}"} "$stage/skill"
  # Guard is the witness, not a gate: a FAIL verdict on a mutated copy is
  # expected data, not an error. Abort only when the witness itself crashed
  # (no JSON verdict at all) — silence here is the silent-failure class this
  # tool exists to catch.
  if ! python3 "$guard" --json "$stage/skill" > "$run/guard.json" 2>"$run/guard.stderr"; then
    if ! grep -q '"verdict"' "$run/guard.json" 2>/dev/null; then
      echo "matrix: skill-guard crashed on $stage/skill (see $run/guard.stderr)" >&2
      exit 2
    fi
  fi
  rm -f "$run/guard.stderr"
  # Staging assertion: mutate always copies SKILL.md, so "SKILL.md missing" in the
  # verdict can only mean the staged copy is broken — loud-fail, never record it.
  if grep -q "SKILL.md missing" "$run/guard.json" 2>/dev/null; then
    echo "matrix: staging broken — mutated copy has no SKILL.md (see $run/guard.json)" >&2
    exit 2
  fi
  sed -e "s|__SKILL_PATH__|$stage/skill|g" -e "s|__WORKDIR__|$stage/work|g" "$template" > "$run/prompt.txt"
  echo "== $cell run-$i (stage $stage_id): dispatching to $host"
  bash "$here/run_host.sh" "$host" "$run/prompt.txt" "$stage/work" "$run/report.md" "$stage/skill"
  mv "$run/report.md.exitcode" "$run/exitcode" 2>/dev/null || true
  printf '{"host":"%s","fault":"%s","cell":"%s","run":%s,"stage":"%s","time":"%s"}\n' \
    "$host" "$spec" "$cell" "$i" "$stage_id" "$(date -u +%FT%TZ)" > "$run/meta.json"
done
echo "cell $cell done: $n run(s) under $results/$cell — now grade each report.md"
