#!/usr/bin/env python3
"""Actual namespace-scoped monitoring foundation and authenticated local alert drill."""
import base64
import contextlib
import copy
import hashlib
import json
import math
import secrets
import subprocess
import time
from runtime_acceptance import CTX, NS, CLUSTER, ROOT, k
from security_acceptance import secure_client_job, immutable_kafka_image
from run_chapter_027 import tls_user
from run_chapter_028 import bootstrap_from_status
from run_chapter_029 import ready_identity, rbac_denials
from performance_lab import broker_snapshot, filesystem_headroom
from broker_acceptance import metrics_map, metric
from monitoring_lab import MonitoringLab
from monitoring_crds import OPERATOR, PROMETHEUS, ALERTMANAGER, GRAFANA
from monitoring_resources import operator_manifests, discovery_manifests, prometheus_manifests, grafana_manifests, monitors, promtool_manifests, server_deployment, service, labels
from monitoring_acceptance import http_json, wait_for, query, scalar_series, targets, owned_alerts, receipt_state, grafana_number, pod_security_inventory, monitoring_pvc, http_text

LIMITS=[
    'This is a single-host disposable kind monitoring foundation, not production Kafka capacity, monitoring HA, multi-zone/CSI resilience or enterprise certification.',
    'Kafka4.0.0/Strimzi0.47.0 remain fixed with RF3/minISR2/SCRAM over TLS and hostname validation. Monitoring components use separate pinned versions and an owned namespace; no production cluster is modified.',
    'KRaft leader/configured-voter metrics are cross-checked with actual Admin quorum status. Configured voter count is not independent quorum liveness proof. No controller/broker failure is injected.',
    'Only the owned synthetic metrics target is stopped/restored. Local authenticated webhook firing/resolved delivery is real; human paging, escalation acknowledgment and production alert delivery are NOT_EXECUTED.',
    'Prometheus discovery RBAC and actual restricted Pod Security admission are validated. Default kind CNI NetworkPolicy enforcement is NOT_QUALIFIED, so unauthorized network isolation remains NOT_VALIDATED.',
    'Grafana uses internal-only Service and secret-mounted local authentication. Production SSO/TLS ingress, external dashboard permissions, visual/independent review and enterprise security acceptance remain pending.',
    'Twelve canary events prove synthetic producer/consumer/commit telemetry, not external business durability or a latency SLO. Per-broker JMX percentile gauges are not global histograms and are never averaged into global p99.',
    'Provider disk latency/IOPS, attributed page cache, node/cAdvisor and kube-state-metrics coverage are NOT_EXECUTED. PVC binding/retention settings and TSDB series cost are measured, not provider storage certification.'
]
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'enterprise_certification':'NOT_CERTIFIED',
    'pending_critical_gates':['qualified CNI network isolation','production SSO/TLS and human paging','provider/node telemetry','independent operational/security signoff'],
    'failure_injection_scope':'MONITORING_ONLY_OWNED_SYNTHETIC_TARGET; no Kafka broker/controller interruption'}


def rbac(lab,account,namespace,resource,expected,subject_namespace=None):
    subject_namespace=subject_namespace or lab.monitor_ns
    command=['kubectl','--context',CTX,'-n',namespace,'auth','can-i','get',resource,'--as=system:serviceaccount:'+subject_namespace+':'+account]
    result=subprocess.run(command,capture_output=True,text=True,timeout=20)
    if result.stdout.strip()!=expected or result.returncode!=(0 if expected=='yes' else 1):raise RuntimeError('Monitoring RBAC did not establish expected '+expected+' for '+resource+' in '+namespace)
    return {'subject':subject_namespace+'/'+account,'namespace':namespace,'verb':'get','resource':resource,'allowed':expected=='yes'}


def restricted_admission(lab):
    pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':lab.tag+'-psa-negative','namespace':lab.monitor_ns},'spec':{'restartPolicy':'Never','containers':[{'name':'invalid','image':lab.image,'securityContext':{'privileged':True}}]}}
    result=subprocess.run(['kubectl','--context',CTX,'-n',lab.monitor_ns,'apply','--dry-run=server','-f','-'],input=json.dumps(pod),capture_output=True,text=True,timeout=30)
    if result.returncode==0 or 'violates PodSecurity' not in result.stderr or 'restricted' not in result.stderr:raise RuntimeError('Actual restricted Pod Security admission was not established')
    if lab.mk('get','pod',pod['metadata']['name'],'--ignore-not-found','-o','json').strip():raise RuntimeError('Negative admission test unexpectedly persisted a Pod')
    return {'status':'PASS','mode':'SERVER_DRY_RUN_ONLY','privileged_pod':'REJECTED_NOT_CREATED','namespace':lab.monitor_ns}


def deploy_servers(lab,bootstrap,username,topic,group,control,probe_user):
    source=lab.source('ObservabilityTarget')
    lab.apply({'apiVersion':'v1','kind':'Secret','metadata':{'name':lab.tag+'-control'},'type':'Opaque','stringData':{'token':control}})
    target=server_deployment(lab.tag,'synthetic',lab.image,source,lab.client_service_account,['target',lab.tag,bootstrap,username,topic,group,lab.tag+'-event'])
    target=secure_client_job(target,lab.client_service_account,lab.ca_secret,lab.identity_secret,['password'])
    pod=target['spec']['template']['spec'];pod['containers'][0]['securityContext']['readOnlyRootFilesystem']=True
    pod['volumes'].append({'name':'control','secret':{'secretName':lab.tag+'-control','defaultMode':0o440}});pod['containers'][0]['volumeMounts'].append({'name':'control','mountPath':'/qa-control','readOnly':True})
    lab.apply(target);lab.apply(service(lab.tag,'synthetic',labels(lab.tag,'synthetic'),8080))
    probe=server_deployment(lab.tag,'quorum-probe',lab.image,source,lab.client_service_account,['probe',lab.tag,bootstrap,probe_user,topic,lab.tag+'-unused-probe-group',lab.tag+'-probe'])
    probe=secure_client_job(probe,lab.client_service_account,lab.ca_secret,probe_user,['password'])
    pod=probe['spec']['template']['spec'];pod['containers'][0]['securityContext']['readOnlyRootFilesystem']=True
    pod['volumes'].append({'name':'control','secret':{'secretName':lab.tag+'-control','defaultMode':0o440}});pod['containers'][0]['volumeMounts'].append({'name':'control','mountPath':'/qa-control','readOnly':True})
    lab.apply(probe);lab.apply(service(lab.tag,'quorum-probe',labels(lab.tag,'quorum-probe'),8080))
    lab.mon_apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.tag+'-receiver-sa'},'automountServiceAccountToken':False})
    receiver_source=lab.tag+'-receiver-source';lab.mon_apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':receiver_source},'immutable':True,'data':{'ObservabilityTarget.java':lab.source_text}})
    receiver=server_deployment(lab.tag,'receiver',lab.image,receiver_source,lab.tag+'-receiver-sa',['receiver',lab.tag])
    pod=receiver['spec']['template']['spec'];pod['volumes'].append({'name':'receiver-auth','secret':{'secretName':lab.tag+'-receiver-auth','defaultMode':0o440}});pod['containers'][0]['volumeMounts'].append({'name':'receiver-auth','mountPath':'/receiver-auth','readOnly':True})
    lab.mon_apply(receiver);lab.mon_apply(service(lab.tag,'receiver',labels(lab.tag,'receiver'),8080))
    k('rollout','status','deployment/'+lab.tag+'-synthetic','--timeout=240s',timeout=250)
    k('rollout','status','deployment/'+lab.tag+'-quorum-probe','--timeout=240s',timeout=250)
    lab.mk('rollout','status','deployment/'+lab.tag+'-receiver','--timeout=240s',timeout=250)


def monitoring_setup(lab,password,receiver_token):
    cluster,local=operator_manifests(lab.tag,lab.monitor_ns)
    for manifest in cluster:lab.apply(manifest)
    for manifest in local:lab.mon_apply(manifest)
    lab.mk('rollout','status','deployment/'+lab.tag+'-operator','--timeout=240s',timeout=250)
    _,discovery=discovery_manifests(lab.tag,lab.monitor_ns)
    for manifest in discovery:lab.apply(copy.deepcopy(manifest));lab.mon_apply(copy.deepcopy(manifest))
    deferred=[]
    for manifest in prometheus_manifests(lab.tag,lab.monitor_ns,receiver_token):
        if manifest['kind']=='PrometheusRule':deferred.append(manifest)
        else:lab.mon_apply(manifest)
    for manifest in monitors(lab.tag,lab.monitor_ns):lab.mon_apply(manifest)
    grafana,metadata=grafana_manifests(lab.tag,lab.monitor_ns,password)
    for manifest in grafana:lab.mon_apply(manifest)
    for manifest in promtool_manifests(lab.tag):lab.mon_apply(manifest)
    lab.mk('wait','job/'+lab.tag+'-promtool','--for=condition=complete','--timeout=180s',timeout=190)
    for container in ('lint','unit'):lab.mon_read('promtool-'+container,'logs','job/'+lab.tag+'-promtool','-c',container,'--tail=200')
    lab.result['checks']['actual_promtool_lint_and_signal_rule_unit_tests']='PASS'
    lab.mk('rollout','status','statefulset/prometheus-'+lab.tag+'-prom','--timeout=300s',timeout=310)
    lab.mk('rollout','status','statefulset/alertmanager-'+lab.tag+'-am','--timeout=240s',timeout=250)
    lab.mk('rollout','status','deployment/'+lab.tag+'-grafana','--timeout=240s',timeout=250)
    return deferred,metadata


def compare_metrics(lab,prom,proof):
    selector='qa_owner="'+lab.tag+'"';result={}
    for name,expected in [('qa_client_produced_records_total',12),('qa_client_processed_records_total',12),('qa_client_errors_total',0),('qa_client_group_lag',0),
        ('qa_client_ack_wait_p99_ms',proof['ack_wait_ms']['p99']),('qa_client_event_age_p99_ms',proof['created_to_processed_ms']['p99']),('qa_client_verified_timestamp_seconds',proof['verified_at_seconds'])]:
        result[name]=scalar_series(prom,name+'{'+selector+'}',expected)
    if not 0<=time.time()-proof['verified_at_seconds']<120:raise RuntimeError('Independent canary proof stale')
    for name,expected in [('qa_under_replicated_partitions',0),('qa_under_min_isr_partitions',0),('qa_raft_current_leader',proof['leader_id']),('qa_raft_number_of_voters',len(proof['voter_ids']))]:
        rows=query(prom,name+'{'+selector+'}')
        if len(rows)!=3 or len({row['labels'].get('broker') for row in rows})!=3 or any(row['value']!=expected for row in rows):raise RuntimeError('Broker/KRaft metric differs from independent source: '+name)
        result[name]=rows
    for name in ('qa_raft_high_watermark','qa_raft_log_end_offset'):
        rows=query(prom,name+'{'+selector+'}')
        if len(rows)!=3 or any(row['value']<0 for row in rows):raise RuntimeError('KRaft log signal absent/unknown')
        result[name]=rows
    for name in ('qa_jvm_heap_bytes','jvm_gc_collection_seconds_count','jvm_gc_collection_seconds_sum'):
        rows=query(prom,name+'{'+selector+',qa_kind="broker"}')
        if {row['labels'].get('broker') for row in rows}!=set(row['labels']['broker'] for row in result['qa_raft_current_leader']) or any(row['value']<0 for row in rows):raise RuntimeError('Required actual JVM metric coverage incomplete')
        result[name]=rows
    result['configured_voters_not_quorum_liveness']='Configured membership matches Admin; independent Admin health also required. No controller failure injection.'
    return result


class UnsafeHealth(Exception):
    pass


def kafka_health(probe,control,observations):
    try:
        proof=http_json(probe,'/quorum',headers={'X-QA-Token':control})
        voters=proof['voter_ids']
        if len(voters)!=3 or len(set(voters))!=3 or proof['leader_id'] not in voters or proof['high_watermark']<0 or not -5<=time.time()-proof['verified_at_seconds']<=30:raise RuntimeError('Independent Kafka quorum evidence invalid/stale')
        observations.append(proof)
        if len(observations)>300:raise RuntimeError('Kafka health observation budget exceeded')
        return proof
    except (OSError,RuntimeError,KeyError,ValueError) as error:raise UnsafeHealth('Independent Kafka health probe failed: '+type(error).__name__) from None


def scale_target(lab,replicas):
    if replicas not in (0,1):raise RuntimeError('Unapproved monitoring-only scale count')
    name=lab.tag+'-synthetic';actual=json.loads(k('get','deployment',name,'-o','json'));expected=next(resource for resource in lab.owned if resource['kind']=='Deployment' and resource['name']==name)
    if actual['metadata']['uid']!=expected['uid'] or actual['spec']['template']['metadata']['labels']!=labels(lab.tag,'synthetic') or actual['spec']['replicas'] not in (0,1):raise RuntimeError('Refuse monitoring fault after target UID/owner drift')
    patch=[{'op':'test','path':'/metadata/uid','value':expected['uid']},{'op':'test','path':'/metadata/resourceVersion','value':actual['metadata']['resourceVersion']},
        {'op':'test','path':'/spec/replicas','value':actual['spec']['replicas']},{'op':'replace','path':'/spec/replicas','value':replicas}]
    k('patch','deployment',name,'--type=json','--patch',json.dumps(patch))
    return {'deployment':name,'uid':expected['uid'],'from':actual['spec']['replicas'],'to':replicas,'scope':'OWNED_SYNTHETIC_METRICS_TARGET_ONLY'}


def alert_drill(lab,prom,am,receiver,probe,control,receiver_token):
    events=[];health=[];headers={'Authorization':'Bearer '+receiver_token};start=time.time();lab.result['synthetic_alert_drill']={'events':events,'independent_kafka_health':health}
    def alerts(state):
        kafka_health(probe,control,health)
        payload=http_json(prom,'/api/v1/alerts')
        if any(alert['labels'].get('alertname')!='KafkaQaSyntheticTargetDown' and alert['labels'].get('severity')=='critical' for alert in owned_alerts(payload,lab.tag,'firing')):raise UnsafeHealth('Unexpected critical monitoring/Kafka alert during synthetic drill')
        return [alert for alert in owned_alerts(payload,lab.tag,state) if alert['labels'].get('alertname')=='KafkaQaSyntheticTargetDown']
    def received(state,after):
        kafka_health(probe,control,health)
        return [entry for entry in receipt_state(http_json(receiver,'/receipts',headers=headers),lab.tag,state) if entry['received_at_seconds']>=after]
    def active_alertmanager():
        kafka_health(probe,control,health)
        return [alert for alert in http_json(am,'/api/v2/alerts') if alert['labels'].get('qa_owner')==lab.tag and alert['labels'].get('alertname')=='KafkaQaSyntheticTargetDown' and alert.get('status',{}).get('state')=='active']
    try:
        events.append(scale_target(lab,0));pending=wait_for(lambda:alerts('pending'),'actual synthetic pending alert',seconds=120);events.append({'state':'pending','observed_at':time.time(),'alerts':pending})
        firing=wait_for(lambda:alerts('firing'),'actual synthetic firing alert',seconds=120);events.append({'state':'firing','observed_at':time.time(),'alerts':firing})
        active=wait_for(active_alertmanager,'actual Alertmanager active synthetic alert',seconds=90)
        events.append({'alertmanager_active':active})
        notifications=wait_for(lambda:received('firing',start),'authenticated local firing notification',seconds=90);events.append({'firing_notifications':notifications})
    finally:
        restored=time.time();events.append(scale_target(lab,1));k('rollout','status','deployment/'+lab.tag+'-synthetic','--timeout=240s',timeout=250)
    wait_for(lambda:not alerts('firing') and not alerts('pending'),'synthetic alert returns inactive',seconds=120)
    resolved=wait_for(lambda:received('resolved',restored),'authenticated local resolved notification',seconds=120);events.append({'state':'resolved','notifications':resolved,'observed_at':time.time()})
    lab.result['checks']['actual_pending_firing_alertmanager_delivery_resolved_and_target_restore']='PASS'
    lab.result['synthetic_alert_drill']['scope']='Authenticated local receiver, no human paging; Kafka Admin full-ISR/quorum checked during polling; no broker/controller stopped'


def grafana_checks(lab,base,password,metadata):
    credential='Basic '+base64.b64encode(('qa-admin:'+password).encode()).decode();headers={'Authorization':credential}
    denied=http_json(base,'/api/user',expected=401)
    user=http_json(base,'/api/user',headers=headers)
    if user.get('login')!='qa-admin':raise RuntimeError('Grafana local authenticated identity mismatch')
    health=http_json(base,'/api/health')
    if health.get('version')!=GRAFANA or health.get('database')!='ok':raise RuntimeError('Grafana version/database health mismatch')
    datasource=wait_for(lambda:http_json(base,'/api/datasources/uid/'+metadata['datasource_uid'],headers=headers),'Grafana provisioned datasource',seconds=60)
    if datasource.get('url')!=metadata['datasource']['datasources'][0]['url'] or not (datasource.get('readOnly') is True or datasource.get('editable') is False):raise RuntimeError('Actual Grafana datasource is not the expected readonly provisioned source')
    source_health=http_json(base,'/api/datasources/uid/'+metadata['datasource_uid']+'/health',headers=headers)
    if source_health.get('status','').upper()!='OK':raise RuntimeError('Actual Grafana datasource health failed')
    dashboard=http_json(base,'/api/dashboards/uid/'+metadata['dashboard_uid'],headers=headers)
    if dashboard.get('dashboard',{}).get('uid')!=metadata['dashboard_uid'] or dashboard.get('meta',{}).get('provisioned') is not True:raise RuntimeError('Expected actual provisioned dashboard missing')
    panel=next(panel for panel in dashboard['dashboard']['panels'] if panel['title']=='Produce p99 per broker')
    if panel['fieldConfig']['defaults']['unit']!='ms' or any('histogram_quantile' in target['expr'] or 'avg(' in target['expr'] for target in panel['targets']):raise RuntimeError('Grafana p99 gauge units/aggregation incorrect')
    common={'datasource':{'type':'prometheus','uid':metadata['datasource_uid']},'instant':True,'range':False,'intervalMs':1000,'maxDataPoints':10}
    request={'from':str(int((time.time()-60)*1000)),'to':str(int(time.time()*1000)),'queries':[
        {**common,'refId':'A','expr':'sum(up{qa_owner="'+lab.tag+'",qa_kind="broker"})'},
        {**common,'refId':'B','expr':'qa:produce_p99_ms:per_broker{qa_owner="'+lab.tag+'"}'}]}
    queried=http_json(base,'/api/ds/query',body=request,headers=headers)
    counts=grafana_number(queried,'A');latencies=grafana_number(queried,'B')
    if any(value!=3 for value in counts) or len(latencies)!=3 or any(value<0 for value in latencies):raise RuntimeError('Actual Grafana backend frames do not show three healthy broker/p99 series')
    return {'unauthenticated_api_status':401,'authenticated_login':user['login'],'health':health,'datasource_health':source_health,'datasource_uid':metadata['datasource_uid'],
        'dashboard_uid':metadata['dashboard_uid'],'provisioned':True,'p99_panel_unit':'ms','backend_broker_count_values':counts,'backend_per_broker_p99_ms':latencies,
        'scope':'Live provisioned API/dataframe validation; local auth, not production SSO or independent visual review'}


def main():
    lab=MonitoringLab('036',LIMITS);phase='isolated_persistent_kafka_monitoring_preflight';error=None
    try:
        lab.prepare()
        # This entry point also bootstraps the changed-chapter matrix.
        from monitoring_crds import main as install_monitoring_crds
        install_monitoring_crds()
        pods=json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'];baseline=broker_snapshot(pods)
        images={immutable_kafka_image(next(container['imageID'] for container in pod['status']['containerStatuses'] if container['name']=='kafka')) for pod in pods}
        if len(images)!=1:raise RuntimeError('Kafka client/broker immutable image identity differs')
        lab.image=images.pop();lab.result['client_image']=lab.image
        kafka=json.loads(k('get','kafka',CLUSTER,'-o','json'))
        if kafka.get('status',{}).get('observedGeneration')!=kafka['metadata']['generation']:raise RuntimeError('Kafka Ready state is from a stale generation')
        storage=lab.inventory('observability-broker-storage');lab.result['persistent_storage']=storage
        lab.result['filesystem_headroom']={entry['pod']:filesystem_headroom(lab.read('df-'+entry['pod'],'exec',entry['pod'],'-c','kafka','--','df','-Pk',entry['mount'])) for entry in storage}
        nodes=json.loads(lab.read('node-budgets','get','nodes','-o','json'))
        for node in nodes['items']:
            conditions={entry['type']:entry['status'] for entry in node['status']['conditions']}
            if any(conditions.get(name)!='False' for name in ('DiskPressure','MemoryPressure','PIDPressure')):raise RuntimeError('Node pressure prevents monitoring lab')
        version=json.loads(k('version','-o','json'))['serverVersion'];minor=int(version['minor'].rstrip('+'))
        if int(version['major'])!=1 or minor<25:raise RuntimeError('Monitoring CRD CEL needs supported Kubernetes version')
        lab.result['kubernetes_server']=version;lab.result['fixture_sha256']=hashlib.sha256((ROOT/'kafka/qa/runtime/strimzi-three-node-observability-ch036.yaml').read_bytes()).hexdigest()
        lab.result['monitoring_versions']={'operator':OPERATOR,'prometheus':PROMETHEUS,'alertmanager':ALERTMANAGER,'grafana':GRAFANA}
        lab.result['checks'][phase]='PASS';phase='owned_namespaces_and_scoped_identities'
        lab.create_namespace();lab.result['pod_security_negative_admission']=restricted_admission(lab)
        bootstrap=bootstrap_from_status(kafka);topic=lab.topic('telemetry-canary');group=lab.tag+'-canary-group';username=lab.tag+'-client'
        identity=tls_user(username,topic,group);identity['spec']['authentication']={'type':'scram-sha-512'};lab.apply(identity)
        lab.result['client_identity']=ready_identity(lab,username,'client-identity-metadata')
        probe_user=lab.tag+'-probe'
        lab.apply({'apiVersion':'kafka.strimzi.io/v1beta2','kind':'KafkaUser','metadata':{'name':probe_user,'labels':{'strimzi.io/cluster':CLUSTER}},
            'spec':{'authentication':{'type':'scram-sha-512'},'authorization':{'type':'simple','acls':[
                {'resource':{'type':'topic','name':topic,'patternType':'literal'},'operations':['Describe'],'host':'*'},
                {'resource':{'type':'cluster'},'operations':['Describe'],'host':'*'}]}}})
        lab.result['readonly_probe_identity']=ready_identity(lab,probe_user,'probe-identity-metadata')
        lab.client_service_account=lab.tag+'-client-sa';lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.identity_secret=username;lab.identity_items=['password']
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        lab.result['client_rbac']=rbac_denials(lab.client_service_account)
        password,control,receiver_token=secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(32)
        basic='Basic '+base64.b64encode(('qa-admin:'+password).encode()).decode();lab.private_values=(password,control,receiver_token,basic,'Bearer '+receiver_token)
        lab.result['checks'][phase]='PASS';phase='pinned_operator_prometheus_alertmanager_grafana_and_rule_tools'
        deferred,grafana_metadata=monitoring_setup(lab,password,receiver_token)
        deploy_servers(lab,bootstrap,username,topic,group,control,probe_user)
        lab.result['monitoring_rbac']=[rbac(lab,lab.tag+'-prom-sa',NS,'pods','yes'),rbac(lab,lab.tag+'-prom-sa',NS,'secrets','no'),
            rbac(lab,lab.tag+'-prom-sa',lab.monitor_ns,'secrets','no'),rbac(lab,lab.tag+'-operator-sa',NS,'secrets','no'),rbac(lab,lab.tag+'-operator-sa',lab.monitor_ns,'secrets','yes')]
        lab.result['checks'][phase]='PASS';phase='actual_discovery_canary_metrics_and_source_correctness'
        with contextlib.ExitStack() as stack:
            prom=stack.enter_context(lab.forward(lab.tag+'-prom',9090));am=stack.enter_context(lab.forward(lab.tag+'-am',9093))
            receiver=stack.enter_context(lab.forward(lab.tag+'-receiver',8080));grafana=stack.enter_context(lab.forward(lab.tag+'-grafana',3000))
            probe=stack.enter_context(lab.forward(lab.tag+'-quorum-probe',8080,NS))
            discovered=wait_for(lambda:targets(http_json(prom,'/api/v1/targets?state=active'),lab.tag,pods),'all six owned fresh monitoring targets',seconds=150)
            lab.result['target_discovery_before']=discovered;lab.record('targets-before',discovered)
            if http_json(prom,'/api/v1/status/buildinfo')['data']['version']!=PROMETHEUS:raise RuntimeError('Actual Prometheus binary version mismatch')
            am_version=http_json(am,'/api/v2/status')['versionInfo']['version']
            if am_version!=ALERTMANAGER:raise RuntimeError('Actual Alertmanager binary version mismatch')
            http_json(receiver,'/receipts',expected=403);http_json(receiver,'/receipts',headers={'Authorization':'Bearer '+receiver_token})
            if query(prom,'qa_client_group_lag{qa_owner="'+lab.tag+'"}',allow_empty=True):raise RuntimeError('Unverified client lag was incorrectly exported as a known value')
            with lab.forward(lab.tag+'-synthetic',8080,NS) as target:
                http_json(target,'/exercise',body={},expected=403);http_json(target,'/proof',expected=404)
                proof=http_json(target,'/exercise',body={},headers={'X-QA-Token':control},timeout=180)
                if proof['produced']!=12 or proof['processed']!=12 or proof['lag']!=0 or proof['committed_offsets']!={'0':4,'1':4,'2':4}:raise RuntimeError('Independent actual Kafka canary proof invalid')
                lab.result['actual_client_canary']=proof
            health=[];lab.result['independent_health_baseline']=kafka_health(probe,control,health)
            measurements=wait_for(lambda:compare_metrics(lab,prom,proof),'Prometheus source metrics match actual canary and Kafka Admin',seconds=90)
            lab.result['prometheus_source_validation']=measurements;lab.record('source-validation',measurements)
            first=sorted(pods,key=lambda pod:pod['metadata']['name'])[0];podname=first['metadata']['name']
            if first['metadata']['labels'].get('strimzi.io/pod-name')!=podname:raise RuntimeError('Unique actual broker metrics selector unavailable')
            lab.apply(service(lab.tag,'direct-metrics',{'strimzi.io/pod-name':podname},9404))
            with lab.forward(lab.tag+'-direct-metrics',9404,NS) as direct:
                text=http_text(direct,'/metrics');selected=[line for line in text.splitlines() if line.startswith(('qa_','jvm_gc_collection_seconds_'))];raw=metrics_map(selected)
                types={line.split()[2]:line.split()[3] for line in text.splitlines() if line.startswith('# TYPE ')}
                if types.get('qa_request_ms')!='gauge' or types.get('qa_request_events_total',types.get('qa_request_events'))!='counter' or metric(raw,'qa_raft_current_leader')!=proof['leader_id'] or metric(raw,'qa_under_min_isr_partitions')!=0:raise RuntimeError('Actual exporter types/source comparison failed')
                lab.result['direct_exporter_validation']={'broker':podname,'pod_uid':first['metadata']['uid'],'request_percentiles_type':'gauge','request_events_type':'counter','selected_raw_series':selected}
                lab.record('direct-exporter',lab.result['direct_exporter_validation'])
            lab.result['checks'][phase]='PASS';phase='actual_recording_rules_grafana_and_monitoring_storage'
            for manifest in deferred:lab.mon_apply(manifest)
            recording=wait_for(lambda:query(prom,'qa:under_min_isr:max{qa_owner="'+lab.tag+'"}'),'actual recording rule output',seconds=60)
            if len(recording)!=3 or any(row['value']!=0 for row in recording):raise RuntimeError('Actual recording rule does not preserve healthy per-broker source values')
            wait_for(lambda:len(query(prom,'qa:produce_p99_ms:per_broker{qa_owner="'+lab.tag+'"}'))==3,'actual per-broker p99 gauge recording',seconds=60)
            lab.result['recording_rules']=recording;lab.result['grafana']=grafana_checks(lab,grafana,password,grafana_metadata)
            prom_pods=json.loads(lab.mk('get','pods','-l','prometheus='+lab.tag+'-prom','-o','json'))['items']
            if len(prom_pods)!=1:raise RuntimeError('Expected one bounded Prometheus replica')
            pod=prom_pods[0];claims=[volume['persistentVolumeClaim']['claimName'] for volume in pod['spec']['volumes'] if 'persistentVolumeClaim' in volume]
            if len(claims)!=1:raise RuntimeError('Prometheus must use exactly one persistent TSDB claim')
            claim=json.loads(lab.mk('get','pvc',claims[0],'-o','json'));pv=json.loads(k('get','pv',claim['spec']['volumeName'],'-o','json'))
            lab.result['monitoring_persistent_storage']=monitoring_pvc(claim,pv,pod,lab.monitor_ns)
            flags=http_json(prom,'/api/v1/status/flags')['data']
            if flags.get('storage.tsdb.retention.time')!='1h' or flags.get('storage.tsdb.retention.size')!='100MB' or str(flags.get('web.enable-admin-api')).lower()!='false':raise RuntimeError('Actual Prometheus retention/admin API configuration mismatch')
            lab.result['prometheus_flags']={name:flags[name] for name in ('storage.tsdb.retention.time','storage.tsdb.retention.size','web.enable-admin-api')}
            stats=http_json(prom,'/api/v1/status/tsdb')['data'];series=int(stats['headStats']['numSeries'])
            if not 0<series<10000 or any(row['name'] in ('event_id','payload','password','token','request_id') for row in stats.get('labelValueCountByLabelName',[])):raise RuntimeError('Actual monitoring cardinality/label budget violated')
            lab.result['cardinality_cost']={'active_head_series':series,'maximum_budget':10000,'scrape_interval_seconds':5,'per_endpoint_sample_limit':5000,'remote_write':'NOT_CONFIGURED','retention':'1h /100MB; local-path request not enforced quota'}
            lab.result['monitoring_pod_security']=pod_security_inventory(json.loads(lab.mk('get','pods','-o','json'))['items'],{lab.tag+'-prom-sa',lab.tag+'-operator-sa'})
            lab.result['checks'][phase]='PASS';phase='safe_synthetic_failure_delivery_and_health_preserving_restore'
            if owned_alerts(http_json(prom,'/api/v1/alerts'),lab.tag,'firing'):raise RuntimeError('Pre-existing owned firing alert invalidates synthetic drill')
            before_target=json.loads(k('get','pods','-l','qa_owner='+lab.tag+',qa_kind=synthetic','-o','json'))['items']
            alert_drill(lab,prom,am,receiver,probe,control,receiver_token)
            restored=wait_for(lambda:targets(http_json(prom,'/api/v1/targets?state=active'),lab.tag,pods),'all targets healthy after synthetic restore',seconds=120)
            lab.result['target_discovery_after']=restored
            after_target=[pod for pod in json.loads(k('get','pods','-l','qa_owner='+lab.tag+',qa_kind=synthetic','-o','json'))['items'] if not pod['metadata'].get('deletionTimestamp')]
            if len(before_target)!=1 or len(after_target)!=1 or before_target[0]['metadata']['uid']==after_target[0]['metadata']['uid']:raise RuntimeError('Actual synthetic target Pod replacement not established')
            lab.result['synthetic_target_replacement']={'before_uid':before_target[0]['metadata']['uid'],'after_uid':after_target[0]['metadata']['uid'],'client_counters_after_restart':'EXPECTED_RESET; initial actual delivery proof retained, not persistent application state'}
            lab.result['independent_health_final']=kafka_health(probe,control,health)
            if broker_snapshot(json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items'])!=baseline:raise RuntimeError('Kafka broker identity/restart drift during monitoring-only drill')
            lab.result['checks'][phase]='PASS'
        lab.result['observability_assessment']=ASSESSMENT;lab.result['runtime_scope']='ACTUAL_SCOPED_OPERATOR_PODMONITOR_PROMETHEUS_GRAFANA_QUERIES_AUTHENTICATED_LOCAL_ALERT_PENDING_FIRING_RESOLVED_NOT_ENTERPRISE_CERTIFICATION';lab.result['status']='PASS'
    except Exception as exc:
        error=exc;lab.result['checks'][phase]='FAIL';lab.result['status']='FAIL'
        print('Chapter036 '+phase+' failed: '+type(exc).__name__+'; see sanitized evidence',flush=True)
    return lab.finish(error)


if __name__=='__main__':raise SystemExit(main())
