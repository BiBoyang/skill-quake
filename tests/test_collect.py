import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "skills/skill-quake/scripts/collect.py"
SPEC = importlib.util.spec_from_file_location("quake_collect", MODULE_PATH)
collect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collect)


class CollectTests(unittest.TestCase):
    def test_invalid_and_ungraded_stay_outside_denominators(self):
        runs = [
            ("run-1", {}, {"level": "INVALID", "detected": False, "reported": True}),
            ("run-2", {}, {
                "level": "L2", "detected": True, "reported": True,
                "contained": False, "recovered": None, "reverified": True,
            }),
            ("run-3", {}, {
                "level": "L0", "detected": False, "reported": False,
                "contained": False, "recovered": True,
            }),
            ("run-4", {}, None),
        ]
        row = collect.summarize_cell(runs)
        self.assertEqual(row["runs"], 4)
        self.assertEqual(row["graded"], 2)
        self.assertEqual(row["excluded"], 1)
        self.assertEqual(row["ungraded"], 1)
        self.assertEqual(row["detected"], 1)
        self.assertEqual(row["levels"], "INVALID,L2,L0,?")
        self.assertEqual(row["metrics"]["detected"], {"x": 1, "n": 2, "unknown": 0})
        self.assertEqual(row["metrics"]["reported"], {"x": 1, "n": 2, "unknown": 0})
        self.assertEqual(row["metrics"]["contained"], {"x": 0, "n": 2, "unknown": 0})
        self.assertEqual(row["metrics"]["recovered"], {"x": 1, "n": 1, "unknown": 1})
        self.assertEqual(row["metrics"]["reverified"], {"x": 1, "n": 1, "unknown": 1})

    def test_valid_false_excludes_even_a_detected_l2(self):
        row = collect.summarize_cell([
            ("run-1", {}, {"level": "L2", "detected": True, "valid": False}),
            ("run-2", {}, {"level": "L0", "detected": False}),
        ])
        self.assertEqual(row["graded"], 1)
        self.assertEqual(row["excluded"], 1)
        self.assertEqual(row["detected"], 0)

    def test_legacy_grades_do_not_invent_new_metrics(self):
        row = collect.summarize_cell([
            ("run-1", {}, {"level": "L2", "detected": True, "drift": "none"}),
            ("run-2", {}, {"level": "L3", "detected": True, "drift": "none"}),
        ])
        self.assertEqual(set(row["metrics"]), {"detected"})
        self.assertEqual(row["graded"], 2)
        self.assertEqual(row["detected"], 2)

    def test_main_writes_summary_and_does_not_crash_on_missing_grade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, grade in enumerate(({"level": "INVALID", "detected": False}, None), 1):
                run = root / "cell-a" / f"run-{index}"
                run.mkdir(parents=True)
                (run / "meta.json").write_text(json.dumps({"run": index}), encoding="utf-8")
                if grade is not None:
                    (run / "grade.json").write_text(json.dumps(grade), encoding="utf-8")
            self.assertEqual(collect.main(["collect.py", str(root)]), 0)
            summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["cell-a"]["graded"], 0)
            self.assertEqual(summary["cell-a"]["excluded"], 1)
            self.assertEqual(summary["cell-a"]["ungraded"], 1)


if __name__ == "__main__":
    unittest.main()
