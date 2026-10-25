"""Offline guards and resource contract tests for Chapter 018."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_chapter_018 as chapter
import select_changed_chapters as selector


class Chapter018Tests(unittest.TestCase):
    def test_unsafe_context_writes_failure_without_cluster_mutation(self):
        with tempfile.TemporaryDirectory(dir=chapter.ROOT) as directory:
            output = Path(directory) / 'result.json'
            with patch.object(chapter, 'OUT', output), patch.object(chapter.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], 0, 'production\n', '')) as shell:
                self.assertEqual(chapter.main(), 1)
            self.assertEqual(shell.call_count, 1)
            result = json.loads(output.read_text())
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['certification'], 'NOT_CERTIFIED')
            self.assertIn('Unsafe', result['error'])

    def test_matching_context_without_kind_node_cannot_mutate_resources(self):
        with tempfile.TemporaryDirectory(dir=chapter.ROOT) as directory:
            output = Path(directory) / 'result.json'
            with patch.object(chapter, 'OUT', output), patch.object(chapter.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], 0, chapter.CTX, '')), patch.object(
                    chapter, 'k', return_value=json.dumps({'metadata': {'labels': {}}})) as kube:
                self.assertEqual(chapter.main(), 1)
            self.assertEqual(kube.call_count, 1)
            self.assertEqual(kube.call_args.args[:2], ('get', 'node'))
            self.assertEqual(json.loads(output.read_text())['status'], 'FAIL')

    def test_missing_kubectl_writes_failure_evidence(self):
        with tempfile.TemporaryDirectory(dir=chapter.ROOT) as directory:
            output = Path(directory) / 'result.json'
            with patch.object(chapter, 'OUT', output), patch.object(chapter.subprocess, 'run',
                    side_effect=FileNotFoundError('kubectl unavailable')):
                self.assertEqual(chapter.main(), 1)
            self.assertEqual(json.loads(output.read_text())['checks'], {})

    def test_new_chapter_selection_and_shared_regression(self):
        self.assertEqual(selector.select(['kafka/qa/run_chapter_018.py']), ['018'])
        self.assertEqual(selector.select(['.github/workflows/kafka-chapter-018.yml']), ['018'])
        self.assertEqual(selector.select(['kafka/qa/runtime/Chapter018.java']), list(selector.SUPPORTED))
        self.assertEqual(selector.select(['kafka/qa/evidence/chapter-018-runtime.json']), [])

    def test_deployment_is_bounded_and_isolated(self):
        manifest = chapter.deployment('ch018-test', 'ch018-topic', 'ch018-group', 'image:4.0.0')
        spec = manifest['spec']['template']['spec']
        self.assertFalse(spec['automountServiceAccountToken'])
        self.assertEqual(spec['terminationGracePeriodSeconds'], 60)
        self.assertEqual(manifest['spec']['strategy']['rollingUpdate']['maxUnavailable'], 0)
        container = spec['containers'][0]
        self.assertIn('ch018-group', container['args'])
        self.assertIn('group.protocol=classic', container['args'])
        self.assertIn('limits', container['resources'])


if __name__ == '__main__':
    unittest.main()
