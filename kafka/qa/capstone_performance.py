"""Chapter035 application-phase and replay support using validated shared components."""
import hashlib
import json
import math
import re
from runtime_acceptance import ROOT
from broker_acceptance import BrokerLab, metrics_map, metric
from java_sources import bundle_java_sources
from consumer_acceptance import json_observation


class CapstoneLab(BrokerLab):
    def source(self,main):
        if main=='BrokerAcceptance':return super().source(main)
        names={'CapstoneAcceptance':('CapstoneAcceptance','BrokerAcceptance','ConsumerAcceptance','PerfAcceptance'),
               'ConsumerAcceptance':('ConsumerAcceptance','PerfAcceptance')}.get(main)
        if names is None:raise RuntimeError('Unapproved capstone main class')
        source=bundle_java_sources(main,{name:(ROOT/'kafka/qa/runtime'/(name+'.java')).read_text(encoding='utf-8-sig') for name in names})
        self.result['java_source_bundle_sha256']=hashlib.sha256(source.encode()).hexdigest()
        return self.apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':self.tag+'-source'},'data':{main+'.java':source}})

    def apply(self,manifest):
        claim=getattr(self,'sink_claim',None)
        if manifest['kind']=='Job' and claim:
            if not re.fullmatch(r'ch035-[a-f0-9]{12}-sink',claim) or {'kind':'PersistentVolumeClaim','name':claim} not in self.owned:raise RuntimeError('Refuse unowned capstone sink PVC')
            pod=manifest['spec']['template']['spec'];pod['volumes'].append({'name':'owned-sink','persistentVolumeClaim':{'claimName':claim}})
            pod['containers'][0]['volumeMounts'].append({'name':'owned-sink','mountPath':'/sink'})
        return super().apply(manifest)


def capacity_model(records_per_second,size_bytes,compression_ratio,replicas,retained_hours,brokers):
    if any(type(value) is not int or value<=0 for value in (records_per_second,size_bytes,replicas,retained_hours,brokers)) or not isinstance(compression_ratio,(int,float)) or isinstance(compression_ratio,bool) or not math.isfinite(compression_ratio) or not 0<compression_ratio<=1:
        raise RuntimeError('Invalid illustrative capacity model input')
    logical=records_per_second*size_bytes;replicated=logical*compression_ratio*replicas
    return {'logical_ingress_bytes_per_second':logical,'estimated_replicated_payload_bytes_per_second':replicated,
        'estimated_retained_replicated_payload_bytes':replicated*retained_hours*3600,
        'average_estimated_bytes_per_broker_if_balanced':replicated*retained_hours*3600/brokers,
        'scope':'ILLUSTRATIVE_ARITHMETIC_NOT_MEASURED_SIZING; excludes indexes/overhead/retries/recovery/retention effects and headroom'}


def application_observations(lines):
    result=json_observation(lines,'APPLICATION_PHASES')
    accepted=result['accepted_sequence_ids'];durable=result['forced_sink_sequence_ids']
    if accepted!=list(range(1200)) or durable!=accepted or result['missing_accepted_ids']!=0 or result['paused_burst_backlog']!=360 or not 0<result['recovery_seconds']<=120:
        raise RuntimeError('Application accepted/durable IDs or recovery budget mismatch')
    events=json_observation(lines,'APPLICATION_EVENT_LEDGER');acks=json_observation(lines,'APPLICATION_ACK_LEDGER_MS')
    if len(events)!=1200 or sorted(row['sequence'] for row in events)!=accepted or len(acks)!=1200:raise RuntimeError('Raw event/ack timing ledger incomplete')
    if any(row['forced_completion_ms']<row['created_ms'] or row['handler_and_force_ms']<0 for row in events):raise RuntimeError('Invalid actual application event times')
    phases=result['phases']
    if [row['phase'] for row in phases]!=['warmup','baseline','burst','recovery']:raise RuntimeError('Application phase sequence mismatch')
    offset=0
    for row,count,cap in zip(phases,(120,360,360,360),(100,200,400,100)):
        if row['records']!=count or row['acknowledged_records']!=count or row['force_sample_count']!=count or row['offered_cap_records_per_second']!=cap:raise RuntimeError('Application phase controlled counts/rates changed')
        phase_events=[event for event in events if offset<=event['sequence']<offset+count]
        raw={'ack_ms':acks[offset:offset+count],'handler_and_force_ms':[event['handler_and_force_ms'] for event in phase_events],
             'created_to_forced_sink_ms':[event['forced_completion_ms']-event['created_ms'] for event in phase_events]}
        offset+=count
        if not math.isfinite(row['producer_completion_seconds']) or row['producer_completion_seconds']<=0 or not math.isclose(row['achieved_acknowledgements_per_second'],count/row['producer_completion_seconds'],rel_tol=1e-9):raise RuntimeError('Actual acknowledgment rate denominator invalid')
        for name in ('ack_ms','handler_and_force_ms','created_to_forced_sink_ms'):
            values=[row[name][key] for key in ('p50','p95','p99','maximum')]
            if any(not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in values) or values!=sorted(values):raise RuntimeError('Application latency evidence missing/invalid')
            samples_sorted=sorted(raw[name])
            if len(samples_sorted)!=count or any(not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in samples_sorted):raise RuntimeError('Raw application timing samples invalid')
            expected=[samples_sorted[math.ceil(count*q)-1] for q in (.5,.95,.99,1)]
            if any(not math.isclose(actual,wanted,abs_tol=1e-9) for actual,wanted in zip(values,expected)):raise RuntimeError('Reported application percentile differs from raw nearest-rank samples')
    prefix='OBS:APPLICATION_LAG:';samples=[json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    start=[row for row in samples if row['phase']=='recovery_start'];end=[row for row in samples if row['phase']=='final']
    if len(start)!=1 or len(end)!=1 or start[0]['lag']!=360 or end[0]['lag']!=0 or end[0]['forced_sink_count']!=1200 or end[0]['accepted_count']!=1200:
        raise RuntimeError('Actual lag checkpoints do not prove recovery')
    if end[0]['captured_ends']!={str(i):200 for i in range(6)} or end[0]['committed_offsets']!=end[0]['captured_ends']:raise RuntimeError('Final per-partition committed ends do not reconcile')
    during=[row for row in samples if row['phase']=='recovery' and row['elapsed_seconds']>start[0]['elapsed_seconds']]
    draining=next((row for row in during if row['lag']<360 and 840<row['accepted_count']<1200),None)
    if draining is None:raise RuntimeError('No sampled positive net drain during new ingress')
    interval=draining['elapsed_seconds']-start[0]['elapsed_seconds'];net_rate=(360-draining['lag'])/interval
    result['first_observed_net_drain_records_per_second']=net_rate
    result['first_interval_estimated_catchup_seconds']=360/net_rate
    result['drain_estimate_scope']='early committed-lag interval under new ingress; batch commits/shared clock sampling, not production sizing'
    prefix='OBS:BROKER_SAMPLE:';metrics=[json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    for broker in range(3):
        rows=[row for row in metrics if row['broker']==broker]
        if len(rows)<3 or rows[0]['phase']!='before' or rows[-1]['phase']!='after' or not any(row['phase']=='application_window' for row in rows):raise RuntimeError('Actual application broker metrics incomplete')
        for row in rows:
            values=metrics_map(row['metrics'])
            if metric(values,'qa_under_replicated_partitions')!=0 or metric(values,'qa_under_min_isr_partitions')!=0:raise RuntimeError('Application broker replication metric unhealthy')
    result['application_broker_samples']=[{'broker':broker,'samples':sum(row['broker']==broker for row in metrics)} for broker in range(3)]
    result['lag_samples']=samples
    result['raw_event_timing_ledger']=events
    result['raw_ack_wait_ms']=acks
    return result
