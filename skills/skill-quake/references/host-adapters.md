# Host adapters

How to drive each host headless, and what "loading a skill" means on each.
All adapters: `scripts/run_host.sh <host> <prompt_file> <workdir> <out_file>`.

## Spike first

Before any matrix, run one hello-level prompt per host and confirm a sane reply:

```bash
scripts/run_host.sh <host> spike-prompt.txt /tmp spike-out.txt
```

A host that fails the spike (auth, sandbox, network) is SKIP for the whole matrix.
Record the skip reason; never silently substitute another host.

## kimi

- Headless: `kimi -p "<prompt>" --output-format text`.
- Preferred for large-N cells: fresh subagents spawned by the orchestrating agent
  (zero shared context, full tools). The CLI path is the portable fallback.
- Skill discovery (interactive): user scope `~/.agents/skills/<name>/SKILL.md`.
  Headless/path-based loading bypasses discovery — say so in the writeup.

## claude (Claude Code)

- Headless: `claude -p "<prompt>" --output-format text --permission-mode acceptEdits`.
- **Pitfall (observed in practice)**: with cwd inside the run workdir, reads of a skill
  directory *outside* the cwd are denied in headless mode (`... you haven't granted
  it yet`). Pass the skill dir via `--add-dir <skill-path>` (run_host.sh does this
  when given the optional 5th argument). Symptom of getting this wrong: reports
  that say "cannot read the skill" — such runs are environment failures, not data;
  discard and rerun.
- Skill discovery: `~/.claude/skills/<name>/SKILL.md` (user scope). To test the real
  loader (e.g. blank-frontmatter), install the mutated skill there temporarily,
  start a fresh session, observe registration; remove afterwards. Pointing at a path
  bypasses discovery — keep the two modes clearly separated in the report.
- Native-model use requires the user's own Claude plan; kimi-backed setups work but
  change the variable from "host+model" to "host harness only". Record which.

## codex

- Headless: `codex exec --skip-git-repo-check --sandbox workspace-write "<prompt>"`.
- Provider/model: defaults come from `~/.codex/config.toml`. Override per run with
  env vars `CODEX_PROVIDER` / `CODEX_MODEL` (e.g. `CODEX_PROVIDER=kimi
  CODEX_MODEL=kimi-for-coding` to run the kimi-backed coding endpoint). A default
  provider dying (quota/403) is a *config* problem — switch provider and rerun;
  only mark the column SKIP when no configured provider remains.
- codex has no skill-installation convention comparable to the others; the neutral
  prompt points at the skill path (prompt-injection mode). Results are about
  "agent following a markdown playbook", not about codex's skill loader.
- `-m <model>` selects the model; default comes from `~/.codex/config.toml`.

## Quota and cost discipline

Every headless run spends the account's quota. State the total run budget before a
matrix (cells x N), spike first, and stop at the budget even mid-matrix.

A spike proves auth works *now*, not that the balance survives the whole matrix —
a relay account died of a 403 mid-matrix in practice, killing 5 of 6 runs. For
metered/relay providers, check the balance before starting and treat mid-matrix
deaths as environment failures (discard the cell), never as data.
