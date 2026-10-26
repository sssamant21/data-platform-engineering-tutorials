#!/usr/bin/env python3
"""Bounded secure native performance microbenchmark, never production capacity evidence."""
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import k, CLUSTER, ROOT
from security_acceptance import SecurityLab, immutable_kafka_image
from run_chapter_027 import tls_user
from run_chapter_028 import bootstrap_from_status
from run_chapter_029 import ready_identity, rbac_denials
from performance_acceptance import trial_plan, producer_summary, consumer_summary, aggregate, RECORDS, SIZE

CHECKS=['native_producer_process_completed_acks_all_idempotent','native_consumer_process_completed',
        'native_payload_multiset_and_committed_catchup_exact','full_isr_quorum_polling_and_final_health']
LIMITS=['Single-host kind with shared local-path PVC filesystem is a functional microbenchmark, not representative throughput, saturation, storage IOPS/latency, node placement or production capacity certification.',
    'Three capped offered rates and three repetitions use 1KiB native deterministic payloads. Separate-process warmup is unmeasured; each trial includes client connection startup. No steady-state or sustained disk limit is inferred.',
    'Kafka 4.0 tool per-trial percentiles are retained; no average of p99 values is called a global p99. Payload MiB is distinct from wire bytes, compression or replication traffic.',
    'Actual Admin leader/full-ISR/quorum polling kills the native process tree on unhealthy observations. It is periodic polling, not continuous proof or Prometheus-based SLO alerting. Broker Pod UID/restart drift is checked between trials.',
    'Client cgroup snapshots cover the entire benchmark Pod, including tool startup, health polling and auditing. Broker CPU/network/storage utilization and provider burst metrics are NOT_AVAILABLE without a monitoring stack; absence is not low usage.',
    'No acks weakening, message-size/compression/partition/concurrency sweep, matched plaintext-vs-TLS overhead, noisy-neighbor experiment, production bottleneck conclusion or independent assessor score is claimed. Full performance assessment and enterprise certification remain pending.']


class PerformanceLab(SecurityLab):
    def apply(self,manifest):
        if manifest['kind']=='Job':
            container=manifest['spec']['template']['spec']['containers'][0]
            container['command'][1]='-Xmx128m'
            container['resources']={'requests':{'cpu':'200m','memory':'256Mi'},'limits':{'cpu':'1','memory':'768Mi'}}
        return super().apply(manifest)


def broker_snapshot(pods):
    snapshot={}
    for pod in pods:
        statuses=[c for c in pod['status'].get('containerStatuses',[]) if c['name']=='kafka']
        if len(statuses)!=1 or not statuses[0].get('ready') or pod['metadata'].get('deletionTimestamp'):raise RuntimeError('Benchmark broker is not ready')
        snapshot[pod['metadata']['name']]={'uid':pod['metadata']['uid'],'restarts':statuses[0]['restartCount']}
    if len(snapshot)!=3:raise RuntimeError('Expected exactly three benchmark brokers')
    return snapshot


def filesystem_headroom(text):
    fields=text.splitlines()[-1].split()
    if len(fields)<6:raise RuntimeError('Unrecognized df output')
    available_kib=int(fields[3]);used_percent=int(fields[4].removesuffix('%'))
    if available_kib<256*1024 or used_percent>=90:raise RuntimeError('Insufficient shared filesystem headroom for bounded synthetic benchmark')
    return {'available_KiB':available_kib,'used_percent':used_percent,'scope':'shared local-path host filesystem, not an enforced PVC quota'}


def main():
    lab=PerformanceLab('031',LIMITS);active_trial=None;error,phase=None,'benchmark_capacity_and_persistent_storage_preflight'
    try:
        lab.prepare();cluster=json.loads(k('get','kafka',CLUSTER,'-o','json'));bootstrap=bootstrap_from_status(cluster)
        baseline_pods=json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'];baseline=broker_snapshot(baseline_pods)
        lab.image=immutable_kafka_image(next(c['imageID'] for c in baseline_pods[0]['status']['containerStatuses'] if c['name']=='kafka'));lab.result['client_image']=lab.image
        storage=lab.inventory('benchmark-storage');lab.result['persistent_storage']=storage
        lab.result['filesystem_headroom']={mapping['pod']:filesystem_headroom(lab.read('df-'+mapping['pod'],'exec',mapping['pod'],'-c','kafka','--','df','-Pk',mapping['mount'])) for mapping in storage}
        nodes=json.loads(lab.read('node-capacity','get','nodes','-o','json'))
        for node in nodes['items']:
            conditions={c['type']:c['status'] for c in node['status']['conditions']}
            if any(conditions.get(c)!='False' for c in ('DiskPressure','MemoryPressure','PIDPressure')):raise RuntimeError('Node resource pressure prevents load test')
        lab.read('quota-limits','get','resourcequota,limitrange','-o','wide')
        lab.result['metrics_gaps']={'broker_cpu_network_storage_provider_metrics':'NOT_AVAILABLE_NO_MONITORING_STACK','client_cgroup':'CAPTURED_WHEN_READABLE; per-trial raw snapshots',
            'production_bottleneck_hypothesis':'UNDETERMINED_ON_SHARED_SINGLE_HOST','prometheus_based_abort':'NOT_CLAIMED; actual Kafka Admin polling used'}
        public={'kafka':'4.0.0','strimzi':'0.47.0','security.protocol':'SASL_SSL','sasl.mechanism':'SCRAM-SHA-512','ssl.endpoint.identification.algorithm':'https',
            'acks':'all','enable.idempotence':True,'compression.type':'none','linger.ms':0,'batch.size':16384,'partitions':3,'replicas':3,'min.insync.replicas':2,
            'client_cpu_limit':'1','client_memory_limit':'768Mi','record_size':SIZE,'measured_records':RECORDS}
        lab.result['public_parameters']=public;lab.result['public_configuration_sha256']=hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest()
        lab.result['fixture_sha256']=hashlib.sha256((ROOT/'kafka/qa/runtime/strimzi-three-node-scram-ch028.yaml').read_bytes()).hexdigest()
        lab.result['checks'][phase]='PASS';phase='scoped_benchmark_identity_and_workload_budget'
        plan=trial_plan();all_trials=[{'trial':'warmup','records':120,'record_size':SIZE,'target_records_per_second':200,'repeat':0},*plan]
        username=lab.tag+'-benchmark';lab.client_service_account=lab.tag+'-sa';lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.identity_secret=username;lab.identity_items=['password']
        for trial in all_trials:trial['topic']=lab.topic(trial['trial']);trial['group']=lab.tag+'-'+trial['trial']+'-group'
        identity=tls_user(username,all_trials[0]['topic'],all_trials[0]['group']);identity['spec']['authentication']={'type':'scram-sha-512'}
        cluster_acl=identity['spec']['authorization']['acls'][-1];identity['spec']['authorization']['acls']=[cluster_acl]
        for trial in all_trials:
            identity['spec']['authorization']['acls'] += [
                {'resource':{'type':'topic','name':trial['topic'],'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'},
                {'resource':{'type':'group','name':trial['group'],'patternType':'literal'},'operations':['Read','Describe'],'host':'*'}]
        lab.apply(identity);lab.result['benchmark_identity']=ready_identity(lab,username,'benchmark-secret-metadata')
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        lab.result['client_rbac']=rbac_denials(lab.client_service_account)
        lab.result['workload_budget']={'measured_trials':9,'unmeasured_warmup_records':120,'payload_bytes_including_warmup':sum(t['records']*SIZE for t in all_trials),
            'replicated_payload_bytes':3*sum(t['records']*SIZE for t in all_trials),'maximum_offered_records_per_second':800,'native_process_seconds':{'producer':90,'consumer':60},
            'health_monitor':'actual Kafka Admin full-ISR/leader/quorum poll during native process; kill tree on failure','abort_on_broker_restart_between_trials':True}
        lab.result['checks'][phase]='PASS';results=[]
        for trial in all_trials:trial['status']='NOT_EXECUTED'
        lab.result['trial_attempts']=all_trials
        for trial in all_trials:
            phase=trial['trial']+'_native_benchmark';active_trial=trial;trial_started=time.monotonic()
            trial['started_utc']=datetime.now(timezone.utc).isoformat();trial['status']='RUNNING'
            trial['evidence']=trial['trial']+'/chapter-031-client.log'
            child=PerformanceLab('031',LIMITS);child.tag,child.image,child.out,child.owned=lab.tag+'-'+trial['trial'],lab.image,lab.out/trial['trial'],lab.owned
            child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,username;child.identity_items=['password']
            try:child.run_job('PerfAcceptance',[bootstrap,username,trial['topic'],trial['group'],trial['trial'],str(trial['records']),str(SIZE),str(trial['target_records_per_second'])],[trial['trial']+'_'+check for check in CHECKS])
            finally:lab.result['checks'].update(child.result['checks'])
            text=(child.out/'chapter-031-client.log').read_text(encoding='utf-8');trial['producer']=producer_summary(text,trial['records']);trial['consumer']=consumer_summary(text,trial['records'],SIZE)
            trial['observations']=child.result['client_observations'];trial['evidence']=str((child.out/'chapter-031-client.log').relative_to(lab.out));trial['harness_completion_seconds']=round(time.monotonic()-trial_started,3)
            after=broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])
            if after!=baseline:raise RuntimeError('ABORT: broker UID/readiness/restart count changed during benchmark')
            trial['status']='PASS';active_trial=None;lab.result['checks'][phase]='PASS'
            if trial['trial']=='warmup':lab.result['unmeasured_warmup']=trial
            else:results.append(trial);lab.result['trials']=results
        phase='repeatability_and_statistical_integrity';lab.result['rate_comparison']=aggregate(results);lab.result['broker_baseline_and_final']=baseline
        lab.result['checks'][phase]='PASS';lab.result['performance_assessment']={'status':'NOT_YET_ACCEPTED','score':None,'production_representativeness':'NOT_ESTABLISHED',
            'critical_gaps':['broker CPU/network/disk resource correlation','production-like sustained load and saturation','independent reviewer signoff'],
            'other_sweeps':'NOT_EXECUTED: message size, acks comparison, compression, partitions, concurrency, matched secure-vs-plaintext overhead'}
        lab.result['runtime_scope']='ACTUAL_SECURE_NATIVE_PERF_TOOLS_NINE_CAPPED_REPEATED_MICROBENCHMARKS_EXACT_DATA_AND_POLLING_NOT_PRODUCTION_CAPACITY';lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL'
        if active_trial is not None and active_trial.get('status')=='RUNNING':active_trial['status']='FAIL';active_trial['failure_class']=type(exc).__name__
        print('Chapter 031 '+phase+' failed: '+type(exc).__name__+'; sanitized evidence has details',file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
