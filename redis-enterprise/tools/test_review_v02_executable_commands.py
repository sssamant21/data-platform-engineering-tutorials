"""Offline fixture tests for V02 executable-command and output-cue triage."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_v02_executable_commands import inspect


class ExecutableCommandQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, text):
        (self.root / "01-demo.md").write_text(text, encoding="utf-8")

    def test_safe_command_with_expected_cue(self):
        self.put("# Chapter 01\n~~~redis\nPING\n~~~\nExpected output: PONG\n")
        summary = inspect(self.root)["summary"]
        self.assertEqual(summary["executable_fenced_blocks"], 1)
        self.assertEqual(summary["blocks_without_nearby_expected_cue"], 0)
        self.assertEqual(summary["high_risk_candidates"], 0)

    def test_cautionary_flush_is_still_a_candidate(self):
        self.put("# Chapter 01\nDo not run this:\n~~~redis\nFLUSHDB\n~~~\n")
        result = inspect(self.root)
        self.assertEqual(result["summary"]["high_risk_candidates"], 1)
        self.assertEqual(result["findings"][0]["verdict"], "HUMAN_CONTEXT_REVIEW_REQUIRED")

    def test_cluster_mutation_and_scan(self):
        self.put("# Chapter 01\n~~~bash\nrladmin restart node 1\nrcli SCAN 0\n~~~\n")
        categories = {x["rule"] for x in inspect(self.root)["findings"]}
        self.assertIn("cluster_mutation", categories)
        self.assertIn("redis_key_scan", categories)

    def test_key_deletion_is_scoped_by_review_not_auto_approved(self):
        self.put("# Chapter 01\n~~~redis\nUNLINK tutorial:owned:1\n~~~\n")
        result = inspect(self.root)
        self.assertEqual(result["summary"]["medium_risk_candidates"], 1)
        self.assertEqual(result["findings"][0]["verdict"], "HUMAN_CONTEXT_REVIEW_REQUIRED")

    def test_no_execution_and_password_redaction(self):
        self.put("# Chapter 01\n~~~bash\nredis-cli -a DO_NOT_EXPOSE PING\nexit 29\n~~~\n")
        result = inspect(self.root)
        self.assertEqual(result["summary"]["high_risk_candidates"], 1)
        self.assertNotIn("DO_NOT_EXPOSE", str(result["findings"]))
        self.assertIn("[REDACTED]", result["findings"][0]["command_excerpt"])


if __name__ == "__main__":
    unittest.main()
