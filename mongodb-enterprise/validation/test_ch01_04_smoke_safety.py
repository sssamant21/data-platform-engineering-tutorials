#!/usr/bin/env python3
"""Offline invariants for the opt-in integration harness; no database required."""
import pathlib
import unittest

import ch01_04_smoke as smoke


class SmokeHarnessSafetyTests(unittest.TestCase):
    def test_four_distinct_owned_databases(self):
        self.assertEqual(list(smoke.NAMES), [1, 2, 3, 4])
        self.assertEqual(len(set(smoke.NAMES.values())), 4)
        self.assertTrue(all(n.startswith("mongodb_enterprise_tutorial_ch") for n in smoke.NAMES.values()))

    def test_no_unconditional_database_drop(self):
        source = pathlib.Path(smoke.__file__).read_text(encoding="utf-8")
        self.assertNotIn(".drop_database(", source)
        self.assertNotIn(".dropDatabase(", source)
        self.assertIn('MONGODB_LAB_MUTATION_APPROVED', source)
        self.assertIn('if name in existing or database.list_collection_names():', source)
        self.assertIn('if marker_count == total == 1', source)

    def test_reject_non_local_target(self):
        from lab_preflight import validate_inputs
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://prod.internal:27017", "prod.internal", 1, "pilot_12345678")


if __name__ == "__main__":
    unittest.main()
