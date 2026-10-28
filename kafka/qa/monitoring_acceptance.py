"""Monitoring API contracts: absence, source freshness and cardinality are explicit."""
import datetime
import ipaddress
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from runtime_acceptance import NS


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,new_url):return None


def http_json(base,path,body=None,headers=None,expected=200,timeout=20):
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{4,5}',base) or not path.startswith('/') or path.startswith('//'):raise RuntimeError('Unapproved monitoring HTTP destination')
    request=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={**({'Content-Type':'application/json'} if body is not None else {}),**(headers or {})})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(request,timeout=timeout) as response:status=response.status;content=response.read(8*1024*1024+1)
    except urllib.error.HTTPError as error:status=error.code;content=error.read(8*1024*1024+1)
    if status!=expected:raise RuntimeError('Monitoring HTTP status '+str(status)+' at '+path.split('?')[0])
    if len(content)>8*1024*1024:raise RuntimeError('Monitoring HTTP evidence exceeded bounded size')
    try:return json.loads(content)
    except (ValueError,UnicodeError):raise RuntimeError('Monitoring API did not return valid JSON') from None


def wait_for(callback,description,seconds=120):
    deadline=time.monotonic()+seconds;last=None
    while time.monotonic()<deadline:
        try:
            result=callback()
            if result:return result
        except (OSError,RuntimeError,KeyError,ValueError) as error:last=type(error).__name__+': '+str(error)[:250]
        time.sleep(1)
    raise RuntimeError(description+' did not converge within bounded deadline; '+str(last))


def vector(payload,allow_empty=False):
    if payload.get('status')!='success' or payload.get('data',{}).get('resultType')!='vector':raise RuntimeError('Prometheus query failed or returned unsupported result type')
    rows=payload['data']['result']
    if not rows and not allow_empty:raise RuntimeError('Required Prometheus series absent; absence is not healthy zero')
    result=[]
    for row in rows:
        value=float(row['value'][1]);stamp=float(row['value'][0])
        if not math.isfinite(value) or not math.isfinite(stamp) or stamp<0:raise RuntimeError('Invalid Prometheus vector sample')
        if any(not isinstance(key,str) or not isinstance(value,str) for key,value in row['metric'].items()):raise RuntimeError('Invalid Prometheus metric labels')
        result.append({'labels':row['metric'],'value':value,'query_evaluation_timestamp':stamp})
    return result


def query(base,expression,allow_empty=False):
    return vector(http_json(base,'/api/v1/query?'+urllib.parse.urlencode({'query':expression})),allow_empty)


def scalar_series(base,expression,expected=None):
    rows=query(base,expression)
    if len(rows)!=1:raise RuntimeError('Expected exactly one controlled metric series')
    if expected is not None and not math.isclose(rows[0]['value'],expected,abs_tol=1e-9):raise RuntimeError('Prometheus sample differs from independent expected value')
    return rows[0]


def targets(payload,owner,pods,now=None):
    if payload.get('status')!='success':raise RuntimeError('Prometheus targets API failed')
    rows=payload['data']['activeTargets'];expected={'broker':3,'strimzi-operator':1,'synthetic':1,'monitoring-operator':1}
    if len(rows)!=6 or any(row['labels'].get('qa_owner')!=owner for row in rows):raise RuntimeError('Unexpected/unowned Prometheus discovery target')
    by_pod={pod['metadata']['name']:pod for pod in pods};seen=set();counts={};result=[];now=time.time() if now is None else now
    for row in rows:
        role=row['labels'].get('qa_kind');counts[role]=counts.get(role,0)+1
        stamp=datetime.datetime.fromisoformat(row['lastScrape'].replace('Z','+00:00')).timestamp()
        if row['health']!='up' or row.get('lastError') or not -5<=now-stamp<=30 or not 0<float(row['lastScrapeDuration'])<3:raise RuntimeError('Monitoring target is unhealthy/stale/too slow')
        url=urllib.parse.urlparse(row['scrapeUrl'])
        if url.username or url.password or url.scheme!='http' or url.path!='/metrics':raise RuntimeError('Unexpected credential-bearing or unsupported scrape endpoint')
        if role=='broker':
            name=row['labels'].get('broker');pod=by_pod.get(name)
            if pod is None or name in seen or row['labels'].get('namespace')!=NS or ipaddress.ip_address(url.hostname)!=ipaddress.ip_address(pod['status']['podIP']) or url.port!=9404:raise RuntimeError('Prometheus broker target does not match actual Pod identity/IP')
            seen.add(name)
        result.append({'role':role,'labels':row['labels'],'scrape_url':row['scrapeUrl'],'last_scrape':row['lastScrape'],'last_scrape_duration_seconds':row['lastScrapeDuration'],'health':row['health'],'last_error':row.get('lastError','')})
    if counts!=expected or seen!=set(by_pod):raise RuntimeError('Required monitoring target count mismatch')
    return result


def owned_alerts(payload,owner,state=None):
    if payload.get('status')!='success':raise RuntimeError('Prometheus alerts API failed')
    return [alert for alert in payload['data']['alerts'] if alert.get('labels',{}).get('qa_owner')==owner and (state is None or alert.get('state')==state)]


def receipt_state(receipts,owner,state):
    return [entry for entry in receipts if entry.get('status')==state and any(alert.get('status')==state and alert.get('qa_owner')==owner and alert.get('alertname')=='KafkaQaSyntheticTargetDown' for alert in entry.get('alerts',[]))]


def grafana_number(payload,ref='A'):
    result=payload.get('results',{}).get(ref,{})
    if result.get('error'):raise RuntimeError('Grafana datasource query failed')
    values=[]
    for frame in result.get('frames',[]):
        for index,field in enumerate(frame.get('schema',{}).get('fields',[])):
            if field.get('type')=='number':
                for value in frame['data']['values'][index]:
                    if value is None or not isinstance(value,(int,float)) or not math.isfinite(value):raise RuntimeError('Grafana returned missing/nonfinite numeric data')
                    values.append(value)
    if not values:raise RuntimeError('Grafana query supplied no actual numeric data')
    return values


def pod_security_inventory(pods,api_accounts):
    result=[]
    for pod in pods:
        spec=pod['spec'];name=pod['metadata']['name'];account=spec.get('serviceAccountName','default')
        token=any('serviceAccountToken' in source for volume in spec.get('volumes',[]) for source in volume.get('projected',{}).get('sources',[]))
        if account in api_accounts:
            if not token:raise RuntimeError('Required discovery/controller token projection missing')
        elif spec.get('automountServiceAccountToken') is not False or token:raise RuntimeError('Non-API monitoring component has an unexpected API token')
        if any(spec.get(field,False) for field in ('hostNetwork','hostPID','hostIPC')):raise RuntimeError('Unexpected monitoring host namespace access')
        if spec.get('securityContext',{}).get('runAsNonRoot') is not True:raise RuntimeError('Monitoring Pod lacks non-root enforcement')
        for container in spec.get('initContainers',[])+spec['containers']:
            security=container.get('securityContext',{})
            if security.get('privileged') or security.get('allowPrivilegeEscalation') is not False or 'ALL' not in security.get('capabilities',{}).get('drop',[]):raise RuntimeError('Monitoring container security boundary mismatch')
        if any(container.get('restartCount',0)!=0 for container in pod.get('status',{}).get('containerStatuses',[])):raise RuntimeError('Monitoring container unexpectedly restarted')
        result.append({'pod':name,'uid':pod['metadata']['uid'],'service_account':account,'api_token_projected':token,'non_root':True,'host_namespace_access':False})
    if not result:raise RuntimeError('Monitoring Pod security inventory empty')
    return result


def monitoring_pvc(claim,pv,pod,namespace):
    if claim['metadata']['namespace']!=namespace or claim['status']['phase']!='Bound' or claim['spec']['storageClassName']!='standard' or claim['spec']['accessModes']!=['ReadWriteOnce'] or claim['spec'].get('volumeMode','Filesystem')!='Filesystem':raise RuntimeError('Prometheus persistent claim is not correctly bound')
    ref=pv['spec']['claimRef']
    if pv['metadata']['name']!=claim['spec']['volumeName'] or pv['status']['phase']!='Bound' or (ref['namespace'],ref['name'],ref['uid'])!=(namespace,claim['metadata']['name'],claim['metadata']['uid']):raise RuntimeError('Prometheus PV claim UID mismatch')
    volumes=[volume for volume in pod['spec']['volumes'] if volume.get('persistentVolumeClaim',{}).get('claimName')==claim['metadata']['name']]
    if len(volumes)!=1:raise RuntimeError('Prometheus Pod does not mount its actual persistent claim')
    container=next((container for container in pod['spec']['containers'] if container['name']=='prometheus'),None)
    if container is None or not any(mount['name']==volumes[0]['name'] and mount['mountPath']=='/prometheus' and not mount.get('readOnly',False) for mount in container['volumeMounts']):raise RuntimeError('Prometheus TSDB mount mismatch')
    return {'pvc':claim['metadata']['name'],'pvc_uid':claim['metadata']['uid'],'pv':pv['metadata']['name'],'pv_uid':pv['metadata']['uid'],'pod_uid':pod['metadata']['uid'],'node':pod['spec']['nodeName'],'class':'standard','requested_storage':claim['spec']['resources']['requests']['storage'],'scope':'single-host local-path binding; not enforced capacity, CSI/provider latency or failure resilience'}


def http_text(base,path,timeout=20):
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{4,5}',base) or path!='/metrics':raise RuntimeError('Unapproved exporter text destination')
    request=urllib.request.Request(base+path)
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(request,timeout=timeout) as response:
            content=response.read(2*1024*1024+1)
            if response.status!=200 or len(content)>2*1024*1024:raise RuntimeError('Invalid/bounded exporter response')
    except urllib.error.HTTPError as error:raise RuntimeError('Exporter HTTP status '+str(error.code)) from None
    return content.decode('utf-8')
