"""Consumer-specific source bundles and explicitly owned non-broker sink mounts."""
import hashlib
import ipaddress
import json
import re
from runtime_acceptance import ROOT, NS
from performance_lab import PerformanceLab, native_arguments
from java_sources import bundle_java_sources
from performance_acceptance import client_metric


class ConsumerLab(PerformanceLab):
    def source(self,main):
        if main!='ConsumerAcceptance':return super().source(main)
        names=(main,'PerfAcceptance')
        source=bundle_java_sources(main,{name:(ROOT/'kafka/qa/runtime'/(name+'.java')).read_text(encoding='utf-8-sig') for name in names})
        self.result['java_source_bundle_sha256']=hashlib.sha256(source.encode()).hexdigest()
        return self.apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':self.tag+'-source'},'data':{main+'.java':source}})

    def apply(self,manifest):
        claim=getattr(self,'sink_claim',None)
        if manifest['kind']=='Job' and claim:
            if not re.fullmatch(r'ch033-[a-f0-9]{12}-sink',claim) or {'kind':'PersistentVolumeClaim','name':claim} not in self.owned:
                raise RuntimeError('Refuse unowned/non-synthetic sink PVC mount')
            pod=manifest['spec']['template']['spec'];pod['volumes'].append({'name':'owned-sink','persistentVolumeClaim':{'claimName':claim}})
            pod['containers'][0]['volumeMounts'].append({'name':'owned-sink','mountPath':'/sink'})
        return super().apply(manifest)
# Version-specific native fetch profiles and evidence validation.

CONSUMER_FIELDS=(('fetch_min_bytes','fetch.min.bytes'),('fetch_max_wait_ms','fetch.max.wait.ms'),
                 ('partition_fetch_bytes','max.partition.fetch.bytes'),('poll_records','max.poll.records'))


def consumer_arguments(bootstrap,username,trial):
    base=native_arguments(bootstrap,username,trial)[:8]
    if trial.get('partitions')!=6 or trial['target_records_per_second']!=400 or trial.get('compression','none')!='none' or trial.get('linger_ms',0)!=0 or trial.get('batch_size',16384)!=16384 or trial.get('payload_mode','native-random')!='native-random':
        raise RuntimeError('Consumer comparison changed controlled producer/topology settings')
    allowed=((1,16384,65536),(100,500,1000),(65536,1048576),(100,500))
    for (field,_),values in zip(CONSUMER_FIELDS,allowed):
        if type(trial[field]) is not int or trial[field] not in values:raise RuntimeError('Unsupported consumer fetch profile')
    return ['fetch',*base,*[str(trial[field]) for field,_ in CONSUMER_FIELDS]]


def json_observation(lines,name):
    prefix='OBS:'+name+':'
    values=[json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    if len(values)!=1:raise RuntimeError('Missing/ambiguous '+name+' observation')
    return values[0]


def native_fetch_observations(text,trial):
    metrics={name:client_metric(text,'consumer-fetch-manager-metrics',name) for name in ('fetch-size-avg','fetch-latency-avg','fetch-rate','records-consumed-total')}
    if metrics['records-consumed-total']!=trial['records']:raise RuntimeError('Native consumer metric count differs from actual trial target')
    return {'native_client_fetch_metrics':metrics,'scope':'native client fetch metrics; no broker metrics or business processing latency inferred',
            'consumer_latency_percentiles':'NOT_REPORTED_BY_NATIVE_CSV'}


def expected_crash(job,pods,checkpoint_passed):
    if not checkpoint_passed or len(pods)!=1 or not any(c['type']=='Failed' and c['status']=='True' for c in job.get('status',{}).get('conditions',[])):
        raise RuntimeError('Expected checkpoint/process failure not established')
    pod=pods[0]
    if pod['status'].get('phase')!='Failed' or not any(r.get('kind')=='Job' and r.get('uid')==job['metadata']['uid'] and r.get('controller') for r in pod['metadata'].get('ownerReferences',[])):
        raise RuntimeError('Crash Pod is not the owned failed Job')
    client=[c for c in pod['status'].get('containerStatuses',[]) if c['name']=='client']
    if len(client)!=1 or client[0].get('state',{}).get('terminated',{}).get('exitCode')!=23:raise RuntimeError('Unexpected client failure (OOM/auth/other exit is not planned crash proof)')
    return {'job_uid':job['metadata']['uid'],'pod_uid':pod['metadata']['uid'],'exit_code':23,'classification':'EXPECTED_PROCESS_HALT_AFTER_FORCED_SINK_BEFORE_COMMIT'}


def sink_binding(claim,pv,pod,expected_name):
    if claim['metadata']['name']!=expected_name or claim['status']['phase']!='Bound' or claim['spec']['storageClassName']!='standard' or claim['spec'].get('volumeMode','Filesystem')!='Filesystem' or claim['spec']['accessModes']!=['ReadWriteOnce']:
        raise RuntimeError('Owned sink PVC binding/class/mode mismatch')
    ref=pv['spec']['claimRef']
    if pv['metadata']['name']!=claim['spec']['volumeName'] or pv['status']['phase']!='Bound' or (ref['namespace'],ref['name'],ref['uid'])!=(NS,expected_name,claim['metadata']['uid']):raise RuntimeError('Sink PV claim UID mismatch')
    volumes=[v for v in pod['spec']['volumes'] if 'persistentVolumeClaim' in v]
    if len(volumes)!=1 or volumes[0]['name']!='owned-sink' or volumes[0]['persistentVolumeClaim']['claimName']!=expected_name:raise RuntimeError('Actual client Pod did not mount the owned sink claim')
    mounts=pod['spec']['containers'][0]['volumeMounts']
    if not any(m['name']=='owned-sink' and m['mountPath']=='/sink' and not m.get('readOnly',False) for m in mounts):raise RuntimeError('Owned sink mount path/read-write contract not met')
    return {'name':expected_name,'pvc_uid':claim['metadata']['uid'],'pv':pv['metadata']['name'],'pv_uid':pv['metadata']['uid'],'node':pod['spec']['nodeName'],'storage_class':'standard','scope':'single-host local-path, not CSI/zone resilience'}


def group_pod_mapping(assignment,pods):
    by_name={pod['metadata']['name']:pod for pod in pods};mapped=[]
    if len(by_name)!=assignment['member_count']:raise RuntimeError('Pod count differs from observed group members')
    for member in assignment['members']:
        pod=by_name.get(member['client_id'])
        if pod is None or ipaddress.ip_address(member['host'].strip('/[]'))!=ipaddress.ip_address(pod['status']['podIP']):raise RuntimeError('Actual consumer client ID/host does not match the expected Pod')
        mapped.append({'pod':pod['metadata']['name'],'uid':pod['metadata']['uid'],'partitions':member['partitions'],'member_id':member['member_id']})
    if len({item['uid'] for item in mapped})!=len(pods):raise RuntimeError('Duplicate/aliased consumer Pod membership')
    return mapped
