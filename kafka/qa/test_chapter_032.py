"""Producer study controls, safe profiles, observed metrics and failure classification bounds."""
import copy
import unittest
from unittest.mock import patch
import run_chapter_032 as chapter
from performance_lab import native_arguments
from performance_acceptance import cgroup_observations, native_metric
import select_changed_chapters as selector


def completed_trials():
    return [{**trial,'producer':{'achieved_records_per_second':400.0,'latency_ms':{'p99':10.0}},
        'producer_metrics':{'batch-size-avg':1024.0,'compression-rate-avg':1.0,'bufferpool-wait-time-ns-total':0.0},
        'observations':['OBS:CONTROLLED_PAYLOAD_DATASET_SHA256:'+'a'*64+':records=1200:bytes_each=1024:compressible_synthetic_not_real_application']}
        for trial in chapter.producer_plan()]


class ProducerTuningTests(unittest.TestCase):
    def test_matched_controls_change_one_primary_factor_per_comparison(self):
        candidates=chapter.CANDIDATES
        for left,right in [(0,1),(1,2),(2,3),(2,4)]:
            differences={key for key in ('linger_ms','batch_size','compression') if candidates[left][key]!=candidates[right][key]}
            self.assertEqual(len(differences),1)
        plan=chapter.producer_plan();self.assertEqual(len(plan),15)
        self.assertEqual({t['target_records_per_second'] for t in plan},{400})
        self.assertEqual({t['partitions'] for t in plan},{6});self.assertEqual({t['payload_mode'] for t in plan},{'compressible-set'})
        self.assertEqual(len({t['trial'] for t in plan}),15)

    def test_native_profile_preserves_031_default_and_rejects_unbounded_or_unsupported_inputs(self):
        trial={'trial':'baseline','topic':'owned','group':'owned','records':1200,'record_size':1024,'target_records_per_second':400}
        self.assertEqual(len(native_arguments('bootstrap','user',trial)),8)
        experimental={**trial,'partitions':6,'linger_ms':5,'batch_size':65536,'compression':'lz4','payload_mode':'compressible-set'}
        self.assertEqual(native_arguments('bootstrap','user',experimental)[8:],['6','5','65536','lz4','compressible-set'])
        for key,value in [('target_records_per_second',400.5),('target_records_per_second',-1),('records',100000),('partitions',1),('linger_ms',9999),('batch_size',2097152),('compression','arbitrary'),('payload_mode','/external/file')]:
            invalid={**experimental,key:value}
            with self.assertRaises(RuntimeError):native_arguments('bootstrap','user',invalid)

    def test_comparison_accepts_slow_observations_without_production_selection(self):
        trials=completed_trials();trials[0]['producer']['achieved_records_per_second']=20.0
        result=chapter.compare_candidates(trials)
        self.assertEqual(len(result),5);self.assertEqual(result[0]['per_trial_p99_ms'],[10,10,10])
        self.assertTrue(all('not a production' in r['decision'] for r in result))

    def test_comparison_rejects_confounded_load_missing_metrics_or_changed_dataset(self):
        for field,value in [('records',1000),('record_size',256),('target_records_per_second',800),('partitions',3),('linger_ms',20)]:
            trials=completed_trials();trials[0][field]=value
            with self.assertRaises(RuntimeError):chapter.compare_candidates(trials)
        trials=completed_trials();trials[0]['producer_metrics']['compression-rate-avg']=None
        with self.assertRaises(RuntimeError):chapter.compare_candidates(trials)
        trials=completed_trials();trials[-1]['observations']=[trials[-1]['observations'][0].replace('a'*64,'b'*64)]
        with self.assertRaises(RuntimeError):chapter.compare_candidates(trials)
        with self.assertRaises(RuntimeError):chapter.compare_candidates(completed_trials()[:-1])

    def test_native_optional_metric_is_not_fabricated_as_zero(self):
        self.assertIsNone(native_metric('unavailable','batch-size-avg',required=False))
        self.assertEqual(native_metric('producer-metrics:batch-size-avg:{client-id=test} : 1024.000\n','batch-size-avg'),1024.0)
        with self.assertRaises(RuntimeError):native_metric('producer-metrics:batch-size-avg:{client-id=test} : -1.0\n','batch-size-avg')

    def test_actual_cgroup_deltas_and_missing_measurements_remain_distinct(self):
        observations=['OBS:CLIENT_CGROUP:before:cpu.stat:usage_usec 1000000;nr_periods 10;nr_throttled 2;throttled_usec 200',
            'OBS:CLIENT_CGROUP:after:cpu.stat:usage_usec 5000000;nr_periods 50;nr_throttled 12;throttled_usec 800',
            'OBS:CLIENT_CGROUP:after:memory.current:123456']
        result=cgroup_observations(observations)
        self.assertEqual(result['cpu_core_seconds'],4.0);self.assertEqual(result['cpu_delta']['nr_throttled'],10)
        self.assertEqual(result['snapshots']['after']['memory.current'],123456)
        self.assertEqual(cgroup_observations(['OBS:CLIENT_CGROUP:before:cpu.stat:NOT_AVAILABLE'])['cpu_delta_status'],'NOT_AVAILABLE')
        with self.assertRaises(RuntimeError):cgroup_observations(observations+[observations[0]])
        with self.assertRaises(RuntimeError):cgroup_observations([observations[0],observations[1].replace('5000000','500')])

    def test_unused_service_port_guard_refuses_real_published_port(self):
        class Lab:
            tag='owned'
            def read(self,*args):return '{"spec":{"ports":[{"port":19095}]}}'
        with patch.object(chapter,'create_performance_topic',side_effect=['owned-1','owned-5']):
            with self.assertRaises(RuntimeError):chapter.extra_setup(Lab())

    def test_shared_performance_changes_regress_031_and_032(self):
        for path in ('kafka/qa/runtime/PerfAcceptance.java','kafka/qa/performance_lab.py','kafka/qa/performance_acceptance.py'):
            self.assertTrue({'031','032'}.issubset(selector.select([path])))
        self.assertEqual(selector.fixture_for('032'),'strimzi-three-node-scram-ch028.yaml')
        self.assertEqual(selector.select(['kafka/qa/run_chapter_032.py']),['032'])


if __name__=='__main__':unittest.main()
