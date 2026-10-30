"""V02 fixture-only tests: no Redis client or command execution."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_v02_examples import audit

FENCE = chr(96) * 3


class V02ExampleAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.put(1, "# Chapter 01\n")
        self.put(2, "# Chapter 02\n")

    def put(self, n, text):
        (self.root / f"{n:02d}-test.md").write_text(text, encoding="utf-8")

    def scan(self):
        return audit(self.root, expected_chapters=2)

    def test_fenced_redis_command_with_expected_result(self):
        self.put(1, f"# Chapter 01\n{FENCE} redis\nPING\n{FENCE}\nExpected: PONG\n")
        s = self.scan()["summary"]
        self.assertEqual(s["explicit_command_blocks"], 1)
        self.assertEqual(s["command_blocks_missing_nearby_expected_cue"], 0)

    def test_missing_expected_result_is_review_only(self):
        self.put(1, f"# Chapter 01\n{FENCE} bash\nredis-cli PING\n{FENCE}\nUnrelated text.\n")
        self.assertEqual(self.scan()["summary"]["command_blocks_missing_nearby_expected_cue"], 1)

    def test_hazard_inside_command_block(self):
        self.put(1, f"# Chapter 01\n{FENCE} redis\nFLUSHALL\n{FENCE}\n")
        self.assertEqual(self.scan()["summary"]["safety_review_candidates"], 1)

    def test_hazard_outside_command_block_not_auto_flagged(self):
        self.put(1, "# Chapter 01\nDo not run FLUSHALL in a shared environment.\n")
        self.assertEqual(self.scan()["summary"]["safety_review_candidates"], 0)

    def test_untyped_command_candidate(self):
        self.put(1, f"# Chapter 01\n{FENCE} text\nGET tutorial:key\n{FENCE}\n")
        self.assertEqual(self.scan()["summary"]["untyped_command_candidates"], 1)

    def test_invalid_json_is_review_candidate(self):
        self.put(1, f"# Chapter 01\n{FENCE} json\n{{oops}}\n{FENCE}\n")
        self.assertEqual(self.scan()["summary"]["json_syntax_review_candidates"], 1)

    def test_python_parse_only_not_execution(self):
        self.put(1, f"# Chapter 01\n{FENCE} python\nraise RuntimeError('must not run')\n{FENCE}\n")
        self.assertEqual(self.scan()["summary"]["python_syntax_findings"], 0)
        self.assertEqual(self.scan()["summary"]["python_blocks"], 1)

    def test_invalid_python_syntax(self):
        self.put(1, f"# Chapter 01\n{FENCE} python\nif :\n{FENCE}\n")
        self.assertEqual(self.scan()["summary"]["python_syntax_findings"], 1)

    def test_incomplete_fence_not_miscounted(self):
        self.put(1, f"# Chapter 01\n{FENCE} bash\nredis-cli PING\n")
        self.assertEqual(self.scan()["summary"]["total_code_fences"], 0)


if __name__ == "__main__":
    unittest.main()
