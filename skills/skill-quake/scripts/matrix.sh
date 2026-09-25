#!/bin/bash
# matrix.sh — run one host x fault cell series: mutate copies, guard, dispatch.
# Usage: matrix.sh <src_skill> <results_dir> <prompt_template> <host> <faultspec> <N>
#   faultspec examples:  truncate-main:60 | truncate-attachment:references/x.md:50
#                        delete-ref:references/x.md | blank-frontmatter
# Run once per host. Grade afterwards (see references/grading-rubric.md), then collect.
set -euo pipefail

src="$1"; results="$2"; template="$3"; host="$4"; spec="$5"; n="$6"
here="$(cd "$(dirname "$0")" && pwd)"
guard="$here/../../../bin/skill-guard"
fault="${spec%%:*}"; args="${spec#*:}"

case "$fault" in
  truncate-main|truncate-attachment|delete-ref) cell="$host+$fault-${args//[\/:]/-}";;
  blank-frontmatter) cell="$host+$fault";;
  *) echo "matrix: unknown fault '$fault'" >&2; exit 2;;
esac

for i in $(seq 1 "$n"); do
  run="$results/$cell/run-$i"
  mkdir -p "$run"
  # Opaque staging: paths visible to the host must never encode the fault type.
  stage_id=$(printf '%s' "$cell-$i-$(date +%s%N)" | shasum -a 256 | cut -c1-12)
  stage="$results/.stage/$stage_id"
  mkdir -p "$stage/work"
  [ -n "${TARGET:-}" ] && cp -R "$TARGET" "$stage/work/target"
  IFS=':' read -ra a <<< "$args"
  bash "$here/mutate.sh" "$src" "$fault" "${a[@]}" "$stage/skill"
  python3 "$guard" --json "$stage/skill" > "$run/guard.json" || true
  sed -e "s|__SKILL_PATH__|$stage/skill|g" -e "s|__WORKDIR__|$stage/work|g" "$template" > "$run/prompt.txt"
  echo "== $cell run-$i (stage $stage_id): dispatching to $host"
  bash "$here/run_host.sh" "$host" "$run/prompt.txt" "$stage/work" "$run/report.md" "$stage/skill"
  mv "$run/report.md.exitcode" "$run/exitcode" 2>/dev/null || true
  printf '{"host":"%s","fault":"%s","cell":"%s","run":%s,"stage":"%s","time":"%s"}\n' \
    "$host" "$spec" "$cell" "$i" "$stage_id" "$(date -u +%FT%TZ)" > "$run/meta.json"
done
echo "cell $cell done: $n run(s) under $results/$cell — now grade each report.md"
