import copy
import json
import unittest
from unittest.mock import patch
import broker_acceptance as broker
import run_chapter_034 as chapter
import select_changed_chapters as selector


def cluster():
    return {'metadata':{'name':broker.CLUSTER,'uid':'owned','resourceVersion':'17','generation':1,'annotations':{'qa.kafka/chapter':'034'}},
        'spec':{'kafka':{'version':'4.0.0','listeners':[{'tls':True}], 'config':{'num.io.threads':8,'default.replication.factor':3,'min.insync.replicas':2,'offsets.topic.replication.factor':3,'transaction.state.log.replication.factor':3,'transaction.state.log.min.isr':2}}}}


def evidence():
    lines=[]
    for sequence,phase in enumerate(('before','native_window','native_window','after')):
        for identity in range(3):
            metrics=['qa_under_replicated_partitions 0','qa_under_min_isr_partitions 0','qa_handler_idle 0.5','qa_network_idle 0.6',
                'qa_jvm_heap_bytes{measure="max",} 536870912','qa_jvm_heap_bytes{measure="used",} 100000000',
                'jvm_gc_collection_seconds_count{gc="G1 Young Generation",} 2','jvm_gc_collection_seconds_sum{gc="G1 Young Generation",} 0.01']
            for request in ('Produce','FetchConsumer','FetchFollower'):
                for stage in ('TotalTimeMs','RequestQueueTimeMs','LocalTimeMs','RemoteTimeMs','ResponseQueueTimeMs','ResponseSendTimeMs'):
                    metrics.append(f'qa_request_events_total{{stage="{stage}",request="{request}",}} {sequence+1}')
                    for q in ('0.95','0.99'):metrics.append(f'qa_request_ms{{stage="{stage}",request="{request}",quantile="{q}",}} 2')
            lines.append('OBS:BROKER_SAMPLE:'+json.dumps({'broker':identity,'sequence':sequence,'phase':phase,'timestamp_utc':f'2026-10-27T00:00:0{sequence}Z','metrics':metrics}))
    for _ in range(2):lines.append('OBS:EFFECTIVE_IO_CONFIG:'+json.dumps([{'broker':str(i),'io_threads':10} for i in range(3)]))
    cpu={'cpu.stat':'usage_usec 1\nnr_periods 1\nnr_throttled 0\nthrottled_usec 0','memory.current':'1000000','io.stat':''}
    lines.append('OBS:BROKER_CONFIG_TRANSITION:'+json.dumps({'apply':{'to':10},'rollback':{'to':8},'broker_uids_and_restarts_unchanged':True,
        'effective_rollback_evidence':'restore/chapter-034-client.log','broker_cgroup_before':{'pod':cpu},'broker_cgroup_after':{'pod':cpu}}))
    return '\n'.join(lines)


class BrokerTests(unittest.TestCase):
    def test_patch_is_only_io_change_and_tests_full_spec_uid_and_version(self):
        baseline=cluster();saved=copy.deepcopy(baseline);ops=broker.config_patch(baseline,10)
        self.assertEqual(baseline,saved)
        self.assertEqual([op['path'] for op in ops if op['op']=='test'],['/metadata/uid','/metadata/resourceVersion','/spec'])
        self.assertEqual([op for op in ops if op['op']!='test'],[{'op':'replace','path':'/spec/kafka/config/num.io.threads','value':10}])

    def test_tuning_rejects_unowned_weakened_and_arbitrary_configuration(self):
        for mutate in (lambda c:c['metadata']['annotations'].clear(),lambda c:c['spec']['kafka']['config'].update({'min.insync.replicas':1}),lambda c:c['spec']['kafka']['config'].update({'num.io.threads':999})):
            c=cluster();mutate(c)
            with self.assertRaises(RuntimeError):broker.config_patch(c,10)
        with self.assertRaises(RuntimeError):broker.config_patch(cluster(),7)

    def test_stale_resource_version_prevents_mutation_and_surfaces_failure(self):
        node={'metadata':{'labels':{'kubernetes.io/hostname':'kafka-qa-control-plane'}}}
        with patch.object(broker,'k',side_effect=[json.dumps(node),json.dumps(cluster()),RuntimeError('conflict')]) as call:
            with self.assertRaisesRegex(RuntimeError,'conflict'):broker.reconcile(10)
        self.assertIn('--dry-run=server',call.call_args.args)
        self.assertEqual(call.call_count,3)

    def test_waits_for_new_observed_generation_and_rejects_concurrent_spec_change(self):
        node={'metadata':{'labels':{'kubernetes.io/hostname':'kafka-qa-control-plane'}}};after=cluster();after['spec']['kafka']['config']['num.io.threads']=10
        after['spec']['kafka']['listeners'][0]['tls']=False
        with patch.object(broker,'k',side_effect=[json.dumps(node),json.dumps(cluster()),'dryrun','patched',json.dumps(after)]):
            with self.assertRaisesRegex(RuntimeError,'spec drift'):broker.reconcile(10)

    def test_matched_plan_rejects_client_load_and_safety_confounders(self):
        plan=chapter.broker_plan();self.assertEqual(len(plan),6)
        for row in plan:self.assertEqual(len(broker.broker_arguments('bootstrap','user',{**row,'topic':'topic','group':'group'})),15)
        for key,value in (('linger_ms',5),('target_records_per_second',800),('compression','zstd'),('io_threads',100)):
            row={**plan[0],'topic':'topic','group':'group',key:value}
            with self.assertRaises(RuntimeError):broker.broker_arguments('bootstrap','user',row)

    def test_per_broker_actual_metrics_keep_quantiles_and_zero_gc_deltas(self):
        proof=broker.broker_observations(evidence(),{'io_threads':10})
        self.assertEqual(len(proof['brokers']),3)
        self.assertEqual(proof['brokers'][0]['gc_cumulative_deltas'][0]['delta'],0)
        self.assertEqual(proof['brokers'][1]['request_stages']['Produce']['TotalTimeMs']['observed_request_count_delta'],3)

    def test_missing_replication_or_nan_metrics_never_count_as_healthy(self):
        for bad in ('qa_under_replicated_partitions 1','qa_under_replicated_partitions NaN','qa_under_replicated_partitions -1'):
            with self.assertRaises(RuntimeError):broker.broker_observations(evidence().replace('qa_under_replicated_partitions 0',bad),{'io_threads':10})
        with self.assertRaises(RuntimeError):broker.broker_observations(evidence().replace('qa_handler_idle 0.5','unavailable_metric 0.5'),{'io_threads':10})
        with self.assertRaises(RuntimeError):broker.metrics_map(['qa_handler_idle 0.5','qa_handler_idle 0.5'])

    def test_combined_role_handler_meter_is_raw_and_network_fraction_remains_strict(self):
        proof=broker.broker_observations(evidence().replace('qa_handler_idle 0.5','qa_handler_idle 1.97'),{'io_threads':10})
        self.assertEqual(proof['brokers'][0]['combined_role_handler_idle_raw_mean_rates'],[1.97]*4)
        with self.assertRaises(RuntimeError):broker.broker_observations(evidence().replace('qa_network_idle 0.6','qa_network_idle 1.1'),{'io_threads':10})

    def test_missing_effective_rollback_or_config_match_fails(self):
        with self.assertRaises(RuntimeError):broker.broker_observations(evidence().replace('"to": 8','"to": 10'),{'io_threads':10})
        with self.assertRaises(RuntimeError):broker.broker_observations(evidence(),{'io_threads':8})

    def test_scoped_selector_and_dedicated_metrics_fixture(self):
        for path in ('kafka/qa/broker_acceptance.py','kafka/qa/runtime/BrokerAcceptance.java','kafka/qa/runtime/strimzi-three-node-metrics-ch034.yaml'):
            self.assertEqual(selector.select([path]),['034'])
        self.assertEqual(selector.fixture_for('034'),'strimzi-three-node-metrics-ch034.yaml')
        self.assertEqual(selector.select(['kafka/qa/java_sources.py']),['033','034'])
        self.assertEqual(selector.select(['kafka/qa/performance_lab.py']),['031','032','033','034'])


if __name__=='__main__':unittest.main()
