#!/bin/bash
# skill-guard fixture tests: each fixture maps to one known fault class.
set -u
cd "$(dirname "$0")/.."
GUARD=bin/skill-guard
fails=0

check() { # name fixture expected_exit expected_substring
  local name="$1" fixture="$2" want_exit="$3" want_str="$4"
  local out rc
  out=$(python3 $GUARD "tests/fixtures/$fixture" 2>&1); rc=$?
  if [ "$rc" -ne "$want_exit" ]; then
    echo "FAIL [$name]: exit=$rc want=$want_exit"; echo "$out"; fails=$((fails+1)); return
  fi
  if [ -n "$want_str" ] && ! grep -qF "$want_str" <<<"$out"; then
    echo "FAIL [$name]: missing '$want_str'"; echo "$out"; fails=$((fails+1)); return
  fi
  echo "ok   [$name]"
}

check healthy           healthy-mini        0 "PASS"
check missing-ref       missing-ref         1 "references/gone.md"
check empty-frontmatter empty-frontmatter   1 "'name' is empty"
check empty-fm-desc     empty-frontmatter   1 "'description' is empty"
check trunc-main-warn   truncated-main      0 "ends at a heading"
check trunc-fence-warn  truncated-fence     0 "odd number of"
check strict-promotes   truncated-main      0 "PASS"   # non-strict: warning only

out=$(python3 $GUARD tests/fixtures/truncated-main --strict 2>&1); rc=$?
if [ "$rc" -eq 1 ]; then echo "ok   [strict-fails-on-warn]"; else echo "FAIL [strict-fails-on-warn]: exit=$rc"; fails=$((fails+1)); fi

out=$(python3 $GUARD tests/fixtures/healthy-mini --json); rc=$?
if [ "$rc" -eq 0 ] && grep -q '"verdict": "PASS"' <<<"$out"; then echo "ok   [json-mode]"; else echo "FAIL [json-mode]"; echo "$out"; fails=$((fails+1)); fi

echo "---"
[ "$fails" -eq 0 ] && echo "ALL TESTS PASSED" || { echo "$fails TEST(S) FAILED"; exit 1; }
