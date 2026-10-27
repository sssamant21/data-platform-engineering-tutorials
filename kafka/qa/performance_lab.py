#!/usr/bin/env python3
"""Reusable isolated native performance execution and evidence lifecycle."""
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import k, CLUSTER, ROOT
from security_acceptance import SecurityLab, immutable_kafka_image
from run_chapter_027 import tls_user
from run_chapter_028 import bootstrap_from_status
from run_chapter_029 import ready_identity, rbac_denials
from performance_acceptance import producer_summary, consumer_summary, RECORDS, SIZE, native_metric, cgroup_observations

CHECKS=['native_producer_process_completed_acks_all_idempotent','native_consumer_process_completed',
        'native_payload_multiset_and_committed_catchup_exact','full_isr_quorum_polling_and_final_health']
PROFILE_KEYS=('partitions','linger_ms','batch_size','compression','payload_mode')


def create_performance_topic(lab,suffix,partitions):
    if partitions==3:return lab.topic(suffix)
    if partitions!=6:raise RuntimeError('Unapproved benchmark partition count')
    name=lab.tag+'-'+suffix
    lab.apply({'apiVersion':'kafka.strimzi.io/v1beta2','kind':'KafkaTopic','metadata':{'name':name,'labels':{'strimzi.io/cluster':CLUSTER}},
        'spec':{'partitions':6,'replicas':3,'config':{'min.insync.replicas':2,'cleanup.policy':'delete','retention.ms':3600000}}})
    k('wait',f'kafkatopic/{name}','--for=condition=Ready','--timeout=240s',timeout=260)
    return name


def native_arguments(bootstrap,username,trial):
    if any(type(trial[key]) is not int for key in ('records','record_size','target_records_per_second')) or trial['records'] not in (120,1200) or trial['record_size']!=1024 or not 0<trial['target_records_per_second']<=800:raise RuntimeError('Unapproved benchmark payload/rate')
    args=[bootstrap,username,trial['topic'],trial['group'],trial['trial'],str(trial['records']),str(trial['record_size']),str(trial['target_records_per_second'])]
    if any(key in trial for key in PROFILE_KEYS):
        profile={**dict(zip(PROFILE_KEYS,(3,0,16384,'none','native-random'))),**{key:trial[key] for key in PROFILE_KEYS if key in trial}}
        if any(type(profile[key]) is not int for key in ('partitions','linger_ms','batch_size')) or profile['partitions'] not in (3,6) or profile['linger_ms'] not in (0,5,20) or profile['batch_size'] not in (16384,65536,131072) or profile['compression'] not in ('none','lz4','zstd','snappy','gzip') or profile['payload_mode'] not in ('native-random','compressible-set'):
            raise RuntimeError('Unapproved native producer profile')
        args.extend(str(profile[key]) for key in PROFILE_KEYS)
    return args


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


def execute_benchmark(chapter, plan, limitations, public_overrides, assessment, aggregation, comparison_key="rate_comparison", extra_setup=None, extra_run=None, runtime_scope="ACTUAL_SECURE_NATIVE_PERF_TOOLS_NINE_CAPPED_REPEATED_MICROBENCHMARKS_EXACT_DATA_AND_POLLING_NOT_PRODUCTION_CAPACITY"):
    lab=PerformanceLab(chapter,limitations);active_trial=None;error,phase=None,'benchmark_capacity_and_persistent_storage_preflight'
    try:
        if not 1<=len(plan)<=15 or len({t['trial'] for t in plan})!=len(plan):raise RuntimeError('Unapproved/missing/duplicate benchmark plan')
        for item in plan:
            if item['records']!=RECORDS or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,23}',item['trial']):raise RuntimeError('Unsafe benchmark trial identifier')
            native_arguments('qa-bootstrap:9095','synthetic',{**item,'topic':'synthetic','group':'synthetic'})
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
            'max.in.flight.requests.per.connection':5,'delivery.timeout.ms':30000,'request.timeout.ms':8000,'max.block.ms':15000,'client_cpu_limit':'1','client_memory_limit':'768Mi','record_size':SIZE,'measured_records':RECORDS}
        public.update(public_overrides)
        invariants={'acks':'all','enable.idempotence':True,'replicas':3,'min.insync.replicas':2,'security.protocol':'SASL_SSL','ssl.endpoint.identification.algorithm':'https','max.in.flight.requests.per.connection':5,'delivery.timeout.ms':30000,'request.timeout.ms':8000,'max.block.ms':15000}
        if any(public.get(key)!=value for key,value in invariants.items()):raise RuntimeError('Public benchmark parameters attempted to weaken reliability/security invariants')
        lab.result['public_parameters']=public;lab.result['public_configuration_sha256']=hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest()
        lab.result['fixture_sha256']=hashlib.sha256((ROOT/'kafka/qa/runtime/strimzi-three-node-scram-ch028.yaml').read_bytes()).hexdigest()
        lab.result['checks'][phase]='PASS';phase='scoped_benchmark_identity_and_workload_budget'
        plan=[dict(t) for t in plan]
        all_trials=[{**plan[0],'trial':'warmup','records':120,'repeat':0},*plan]
        username=lab.tag+'-benchmark';lab.client_service_account=lab.tag+'-sa';lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.identity_secret=username;lab.identity_items=['password']
        for trial in all_trials:
            trial['topic']=create_performance_topic(lab,trial['trial'],trial.get('partitions',3));trial['group']=lab.tag+'-'+trial['trial']+'-group'
        extras=extra_setup(lab) if extra_setup else {'topics':[],'groups':[]}
        identity=tls_user(username,all_trials[0]['topic'],all_trials[0]['group']);identity['spec']['authentication']={'type':'scram-sha-512'}
        cluster_acl=identity['spec']['authorization']['acls'][-1];identity['spec']['authorization']['acls']=[cluster_acl]
        for trial in all_trials:
            identity['spec']['authorization']['acls'] += [
                {'resource':{'type':'topic','name':trial['topic'],'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'},
                {'resource':{'type':'group','name':trial['group'],'patternType':'literal'},'operations':['Read','Describe'],'host':'*'}]
        for topic in extras['topics']:identity['spec']['authorization']['acls'].append({'resource':{'type':'topic','name':topic,'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'})
        for group in extras['groups']:identity['spec']['authorization']['acls'].append({'resource':{'type':'group','name':group,'patternType':'literal'},'operations':['Read','Describe'],'host':'*'})
        lab.apply(identity);lab.result['benchmark_identity']=ready_identity(lab,username,'benchmark-secret-metadata')
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        lab.result['client_rbac']=rbac_denials(lab.client_service_account)
        lab.result['workload_budget']={'measured_trials':len(plan),'unmeasured_warmup_records':120,'payload_bytes_including_warmup':sum(t['records']*SIZE for t in all_trials),
            'replicated_payload_bytes':3*sum(t['records']*SIZE for t in all_trials),'maximum_offered_records_per_second':max(t['target_records_per_second'] for t in all_trials),'native_process_seconds':{'producer':90,'consumer':60},
            'health_monitor':'actual Kafka Admin full-ISR/leader/quorum poll during native process; kill tree on failure','abort_on_broker_restart_between_trials':True}
        lab.result['checks'][phase]='PASS';results=[]
        for trial in all_trials:trial['status']='NOT_EXECUTED'
        lab.result['trial_attempts']=all_trials
        if extra_run:
            phase='additional_correctness_and_recovery';extra_run(lab,{'bootstrap':bootstrap,'username':username,'extras':extras,'baseline':baseline})
            if broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])!=baseline:raise RuntimeError('Broker drift during additional acceptance')
            lab.result['checks'][phase]='PASS'
        for trial in all_trials:
            phase=trial['trial']+'_native_benchmark';active_trial=trial;trial_started=time.monotonic()
            trial['started_utc']=datetime.now(timezone.utc).isoformat();trial['status']='RUNNING'
            print('Chapter '+chapter+' trial '+trial['trial']+' started (bounded synthetic load)',flush=True)
            trial['evidence']=trial['trial']+f'/chapter-{chapter}-client.log'
            child=PerformanceLab(chapter,limitations);child.tag,child.image,child.out,child.owned=lab.tag+'-'+trial['trial'],lab.image,lab.out/trial['trial'],lab.owned
            child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,username;child.identity_items=['password']
            try:child.run_job('PerfAcceptance',native_arguments(bootstrap,username,trial),[trial['trial']+'_'+check for check in CHECKS])
            finally:lab.result['checks'].update(child.result['checks'])
            text=(child.out/f'chapter-{chapter}-client.log').read_text(encoding='utf-8');trial['producer']=producer_summary(text,trial['records']);trial['consumer']=consumer_summary(text,trial['records'],SIZE)
            trial['observations']=child.result['client_observations'];trial['client_cgroup']=cgroup_observations(trial['observations'])
            trial['producer_metrics']={name:native_metric(text,name,required=False) for name in ('batch-size-avg','compression-rate-avg','bufferpool-wait-time-ns-total','buffer-available-bytes','requests-in-flight')}
            trial['public_profile']={**public,'linger.ms':trial.get('linger_ms',0),'batch.size':trial.get('batch_size',16384),'compression.type':trial.get('compression','none'),'partitions':trial.get('partitions',3),'payload_mode':trial.get('payload_mode','native-random'),'measured_records':trial['records']}
            trial['public_profile_sha256']=hashlib.sha256(json.dumps(trial['public_profile'],sort_keys=True).encode()).hexdigest()
            trial['evidence']=str((child.out/f'chapter-{chapter}-client.log').relative_to(lab.out));trial['harness_completion_seconds']=round(time.monotonic()-trial_started,3)
            after=broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])
            if after!=baseline:raise RuntimeError('ABORT: broker UID/readiness/restart count changed during benchmark')
            current=json.loads(k('get','kafka',CLUSTER,'-o','json'))
            if not any(c['type']=='Ready' and c['status']=='True' for c in current.get('status',{}).get('conditions',[])):raise RuntimeError('ABORT: Kafka CR is not Ready between trials')
            trial['kafka_ready_after_trial']=True
            trial['status']='PASS';active_trial=None;print('Chapter '+chapter+' trial '+trial['trial']+' PASS: '+str(trial['producer']['acknowledged_records'])+' acknowledged records',flush=True);lab.result['checks'][phase]='PASS'
            if trial['trial']=='warmup':lab.result['unmeasured_warmup']=trial
            else:results.append(trial);lab.result['trials']=results
        phase='repeatability_and_statistical_integrity';lab.result[comparison_key]=aggregation(results);lab.result['broker_baseline_and_final']=baseline
        lab.result['checks'][phase]='PASS'
        lab.result['performance_assessment']=assessment
        lab.result['runtime_scope']=runtime_scope;lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL'
        if active_trial is not None and active_trial.get('status')=='RUNNING':active_trial['status']='FAIL';active_trial['failure_class']=type(exc).__name__
        print('Chapter '+chapter+' '+phase+' failed: '+type(exc).__name__+'; sanitized evidence has details',file=sys.stderr)
    return lab.finish(error)
