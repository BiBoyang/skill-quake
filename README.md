# skill-quake

Fault-injection tooling for Agent Skills, plus the mechanical integrity gate that
the experiments argue for. Born from an experiment on Alibaba's
[`skill-up`](https://github.com/alibaba/skill-up) (the `skill-upper` skill): when a
skill's own files are damaged, does the host agent notice? (Answer: only
probabilistically, and only when the damage blocks the path.)

Two layers, deliberately separated:

| layer | tool | question | nature |
|---|---|---|---|
| foundation | `bin/skill-guard` | Is the skill file set intact? | deterministic CLI, CI-able, exit 0/1 |
| experiment | `skills/skill-quake/` | Does the host agent notice damage? | orchestration skill (LLM judgment) |

The separation is the thesis: **the foundation only accepts or rejects; grading is
for judges.** Mechanical checks must not depend on an agent happening to notice.

## skill-guard

```bash
bin/skill-guard path/to/skill            # human report, exit 1 on hard errors
bin/skill-guard path/to/skill --strict   # warnings also fail
bin/skill-guard path/to/skill --json     # machine-readable
```

Hard errors: missing SKILL.md; missing/unterminated frontmatter; empty `name` or
`description`; files referenced from SKILL.md but absent on disk.
Warnings: truncation signatures (dangling code fence, file ending at a heading or
colon), name/dir mismatch, empty files. Info: orphan attachments, dangling links in
secondary docs.

Known blind spots (v1): a *stealth* cut whose tail looks complete passes the gate —
integrity against tampering needs a known-good manifest/hash comparison (future
work). Run the fixture suite: `bash tests/run_tests.sh`.

## skill-quake (the experiment skill)

Install into your agent host (e.g. `~/.agents/skills/skill-quake` for kimi-code) or
drive its scripts directly. It enforces the methodology: fresh zero-context hosts,
neutral prompts, mutated copies only, guard witness per run, L0-L3 grading,
negative controls, honest x/N reporting. See `skills/skill-quake/SKILL.md`.

## Replicating with native Claude/GPT hosts

Hand `docs/REPLICATION.md` to anyone with a Claude Code / Codex subscription: it is
a self-contained runbook (spike, matrix, grading, what to send back).

## Layout

```
bin/skill-guard            mechanical gate (stdlib-only python3)
skills/skill-quake/        orchestration skill (SKILL.md + scripts/ + references/)
examples/greeting-card/    demo target skill
tests/                     guard fixture suite
docs/REPLICATION.md        native-model replication runbook
```

License: TBD (Apache-2.0 intended). No affiliation with Alibaba; skill-up is its
own project.
