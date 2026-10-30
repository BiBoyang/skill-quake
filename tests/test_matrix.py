import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[1]
META_PATH = REPO / "skills/skill-quake/scripts/write_meta.py"
SPEC = importlib.util.spec_from_file_location("quake_matrix_meta", META_PATH)
meta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(meta)


class MatrixTests(unittest.TestCase):
    def make_workspace(self, root):
        scripts = root / "skills/skill-quake/scripts"
        scripts.parent.mkdir(parents=True)
        shutil.copytree(REPO / "skills/skill-quake/scripts", scripts)
        (root / "bin").mkdir()
        shutil.copy2(REPO / "bin/skill-guard", root / "bin/skill-guard")
        fake = scripts / "run_host.sh"
        fake.write_text(
            "#!/bin/bash\nprintf 'host-side fixture change\\n' >> \"$5/SKILL.md\"\n"
            "printf 'fake report\\n' > \"$4\"\nprintf '0\\n' > \"$4.exitcode\"\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        source = root / "source"
        shutil.copytree(REPO / "tests/fixtures/healthy-mini", source)
        prompt = root / "prompt.txt"
        prompt.write_text("Read __SKILL_PATH__ and work in __WORKDIR__\n", encoding="utf-8")
        return scripts / "matrix.sh", source, prompt

    def test_matrix_writes_rich_meta_without_touching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix, source, prompt = self.make_workspace(root)
            before = hashlib.sha256((source / "SKILL.md").read_bytes()).hexdigest()
            env = os.environ.copy()
            env.update({
                "QUAKE_TARGET_VERSION": "target-v1",
                "QUAKE_HOST_VERSION": "fake-host-v1",
                "QUAKE_MODEL": "demo-model",
                "QUAKE_EFFORT": "low",
                "QUAKE_STRICT_META": "1",
            })
            expected_fixture = root / "expected-fixture"
            subprocess.run(
                ["bash", str(matrix.parent / "mutate.sh"), str(source), "truncate-main", "60", str(expected_fixture)],
                check=True, capture_output=True, text=True,
            )
            expected_hash = meta.tree_hash(expected_fixture)
            results = root / "results"
            subprocess.run(
                ["bash", str(matrix), str(source), str(results), str(prompt), "fake", "truncate-main:60", "1"],
                check=True, capture_output=True, text=True, env=env,
            )
            after = hashlib.sha256((source / "SKILL.md").read_bytes()).hexdigest()
            self.assertEqual(before, after)
            run = results / "fake+truncate-main-60/run-1"
            data = json.loads((run / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(data["target_version"], "target-v1")
            self.assertEqual(data["host_version"], "fake-host-v1")
            self.assertEqual(data["model"], "demo-model")
            self.assertEqual(data["effort"], "low")
            self.assertEqual(data["missing"], [])
            self.assertEqual(len(data["prompt_sha256"]), 64)
            self.assertEqual(data["fixture_sha256"], expected_hash)
            stage = results / ".stage" / data["stage"] / "skill"
            self.assertNotEqual(meta.tree_hash(stage), expected_hash)
            self.assertIn("verdict", data["witness"])
            self.assertTrue((run / "report.md").is_file())
            self.assertTrue((run / "guard.json").is_file())

    def test_strict_meta_stops_before_host_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix, source, prompt = self.make_workspace(root)
            env = os.environ.copy()
            env["QUAKE_STRICT_META"] = "1"
            result = subprocess.run(
                ["bash", str(matrix), str(source), str(root / "results"), str(prompt), "fake", "truncate-main:60", "1"],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("incomplete provenance", result.stderr)
            self.assertFalse((root / "results").exists())


if __name__ == "__main__":
    unittest.main()
