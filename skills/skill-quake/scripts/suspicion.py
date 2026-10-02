#!/usr/bin/env python3
"""suspicion.py — reread_any: a trace-level early-warning tripwire (zero tokens).

Definition (wound-agnostic, computable from the tool-call trace alone):
  reread_any is TRUE when any single file is read >= 2 times in one run.

Why it exists: in the pi host column (2026-10, pi 1.0.0 x kimi-for-coding, 34 graded
runs) every healthy or non-blocking run read each file exactly once, while every run
that detected a stealth content truncation re-read the wounded file 2+ extra times
(confusion: TP=8 FP=0 TN=23 FN=3). Stealth truncation is the fault class where the
gate (skill-guard), the loader, and a single first read are ALL blind — this signal
covers exactly that class, from the trace alone, before any report exists.

Boundary conditions (observed, do not oversell):
  - FN by design: wounds visible on first read (e.g. empty frontmatter) or wounds that
    surface as tool errors (missing file -> ENOENT) can be detected WITHOUT re-reading.
  - The healthy baseline "one read per file" is task-shaped. Calibrate per task with
    healthy (C0) runs before trusting the flag; a task that legitimately requires
    re-reading will produce false positives.
  - Requires an ordered tool-call trace. Text-only adapters (kimi -p) cannot supply it;
    see references/host-adapters.md for which hosts can.

Inputs (one of):
  --trace <trace.json>     ordered tool calls: [{"name": "...", "arguments": {...}}, ...]
  --pi-jsonl <out.jsonl>   extract the trace from a pi --mode json transcript first
  --results <results-dir>  walk <cell>/<run>/trace.json, join with grade.json when
                           present, print per-run table + confusion view

Output: JSON (single-trace mode) or a table (results mode).
"""
import glob
import json
import os
import sys
from collections import defaultdict


def analyze_trace(tools: list) -> dict:
    """Compute reread features from an ordered list of tool calls."""
    seq = []
    for t in tools:
        if not isinstance(t, dict) or t.get("name") != "read":
            continue
        args = t.get("arguments") or {}
        path = args.get("path") or args.get("file_path") or json.dumps(args, ensure_ascii=False)
        seq.append(str(path))
    counts = defaultdict(int)
    for p in seq:
        counts[p] += 1
    # secondary feature: return-sweep — f re-read after >=2 distinct other files
    last_seen = {}
    others_since = defaultdict(set)
    sweeps = set()
    for p in seq:
        if p in last_seen and len(others_since[p]) >= 2:
            sweeps.add(p)
        others_since[p] = set()
        for f in others_since:
            if f != p:
                others_since[f].add(p)
        last_seen[p] = True
    return {
        "reads_total": len(seq),
        "distinct_files": len(counts),
        "max_single_reads": max(counts.values()) if counts else 0,
        "reread_any": bool(counts) and max(counts.values()) >= 2,
        "reread_files": sorted(p for p, c in counts.items() if c >= 2),
        "return_sweep_files": sorted(sweeps),
    }


def trace_from_pi_jsonl(path: str) -> list:
    """Pull ordered tool calls out of a pi --mode json transcript."""
    tools = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "message_end":
                continue
            message = event.get("message") or {}
            if message.get("role") != "assistant":
                continue
            for block in message.get("content", []):
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    tools.append({"name": block.get("name"), "arguments": block.get("arguments")})
    return tools


def run_results_mode(results_dir: str) -> None:
    rows = []
    for trace_path in sorted(glob.glob(os.path.join(results_dir, "*", "*", "trace.json"))):
        parts = trace_path.replace("\\", "/").split("/")
        cell, run = parts[-3], parts[-2]
        with open(trace_path, encoding="utf-8") as fh:
            tools = json.load(fh)
        feat = analyze_trace(tools)
        grade = None
        grade_path = os.path.join(os.path.dirname(trace_path), "grade.json")
        if os.path.isfile(grade_path):
            grade = json.load(open(grade_path, encoding="utf-8"))
        rows.append({"cell": cell, "run": run, **feat,
                     "detected": grade.get("detected") if grade else None,
                     "level": grade.get("level") if grade else None})

    print(f"{'cell':<24} {'run':<8} {'det':<6} {'lvl':<4} {'reads':<5} {'max':<4} reread_any")
    for r in rows:
        print(f"{r['cell']:<24} {r['run']:<8} {str(r['detected']):<6} {str(r['level']):<4} "
              f"{r['reads_total']:<5} {r['max_single_reads']:<4} {str(r['reread_any'])}")

    tp = fp = tn = fn = 0
    for r in rows:
        if r["detected"] is None:
            continue
        if r["reread_any"] and r["detected"]:
            tp += 1
        elif r["reread_any"]:
            fp += 1
        elif r["detected"]:
            fn += 1
        else:
            tn += 1
    graded = tp + fp + tn + fn
    if graded:
        print(f"\nreread_any vs detection over {graded} graded runs: TP={tp} FP={fp} TN={tn} FN={fn}")
        print("FP>0 means the task baseline needs recalibration (see docstring).")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--results":
        run_results_mode(args[1])
        return
    if args[0] == "--pi-jsonl":
        result = analyze_trace(trace_from_pi_jsonl(args[1]))
    elif args[0] == "--trace":
        with open(args[1], encoding="utf-8") as fh:
            result = analyze_trace(json.load(fh))
    else:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
