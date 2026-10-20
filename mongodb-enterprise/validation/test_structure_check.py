#!/usr/bin/env python3
"""Offline-only unit tests for the Phase 4 structure checker; no MongoDB connection."""
import pathlib
import tempfile
import unittest

from structure_check import audit


class StructureCheckTests(unittest.TestCase):
    def test_complete_synthetic_curriculum_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for n in range(1, 81):
                (root / f"{n:02d}-synthetic.md").write_text(
                    f"# Chapter {n:02d}\n\n[Next](01-synthetic.md)\n\n```javascript\nprint(1)\n```\n",
                    encoding="utf-8",
                )
            result = audit(root)
            self.assertTrue(result["passed"], result["errors"])
            self.assertEqual(result["chapters_found"], 80)
            self.assertFalse(result["runtime_certified"])

    def test_missing_chapter_and_bad_link_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "01-only.md").write_text(
                "# Chapter 01\n[Missing](02-missing.md)\n", encoding="utf-8"
            )
            result = audit(root)
            self.assertFalse(result["passed"])
            self.assertTrue(any("Missing chapter 02" in e for e in result["errors"]))
            self.assertTrue(any("missing local link" in e for e in result["errors"]))

    def test_unbalanced_fence_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for n in range(1, 81):
                (root / f"{n:02d}-synthetic.md").write_text(
                    "# Test\n" + ("```python\n" if n == 3 else ""),
                    encoding="utf-8",
                )
            result = audit(root)
            self.assertFalse(result["passed"])
            self.assertTrue(any("03-synthetic.md: unbalanced" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
