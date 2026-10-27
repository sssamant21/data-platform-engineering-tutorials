"""Chapter-owned broker tuning, measured JMX samples and guaranteed rollback."""
import hashlib
import json
import math
import re
import time
from runtime_acceptance import ROOT, CLUSTER, k
from performance_lab import PerformanceLab, native_arguments, broker_snapshot
from java_sources import bundle_java_sources

FIXTURE='strimzi-three-node-metrics-ch034.yaml'


def config_patch(cluster,target):
    if cluster['metadata']['name']!=CLUSTER or cluster['metadata'].get('annotations',{}).get('qa.kafka/chapter')!='034' or target not in (8,10):
        raise RuntimeError('Refuse tuning outside chapter-owned disposable fixture')
    spec=cluster['spec']['kafka']; config=spec['config']
    required={'default.replication.factor':3,'min.insync.replicas':2,'offsets.topic.replication.factor':3,'transaction.state.log.replication.factor':3,'transaction.state.log.min.isr':2}
    if spec['version']!='4.0.0' or config.get('num.io.threads') not in (8,10) or any(config.get(key)!=value for key,value in required.items()):
        raise RuntimeError('Unexpected broker baseline or weakened durability')
    return [{'op':'test','path':'/metadata/uid','value':cluster['metadata']['uid']},
            {'op':'test','path':'/metadata/resourceVersion','value':cluster['metadata']['resourceVersion']},
            {'op':'test','path':'/spec','value':cluster['spec']},
            {'op':'replace','path':'/spec/kafka/config/num.io.threads','value':target}]


def reconcile(target):
    # Context is explicit on every API call; the dedicated fixture annotation is mandatory.
    node=json.loads(k('get','node','kafka-qa-control-plane','-o','json'))
    if node['metadata'].get('labels',{}).get('kubernetes.io/hostname')!='kafka-qa-control-plane':raise RuntimeError('Expected disposable kind node')
    before=json.loads(k('get','kafka',CLUSTER,'-o','json')); patch=config_patch(before,target)
    original=before['spec']['kafka']['config']['num.io.threads']
    if original!=target:
        k('patch','kafka',CLUSTER,'--type=json','--patch',json.dumps(patch),'--dry-run=server','-o','name')
        k('patch','kafka',CLUSTER,'--type=json','--patch',json.dumps(patch))
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        after=json.loads(k('get','kafka',CLUSTER,'-o','json'))
        if after['metadata']['uid']!=before['metadata']['uid']:raise RuntimeError('Kafka UID changed during reconciliation')
        expected={**before['spec']['kafka']['config'],'num.io.threads':target}
        expected_spec={**before['spec'],'kafka':{**before['spec']['kafka'],'config':expected}}
        if after['spec']!=expected_spec:raise RuntimeError('Concurrent/unapproved broker spec drift')
        if after.get('status',{}).get('observedGeneration')==after['metadata']['generation'] and any(c['type']=='Ready' and c['status']=='True' for c in after.get('status',{}).get('conditions',[])):
            return {'uid':after['metadata']['uid'],'from':original,'to':target,'generation':after['metadata']['generation'],'observed_generation':after['status']['observedGeneration'],'server_dry_run':original!=target}
        time.sleep(1)
    raise RuntimeError('Strimzi tuning reconciliation exceeded deadline')


def broker_cgroups(lab,label):
    observations={}
    for i in range(3):
        pod=f'{CLUSTER}-dual-role-{i}'
        observations[pod]={}
        for name in ('cpu.stat','memory.current','io.stat'):
            observations[pod][name]=lab.read(label+'-'+pod+'-'+name.replace('.','-'),'exec',pod,'-c','kafka','--','cat','/sys/fs/cgroup/'+name).strip()
    return observations


class BrokerLab(PerformanceLab):
    def prepare(self):
        super().prepare()
        cluster=json.loads(self.read('broker-baseline-cr','get','kafka',CLUSTER,'-o','json'));config_patch(cluster,8)
        if cluster['spec']['kafka']['config']['num.io.threads']!=8:raise RuntimeError('Initial broker baseline must be eight IO threads')
        for kind in ('kafkas','kafkanodepools'):
            self.read(kind+'-crd','get','crd',kind+'.kafka.strimzi.io','-o','json')
        pool=json.loads(self.read('broker-resource-budgets','get','kafkanodepool','dual-role','-o','json'))
        if pool['spec']['resources']['limits']!={'memory':'1280Mi','cpu':'2'} or pool['spec']['jvmOptions']!={'-Xms':'256m','-Xmx':'512m'} or pool['spec']['replicas']!=3 or set(pool['spec']['roles'])!={'broker','controller'}:
            raise RuntimeError('Unexpected broker JVM/container budget or replica count')
        self.result['checks']['chapter_owned_instrumented_broker_baseline']='PASS'

    def source(self,main):
        if main!='BrokerAcceptance':return super().source(main)
        source=bundle_java_sources(main,{name:(ROOT/'kafka/qa/runtime'/(name+'.java')).read_text(encoding='utf-8-sig') for name in (main,'PerfAcceptance')})
        self.result['java_source_bundle_sha256']=hashlib.sha256(source.encode()).hexdigest()
        return self.apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':self.tag+'-source'},'data':{main+'.java':source}})

    def apply(self,manifest):
        if manifest['kind']=='KafkaUser':
            for acl in manifest['spec']['authorization']['acls']:
                if acl['resource']['type']=='cluster':acl['operations'].append('DescribeConfigs')
        return super().apply(manifest)

    def run_job(self,main,args,required):
        if main!='BrokerAcceptance':return super().run_job(main,args,required)
        target=int(args[-1]); original_tag=self.tag; original_out=self.out
        transitions={}; original_log=original_out/'chapter-034-client.log'
        before=broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])
        # Even a partially failed apply is followed by rollback; never discard a failed trial.
        try:
            transitions['apply']=reconcile(target)
            transitions['broker_cgroup_before']=broker_cgroups(self,'cgroup-before')
            super().run_job(main,args,required)
        finally:
            transitions['rollback']=reconcile(8)
            self.tag=original_tag+'-restore';self.out=original_out/'restore'
            try:
                verify=['verify',args[0],args[1],args[2],args[3],args[-2],'8']
                super().run_job(main,verify,['restore_effective_broker_config_full_isr_and_quorum'])
                restore=self.out/'chapter-034-client.log'
                transitions['effective_rollback_evidence']=str(restore.relative_to(original_out))
                after=broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])
                if after!=before:raise RuntimeError('Broker restarted or changed during dynamic tuning/rollback')
                transitions['broker_uids_and_restarts_unchanged']=True
                transitions['broker_cgroup_after']=broker_cgroups(self,'cgroup-after')
            finally:
                self.tag,self.out=original_tag,original_out
                original_out.mkdir(parents=True,exist_ok=True)
                line='OBS:BROKER_CONFIG_TRANSITION:'+json.dumps(transitions,sort_keys=True)
                with original_log.open('a',encoding='utf-8') as output:output.write('\n'+line+'\n')
            self.result['client_observations']=[line for line in original_log.read_text(encoding='utf-8').splitlines() if line.startswith(('OBS:','CHECK:'))]

    def finish(self,error=None):
        self.result['fixture_sha256']=hashlib.sha256((ROOT/'kafka/qa/runtime'/FIXTURE).read_bytes()).hexdigest()
        self.result['metrics_gaps']={'provider_iops_latency_credits':'NOT_AVAILABLE_ON_SHARED_KIND_HOST','page_cache_attribution':'NOT_VALIDATED','broker_jmx':'ACTUAL_PER_BROKER_SAMPLES_DURING_NATIVE_LOAD_WHEN_TRIAL_PASSES','production_capacity':'NOT_ESTABLISHED'}
        return super().finish(error)


def broker_arguments(bootstrap,username,trial):
    controls={'partitions':6,'target_records_per_second':400,'record_size':1024,'linger_ms':0,'batch_size':16384,'compression':'none','payload_mode':'native-random'}
    if type(trial.get('io_threads')) is not int or trial['io_threads'] not in (8,10) or any(trial.get(key)!=value for key,value in controls.items()):raise RuntimeError('Unapproved broker experiment')
    base=native_arguments(bootstrap,username,trial)
    # Stable headless broker names, not externally supplied URLs or unrestricted targets.
    hosts=','.join(f'{CLUSTER}-dual-role-{i}.{CLUSTER}-kafka-brokers.kafka-qa.svc:9404' for i in range(3))
    return [*base,hosts,str(trial['io_threads'])]


def observation(text,name):
    prefix='OBS:'+name+':'
    values=[json.loads(line[len(prefix):]) for line in text.splitlines() if line.startswith(prefix)]
    if len(values)!=1:raise RuntimeError('Missing/ambiguous '+name)
    return values[0]


METRIC=re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(.*)\})?\s+([^\s]+)(?:\s+\d+)?$')
LABEL=re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"\\]*)"')


def metrics_map(lines):
    result={}
    for line in lines:
        match=METRIC.fullmatch(line)
        if not match:raise RuntimeError('Malformed selected broker metric')
        name,raw,value=match.groups();raw=raw or '';labels=dict(LABEL.findall(raw))
        if raw.replace(',','')!=''.join(m.group(0) for m in LABEL.finditer(raw)).replace(',','') or len(labels)!=len(LABEL.findall(raw)):
            raise RuntimeError('Ambiguous broker metric labels')
        number=float(value)
        if not math.isfinite(number) or number<0:raise RuntimeError('Invalid broker metric value')
        key=(name,tuple(sorted(labels.items())))
        if key in result:raise RuntimeError('Duplicate broker metric sample')
        result[key]=number
    return result


def metric(values,name,**labels):
    key=(name,tuple(sorted(labels.items())))
    if key not in values:raise RuntimeError('Required broker metric absent: '+name+' '+str(labels))
    return values[key]


def broker_observations(text,trial):
    prefix='OBS:BROKER_SAMPLE:'
    samples=[json.loads(line[len(prefix):]) for line in text.splitlines() if line.startswith(prefix)]
    results=[]
    if any(row.get('broker') not in (0,1,2) for row in samples):raise RuntimeError('Unexpected broker metrics identity')
    for broker in range(3):
        rows=[row for row in samples if row['broker']==broker]
        if len(rows)<4 or rows[0]['phase']!='before' or rows[-1]['phase']!='after' or sum(row['phase']=='native_window' for row in rows)<2:
            raise RuntimeError('Missing actual before/during/after samples for every broker')
        if [r['sequence'] for r in rows]!=sorted({r['sequence'] for r in rows}):raise RuntimeError('Duplicate/backwards broker samples')
        maps=[metrics_map(row['metrics']) for row in rows]
        for values in maps:
            for name in ('qa_under_replicated_partitions','qa_under_min_isr_partitions'):
                if metric(values,name)!=0:raise RuntimeError('Broker replication health metric violated')
            # Kafka4 combined-role pools share this Yammer meter name; its raw mean
            # sums both independently normalized pool contributions. It is not a broker fraction.
            metric(values,'qa_handler_idle')
            if not 0<=metric(values,'qa_network_idle')<=1:raise RuntimeError('Broker network idle fraction outside supported range')
            if metric(values,'qa_jvm_heap_bytes',measure='max')!=512*1024*1024 or metric(values,'qa_jvm_heap_bytes',measure='used')>512*1024*1024:
                raise RuntimeError('Effective JVM heap exceeds approved memory budget')
        stages={}
        for request in ('Produce','FetchConsumer','FetchFollower'):
            stages[request]={}
            for stage in ('TotalTimeMs','RequestQueueTimeMs','LocalTimeMs','RemoteTimeMs','ResponseQueueTimeMs','ResponseSendTimeMs'):
                counters=[metric(values,'qa_request_events_total',request=request,stage=stage) for values in maps]
                if any(a>b for a,b in zip(counters,counters[1:])) or (trial.get('trial')!='warmup' and counters[-1]<=counters[0]):raise RuntimeError('Broker request samples did not observe matched traffic or counter reset')
                stages[request][stage]={'observed_request_count_delta':counters[-1]-counters[0],
                    'p95_ms_snapshots':[metric(values,'qa_request_ms',request=request,stage=stage,quantile='0.95') for values in maps],
                    'p99_ms_snapshots':[metric(values,'qa_request_ms',request=request,stage=stage,quantile='0.99') for values in maps],
                    'scope':'broker reservoir snapshots; not interval-only percentiles or summed/averaged p99'}
        gc=[]
        keys=[key for key in maps[0] if key[0] in ('qa_jvm_gc_collections_total','qa_jvm_gc_collection_time_ms_total')]
        if not keys:raise RuntimeError('JVM GC collector observations absent')
        for key in keys:
            values=[m.get(key) for m in maps]
            if any(v is None for v in values) or any(a>b for a,b in zip(values,values[1:])):raise RuntimeError('GC counter disappeared or reset')
            gc.append({'name':key[0],'labels':dict(key[1]),'delta':values[-1]-values[0]})
        results.append({'broker':broker,'sample_count':len(rows),'request_stages':stages,'gc_cumulative_deltas':gc,
            'combined_role_handler_idle_raw_mean_rates':[metric(values,'qa_handler_idle') for values in maps],
            'handler_idle_scope':'shared broker/controller meter; NOT an isolated broker fraction or saturation gate',
            'network_idle_fractions':[metric(values,'qa_network_idle') for values in maps],
            'heap_max_bytes':512*1024*1024,'container_memory_limit_bytes':1280*1024*1024,'budget_remaining_bytes_not_free_memory':768*1024*1024,
            'timestamps_utc':[row['timestamp_utc'] for row in rows]})
    configs=[json.loads(line.split(':',2)[2]) for line in text.splitlines() if line.startswith('OBS:EFFECTIVE_IO_CONFIG:')]
    if not isinstance(configs,list) or len(configs)!=2 or any(len(config)!=3 or any(row['io_threads']!=trial['io_threads'] for row in config) for config in configs):
        raise RuntimeError('Actual effective broker setting before/after native trial missing')
    transition=observation(text,'BROKER_CONFIG_TRANSITION')
    if transition['apply']['to']!=trial['io_threads'] or transition['rollback']['to']!=8 or not transition['broker_uids_and_restarts_unchanged'] or not transition.get('effective_rollback_evidence'):
        raise RuntimeError('Successful effective rollback and stable broker identities not established')
    cgroups=[]
    for pod,before in transition['broker_cgroup_before'].items():
        after=transition['broker_cgroup_after'][pod]
        cpu=[]
        for entry in (before,after):
            parsed=dict(line.split() for line in entry['cpu.stat'].splitlines())
            cpu.append({name:int(parsed[name]) for name in ('usage_usec','nr_periods','nr_throttled','throttled_usec')})
        if any(cpu[1][key]<value for key,value in cpu[0].items()):raise RuntimeError('Broker cgroup counter reset')
        cgroups.append({'pod':pod,'cpu_counter_deltas':{key:cpu[1][key]-value for key,value in cpu[0].items()},
            'memory_current_bytes_before':int(before['memory.current']),'memory_current_bytes_after':int(after['memory.current']),
            'io_stat_raw_before':before['io.stat'],'io_stat_raw_after':after['io.stat'],
            'scope':'container cumulative deltas over whole harness including operator reconciliation; io devices not attributed to a broker PVC latency/IOPS'})
    return {'brokers':results,'broker_cgroups':cgroups,'operator_transition':transition,'effective_configs_before_and_after':configs,
        'jvm_gc_scope':'cumulative count and time, not GC pause p99 or allocation profiling',
        'broker_latency_scope':'actual exporter reservoirs include background traffic; no causality/production capacity claim'}
