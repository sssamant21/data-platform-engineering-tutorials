"""Chapter 022 governance rejection and dispatch cost-control regression tests."""
import copy
import unittest
import run_chapter_022 as chapter
import select_changed_chapters as selector


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.before = {'metadata': {'name': 'ch022-012345abcdef-storage',
                       'annotations': copy.deepcopy(chapter.ANNOTATIONS), 'labels': {'strimzi.io/cluster': chapter.CLUSTER}},
                       'spec': {'partitions': 3, 'replicas': 3, 'config': copy.deepcopy(chapter.BASE_CONFIG)}}
        self.after = copy.deepcopy(self.before)
        self.after['spec']['config']['retention.ms'] = 7200000

    def test_only_reviewed_synthetic_lifecycle_is_allowed(self):
        chapter.validate_policy_change(self.before, self.after, synthetic_lab_authorized=True, record_age_seconds=100)
        chapter.validate_policy_change(self.after, self.before, synthetic_lab_authorized=True, record_age_seconds=200)
        for authorized, age in [(False, 100), (True, 3600), (True, -1)]:
            with self.assertRaisesRegex(RuntimeError, 'authorized'):
                chapter.validate_policy_change(self.before, self.after, synthetic_lab_authorized=authorized, record_age_seconds=age)

    def test_governance_and_durability_changes_are_rejected(self):
        for field, value in [('replicas', 1), ('partitions', 4)]:
            altered = copy.deepcopy(self.after);altered['spec'][field] = value
            with self.assertRaises(RuntimeError):
                chapter.validate_policy_change(self.before, altered, synthetic_lab_authorized=True, record_age_seconds=100)
        altered = copy.deepcopy(self.after);altered['spec']['config']['min.insync.replicas'] = 1
        with self.assertRaises(RuntimeError):
            chapter.validate_policy_change(self.before, altered, synthetic_lab_authorized=True, record_age_seconds=100)
        altered = copy.deepcopy(self.after);altered['metadata']['annotations'].pop('sre.example.com/owner')
        with self.assertRaises(RuntimeError):
            chapter.validate_policy_change(self.before, altered, synthetic_lab_authorized=True, record_age_seconds=100)

    def test_production_topic_cannot_use_lab_approval(self):
        self.before['metadata']['name'] = 'production-orders'
        self.after['metadata']['name'] = 'production-orders'
        with self.assertRaisesRegex(RuntimeError, 'Unowned'):
            chapter.validate_policy_change(self.before, self.after, synthetic_lab_authorized=True, record_age_seconds=100)

    def test_capacity_scenario_detects_size_truncating_time_requirement(self):
        forecast = chapter.capacity_forecast(20*1024**2, 48*3600, 12, 3, 50*1024**3)
        self.assertFalse(forecast['size_budget_satisfies_time_window'])
        self.assertEqual(forecast['logical_bytes'], 3623878656000)
        self.assertEqual(forecast['nominal_size_limited_replay_seconds'], 30720)
        with self.assertRaises(ValueError):
            chapter.capacity_forecast(1, 1, 0, 3, 1)

    def test_scoped_shared_storage_dependencies_and_registration(self):
        self.assertEqual(selector.fixture_for('022'), 'strimzi-three-node-persistent-ch021.yaml')
        self.assertIn('022', selector.select(['kafka/qa/select_changed_chapters.py', 'kafka/qa/run_chapter_022.py']))
        self.assertTrue({'021', '022'}.issubset(selector.select(['kafka/qa/runtime/StorageAcceptance.java'])))
        self.assertEqual(selector.select(['kafka/qa/select_changed_chapters.py']), list(selector.SUPPORTED))
        self.assertEqual(selector.select(['kafka/qa/runtime_acceptance.py']), list(selector.SUPPORTED))


if __name__ == '__main__':
    unittest.main()
