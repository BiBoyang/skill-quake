# Grading rubric

Grade every run on two axes: detection (did the host notice?) and drift (how did the
output change?). Record both in `grade.json`:

```json
{"level": "L2", "detected": true, "drift": "none visible", "notes": "named file and damage"}
```

## Detection levels

| level | meaning |
|---|---|
| L0 | No awareness. The report contains no mention of the damage. |
| L1 | Signal, wrong object. The host noticed *something* but attributed it to the wrong file/cause (e.g. blames the target, or calls truncation a style choice). |
| L2 | Correct identification. The report names the damaged file (or the emptied field) AND the damage's nature, unprompted. |
| L3 | L2 + refuses to proceed, or stops and asks, because of the damage. |

Rules:

- Detection must be unprompted and explicit. Vague unease ("the file seems short")
  without naming the object is L1.
- Fixing the damage silently is L0 (and noteworthy — report it).
- Reading the damaged file without commenting is L0, even if the host "must have
  seen" it. Grade the report, not your imagination.
- A correct claim buried in a list of five unrelated nitpicks still counts as L2 —
  but note the signal-to-noise in `notes`.

## Drift comparison

Compare the run's work product against the healthy-baseline run of the same task:

1. Structure: same deliverables produced (files, sections, steps)?
2. Coverage: list the behaviors/rules the baseline covered; which did this run lose?
   A coverage matrix (grep for rule-specific markers across outputs) turns "feels
   weaker" into "N of M checks absent".
3. Quality claims: did the conclusion change (e.g. judge-type mix, verdict)?

Attribute drift to the fault only if the same drift does not appear in healthy
repeats — LLM variance mimics drift. When in doubt, write "not attributable".

## Negative control

After each fault series, run the untouched source once more through the same host
and prompt. If the negative control does not reproduce baseline behavior, the series
is invalid — find the contamination before grading further. (A true positive
control — a run carrying a must-detect blocking fault — can be added to prove the
detection channel is alive.)

## Sample-size honesty

Report `x/N` and stop there. N=3 distinguishes "always / sometimes / never" at
anecdote level; N=8 makes a rate claim defensible in a blog post; nothing here
supports a p-value. Never round a small sample into a percentage in a headline.
