"""Fixture tests for the offline Redis interactive fence syntax review."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_v02_redis_fence_syntax import inspect


class RedisFenceSyntaxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def put(self, contents):
        (self.root / "03-fixture.md").write_text(contents, encoding="utf-8")

    def test_reports_bash_continuation_inside_redis_fence(self):
        self.put("# Fixture\n~~~redis\nHSET lab:key \\\n  name Alice\n~~~\n")
        findings = inspect(self.root)["findings"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "shell_continuation_in_interactive_redis")

    def test_reports_missing_scan_cursor(self):
        self.put("# Fixture\n~~~redis\nSCAN\nHSCAN\nSSCAN\nZSCAN\n~~~\n")
        result = inspect(self.root)
        self.assertEqual(result["summary"]["syntax_review_candidates"], 4)
        self.assertTrue(all(x["rule"] == "cursor_command_missing_arguments" for x in result["findings"]))

    def test_complete_commands_pass(self):
        self.put("# Fixture\n~~~redis\nSET tutorial:chapter03:x Alice\nHSET tutorial:chapter03:y name Alice\nSCAN 0 MATCH 'tutorial:chapter03:*' COUNT 100\nHSCAN tutorial:chapter03:y 0 COUNT 100\n~~~\n")
        self.assertEqual(inspect(self.root)["summary"]["syntax_review_candidates"], 0)

    def test_bash_continuation_is_outside_scope(self):
        self.put("# Fixture\n~~~bash\nredis-cli HSET lab:key \\\n  name Alice\n~~~\n")
        self.assertEqual(inspect(self.root)["summary"]["syntax_review_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
