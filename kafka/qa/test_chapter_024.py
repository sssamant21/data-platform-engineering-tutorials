"""Conditional remote integration must fail closed without reviewed prerequisites."""
import unittest
import run_chapter_024 as chapter
import select_changed_chapters as selector


class TieredPreflightTests(unittest.TestCase):
    def test_missing_review_never_implies_integration_readiness(self):
        gate = chapter.integration_gate({})
        self.assertFalse(gate['ready_for_conditional_integration'])
        self.assertEqual(set(gate['missing_prerequisites']), set(chapter.REQUIRED_REVIEW))
        self.assertIn('NOT_EXECUTED', gate['status'])

    def test_complete_review_inputs_are_still_not_runtime_proof(self):
        review = {name: True for name in chapter.REQUIRED_REVIEW}
        review['reviewed_plugin_artifact_digest'] = 'sha256:' + 'a'*64
        gate = chapter.integration_gate(review)
        self.assertTrue(gate['ready_for_conditional_integration'])
        self.assertIn('NOT_RUNTIME_PROOF', gate['status'])
        review['reviewed_plugin_artifact_digest'] = 'latest'
        self.assertFalse(chapter.integration_gate(review)['ready_for_conditional_integration'])

    def test_capacity_example_is_not_a_provider_bill(self):
        estimate = chapter.capacity_example()
        self.assertEqual(estimate['daily_logical_bytes'], 724775731200)
        self.assertEqual(estimate['retained_logical_bytes_before_overhead'], 21743271936000)
        self.assertIn('NOT_MEASURED_OR_PRICED', estimate['classification'])
        with self.assertRaises(ValueError):
            chapter.capacity_example(rate=0)

    def test_dispatch_only_selects_tiered_client_and_preserves_shared_importers(self):
        self.assertEqual(selector.select(['kafka/qa/runtime/TieredPreflight.java']), ['024'])
        self.assertEqual(selector.fixture_for('024'), 'strimzi-three-node-persistent-ch021.yaml')
        self.assertTrue({'021','022','023','024'}.issubset(selector.select(['kafka/qa/run_chapter_021.py'])))
        self.assertEqual(selector.select(['kafka/qa/select_changed_chapters.py','kafka/qa/run_chapter_024.py']), ['024'])


if __name__ == '__main__':
    unittest.main()
