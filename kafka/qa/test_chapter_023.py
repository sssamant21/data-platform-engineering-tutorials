"""Cleaner evidence must distinguish measured progress from an unobserved deadline."""
import unittest
import run_chapter_023 as chapter
import select_changed_chapters as selector


class CompactionTests(unittest.TestCase):
    def test_observed_progress_requires_fewer_physical_records_than_acknowledged(self):
        r = chapter.cleaner_observation(['OBS:CLEANER_PROGRESS:OBSERVED:visible_records=38:acknowledged_records=108'])
        self.assertEqual(r['visible_records'], 38)
        self.assertFalse(r['completion_guarantee'])
        for record in ['OBS:CLEANER_PROGRESS:OBSERVED:visible_records=108:acknowledged_records=108',
                       'OBS:CLEANER_PROGRESS:NOT_OBSERVED_WITHIN_BOUND:visible_records=37:acknowledged_records=108',
                       'OBS:CLEANER_PROGRESS:OBSERVED:visible_records=0:acknowledged_records=108']:
            with self.assertRaises(RuntimeError):
                chapter.cleaner_observation([record])

    def test_absent_progress_is_explicit_and_does_not_claim_completion(self):
        r = chapter.cleaner_observation(['OBS:CLEANER_PROGRESS:NOT_OBSERVED_WITHIN_BOUND:visible_records=108:acknowledged_records=108'])
        self.assertEqual(r['status'], 'NOT_OBSERVED_WITHIN_BOUND')
        self.assertFalse(r['completion_guarantee'])
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            chapter.cleaner_observation([])

    def test_dependency_dispatch_is_bounded_and_preserves_prior_storage_users(self):
        self.assertEqual(selector.select(['kafka/qa/runtime/CompactionAcceptance.java']), ['023'])
        self.assertEqual(selector.fixture_for('023'), 'strimzi-three-node-persistent-ch021.yaml')
        self.assertEqual(selector.select(['kafka/qa/run_chapter_021.py']), ['021', '022', '023'])
        self.assertEqual(selector.select(['kafka/qa/runtime/StorageAcceptance.java']), ['021', '022'])


if __name__ == '__main__':
    unittest.main()
