# skill-quake bundle alignment

repo-quake is the canonical source. The standalone BiBoyang/skill-quake repository
is the small, self-contained file/skill-layer bundle; method changes flow from the
umbrella to the bundle, never by blindly copying the whole tree.

Shared portable surface: `skills/skill-quake/SKILL.md` (byte-identical to the
umbrella, Step 0.5 included), `references/grading-rubric.md`, `scripts/collect.py`,
`matrix.sh`, `write_meta.py`, and their portable tests. `bin/skill-guard` is shared
without changes. Step 0.5 names two files outside the skill; both are carried at the
same relative paths so the step resolves here: `examples/experiment-card.json` and
`skills/repo-quake/scripts/validate_card.py` (stdlib-only).

Intentional bundle exclusions: the rest of `skills/repo-quake/` (its SKILL.md,
references and `audit_artifacts.py`), the other example cards, the validator's unit
tests, paired/memory/metamorphic/quality-cost playbooks, umbrella runs, the fault
ledger and artifact-audit tooling.

Both repositories must pass their own `tests/run_tests.sh` after a sync. The
standalone suite includes the guard fixtures (with `cross-skill-ref`), the dogfood
gate on `skills/skill-quake`, a smoke check that the example card validates, and the
collector, metadata and matrix tests, but not the umbrella's card-validator unit
tests, ledger check, factorial dry-run or artifact-audit tests.
