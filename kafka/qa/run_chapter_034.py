#!/usr/bin/env python3
"""Per-broker request/JVM metrics and supported one-factor Strimzi tuning/rollback."""
import statistics
from broker_acceptance import BrokerLab, broker_arguments, broker_observations
from performance_lab import TrialDriver, execute_benchmark

LIMITS=[
    'Single-node kind with shared local-path PVCs and dual-role brokers is not production broker capacity, independent failure domains, cloud/CSI latency or storage certification.',
    'Six matched short trials use fixed offered cap400 records/s and1200x1KiB synthetic records. IO thread8 versus10 is an observation, not a required improvement or production tuning recommendation.',
    'Per-broker JMX request histogram percentiles are actual reservoir snapshots containing background traffic. They are never summed/averaged across brokers or treated as interval-only application p99.',
    'JVM heap and cumulative GC count/time are measured. Allocation profiling, pause distributions and attributed node page cache remain NOT_EXECUTED; heap headroom budget is not measured free memory.',
    'Provider IOPS/latency, burst credits, sustained warm-cache sensitivity, tenant quota fairness, TLS/plaintext overhead comparisons, JVM/resource rolling experiments and independent review remain NOT_EXECUTED/PENDING.',
    'The operator-managed IO thread change and rollback use only the disposable chapter fixture. No broker PVC/segment mutation, direct Pod edits or durability/security reductions are performed. Full assessment NOT_YET_ACCEPTED and enterprise NOT_CERTIFIED.'
]
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'production_configuration_selection':'NOT_MADE',
    'critical_gaps':['provider storage latency/IOPS and page-cache attribution','allocation and GC pause profiling','independent assessor/security signoff'],
    'unexecuted_experiments':['JVM/resource rolling reconciliation','network thread sweep','quota fairness','sustained production representative load','matched plaintext overhead']}


def broker_plan():
    return [{'trial':f'r{repeat+1}-'+('baseline' if value==8 else 'io10'),'candidate':'baseline' if value==8 else 'io10',
        'repeat':repeat+1,'io_threads':value,'records':1200,'record_size':1024,'target_records_per_second':400,
        'partitions':6,'linger_ms':0,'batch_size':16384,'compression':'none','payload_mode':'native-random'}
        for repeat in range(3) for value in ((8,10) if repeat%2==0 else (10,8))]


def compare_brokers(trials):
    if len(trials)!=6:raise RuntimeError('All six matched broker trials required')
    result=[]
    for value in (8,10):
        selected=[t for t in trials if t['io_threads']==value]
        if len(selected)!=3 or {t['repeat'] for t in selected}!={1,2,3}:raise RuntimeError('Missing/duplicate broker candidate repetition')
        for row in selected:
            expected={'candidate':'baseline' if value==8 else 'io10','records':1200,'record_size':1024,'target_records_per_second':400,'partitions':6,'linger_ms':0,'batch_size':16384,'compression':'none','payload_mode':'native-random'}
            if any(row.get(k)!=v for k,v in expected.items()) or len(row['study_observations']['brokers'])!=3:raise RuntimeError('Uncontrolled broker comparison or missing per-broker telemetry')
        rates=[row['producer']['achieved_records_per_second'] for row in selected]
        result.append({'io_threads':value,'trials':3,'median_achieved_producer_records_per_second':statistics.median(rates),
            'sample_standard_deviation':statistics.stdev(rates),'client_producer_p99_ms':[row['producer']['latency_ms']['p99'] for row in selected],
            'per_broker_observations':[row['study_observations'] for row in selected],
            'decision':'OBSERVED_ONLY; no production recommendation or faster-candidate requirement'})
    return result


def main():
    driver=TrialDriver(lab_class=BrokerLab,main='BrokerAcceptance',arguments=broker_arguments,analyze=broker_observations,profile_fields=(('io_threads','num.io.threads'),))
    return execute_benchmark('034',broker_plan(),LIMITS,{'partitions':6,'broker_metrics':'JMX exporter; actual per-broker samples'},ASSESSMENT,compare_brokers,
        'broker_tuning_comparison',runtime_scope='ACTUAL_PER_BROKER_JMX_MATCHED_SECURE_LOAD_AND_STRIMZI_IO_THREAD_CHANGE_EFFECTIVE_ROLLBACK_NOT_PRODUCTION_CAPACITY',driver=driver)


if __name__=='__main__':raise SystemExit(main())
