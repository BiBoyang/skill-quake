# 上游 issue 草案（未提交——等用户拍板）

> 中文备忘：建议只发 issue，把 PR 作为"如维护者有兴趣我们愿意贡献"的提议放在末尾。
> 理由：发现本身（无完整性防线 + 宿主检出概率性 + 剂量-响应数据）对社区有独立价值；
> PR 涉及给 `skill-up validate` 加 skill 内容层检查，是设计决策，应先由维护者表态。
> 以下正文为英文（面向维护者）。

---

**Title:** SKILL.md / asset integrity is never checked: fault-injection findings and a proposal

## Summary

We ran a controlled fault-injection experiment against the `skill-upper` skill
(truncated SKILL.md, deleted/truncated referenced attachments, blanked frontmatter)
and measured whether host agents notice the damage while following the skill.
Headline result: detection by the host is **probabilistic and path-dependent**
(8/8 when the damage blocks the main flow; 2/8 when it sits in an optionally-read
reference), and the toolchain itself performs **no integrity checking at any layer**.

## Findings

1. **The CLI never parses SKILL.md.** `internal/cli/run.go` only requires it to be a
   regular file (`isRegularFile`); `internal/skill` installs by copying. Nothing
   validates frontmatter or verifies that files referenced from SKILL.md exist.
   Your own e2e fixtures demonstrate this: their SKILL.md files are frontmatter-less
   stubs. Meanwhile `skill-up validate` *does* hard-fail on broken `eval.yaml`
   (missing case files, malformed YAML) — the eval-config layer is defended, the
   skill-content layer is not.
2. **The skill-upper workflow has no integrity step.** Step 1 reads the target
   SKILL.md to extract behaviors, but nothing checks document completeness or
   reference liveness before cases are generated. In our wounded-examiner run, a
   target skill whose tone-guide was truncated lost coverage of 5 format rules in
   the generated suite, silently.
3. **Host-agent vigilance is not a substitute.** Across 30+ runs on three hosts
   (kimi-code, Claude Code, Codex CLI): damage blocking the executing instruction
   was reliably reported (14/14), damage in optionally-read attachments was not
   (2/8 on kimi-code). Full data, grading rubric, and raw reports:
   <link to skill-quake repo / experiment log>.

## Proposal

Cheap, deterministic, in the spirit of the existing `validate` command:

1. Extend `skill-up validate` (or add `validate --skill`) to also check the skill
   itself: frontmatter parses, `name`/`description` non-empty, and every
   `references/|assets/|scripts/` path mentioned in SKILL.md exists on disk.
2. Optionally, one line in `skills/skill-upper/SKILL.md` Step 1 instructing the
   agent to run that check before scaffolding.
3. (Larger, future) a manifest/hash mode for tamper evidence against stealth cuts.

We have a working reference implementation of the checks (stdlib-only Python,
~150 LOC, fixture-tested) and would be happy to contribute it as a Go PR if you
think the direction fits.

## Notes

- All experiments ran on local copies; no third-party skills were harmed.
- We deliberately did not test semantic tampering (plausible-wrong instructions) —
  that is a separate, scarier question.
