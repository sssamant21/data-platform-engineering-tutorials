#!/usr/bin/env python3
"""Matched secure producer tuning and explicit ordering/metadata-timeout boundaries."""
import json
import math
import re
import statistics
from runtime_acceptance import k, CLUSTER
from performance_acceptance import RECORDS, SIZE, cgroup_observations
from performance_lab import PerformanceLab, create_performance_topic, execute_benchmark

CANDIDATES=[{'candidate':'baseline','linger_ms':0,'batch_size':16384,'compression':'none'},
    {'candidate':'linger5','linger_ms':5,'batch_size':16384,'compression':'none'},
    {'candidate':'batch64','linger_ms':5,'batch_size':65536,'compression':'none'},
    {'candidate':'lz4','linger_ms':5,'batch_size':65536,'compression':'lz4'},
    {'candidate':'zstd','linger_ms':5,'batch_size':65536,'compression':'zstd'}]
LIMITS=['These are short six-partition SASL_SSL microbenchmarks on one kind host with shared local-path PVC storage. No production throughput, saturation, storage IOPS or multi-zone capacity is certified.',
    'Five candidates vary linger, batching and compression through matched comparisons at fixed offered cap, payload entropy, client resources, acks=all, idempotence=true, RF3/minISR2 and security. A faster result is not required and no production configuration is selected.',
    'Controlled compressible payload IDs/padding are synthetic, not representative application JSON/Avro/Protobuf. Native unkeyed distribution is recorded, not claimed uniformly balanced. Separate keyed checks prove only partition-local healthy-session ordering.',
    'The unreachable bootstrap test establishes metadata max.block timeout (failed Future or direct exception) and unchanged target log end. It does not prove queued delivery timeout, ambiguous-ack outcome handling, wire-ack-loss retry deduplication or external business exactly-once effects.',
    'Client cgroup observations include JVM startup, native CLI, monitoring and auditing. Broker CPU/network/IOPS, provider burst credits, production GC/queue telemetry and alert dashboards are NOT_AVAILABLE; absence is not low utilization.',
    'Extra linger/batch values, snappy/gzip, message-size/skew/concurrency and matched plaintext/security-overhead experiments remain NOT_EXECUTED. Independent performance/security review, production rollout selection and the full assessment remain pending.']
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'production_configuration_selection':'NOT_MADE',
    'critical_gaps':['controlled in-flight acknowledgement-loss retry/deduplication','broker CPU/network/storage and production resource correlation','independent assessor signoff'],
    'other_sweeps':'NOT_EXECUTED: linger20/batch128, snappy/gzip, message size/key skew, concurrency, matched plaintext/security overhead',
    'exactly_once_business_effects':'NOT_CLAIMED'}
CORRECTNESS_CHECKS=['unsupported_idempotent_inflight_rejected_before_traffic','unreachable_metadata_max_block_classified_before_append',
    'keyed_ordering_commits_max_inflight_1','keyed_ordering_commits_max_inflight_5','secure_producer_recovery_full_isr_and_quorum']


def producer_plan():
    plan=[]
    for repeat in range(3):
        offset=repeat*2%len(CANDIDATES)
        for candidate in CANDIDATES[offset:]+CANDIDATES[:offset]:
            plan.append({**candidate,'trial':f'r{repeat+1}-'+candidate['candidate'],'repeat':repeat+1,'records':RECORDS,'record_size':SIZE,
                         'target_records_per_second':400,'partitions':6,'payload_mode':'compressible-set'})
    return plan


def compare_candidates(trials):
    if len(trials)!=15:raise RuntimeError('All fifteen tuning trials must be retained')
    comparisons=[]
    for expected in CANDIDATES:
        selected=[trial for trial in trials if trial['candidate']==expected['candidate']]
        if len(selected)!=3 or {trial['repeat'] for trial in selected}!={1,2,3}:raise RuntimeError('Missing/duplicate candidate repetitions')
        for trial in selected:
            if any(trial.get(key)!=value for key,value in expected.items()) or trial.get('partitions')!=6 or trial.get('target_records_per_second')!=400 or trial.get('payload_mode')!='compressible-set' or trial.get('records')!=RECORDS or trial.get('record_size')!=SIZE:
                raise RuntimeError('Candidate trial changed an uncontrolled factor')
            if any(trial['producer_metrics'].get(name) is None or not math.isfinite(trial['producer_metrics'][name]) or trial['producer_metrics'][name]<0 for name in ('batch-size-avg','compression-rate-avg','bufferpool-wait-time-ns-total')):raise RuntimeError('Required native batching/compression/buffer metric missing')
            datasets=[line for line in trial['observations'] if line.startswith('OBS:CONTROLLED_PAYLOAD_DATASET_SHA256:')]
            if len(datasets)!=1 or not re.fullmatch(r'OBS:CONTROLLED_PAYLOAD_DATASET_SHA256:[a-f0-9]{64}:records=1200:bytes_each=1024:compressible_synthetic_not_real_application',datasets[0]):raise RuntimeError('Controlled dataset fingerprint missing/ambiguous/malformed')
        values=[trial['producer']['achieved_records_per_second'] for trial in selected]
        if not all(math.isfinite(value) and value>0 for value in values):raise RuntimeError('Invalid candidate throughput sample')
        comparisons.append({**expected,'trials':3,'median_achieved_records_per_second':statistics.median(values),
            'sample_standard_deviation_records_per_second':statistics.stdev(values),'per_trial_p99_ms':[trial['producer']['latency_ms']['p99'] for trial in selected],
            'batch_size_avg_bytes':[trial['producer_metrics']['batch-size-avg'] for trial in selected],
            'compression_rate_avg':[trial['producer_metrics']['compression-rate-avg'] for trial in selected],
            'bufferpool_wait_time_ns_total':[trial['producer_metrics']['bufferpool-wait-time-ns-total'] for trial in selected],
            'decision':'OBSERVED_ONLY; not a production configuration recommendation'})
    fingerprints={line.split(':',3)[2] for trial in trials for line in trial['observations'] if line.startswith('OBS:CONTROLLED_PAYLOAD_DATASET_SHA256:')}
    if len(fingerprints)!=1:raise RuntimeError('Payload entropy/dataset changed between candidates')
    return comparisons


def extra_setup(lab):
    topics=[create_performance_topic(lab,'ordering-'+str(inflight),6) for inflight in (1,5)]
    group=lab.tag+'-ordering-group'
    service=json.loads(lab.read('metadata-timeout-service','get','service',CLUSTER+'-kafka-bootstrap','-o','json'))
    if any(port['port']==19095 for port in service['spec']['ports']):raise RuntimeError('Client negative port is published; refuse test')
    return {'topics':topics,'groups':[group],'unused_service_port':19095}


def extra_run(lab,context):
    child=PerformanceLab('032',LIMITS);child.tag,child.image,child.out,child.owned=lab.tag+'-correctness',lab.image,lab.out/'correctness',lab.owned
    child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,context['username'];child.identity_items=['password']
    extras=context['extras'];args=['correctness',context['bootstrap'],context['username'],*extras['topics'],extras['groups'][0],str(extras['unused_service_port'])]
    try:child.run_job('PerfAcceptance',args,['producer-correctness_'+name for name in CORRECTNESS_CHECKS])
    finally:lab.result['checks'].update(child.result['checks'])
    observations=child.result['client_observations']
    lab.result['producer_correctness']={'checks':child.result['checks'],'observations':observations,'client_cgroup':cgroup_observations(observations),
        'data_budget':{'keyed_records':60,'maximum_partition_inflight_modes':[1,5],'negative_metadata_target_records_appended':0},
        'ordering_scope':'one explicit partition per healthy session; captured starting/end offsets, exact callback and committed sequence',
        'metadata_timeout_scope':'metadata max.block failure with observed API surface and unchanged target log end, not queued delivery-timeout proof',
        'retry_ack_loss':'NOT_EXECUTED','business_exactly_once':'NOT_CLAIMED'}


def main():
    return execute_benchmark('032',producer_plan(),LIMITS,{'partitions':6,'offered_records_per_second':400,'payload_mode':'compressible-set',
        'experimental_factors':['linger.ms','batch.size','compression.type']},ASSESSMENT,compare_candidates,'candidate_comparison',extra_setup,extra_run,
        runtime_scope='ACTUAL_SECURE_LINGER_BATCH_LZ4_ZSTD_MICROBENCHMARKS_KEYED_ORDERING_AND_METADATA_TIMEOUT_NOT_PRODUCTION_TUNING_CERTIFICATION')


if __name__=='__main__':raise SystemExit(main())
