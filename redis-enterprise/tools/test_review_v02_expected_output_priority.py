"""Fixtures for V02 expected-output priority queue."""
import tempfile
import unittest
from pathlib import Path
from review_v02_expected_output_priority import inspect

class ExpectedOutputPriorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def add(self, name, content):
        (self.root/name).write_text(content, encoding="utf-8")

    def test_release_sensitive_redisjson_precedes_generic(self):
        self.add("01-fixture.md", "## Lab\n~~~redis\nJSON.GET tutorial:chapter01:json '$.name'\n~~~\n## Another\n~~~redis\nGET tutorial:chapter01:key\n~~~\n")
        data = inspect(self.root)
        self.assertEqual(data["summary"]["candidates"], 2)
        self.assertEqual(data["review_queue"][0]["category"], "release_sensitive")

    def test_expected_cue_removes_candidate(self):
        self.add("01-fixture.md", "## Lab\n~~~redis\nGET tutorial:chapter01:key\n~~~\nExpected: demo\n")
        self.assertEqual(inspect(self.root)["summary"]["candidates"], 0)

    def test_untyped_command_is_not_top_risk(self):
        self.add("01-fixture.md", "## List\n~~~text\nGET key\n~~~\n## Executable\n~~~redis\nSET tutorial:chapter01:key one\n~~~\n")
        rows = inspect(self.root)["review_queue"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["category"], "write_side_effect")
        self.assertGreater(rows[0]["score"], rows[1]["score"])

    def test_caution_does_not_hide_prohibited_example(self):
        self.add("01-fixture.md", "## Anti-pattern\nDo not run:\n~~~redis\nDEL user:1001\n~~~\n")
        rows = inspect(self.root)["review_queue"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["caution_context"])

if __name__ == "__main__":
    unittest.main()
