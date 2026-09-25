# Fault menu

Standard faults. Each maps to one observed real-world damage class. One fault per
copy — never stack faults unless the experiment is explicitly about interaction.

## F1 truncate-main `<pct>`

Keep the first `<pct>`% of SKILL.md lines (counting frontmatter). Models partial
writes, bad syncs, truncated downloads.

Cut-point rules: cut at a line boundary; prefer a spot right after a *complete*
line (bullet or sentence) so no marker betrays the cut. A cut that leaves a dangling
heading or half sentence is a different, easier-to-detect fault — say which you used.

## F2 delete-ref `<relpath>`

Delete one attachment that SKILL.md references. Models lost files in
copy/install/sync. Choose an attachment the main flow actually points at.

## F3 truncate-attachment `<relpath>` `<pct>`

Keep the first `<pct>`% of one attachment. The subtlest standard fault: all
references still resolve, frontmatter intact, content just stops.

## F4 blank-frontmatter

Empty the `name` and `description` values (keep the keys and fences). Models broken
generation or bad edits. Note: this damage mainly hits the *discovery* layer —
a host pointed directly at the file will not feel it; a real loader may reject or
never trigger the skill. Report which loading path the experiment used.

## Adding faults

- Name them `F5+`, keep them one-purpose, and record the exact mutation command.
- Semantic tampering (flip a recommendation, rename a flag to a plausible wrong one)
  is a different research question (supply-chain poisoning, not accidental damage);
  do not mix it into integrity series.
- Every new fault needs a corresponding `skill-guard` expectation: which check
  should catch it, at error or warning level — or an explicit "gate-blind" note.

## Known gate coverage (skill-guard v1)

| fault | gate verdict |
|---|---|
| F1 stealth cut (complete-line tail) | PASS — blind spot; only caught if heuristics fire |
| F1 dangling-heading/fence cut | PASS + warning (`--strict` fails) |
| F2 | FAIL (missing reference) |
| F3 dangling-heading cut | PASS + warning |
| F3 stealth cut | PASS — blind spot |
| F4 | FAIL (empty required fields) |

A gate PASS never means "skill is good" — the foundation only accepts or rejects.
To catch stealth cuts, compare against a known-good manifest/hash (future work).
