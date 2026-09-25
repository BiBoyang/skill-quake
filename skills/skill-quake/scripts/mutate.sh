#!/bin/bash
# mutate.sh — apply exactly one integrity fault to a COPY of a skill.
# Never touches the source. One fault per copy; combine via multiple copies.
#
# Usage:
#   mutate.sh <src_skill_dir> truncate-main <pct> <dst_dir>
#   mutate.sh <src_skill_dir> truncate-attachment <relpath> <pct> <dst_dir>
#   mutate.sh <src_skill_dir> delete-ref <relpath> <dst_dir>
#   mutate.sh <src_skill_dir> blank-frontmatter <dst_dir>
set -euo pipefail

src="$1"; fault="$2"
[ -f "$src/SKILL.md" ] || { echo "mutate: $src has no SKILL.md" >&2; exit 2; }

keep_pct() { # file pct -> stdout: line count to keep (min 1)
  local total
  total=$(wc -l < "$1" | tr -d ' ')
  local n=$(( total * $2 / 100 ))
  [ "$n" -lt 1 ] && n=1
  echo "$n"
}

case "$fault" in
  truncate-main)
    pct="$3"; dst="$4"
    rm -rf "$dst"; cp -R "$src" "$dst"
    n=$(keep_pct "$src/SKILL.md" "$pct")
    head -n "$n" "$src/SKILL.md" > "$dst/SKILL.md"
    echo "truncate-main: SKILL.md $(wc -l < "$src/SKILL.md" | tr -d ' ') -> $n lines ($pct%)"
    ;;
  truncate-attachment)
    rel="$3"; pct="$4"; dst="$5"
    [ -f "$src/$rel" ] || { echo "mutate: $rel not in source" >&2; exit 2; }
    rm -rf "$dst"; cp -R "$src" "$dst"
    n=$(keep_pct "$src/$rel" "$pct")
    head -n "$n" "$src/$rel" > "$dst/$rel"
    echo "truncate-attachment: $rel $(wc -l < "$src/$rel" | tr -d ' ') -> $n lines ($pct%)"
    ;;
  delete-ref)
    rel="$3"; dst="$4"
    [ -e "$src/$rel" ] || { echo "mutate: $rel not in source" >&2; exit 2; }
    rm -rf "$dst"; cp -R "$src" "$dst"
    rm "$dst/$rel"
    echo "delete-ref: removed $rel"
    ;;
  blank-frontmatter)
    dst="$3"
    rm -rf "$dst"; cp -R "$src" "$dst"
    awk '
      NR==1 && $0=="---" {fm=1; print; next}
      fm && $0=="---" {fm=0; print; next}
      fm && /^name:/ {print "name: \"\""; next}
      fm && /^description:/ {print "description: \"\""; next}
      {print}
    ' "$src/SKILL.md" > "$dst/SKILL.md"
    echo "blank-frontmatter: name/description emptied"
    ;;
  *)
    echo "mutate: unknown fault '$fault'" >&2; exit 2;;
esac
