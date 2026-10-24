#!/usr/bin/env python3
"""Static regression tests for Chapter 001 recovery acceptance invariants.

These checks do not replace live kind/Strimzi integration testing.
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
FILES = {
    "single": ROOT / "certify_chapter_001_recovery.py",
    "three": ROOT / "certify_chapter_001_ha.py",
    "six": ROOT / "certify_chapter_001_six_pod.py",
}

class Chapter001RecoveryGuards(unittest.TestCase):
    def test_all_scripts_parse(self):
        for label, path in FILES.items():
            with self.subTest(lab=label):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_replacement_uid_required(self):
        for label, path in FILES.items():
            with self.subTest(lab=label):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                comparisons = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.Compare)
                    and any(isinstance(op, ast.NotEq) for op in node.ops)
                ]
                self.assertTrue(comparisons, f"{label}: missing new-UID comparison")
                source = path.read_text(encoding="utf-8")
                self.assertIn('["uid"]', source)

    def test_bounded_replacement_wait(self):
        for label, path in FILES.items():
            with self.subTest(lab=label):
                source = path.read_text(encoding="utf-8")
                self.assertIn("time.monotonic()", source)
                self.assertIn("time.sleep(5)", source)
                self.assertIn("containerStatuses", source)
                self.assertIn("status", source)

    def test_context_guard(self):
        for label, path in FILES.items():
            with self.subTest(lab=label):
                source = path.read_text(encoding="utf-8")
                self.assertIn("kind-kafka-qa", source)
                self.assertIn("current-context", source)
                self.assertIn("raise RuntimeError", source)

    def test_result_written_on_failure(self):
        for label, path in FILES.items():
            with self.subTest(lab=label):
                source = path.read_text(encoding="utf-8")
                self.assertIn("finally:", source)
                self.assertIn("write_text(", source)
                self.assertIn("return 0 if", source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
