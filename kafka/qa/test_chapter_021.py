"""Offline Chapter 021 storage, replica coverage and read-only target guards."""
import copy
import json
import unittest
from decimal import Decimal
import run_chapter_021 as chapter
import select_changed_chapters as selector


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.pool = {'metadata': {'name': 'dual-role'}, 'spec': {'replicas': 3, 'roles': ['controller', 'broker'],
                     'storage': {'type': 'persistent-claim', 'size': '1Gi', 'class': 'standard', 'deleteClaim': False}}}
        self.pods, self.claims, self.volumes = [], {}, {}
        for i in range(3):
            self.pods.append({'metadata': {'name': f'broker-{i}', 'uid': f'pod-{i}', 'labels': {'strimzi.io/pool-name': 'dual-role'}},
                              'status': {'containerStatuses': [{'name': 'kafka', 'ready': True}]},
                              'spec': {'nodeName': 'kind-node', 'volumes': [{'name': 'data', 'persistentVolumeClaim': {'claimName': f'claim-{i}'}}],
                                       'containers': [{'name': 'kafka', 'volumeMounts': [{'name': 'data', 'mountPath': '/var/lib/kafka/data'}]}]}})
            self.claims[f'claim-{i}'] = {'metadata': {'uid': f'claim-uid-{i}'},
                'spec': {'storageClassName': 'standard', 'accessModes': ['ReadWriteOnce'], 'volumeName': f'pv-{i}', 'resources': {'requests': {'storage': '1Gi'}}},
                'status': {'phase': 'Bound', 'capacity': {'storage': '1Gi'}}}
            self.volumes[f'pv-{i}'] = {'metadata': {'name': f'pv-{i}', 'uid': f'pv-uid-{i}'}, 'status': {'phase': 'Bound'},
                'spec': {'storageClassName': 'standard', 'capacity': {'storage': '1Gi'}, 'hostPath': {'path': f'/data/{i}'},
                         'claimRef': {'namespace': chapter.NS, 'name': f'claim-{i}', 'uid': f'claim-uid-{i}'}}}
        self.classes = {'standard': {'metadata': {'name': 'standard'}, 'provisioner': 'rancher.io/local-path', 'volumeBindingMode': 'WaitForFirstConsumer', 'reclaimPolicy': 'Delete'}}
        self.topic = 'ch021-012345abcdef-storage'

    def inventory(self):
        return chapter.storage_inventory(self.pool, self.pods, self.claims, self.volumes, self.classes)

    def test_inventory_uses_actual_pod_volume_and_claim_uid(self):
        actual = self.inventory()
        self.assertEqual(len(actual), 3)
        self.assertEqual(actual[1]['pvc'], 'claim-1')
        self.assertEqual(actual[1]['pv_uid'], 'pv-uid-1')
        self.assertEqual(actual[1]['mount'], '/var/lib/kafka/data')

    def test_ephemeral_or_auto_delete_storage_rejected(self):
        for key, value in [('type', 'ephemeral'), ('deleteClaim', True), ('class', 'unreviewed')]:
            with self.subTest(key=key):
                original = copy.deepcopy(self.pool)
                self.pool['spec']['storage'][key] = value
                with self.assertRaises(RuntimeError):
                    self.inventory()
                self.pool = original

    def test_pending_undersized_or_wrong_bound_claim_is_rejected(self):
        cases = [('pending', lambda: self.claims['claim-0']['status'].update(phase='Pending')),
                 ('undersized', lambda: self.claims['claim-0']['status']['capacity'].update(storage='512Mi')),
                 ('wrong-uid', lambda: self.volumes['pv-0']['spec']['claimRef'].update(uid='another-claim')),
                 ('wrong-class', lambda: self.claims['claim-0']['spec'].update(storageClassName='other'))]
        for label, mutate in cases:
            with self.subTest(case=label):
                claims, volumes = copy.deepcopy(self.claims), copy.deepcopy(self.volumes)
                mutate()
                with self.assertRaises(RuntimeError):
                    self.inventory()
                self.claims, self.volumes = claims, volumes

    def test_mount_must_reference_the_pvc_volume(self):
        self.pods[0]['spec']['containers'][0]['volumeMounts'][0]['name'] = 'empty-dir'
        with self.assertRaisesRegex(RuntimeError, 'mount'):
            self.inventory()

    def test_shared_pvc_between_brokers_rejected(self):
        self.pods[1]['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = 'claim-0'
        with self.assertRaisesRegex(RuntimeError, 'shared'):
            self.inventory()

    def test_paths_cannot_escape_verified_pvc_or_target_unowned_topics(self):
        base = '/var/lib/kafka/data'
        self.assertEqual(chapter.safe_partition_path(base + '/kafka-log0', base, self.topic, 2), base + '/kafka-log0/' + self.topic + '-2')
        for path, topic in [(base + '/../secret', self.topic), (base + '-other/log', self.topic), (base, 'business-topic')]:
            with self.subTest(path=path, topic=topic), self.assertRaises(RuntimeError):
                chapter.safe_partition_path(path, base, topic, 0)

    def test_segment_roll_requires_nonempty_logs_and_index_families(self):
        listing = ''.join(f'{i:020d}.{ext} {size}\n' for i in (0, 15) for ext, size in [('log', 1000), ('index', 10), ('timeindex', 10)])
        self.assertEqual(len(chapter.segment_files(listing)), 6)
        for bad in ['', listing.replace('00000000000000000015.log 1000', '00000000000000000015.log 0'), listing.replace('00000000000000000015.timeindex 10\n', '')]:
            with self.assertRaises(RuntimeError):
                chapter.segment_files(bad)

    def test_log_dirs_requires_nine_unique_healthy_replicas(self):
        data = {'brokers': [{'broker': i, 'logDirs': [{'logDir': '/data/log', 'error': None,
                'partitions': [{'partition': self.topic + '-' + str(p), 'size': 100, 'isFuture': False, 'offsetLag': 0} for p in range(3)]}]} for i in range(3)]}
        self.assertEqual(len(chapter.log_dirs('Informational preamble\n' + json.dumps(data), self.topic)), 9)
        data['brokers'][0]['logDirs'][0]['error'] = 'KAFKA_STORAGE_ERROR'
        with self.assertRaisesRegex(RuntimeError, 'storage error'):
            chapter.log_dirs(json.dumps(data), self.topic)
        data['brokers'].pop(0)
        with self.assertRaisesRegex(RuntimeError, 'three healthy replicas'):
            chapter.log_dirs(json.dumps(data), self.topic)

    def test_quantities_compare_capacity_without_equating_to_free_space(self):
        self.assertEqual(chapter.quantity_bytes('1Gi'), chapter.quantity_bytes('1024Mi'))
        self.assertGreater(chapter.quantity_bytes('1Gi'), chapter.quantity_bytes('1G'))
        self.assertEqual(chapter.quantity_bytes('1.5Gi'), Decimal(1610612736))
        with self.assertRaises(ValueError):
            chapter.quantity_bytes('unbounded')

    def test_selector_keeps_existing_fixtures_and_selects_persistent_021(self):
        self.assertEqual(selector.select(['kafka/qa/run_chapter_021.py']), ['021', '022'])
        self.assertEqual(selector.fixture_for('021'), 'strimzi-three-node-persistent-ch021.yaml')
        self.assertEqual(selector.fixture_for('020'), 'strimzi-three-node-ch004.yaml')
        self.assertEqual(selector.fixture_for('001'), 'strimzi-single-node.yaml')
        self.assertIn('021', selector.select(['kafka/qa/runtime/strimzi-three-node-persistent-ch021.yaml']))


if __name__ == '__main__':
    unittest.main()
