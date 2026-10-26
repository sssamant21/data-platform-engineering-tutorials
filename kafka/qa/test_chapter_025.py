"""Capstone headroom, checksum, ownership dependency and safe policy contracts."""
import copy
import unittest
import run_chapter_025 as chapter
import run_chapter_022 as retention
import select_changed_chapters as selector


class StorageCapstoneTests(unittest.TestCase):
    def test_filesystem_headroom_comes_from_df_not_pvc_request(self):
        self.assertEqual(chapter.available_bytes('Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/local 1000 200 800 20% /data\n'), 819200)
        with self.assertRaises(RuntimeError):
            chapter.available_bytes('PVC requested 1Gi')

    def test_checksum_must_be_present_and_consistent(self):
        value='a'*64
        self.assertEqual(chapter.state_checksum('OBS:STATE_CHECKSUM:'+value+'\nOBS:STATE_CHECKSUM:'+value+'\n'),value)
        for text in ['', 'OBS:STATE_CHECKSUM:'+value+'\nOBS:STATE_CHECKSUM:'+'b'*64+'\n']:
            with self.assertRaises(RuntimeError):
                chapter.state_checksum(text)

    def test_real_consumer_readiness_and_shutdown_are_bounded(self):
        manifest=chapter.consumer_manifest('test','strimzi:4.0.0','source',['topic','tag'])
        pod=manifest['spec']['template']['spec'];container=pod['containers'][0]
        self.assertEqual(container['command'][-1],'serve')
        self.assertIn('/qa/CompactionAcceptance.java',container['command'])
        self.assertEqual(container['readinessProbe']['exec']['command'],['test','-f','/tmp/compaction-ready'])
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['terminationGracePeriodSeconds'],30)
        self.assertEqual(manifest['spec']['strategy']['rollingUpdate']['maxUnavailable'],0)

    def test_capstone_retention_guard_still_rejects_production_or_unreviewed_change(self):
        before={'metadata':{'name':'ch025-012345abcdef-storage','labels':{'strimzi.io/cluster':chapter.CLUSTER},'annotations':copy.deepcopy(chapter.ANNOTATIONS)},
                'spec':{'partitions':3,'replicas':3,'config':copy.deepcopy(chapter.BASE_CONFIG)}}
        after=copy.deepcopy(before);after['spec']['config']['retention.ms']=7200000
        retention.validate_policy_change(before,after,synthetic_lab_authorized=True,record_age_seconds=50,chapter='025',annotations=chapter.ANNOTATIONS)
        with self.assertRaises(RuntimeError):
            retention.validate_policy_change(before,after,synthetic_lab_authorized=True,record_age_seconds=50,chapter='021',annotations=chapter.ANNOTATIONS)

    def test_stage_resource_names_are_dns_safe(self):
        self.assertEqual(chapter.stage_resource_suffix('retention_baseline'),'retention-baseline')
        self.assertEqual(chapter.stage_resource_suffix('state-seed'),'state-seed')
        for value in ['UPPER', 'bad stage', '-invalid', 'x'*31]:
            with self.assertRaises(ValueError):
                chapter.stage_resource_suffix(value)

    def test_shared_client_and_guard_dependencies_include_capstone(self):
        self.assertIn('025',selector.select(['kafka/qa/runtime/CompactionAcceptance.java']))
        self.assertIn('025',selector.select(['kafka/qa/runtime/StorageAcceptance.java']))
        self.assertEqual(selector.select(['kafka/qa/run_chapter_020.py']),['020','025'])
        self.assertEqual(selector.fixture_for('025'),'strimzi-three-node-persistent-ch021.yaml')


if __name__=='__main__':unittest.main()
