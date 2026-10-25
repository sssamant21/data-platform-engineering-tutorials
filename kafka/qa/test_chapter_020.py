"""Fault-ownership and process contracts for the disposable capstone."""
import copy
import unittest
import run_chapter_020 as chapter
import select_changed_chapters as selector


class CapstoneTests(unittest.TestCase):
    def setUp(self):
        self.pod = {'metadata': {'uid': 'pod-uid', 'ownerReferences': [{'kind': 'ReplicaSet', 'uid': 'rs-uid', 'controller': True}]}}
        self.rs = {'metadata': {'uid': 'rs-uid', 'ownerReferences': [{'kind': 'Deployment', 'uid': 'deployment-uid', 'controller': True}]}}
        self.deployment = {'metadata': {'uid': 'deployment-uid'}}

    def test_exact_controller_ownership_chain_required(self):
        self.assertTrue(chapter.verify_pod_owner(self.pod, self.rs, self.deployment))
        unrelated = copy.deepcopy(self.rs)
        unrelated['metadata']['ownerReferences'][0]['uid'] = 'other-deployment'
        self.assertFalse(chapter.verify_pod_owner(self.pod, unrelated, self.deployment))
        unrelated = copy.deepcopy(self.pod)
        unrelated['metadata']['ownerReferences'][0]['uid'] = 'broker-controller'
        self.assertFalse(chapter.verify_pod_owner(unrelated, self.rs, self.deployment))

    def test_terminating_or_non_controller_pod_cannot_be_fault_target(self):
        self.pod['metadata']['deletionTimestamp'] = 'now'
        self.assertFalse(chapter.verify_pod_owner(self.pod, self.rs, self.deployment))
        del self.pod['metadata']['deletionTimestamp']
        self.pod['metadata']['ownerReferences'][0]['controller'] = False
        self.assertFalse(chapter.verify_pod_owner(self.pod, self.rs, self.deployment))

    def test_entrypoint_is_real_worker_with_readiness_and_bounded_shutdown(self):
        deployment = chapter.worker_manifest('app', 'strimzi:4.0.0', 'source', ['in', 'out', 'group', 'tag'])
        pod = deployment['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['terminationGracePeriodSeconds'], 60)
        container = pod['containers'][0]
        self.assertEqual(container['command'][-1], 'worker')
        self.assertIn('/qa/TransactionAcceptance.java', container['command'])
        self.assertEqual(container['readinessProbe']['exec']['command'], ['test', '-f', '/tmp/qa-ready'])
        self.assertEqual(deployment['spec']['strategy']['rollingUpdate']['maxUnavailable'], 0)

    def test_chapter_020_selection_is_independent(self):
        self.assertEqual(selector.select(['kafka/qa/run_chapter_020.py']), ['020'])
        self.assertEqual(selector.select(['.github/workflows/kafka-chapter-020.yml']), ['020'])
        self.assertEqual(len(selector.SUPPORTED), 20)


if __name__ == '__main__':
    unittest.main()
