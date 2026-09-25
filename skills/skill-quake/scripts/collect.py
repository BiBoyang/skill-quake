#!/usr/bin/env python3
"""collect.py — aggregate fault-injection runs into a summary table.

Expects: <results>/<cell>/<run>/{meta.json, report.md, grade.json}
  meta.json   (runner-written): {"host": "...", "fault": "...", "notes": "..."}
  grade.json  (grader-written): {"level": "L0|L1|L2|L3", "detected": true|false,
                                 "drift": "...", "notes": "..."}
Cell = one host x fault combination (e.g. "kimi+truncate-main").
"""
import json
import os
import sys


def main():
    results_dir = sys.argv[1]
    cells = {}
    ungraded = 0
    for cell in sorted(os.listdir(results_dir)):
        cpath = os.path.join(results_dir, cell)
        if not os.path.isdir(cpath):
            continue
        for run in sorted(os.listdir(cpath)):
            rpath = os.path.join(cpath, run)
            meta_p = os.path.join(rpath, "meta.json")
            if not os.path.isfile(meta_p):
                continue
            meta = json.load(open(meta_p, encoding="utf-8"))
            grade_p = os.path.join(rpath, "grade.json")
            grade = json.load(open(grade_p, encoding="utf-8")) if os.path.isfile(grade_p) else None
            if grade is None:
                ungraded += 1
            cells.setdefault(cell, []).append((run, meta, grade))

    rows, summary = [], {}
    for cell, runs in cells.items():
        graded = [g for _, _, g in runs if g]
        det = sum(1 for g in graded if g.get("detected"))
        levels = ",".join(g.get("level", "?") for _, _, g in runs) or "-"
        rows.append((cell, len(runs), len(graded), det, levels))
        summary[cell] = {"runs": len(runs), "graded": len(graded), "detected": det, "levels": levels}

    print("| cell | runs | graded | detected | levels |")
    print("|---|---|---|---|---|")
    for cell, n, ng, det, levels in rows:
        print(f"| {cell} | {n} | {ng} | {det}/{ng or '-'} | {levels} |")
    with open(os.path.join(results_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    if ungraded:
        print(f"\n{ungraded} run(s) missing grade.json — grade before trusting rates.", file=sys.stderr)


if __name__ == "__main__":
    main()
