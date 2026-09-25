**Title:** SKILL.md / asset integrity is never checked: fault-injection findings and a proposal

## Summary

We ran a controlled fault-injection experiment against the `skill-upper` skill (truncated SKILL.md, deleted/truncated referenced attachments, blanked frontmatter) and measured whether host agents notice the damage while following the skill. Headline result: detection by the host is **probabilistic and path-dependent** — damage that blocks the executing instruction is reliably reported (14/14 across three hosts); damage in an optionally-read reference is not (down to 2/8). The toolchain itself performs **no integrity checking at any layer**.

## Findings

**1. The CLI never parses SKILL.md.** `internal/cli/run.go` only requires it to be a regular file (`isRegularFile`); `internal/skill` installs by copying. Nothing validates frontmatter or verifies that files referenced from SKILL.md exist. Your own e2e fixtures demonstrate this — their SKILL.md files are frontmatter-less stubs (`mock-engine`, `multiturn-session`, `custom-engine`), which works because nothing reads them. Meanwhile `skill-up validate` *does* hard-fail on broken `eval.yaml` (missing case files, malformed YAML): the eval-config layer is defended, the skill-content layer is not.

**2. The skill-upper workflow has no integrity step.** Step 1 reads the target SKILL.md to extract behaviors, but nothing checks document completeness or reference liveness before cases are generated. In our wounded-examiner run, a target skill whose reference doc was truncated lost coverage of 5 format rules in the generated eval suite — silently.

**3. Host vigilance is not a substitute.** 30+ runs, three hosts (kimi-code, Claude Code, Codex CLI), same model across hosts:

| fault | host | detected |
|---|---|---|
| SKILL.md truncated at 60% (blocks main flow) | kimi-code | 8/8 |
| SKILL.md truncated at 60% | Claude Code / Codex CLI | 3/3 / 3/3 |
| SKILL.md truncated at 85% (only tail index lost) | kimi-code | 1/3 |
| attachment truncated at 50% (optionally read) | kimi-code | 2/8 |
| attachment truncated at 50% | Claude Code / Codex CLI | 3/3 / 2/3 |
| Step-2-mandated template deleted | kimi-code | 3/3 |
| frontmatter name/description blanked | kimi-code | 3/4 |

Detection tracks whether the damage contradicts the instruction the agent is executing right now — not how severe the damage is.

## Proposal

Cheap, deterministic, in the spirit of the existing `validate` command:

1. Extend `skill-up validate` (or add `validate --skill`) to also check the skill itself: frontmatter parses, `name`/`description` non-empty, and every `references/`, `assets/`, `scripts/` path mentioned in SKILL.md exists on disk.
2. Optionally one line in `skills/skill-upper/SKILL.md` Step 1 instructing the agent to run that check before scaffolding.
3. (Larger, future) a manifest/hash mode for tamper evidence against stealth cuts.

We have a working reference implementation of the checks (stdlib-only Python, ~150 LOC, fixture-tested) and a reusable fault-injection harness, both at https://github.com/BiBoyang/skill-quake (full experiment log, grading rubric, and raw per-cell summaries included). Happy to contribute the validate-side check as a Go PR if the direction fits.

## Notes

- All experiments ran on local copies; no third-party skills were harmed. The evaluated "target" skill is a synthetic fixture.
- We deliberately did not test semantic tampering (plausible-wrong instructions) — a separate, scarier question.
