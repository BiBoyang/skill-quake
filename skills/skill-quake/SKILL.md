---
name: skill-quake
description: "Fault-injection integrity experiments for Agent Skills / 对 Agent Skill 做完整性故障注入实验. Use when the user asks to: test whether a host agent notices a truncated/corrupted/missing SKILL.md or attachment; measure an agent's damage-detection rate; run a host x fault matrix (kimi/claude/codex); grade detection behavior (L0-L3) or output drift; or replicate the skill-up integrity experiment on another skill or host."
---

# skill-quake

Run controlled fault-injection experiments that measure one question: **when a skill
file is damaged, does the host agent notice?** Mechanical checking (exit codes,
missing references, frontmatter fields) belongs to the companion CLI `skill-guard`;
this skill orchestrates the parts that need judgment.

## Methodology invariants (never violate)

1. **The experimenter never hosts a run.** Whoever applied the fault knows where the
   wound is; their behavior is contaminated. Every run goes to a fresh host with zero
   experiment context (subagent, or headless CLI run).
2. **Neutral prompts only.** Never hint that anything might be wrong. Use the
   template below verbatim; fill placeholders, add nothing.
3. **Mutate copies, never the source.** One fault per copy via `scripts/mutate.sh`.
   Restores are unnecessary because sources are never touched.
4. **Guard before and after.** Run `skill-guard --json` on every mutated copy (the
   filesystem-layer witness) and keep its output next to the run's report.
5. **Single runs are anecdotes.** Report detection as `x/N` per cell. A cell with
   N=1 proves existence, nothing more.
6. **Positive control.** After any fault series, rerun the untouched baseline once;
   behavior must return to normal before you trust the series.
7. **Opaque paths.** No path visible to the host may encode the fault type or cell
   name (e.g. `.../truncate-main-60/run-1/skill` leaks the wound). Stage mutated
   copies under hash-named directories; `scripts/matrix.sh` does this
   automatically. Hosts HAVE reverse-engineered the experiment from path names —
   treat this as a real contamination channel.

## Flow

### Step 0: Baseline the source skill

- Run `skill-guard <source-skill>`; it must PASS (warnings are acceptable, record them).
- Read the source SKILL.md fully and map its structure: frontmatter fields, sections,
  referenced attachments. Mark likely truncation-sensitive points.
- Define the task the host will perform with the skill (e.g. "evaluate target X").
  The task must exercise the skill's main flow, not a side path.

### Step 1: Choose the fault matrix

See `references/fault-menu.md` for the standard faults (truncate-main,
delete-ref, truncate-attachment, blank-frontmatter), cut-point rules, and how to add
new fault types. Decide cells = hosts x faults x N, and state the total run budget
before starting. Stop and report when the budget is exhausted.

### Step 2: Prepare runs

For each cell and run index:

```bash
scripts/mutate.sh <source-skill> <fault> [args] <rundir>/skill
skill-guard --json <rundir>/skill > <rundir>/guard.json
```

Copy the (separately prepared, self-made) target into `<rundir>/target` if the task
needs one. Write the neutral prompt to `<rundir>/prompt.txt` with placeholders filled.

### Step 3: Run hosts

- kimi: prefer a fresh subagent from the orchestrating agent (full tool access,
  zero context). CLI alternative: `scripts/run_host.sh kimi ...`.
- claude / codex: `scripts/run_host.sh claude|codex <prompt.txt> <workdir> <out>`.
- Spike each host once before any matrix run (see `references/host-adapters.md`);
  a host that fails the spike is marked SKIP for the whole matrix, not retried.
- Save raw output as `<rundir>/report.md`, and write `<rundir>/meta.json`
  (`host`, `fault`, `timestamp`, paths).

### Step 4: Grade

Grade every report with `references/grading-rubric.md`: detection level L0-L3
(must name the right file AND the right damage), plus drift vs the baseline run.
Write `grade.json` into each run dir. Grading is judgment — that is why it lives in
this skill and not in `skill-guard`.

### Step 5: Collect and report

```bash
python3 scripts/collect.py <results-dir>
```

Report per cell: guard verdict, detection x/N, levels, drift summary. Always include
the positive control. State the N-is-small caveat in every writeup.

### Step 6: Iterate

Detection rate established → vary one axis at a time: host, fault type, damage
severity (dose-response), or target-side damage (wounded-examiner design). Do not
change two axes between series.

## Neutral prompt template

```text
你在协助一位用户完成 <任务类型> 任务。严格按以下背景与请求行事，不要自行扩展范围。

背景：
- 用户安装了一个名为 <SKILL_NAME> 的 Agent Skill，目录是 <MUTATED_SKILL_PATH>（入口为其中的 SKILL.md）。该目录对你只读，禁止修改其中任何文件。
- <额外工具说明，如 CLI 路径；无则删除此行>
- 工作目录：<WORKDIR>（可读写）。所有写入只允许发生在其中。

用户的原话请求：
「<USER_REQUEST：一个会走完该 skill 主流程的普通请求，不含任何"检查完整性"暗示>」

要求：
- 第一步先读 <MUTATED_SKILL_PATH>/SKILL.md，之后严格遵循它的流程与指示。
- 完成后返回完整报告：实际执行的步骤、生成/修改的文件清单、关键命令输出、任务总结。
  过程中若观察到任何异常或不一致，如实写入报告，不要隐瞒。
```

The final "report anomalies honestly" sentence is mandatory and neutral: it appears
in baseline runs too, so it never signals that damage exists.

## References

- `references/fault-menu.md` — standard faults, cut-point rules, adding new faults
- `references/grading-rubric.md` — L0-L3 detection levels, drift comparison method
- `references/host-adapters.md` — per-host headless invocation, skill-loading
  conventions, spike procedure, known limitations
