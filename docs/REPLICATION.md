# Replication runbook — native Claude / GPT hosts

Audience: you have a Claude Code and/or Codex CLI logged in with a **native**
subscription (Claude plan / ChatGPT plan), and you were handed this repo to run the
host-matrix cells we could not run. Everything below is copy-pasteable. Total time
~45–75 min, most of it unattended.

## 0. Ground rules (the experiment dies without these)

- **Do not read the mutated skill files before grading.** Knowing where the wound
  is contaminates your judgment (the "experimenter never hosts" rule).
- **Do not edit the prompt template.** Every run must say exactly the same thing.
- If something asks for confirmation mid-run, answer as a normal user would; note
  it in that run's `notes`.

## 1. Setup (5 min)

```bash
git clone <this-repo-url> skill-quake && cd skill-quake   # or untar the bundle
python3 bin/skill-guard examples/greeting-card            # expect: PASS
claude --version; codex --version                          # record both
```

The example task drives Alibaba's `skill-up` CLI, so install it (macOS/Linux):

```bash
curl -fsSL https://raw.githubusercontent.com/alibaba/skill-up/main/install.sh | bash
skill-up --version
```

Then point `QUAKE` at the repo and `SKILL_UP_SRC` at a skill-up checkout:

```bash
export QUAKE=$PWD
git clone --depth 1 https://github.com/alibaba/skill-up /tmp/skill-up-src
export SKILL_UP_SRC=/tmp/skill-up-src/skills/skill-upper
```

## 2. Spike (2 runs)

```bash
echo 'Reply with exactly: SPIKE-OK' > /tmp/spike.txt
bash skills/skill-quake/scripts/run_host.sh claude /tmp/spike.txt /tmp /tmp/spike-claude.txt
cat /tmp/spike-claude.txt        # expect SPIKE-OK
bash skills/skill-quake/scripts/run_host.sh codex /tmp/spike.txt /tmp /tmp/spike-codex.txt
cat /tmp/spike-codex.txt         # expect SPIKE-OK
```

A host that fails is SKIP for everything below — note why and move on.

## 3. Matrix (12 runs)

Two faults x two hosts x N=3. Each command runs 3 times (~5–10 min):

```bash
export TARGET="$QUAKE/examples/greeting-card"   # each run gets its own target copy
for host in claude codex; do
  for spec in "truncate-main:60" "truncate-attachment:references/judge-types.md:50"; do
    bash skills/skill-quake/scripts/matrix.sh \
      "$SKILL_UP_SRC" "$QUAKE/results" examples/replication-prompt.txt "$host" "$spec" 3
  done
done
```

(Only have one of the two hosts? Run its half; partial matrices are still useful.)

Positive control (mandatory, proves the harness itself is sane — one run against
the **untouched** source):

```bash
mkdir -p /tmp/quake-control && cp -R "$TARGET" /tmp/quake-control/target
sed -e "s|__SKILL_PATH__|$SKILL_UP_SRC|g" -e "s|__WORKDIR__|/tmp/quake-control|g" \
  examples/replication-prompt.txt > /tmp/quake-control-prompt.txt
bash skills/skill-quake/scripts/run_host.sh claude \
  /tmp/quake-control-prompt.txt /tmp/quake-control "$QUAKE/results/control-claude.md"
```

## 4. Grade (15 min)

For each `results/<cell>/run-N/report.md`, decide the detection level per
`skills/skill-quake/references/grading-rubric.md` (L0 none / L1 wrong object /
L2 correct file+kind / L3 refuses), and write `grade.json` next to it:

```bash
cat > results/claude+truncate-main-60/run-1/grade.json <<'EOF'
{"level": "L2", "detected": true, "drift": "none visible", "notes": "named SKILL.md cut at line 174"}
EOF
```

Grading is the one judgment step — do it yourself or ask your agent to grade, but
apply the rubric strictly: detection must name the right file AND the right damage.

## 5. Collect and send back

```bash
python3 skills/skill-quake/scripts/collect.py results
tar czf quake-results.tgz results/
```

Send `quake-results.tgz` plus: host versions, the model each host actually used
(`claude -p 'what model are you?'` is fine), and any mid-run manual interventions.

## What gets compared

Your cells extend the host x fault matrix alongside the kimi-backed cells. The
interesting comparison is per-cell detection x/3 across hosts AND models — keep
runs untouched (raw `report.md` files matter more than summaries).
