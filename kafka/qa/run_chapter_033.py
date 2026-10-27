#!/usr/bin/env python3
"""Secure consumer fetch, actual assignments/scaling, and durable pre-commit replay."""
import json
import statistics
import time
from runtime_acceptance import k, CLUSTER
from security_acceptance import secure_client_job, immutable_kafka_image
from performance_acceptance import cgroup_observations
from performance_lab import execute_benchmark, TrialDriver, create_performance_topic
from consumer_acceptance import ConsumerLab, CONSUMER_FIELDS, consumer_arguments, native_fetch_observations, json_observation, expected_crash, sink_binding, group_pod_mapping
from run_chapter_020 import verify_pod_owner

PROFILES=[{'candidate':'baseline','fetch_min_bytes':1,'fetch_max_wait_ms':100},
          {'candidate':'min64','fetch_min_bytes':65536,'fetch_max_wait_ms':100},
          {'candidate':'wait500','fetch_min_bytes':65536,'fetch_max_wait_ms':500}]
LIMITS=['Single-host kind with shared local-path storage is not production consumer capacity, cross-zone/network isolation, CSI reliability or downstream database certification.',
    'Native tools measure fetch throughput and sampled client fetch metrics, not business handler p99. Separate functional Jobs measure a one-millisecond synthetic handler and event age on the shared host clock.',
    'Parallelism groups of 1/3/6/8 members are threads in one Pod; the separate actual Deployment scales manually 1/3/6 Pods. No linear capacity or eight-Pod throughput claim is made.',
    'The durable idempotent sink is a forced single-writer synthetic file on an owned non-broker PVC. Process-crash replay is real; external DB exactly-once, host/power loss, attachment failover and multi-zone durability are NOT_VALIDATED.',
    'Classic protocol and RangeAssignor are explicit. Cooperative/static membership, HPA/KEDA, production downstream backpressure, broker CPU/network/IOPS telemetry and independent review remain NOT_EXECUTED/PENDING.',
    'Client/worker cgroup observations are actual Pod counters; missing metrics are unavailable, not low usage. No numeric full-assessment score or enterprise certification.']
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'critical_gaps':['production resource/broker/downstream correlation','independent technical/security signoff'],
    'other_gates':'NOT_EXECUTED: HPA/KEDA, cooperative/static membership, full fetch-size/poll/slow-handler sweeps, external durable sink recovery',
    'production_representativeness':'NOT_ESTABLISHED'}


def fetch_plan():
    return [{**profile,'trial':f'r{repeat+1}-'+profile['candidate'],'repeat':repeat+1,'records':1200,'record_size':1024,
        'target_records_per_second':400,'partitions':6,'partition_fetch_bytes':1048576,'poll_records':500}
        for repeat in range(3) for profile in PROFILES[repeat:]+PROFILES[:repeat]]


def compare_fetch(trials):
    if len(trials)!=9:raise RuntimeError('All nine native fetch trials must be retained')
    result=[]
    for profile in PROFILES:
        selected=[t for t in trials if t['candidate']==profile['candidate']]
        if len(selected)!=3 or {t['repeat'] for t in selected}!={1,2,3}:raise RuntimeError('Missing/duplicate consumer profile repetition')
        for trial in selected:
            if any(trial.get(key)!=value for key,value in profile.items()) or trial['records']!=1200 or trial['record_size']!=1024 or trial['target_records_per_second']!=400 or trial['partitions']!=6 or trial['partition_fetch_bytes']!=1048576 or trial['poll_records']!=500:
                raise RuntimeError('Fetch comparison changed an uncontrolled factor')
        rates=[t['consumer']['records_per_second_including_group_join'] for t in selected]
        result.append({**profile,'trials':3,'median_native_consumer_records_per_second':statistics.median(rates),'sample_standard_deviation':statistics.stdev(rates),
            'native_fetch_metrics':[t['study_observations']['native_client_fetch_metrics'] for t in selected],
            'consumer_processing_p99':'NOT_INFERRED_FROM_NATIVE_FETCH','decision':'OBSERVED_ONLY; no production fetch configuration selection'})
    return result


def stage(lab,suffix,args,checks,sink=None,planned_crash=False):
    child=ConsumerLab('033',LIMITS);child.tag,child.image,child.out,child.owned=lab.tag+'-'+suffix,lab.image,lab.out/suffix,lab.owned
    child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,lab.identity_secret;child.identity_items=['password']
    if sink:child.sink_claim=sink
    failure=None
    try:child.run_job('ConsumerAcceptance',args,checks)
    except RuntimeError as exc:
        if not planned_crash:raise
        failure=exc
    finally:lab.result['checks'].update(child.result['checks'])
    log_path=child.out/'chapter-033-client.log';text=log_path.read_text(encoding='utf-8');observations=[line for line in text.splitlines() if line.startswith(('OBS:','CHECK:'))]
    result={'job':child.tag+'-client','source_sha256':child.result['java_source_bundle_sha256'],'observations':observations,'evidence':str(log_path.relative_to(lab.out))}
    if planned_crash:
        job=json.loads(k('get','job',child.tag+'-client','-o','json'));pods=json.loads(k('get','pods','-l','app='+child.tag+'-client','-o','json'))['items']
        result['expected_fault']=expected_crash(job,pods,failure is not None and all(child.result['checks'].get(name)=='PASS' for name in checks));result['pod']=pods[0]
    return result


def setup(lab):
    parallel={str(n):{'topic':create_performance_topic(lab,'parallel-'+str(n),6),'group':lab.tag+'-parallel-'+str(n)+'-group'} for n in (1,3,6,8)}
    scale={'topic':create_performance_topic(lab,'scale',6),'group':lab.tag+'-scale-group','prefix':lab.tag+'-scale'}
    replay={'topic':create_performance_topic(lab,'replay',6),'group':lab.tag+'-replay-group','event_id':lab.tag+'-replay','sink':lab.tag+'-sink'}
    lab.apply({'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':{'name':replay['sink'],'labels':{'qa.kafka/test-owner':lab.tag},'annotations':{'qa.kafka/purpose':'synthetic idempotent consumer sink; never broker data'}},
        'spec':{'accessModes':['ReadWriteOnce'],'storageClassName':'standard','volumeMode':'Filesystem','resources':{'requests':{'storage':'1Gi'}}}})
    return {'topics':[info['topic'] for info in parallel.values()]+[scale['topic'],replay['topic']],
            'groups':[info['group'] for info in parallel.values()]+[scale['group'],replay['group']], 'parallel':parallel,'scale':scale,'replay':replay}


def replay_checks(lab,context):
    cfg=context['extras']['replay'];base=[context['bootstrap'],context['username'],cfg['topic']]
    seed=stage(lab,'replay-seed',['seed',*base,cfg['event_id'],'120'],['seed_bounded_six_partition_seed_acks_all'])
    crash=stage(lab,'replay-crash',['replay-crash',*base,cfg['group'],cfg['event_id']],['replay-crash_forced_sink_checkpoint_before_commit_expected_halt'],cfg['sink'],True)
    checkpoint=json_observation(crash['observations'],'REPLAY_CHECKPOINT')
    claim=json.loads(lab.read('sink-claim-after-crash','get','pvc',cfg['sink'],'-o','json'));pv=json.loads(lab.read('sink-pv-after-crash','get','pv',claim['spec']['volumeName'],'-o','json'))
    before=sink_binding(claim,pv,crash['pod'],cfg['sink']);crash.pop('pod')
    recovery=stage(lab,'replay-recover',['replay-recover',*base,cfg['group'],cfg['event_id']],['replay-recover_replayed_uncommitted_ids_deduplicated_and_no_missing_ids','replay-recover_commit_after_success_reaches_captured_ends'],cfg['sink'])
    pod=json.loads(k('get','pods','-l','app='+recovery['job'],'-o','json'))['items']
    if len(pod)!=1:raise RuntimeError('Expected one recovery Pod')
    claim=json.loads(lab.read('sink-claim-after-recover','get','pvc',cfg['sink'],'-o','json'));pv=json.loads(lab.read('sink-pv-after-recover','get','pv',claim['spec']['volumeName'],'-o','json'))
    after=sink_binding(claim,pv,pod[0],cfg['sink'])
    if before!=after:raise RuntimeError('Recovery did not use the same owned PVC/PV/node binding')
    lab.result['consumer_replay']={'seed':seed,'crash':crash,'checkpoint':checkpoint,'recovery':recovery,'sink_binding':after,
        'outcome':json_observation(recovery['observations'],'REPLAY_RECOVERY'),'scope':'real process termination before commit, forced single-writer synthetic file deduplication, no production offset reset'}
    lab.result['checks']['same_owned_sink_binding_across_process_crash']='PASS'


def deployment_manifest(lab,name,source,cfg,context):
    manifest={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':name},'spec':{'replicas':1,'selector':{'matchLabels':{'app':name}},
        'strategy':{'type':'RollingUpdate','rollingUpdate':{'maxSurge':1,'maxUnavailable':0}},'template':{'metadata':{'labels':{'app':name}},'spec':{
            'terminationGracePeriodSeconds':30,'volumes':[{'name':'source','configMap':{'name':source}}],
            'containers':[{'name':'client','image':lab.image,'command':['java','-Xmx128m','-cp','/opt/kafka/libs/*','/qa/ConsumerAcceptance.java','worker',context['bootstrap'],context['username'],cfg['topic'],cfg['group'],cfg['prefix']],
                'env':[{'name':'POD_NAME','valueFrom':{'fieldRef':{'fieldPath':'metadata.name'}}}],
                'volumeMounts':[{'name':'source','mountPath':'/qa','readOnly':True}],
                'readinessProbe':{'exec':{'command':['/bin/bash','-c','test -f /tmp/consumer-joined']},'periodSeconds':2,'timeoutSeconds':2},
                'resources':{'requests':{'cpu':'100m','memory':'256Mi'},'limits':{'cpu':'500m','memory':'512Mi'}}}]}}}}
    return secure_client_job(manifest,lab.client_service_account,lab.ca_secret,lab.identity_secret,['password'])


def deployment_pods(lab,name,uid,replicas):
    deployment=json.loads(k('get','deployment',name,'-o','json'))
    if deployment['metadata']['uid']!=uid or deployment['spec']['replicas']!=replicas:raise RuntimeError('Owned Deployment UID/replica drift')
    pods=json.loads(k('get','pods','-l','app='+name,'-o','json'))['items']
    if len(pods)!=replicas:raise RuntimeError('Actual Deployment Pod count mismatch')
    for pod in pods:
        refs=[ref for ref in pod['metadata'].get('ownerReferences',[]) if ref.get('controller') and ref['kind']=='ReplicaSet']
        if len(refs)!=1:raise RuntimeError('Consumer Pod has no unique ReplicaSet owner')
        rs=json.loads(k('get','replicaset',refs[0]['name'],'-o','json'))
        if not verify_pod_owner(pod,rs,deployment):raise RuntimeError('Consumer Pod owner UID chain mismatch')
        containers=[c for c in pod['status'].get('containerStatuses',[]) if c['name']=='client']
        if len(containers)!=1 or not containers[0].get('ready') or containers[0]['restartCount']!=0 or immutable_kafka_image(containers[0]['imageID'])!=lab.image:raise RuntimeError('Consumer Pod readiness/restart/immutable image guard failed')
    return pods


def scaling_checks(lab,context):
    cfg=context['extras']['scale'];name=lab.tag+'-consumers';source=lab.source('ConsumerAcceptance');lab.apply(deployment_manifest(lab,name,source,cfg,context))
    uid=json.loads(k('get','deployment',name,'-o','json'))['metadata']['uid'];results=[]
    for replicas in (1,3,6):
        if replicas!=1:k('scale','deployment',name,'--replicas='+str(replicas))
        k('rollout','status','deployment/'+name,'--timeout=240s',timeout=260);pods=deployment_pods(lab,name,uid,replicas)
        proof=stage(lab,'scale-'+str(replicas),['inspect',context['bootstrap'],context['username'],cfg['topic'],cfg['group'],str(replicas),cfg['prefix']+'-'+str(replicas)],
            ['scale-'+str(replicas)+'_stable_membership_and_committed_canary','scale-'+str(replicas)+'_healthy_quorum_and_full_isr'])
        outcome=json_observation(proof['observations'],'SCALE_GROUP');pods=deployment_pods(lab,name,uid,replicas)
        proof['group_to_actual_pods']=group_pod_mapping(outcome['assignment'],pods);proof['outcome']=outcome;results.append(proof)
        for pod in pods:lab.read('worker-'+str(replicas)+'-'+pod['metadata']['name'],'logs',pod['metadata']['name'],'-c','client','--tail=300')
    lab.result['manual_deployment_scaling']={'deployment':name,'uid':uid,'replicas':[1,3,6],'stages':results,'hpa_keda':'NOT_EXECUTED_NO_REVIEWED_METRICS_SCALER'}
    # Release idle consumers before native measurements so their footprint does not confound profiles.
    current=json.loads(k('get','deployment',name,'-o','json'))
    if current['metadata']['uid']!=uid:raise RuntimeError('Refuse teardown after owned Deployment UID changed')
    k('delete','deployment',name,'--wait=true','--timeout=120s',timeout=140)
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        if not json.loads(k('get','pods','-l','app='+name,'-o','json'))['items']:break
        time.sleep(1)
    else:raise RuntimeError('Owned consumer Pods did not terminate before native measurement')
    lab.result['checks']['owned_deployment_released_before_native_fetch_trials']='PASS'


def extra(lab,context):
    replay_checks(lab,context)
    rows=[]
    for count in (1,3,6,8):
        cfg=context['extras']['parallel'][str(count)];label='parallel-'+str(count)
        proof=stage(lab,label,['parallel',context['bootstrap'],context['username'],cfg['topic'],cfg['group'],str(count),label],
            [label+'_exclusive_six_partition_assignment_and_idle_ceiling',label+'_processed_ids_commit_after_success_and_captured_end_catchup',label+'_healthy_quorum_and_full_isr'])
        proof['outcome']=json_observation(proof['observations'],'GROUP_FUNCTIONAL');proof['client_cgroup']=cgroup_observations(proof['observations']);rows.append(proof)
    lab.result['group_parallelism']={'stages':rows,'scope':'1/3/6/8 member threads in one Pod per fresh group, not an eight-Pod capacity experiment'}
    scaling_checks(lab,context)


def main():
    driver=TrialDriver(lab_class=ConsumerLab,main='ConsumerAcceptance',arguments=consumer_arguments,analyze=native_fetch_observations,profile_fields=CONSUMER_FIELDS)
    return execute_benchmark('033',fetch_plan(),LIMITS,{'partitions':6,'group.protocol':'classic','partition.assignment.strategy':'org.apache.kafka.clients.consumer.RangeAssignor','session.timeout.ms':10000,'heartbeat.interval.ms':3000,'max.poll.interval.ms':120000,'auto.offset.reset':'earliest','enable.auto.commit':False,'fetch.max.bytes':1048576},ASSESSMENT,compare_fetch,
        'fetch_comparison',setup,extra,runtime_scope='ACTUAL_SECURE_NATIVE_FETCH_GROUP_PARALLELISM_MANUAL_DEPLOYMENT_SCALING_AND_FORCED_SINK_REPLAY_NOT_PRODUCTION_CAPACITY',driver=driver)


if __name__=='__main__':raise SystemExit(main())
