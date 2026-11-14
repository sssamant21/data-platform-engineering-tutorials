"""Fixture-only tests for comprehensive V02 safety review inventory."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_v02_safety import audit, as_markdown


class SafetyAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, text: str):
        (self.root / "01-demo.md").write_text(text, encoding="utf-8")

    def test_negative_examples_still_require_review(self):
        self.put("# Chapter 01\nNever execute this command:\n~~~redis\nFLUSHALL\n~~~\n")
        r = audit(self.root)
        self.assertEqual(r["summary"]["candidates"], 1)
        self.assertEqual(r["findings"][0]["pattern"], "flush_database")
        self.assertEqual(r["findings"][0]["verdict"], "NEEDS_CONTEXT_REVIEW")
        self.assertIn("Never execute", r["findings"][0]["before"])

    def test_matches_all_patterns_per_block(self):
        self.put("# Chapter 01\n~~~redis\nFLUSHALL\nKEYS *\n~~~\n")
        r = audit(self.root)
        self.assertEqual(r["summary"]["candidates"], 2)
        self.assertEqual({x["pattern"] for x in r["findings"]},
                         {"flush_database", "unbounded_keys"})

    def test_password_redaction(self):
        self.put("# Chapter 01\n~~~bash\nredis-cli -a NEVER_PRINT_THIS_SECRET PING\n~~~\n")
        r = audit(self.root)
        self.assertEqual(r["summary"]["candidates"], 1)
        self.assertNotIn("NEVER_PRINT_THIS_SECRET", as_markdown(r))
        self.assertIn("[REDACTED]", r["findings"][0]["matched_line"])

    def test_safe_example_has_no_findings(self):
        self.put("# Chapter 01\n~~~bash\nredis-cli --tls PING\n~~~\n")
        self.assertEqual(audit(self.root)["summary"]["candidates"], 0)


if __name__ == "__main__":
    unittest.main()
