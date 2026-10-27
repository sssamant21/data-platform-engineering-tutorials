"""Conservative native output parsing, repeatability and safe load admission."""
import copy
import unittest
from performance_acceptance import producer_summary, consumer_summary, trial_plan, aggregate
import run_chapter_031 as chapter
import select_changed_chapters as selector

PRODUCER='1200 records sent, 200.0 records/sec (0.20 MB/sec), 2.00 ms avg latency, 20.00 ms max latency, 1 ms 50th, 4 ms 95th, 8 ms 99th, 15 ms 99.9th.\nproducer-metrics:record-error-total:{client-id=perf-producer-client} : 0.000\nproducer-metrics:record-retry-total:{client-id=perf-producer-client} : 1.000\n'
HEADER='start.time, end.time, data.consumed.in.MB, MB.sec, data.consumed.in.nMsg, nMsg.sec, rebalance.time.ms, fetch.time.ms, fetch.MB.sec, fetch.nMsg.sec\n'
CONSUMER=HEADER+'2026-10-26 01:00:00:000, 2026-10-26 01:00:04:000, 1.1719, 0.2930, 1200, 300.0, 3000, 1000, 1.1719, 1200.0\n'


class PerformanceTests(unittest.TestCase):
    def test_native_acknowledged_count_errors_and_percentiles_are_independent_gates(self):
        result=producer_summary(PRODUCER,1200)
        self.assertEqual(result['latency_ms']['p99'],8);self.assertEqual(result['record_retries'],1)
        for bad in [PRODUCER.replace('1200 records','1199 records'),PRODUCER+PRODUCER,
                    PRODUCER.replace('8 ms 99th','21 ms 99th'),PRODUCER.replace('0.000','2.000'),
                    PRODUCER.replace('producer-metrics:record-error-total','other-metrics:record-error-total'),PRODUCER.replace('200.0 records/sec','0.0 records/sec')]:
            with self.assertRaises(RuntimeError):producer_summary(bad,1200)

    def test_consumer_count_bytes_and_elapsed_units_are_checked(self):
        result=consumer_summary(CONSUMER,1200,1024);self.assertEqual(result['consumed_records'],1200)
        self.assertEqual(result['records_per_second_including_group_join'],300.0)
        for bad in [CONSUMER.replace(', 1200,',', 1199,'),CONSUMER.replace('1.1719, 0.2930','2.0000, 0.2930'),CONSUMER+CONSUMER,
                    CONSUMER.replace('1200.0\n','Infinity\n'),CONSUMER.replace('1200, 300.0','1200.5, 300.0')]:
            with self.assertRaises(RuntimeError):consumer_summary(bad,1200,1024)

    def test_zero_millisecond_fetch_rate_is_unmeasurable_not_invented(self):
        result=consumer_summary(CONSUMER.replace('1000, 1.1719, 1200.0','0, Infinity, Infinity'),1200,1024)
        self.assertIsNone(result['fetch_records_per_second']);self.assertEqual(result['fetch_rate_resolution'],'NOT_MEASURABLE_ZERO_MILLISECOND_INTERVAL')

    def test_balanced_trials_and_no_averaged_global_percentile(self):
        plan=trial_plan();self.assertEqual(len(plan),9)
        for index in range(3):self.assertEqual({t['target_records_per_second'] for t in plan[index::3]},{200,400,800})
        trials=[{**t,'producer':{'achieved_records_per_second':float(t['target_records_per_second']),'latency_ms':{'p99':t['repeat']}}} for t in plan]
        result=aggregate(trials);self.assertEqual(result[0]['median_achieved_records_per_second'],200)
        self.assertEqual(result[0]['per_trial_p99_ms'],[1,2,3]);self.assertNotIn('global_p99',result[0])
        with self.assertRaises(RuntimeError):aggregate(trials[:-1])
        trials[-1]['repeat']=1
        with self.assertRaises(RuntimeError):aggregate(trials)

    def test_filesystem_headroom_is_required_and_shared_quota_is_not_claimed(self):
        safe='Filesystem 1024-blocks Used Available Capacity Mounted\n/dev/shared 1000000 200000 800000 20% /data\n'
        self.assertEqual(chapter.filesystem_headroom(safe)['available_KiB'],800000)
        with self.assertRaises(RuntimeError):chapter.filesystem_headroom(safe.replace('800000','100000'))
        with self.assertRaises(RuntimeError):chapter.filesystem_headroom(safe.replace('20%','95%'))

    def test_broker_uid_restart_and_ready_changes_are_observable(self):
        pods=[{'metadata':{'name':str(i),'uid':'uid-'+str(i)},'status':{'containerStatuses':[{'name':'kafka','ready':True,'restartCount':0}]}} for i in range(3)]
        baseline=chapter.broker_snapshot(pods);changed=copy.deepcopy(pods);changed[0]['status']['containerStatuses'][0]['restartCount']=1
        self.assertNotEqual(chapter.broker_snapshot(changed),baseline)
        changed[0]['status']['containerStatuses'][0]['ready']=False
        with self.assertRaises(RuntimeError):chapter.broker_snapshot(changed)

    def test_performance_dependencies_are_scoped_to_new_client(self):
        self.assertIn('031',selector.select(['kafka/qa/performance_acceptance.py']))
        self.assertIn('031',selector.select(['kafka/qa/runtime/PerfAcceptance.java']))
        self.assertEqual(selector.fixture_for('031'),'strimzi-three-node-scram-ch028.yaml')
        for path in ['kafka/qa/run_chapter_027.py','kafka/qa/run_chapter_028.py','kafka/qa/run_chapter_029.py','kafka/qa/security_acceptance.py']:
            self.assertIn('031',selector.select([path]))


if __name__=='__main__':unittest.main()
