"""Offline lifecycle, failure propagation and isolation tests for transaction QA."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import runtime_acceptance as harness
import run_chapter_019 as chapter
import select_changed_chapters as selector


class AcceptanceHarnessTests(unittest.TestCase):
    def test_job_has_no_retry_and_bounded_runtime(self):
        manifest = harness.job_manifest('ch019-test', 'image:4.0.0', 'source', 'Main', ['input'])
        self.assertEqual(manifest['spec']['backoffLimit'], 0)
        self.assertEqual(manifest['spec']['activeDeadlineSeconds'], 600)
        pod = manifest['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['restartPolicy'], 'Never')
        self.assertTrue(pod['containers'][0]['volumeMounts'][0]['readOnly'])

    def test_unsafe_context_fails_without_mutating_cluster(self):
        lab = harness.Lab('019', [])
        with patch.object(harness.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'production', '')), patch.object(harness, 'k') as kube:
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                lab.prepare()
        kube.assert_not_called()
        self.assertFalse(lab.safe)

    def test_failed_job_reports_error_without_waiting_for_timeout(self):
        with tempfile.TemporaryDirectory(dir=harness.ROOT) as directory:
            lab = harness.Lab('019', [])
            lab.image, lab.out = 'image:4.0.0', Path(directory)
            with patch.object(lab, 'source', return_value='source'), patch.object(lab, 'apply'), patch.object(
                    harness, 'k', side_effect=[json.dumps({'status': {'conditions': [{'type': 'Failed', 'status': 'True'}]}}), 'JAVA_FAILURE']):
                with self.assertRaisesRegex(RuntimeError, 'JAVA_FAILURE'):
                    lab.run_job('Main', [], ['expected_assertion'])
            self.assertEqual(lab.result['checks'], {'expected_assertion': 'NOT_RUN_OR_FAILED'})
            self.assertIn('JAVA_FAILURE', (lab.out / 'chapter-019-client.log').read_text())

    def test_missing_assertion_cannot_pass_job(self):
        with tempfile.TemporaryDirectory(dir=harness.ROOT) as directory:
            lab = harness.Lab('019', [])
            lab.out, lab.image = Path(directory), 'image:4.0.0'
            with patch.object(lab, 'source', return_value='source'), patch.object(lab, 'apply'), patch.object(
                    harness, 'k', side_effect=[json.dumps({'status': {'conditions': [{'type': 'Complete', 'status': 'True'}]}}), 'no assertions']):
                with self.assertRaisesRegex(RuntimeError, 'Missing client assertion'):
                    lab.run_job('Main', [], ['required'])

    def test_cleanup_failure_fails_result_and_targets_only_owned_resources(self):
        with tempfile.TemporaryDirectory(dir=harness.ROOT) as directory:
            lab = harness.Lab('019', [])
            lab.out, lab.safe, lab.result['status'] = Path(directory), True, 'PASS'
            lab.owned.append({'kind': 'Job', 'name': lab.tag + '-client'})
            def kube(*args, **kwargs):
                if args[0] == 'delete':
                    self.assertEqual(args[1:3], ('Job', lab.tag + '-client'))
                    raise RuntimeError('cleanup failed')
                return ''
            with patch.object(harness, 'k', side_effect=kube):
                self.assertEqual(lab.finish(), 1)
            result = json.loads((lab.out / 'chapter-019-runtime.json').read_text())
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['certification'], 'NOT_CERTIFIED')

    def test_selector_includes_new_runner_and_shared_helper(self):
        self.assertEqual(selector.select(['kafka/qa/run_chapter_019.py']), ['019'])
        self.assertEqual(selector.select(['kafka/qa/runtime_acceptance.py']), list(selector.SUPPORTED))


if __name__ == '__main__':
    unittest.main()
