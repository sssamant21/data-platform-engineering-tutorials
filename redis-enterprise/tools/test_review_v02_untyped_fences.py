"""Offline regression tests for command-like text/unlabeled fence classifier."""
import tempfile
import unittest
from pathlib import Path
from review_v02_untyped_fences import inspect, bucket

class UntypedFencesTests(unittest.TestCase):
    def test_full_redis_command_is_prioritized(self):
        self.assertEqual(bucket("DEL tutorial:chapter01:hello", "Run this in a lab:")[0],
                         "possible_runnable_command")

    def test_command_under_warning_is_not_promoted_as_safe(self):
        self.assertEqual(bucket("DEL dangerous:key", "Never do this against production")[0],
                         "potential_negative_example")

    def test_symbolic_ttl_is_not_executable(self):
        self.assertEqual(bucket("TTL = 3600", "A hypothetical cache")[0], "formula_or_symbolic_text")

    def test_command_vocabulary_is_not_copyable(self):
        self.assertEqual(bucket("GET\nSET\nHSET\nTTL", "Common commands")[0],
                         "command_vocabulary_list")

    def test_natural_language_set_is_not_runnable(self):
        classification, _ = bucket("set only if the key exists", "XX means:")
        self.assertNotEqual(classification, "possible_runnable_command")

    def test_explanatory_expected_ttl_is_not_runnable(self):
        classification, _ = bucket("TTL remains positive", "Expected:")
        self.assertNotEqual(classification, "possible_runnable_command")

    def test_contextual_diagram_is_not_runnable(self):
        classification, _ = bucket("GET key\nif missing:\n  SET key", "Concept:")
        self.assertEqual(classification, "ambiguous_reference_text")

    def test_ledger_counts_text_and_unlabeled(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"01-fixture.md"
            p.write_text("# Sample\n~~~text\nGET\nSET\n~~~\n\n~~~\nTTL = 3600\n~~~\n",
                         encoding="utf-8")
            r=inspect(Path(d))
            self.assertEqual(r["summary"]["candidates"],2)
            self.assertEqual(r["summary"]["chapters"],1)

if __name__ == "__main__":
    unittest.main()
