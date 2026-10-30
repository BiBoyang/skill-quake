# skill-quake bundle alignment

repo-quake is the canonical source. The standalone BiBoyang/skill-quake repository
is the small, self-contained file/skill-layer bundle; method changes flow from the
umbrella to the bundle, never by blindly copying the whole tree.

Shared portable surface: `skills/skill-quake/SKILL.md` (apart from the umbrella-only
experiment-card step), `references/grading-rubric.md`, `scripts/collect.py`,
`matrix.sh`, `write_meta.py`, and their portable tests. `bin/skill-guard` is shared
without changes.

Intentional bundle exclusions: `skills/repo-quake/`, its experiment-card validator
and examples, paired/memory/metamorphic/quality-cost playbooks, umbrella runs and
artifact-audit tooling. The standalone Step 0.5 experiment-card section is omitted
because those paths do not exist in the bundle. All other portable SKILL.md content
is aligned.

Both repositories must pass their own `tests/run_tests.sh` after a sync. The
standalone suite includes collector, metadata and matrix tests but not umbrella
card-validator or artifact-audit tests.
