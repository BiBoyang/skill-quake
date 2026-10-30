import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "skills/skill-quake/scripts/write_meta.py"
SPEC = importlib.util.spec_from_file_location("quake_write_meta", MODULE_PATH)
meta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(meta)


class WriteMetaTests(unittest.TestCase):
    def test_tree_hash_is_deterministic_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "refs").mkdir()
            (root / "empty").mkdir()
            (root / "SKILL.md").write_text("one\n", encoding="utf-8")
            (root / "refs/a.txt").write_text("a\n", encoding="utf-8")
            os.symlink("refs/a.txt", root / "link.txt")
            first = meta.tree_hash(root)
            self.assertEqual(first, meta.tree_hash(root))
            self.assertEqual(len(first), 64)
            (root / "SKILL.md").write_text("two\n", encoding="utf-8")
            self.assertNotEqual(first, meta.tree_hash(root))

    def test_tree_hash_rejects_a_file_instead_of_a_fixture_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("demo", encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                meta.tree_hash(path)

    def test_manifest_contains_provenance_hashes_and_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture"
            fixture.mkdir()
            (fixture / "SKILL.md").write_text("demo\n", encoding="utf-8")
            prompt = root / "prompt.txt"
            prompt.write_text("neutral prompt\n", encoding="utf-8")
            guard = root / "guard.json"
            guard.write_text('{"verdict":"FAIL"}\n', encoding="utf-8")
            checker = root / "checker"
            checker.write_text("checker-v1\n", encoding="utf-8")
            output = root / "meta.json"
            rc = meta.main([
                "--output", str(output), "--host", 'fake"host', "--fault", "f1",
                "--cell", "cell-a", "--run", "1", "--stage", "abc123",
                "--time", "2026-10-24T00:00:00Z", "--prompt", str(prompt),
                "--fixture", str(fixture), "--guard", str(guard),
                "--witness-checker", str(checker), "--target-version", "target-v1",
                "--host-version", "host-v1", "--model", "model-v1", "--effort", "high",
            ])
            self.assertEqual(rc, 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["host"], 'fake"host')
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["prompt_sha256"], meta.file_hash(prompt))
            self.assertEqual(data["fixture_sha256"], meta.tree_hash(fixture))
            self.assertEqual(data["witness"]["verdict"], "FAIL")
            self.assertEqual(data["witness"]["checker_sha256"], meta.file_hash(checker))
            self.assertEqual(data["missing"], [])

    def test_strict_mode_rejects_missing_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture"
            fixture.mkdir()
            prompt = root / "prompt"
            prompt.write_text("x", encoding="utf-8")
            guard = root / "guard"
            guard.write_text('{"verdict":"PASS"}', encoding="utf-8")
            rc = meta.main([
                "--output", str(root / "meta"), "--host", "h", "--fault", "f",
                "--cell", "c", "--run", "1", "--stage", "s", "--prompt", str(prompt),
                "--fixture", str(fixture), "--guard", str(guard),
                "--witness-checker", str(prompt), "--strict",
            ])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
