import copy
import json
import unittest
from unittest.mock import patch
from runtime_acceptance import job_manifest
from capstone_performance import CapstoneLab, capacity_model, application_observations
from broker_acceptance import BrokerLab
from java_sources import bundle_java_sources
import select_changed_chapters as selector
from pathlib import Path


def lines():
    phases=[]
    for name,count,cap in zip(('warmup','baseline','burst','recovery'),(120,360,360,360),(100,200,400,100)):
        distribution=lambda value:dict(zip(('p50','p95','p99','maximum'),[value]*4))
        phases.append({'phase':name,'records':count,'acknowledged_records':count,'force_sample_count':count,'offered_cap_records_per_second':cap,
            'producer_completion_seconds':count/cap,'achieved_acknowledgements_per_second':cap,'ack_ms':distribution(1),
            'handler_and_force_ms':distribution(1),'created_to_forced_sink_ms':distribution(2)})
    result={'accepted_sequence_ids':list(range(1200)),'forced_sink_sequence_ids':list(range(1200)),'missing_accepted_ids':0,'paused_burst_backlog':360,'recovery_seconds':10,'phases':phases}
    rows=['OBS:APPLICATION_PHASES:'+json.dumps(result),'OBS:APPLICATION_ACK_LEDGER_MS:'+json.dumps([1]*1200),
        'OBS:APPLICATION_EVENT_LEDGER:'+json.dumps([{'sequence':i,'created_ms':1000,'forced_completion_ms':1002,'handler_and_force_ms':1} for i in range(1200)])]
    for phase,elapsed,lag,accepted,processed in [('recovery_start',10,360,840,480),('recovery',11,100,900,800),('final',20,0,1200,1200)]:
        rows.append('OBS:APPLICATION_LAG:'+json.dumps({'phase':phase,'elapsed_seconds':elapsed,'lag':lag,'accepted_count':accepted,'forced_sink_count':processed,
            'captured_ends':{str(i):200 for i in range(6)},'committed_offsets':{str(i):200 for i in range(6)}}))
    for broker in range(3):
        for phase in ('before','application_window','after'):
            rows.append('OBS:BROKER_SAMPLE:'+json.dumps({'broker':broker,'phase':phase,'metrics':['qa_under_replicated_partitions 0','qa_under_min_isr_partitions 0']}))
    return rows


def alter(rows,name,edit):
    prefix='OBS:'+name+':'
    result=[]
    for row in rows:
        if row.startswith(prefix):
            value=json.loads(row[len(prefix):]);edit(value);row=prefix+json.dumps(value)
        result.append(row)
    return result


class CapstoneTests(unittest.TestCase):
    def test_capacity_formula_has_cluster_vs_balanced_average_and_no_sizing_claim(self):
        model=capacity_model(5000,1024,.6,3,24,3)
        self.assertEqual(model['estimated_retained_replicated_payload_bytes'],796262400000)
        self.assertEqual(model['average_estimated_bytes_per_broker_if_balanced'],265420800000)
        self.assertIn('ILLUSTRATIVE',model['scope'])
        for value in (0,-1,float('nan'),2,True):
            with self.assertRaises(RuntimeError):capacity_model(5000,1024,value,3,24,3)

    def test_owned_nonbroker_pvc_guard_does_not_allow_foreign_claim(self):
        lab=CapstoneLab('035',[]);lab.sink_claim='production-data';manifest=job_manifest('owned','image','source','CapstoneAcceptance',[])
        with self.assertRaises(RuntimeError):lab.apply(manifest)
        lab.sink_claim='ch035-0123456789ab-sink';lab.owned=[{'kind':'PersistentVolumeClaim','name':lab.sink_claim}]
        with patch.object(BrokerLab,'apply',side_effect=lambda m:m):result=lab.apply(manifest)
        pod=result['spec']['template']['spec'];self.assertEqual(pod['volumes'][-1]['persistentVolumeClaim']['claimName'],lab.sink_claim)
        self.assertEqual(pod['containers'][0]['volumeMounts'][-1]['mountPath'],'/sink')

    def test_phase_parser_reconciles_ids_raw_quantiles_commits_and_new_ingress_drain(self):
        proof=application_observations(lines());self.assertEqual(proof['first_observed_net_drain_records_per_second'],260)
        self.assertEqual(len(proof['raw_event_timing_ledger']),1200);self.assertEqual(len(proof['application_broker_samples']),3)

    def test_missing_and_duplicate_durable_ids_do_not_pass(self):
        for edit in (lambda value:value['forced_sink_sequence_ids'].pop(),lambda value:value['forced_sink_sequence_ids'].__setitem__(1,0)):
            with self.assertRaises(RuntimeError):application_observations(alter(lines(),'APPLICATION_PHASES',edit))

    def test_fabricated_percentile_and_mismatched_ack_rate_rejected(self):
        for edit in (lambda value:value['phases'][1]['ack_ms'].update({'p99':2,'maximum':2}),lambda value:value['phases'][1].update({'achieved_acknowledgements_per_second':9999})):
            with self.assertRaises(RuntimeError):application_observations(alter(lines(),'APPLICATION_PHASES',edit))
        with self.assertRaises(RuntimeError):application_observations(alter(lines(),'APPLICATION_EVENT_LEDGER',lambda events:events[0].update({'forced_completion_ms':999})))

    def test_no_catchup_claim_without_sampled_drain_under_new_ingress_or_final_commits(self):
        with self.assertRaises(RuntimeError):application_observations(alter(lines(),'APPLICATION_LAG',lambda row:row.update({'accepted_count':840}) if row['phase']=='recovery' else None))
        with self.assertRaises(RuntimeError):application_observations(alter(lines(),'APPLICATION_LAG',lambda row:row['committed_offsets'].update({'0':199}) if row['phase']=='final' else None))
        with self.assertRaises(RuntimeError):application_observations([row for row in lines() if 'application_window' not in row])

    def test_real_application_source_bundle_has_one_main_and_accepted_dependencies(self):
        directory=Path(__file__).parent/'runtime';names=('CapstoneAcceptance','BrokerAcceptance','ConsumerAcceptance','PerfAcceptance')
        source=bundle_java_sources(names[0],{name:(directory/(name+'.java')).read_text(encoding='utf-8-sig') for name in names})
        self.assertEqual(source.count('public class '),1)
        self.assertLess(source.index('public class CapstoneAcceptance'),source.index('class BrokerAcceptance'))
        self.assertIn('class ConsumerAcceptance',source);self.assertIn('class PerfAcceptance',source)

    def test_selector_tracks_reused_components_and_inherited_metrics_fixture(self):
        for path in ('kafka/qa/run_chapter_035.py','kafka/qa/capstone_performance.py','kafka/qa/runtime/CapstoneAcceptance.java'):
            self.assertEqual(selector.select([path]),['035'])
        self.assertEqual(selector.select(['kafka/qa/broker_acceptance.py']),['034','035'])
        self.assertEqual(selector.select(['kafka/qa/runtime/ConsumerAcceptance.java']),['033','035'])
        self.assertEqual(selector.select(['kafka/qa/java_sources.py']),['033','034','035'])
        self.assertEqual(selector.fixture_for('035'),'strimzi-three-node-metrics-ch034.yaml')


if __name__=='__main__':unittest.main()
