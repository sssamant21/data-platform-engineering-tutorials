"""Owned monitoring namespace, bounded loopback access and secret-safe evidence."""
import contextlib
import hashlib
import json
import re
import socket
import subprocess
import time
from pathlib import Path
from runtime_acceptance import CTX, NS, ROOT, k
from security_acceptance import SecurityLab
from java_sources import bundle_java_sources


def monitoring_namespace(tag):
    if not re.fullmatch(r'ch036-[a-f0-9]{12}',tag):raise RuntimeError('Invalid monitoring owner')
    return tag+'-monitoring'


class MonitoringLab(SecurityLab):
    def __init__(self,chapter,limitations):
        super().__init__(chapter,limitations)
        self.namespace_uid=None;self.monitor_ns=monitoring_namespace(self.tag);self.mon_owned=[];self.result['monitoring_resources']=self.mon_owned;self.forwards=[]

    def source(self,main):
        if main!='ObservabilityTarget':raise RuntimeError('Unapproved monitoring Java source')
        source=bundle_java_sources(main,{name:(ROOT/'kafka/qa/runtime'/(name+'.java')).read_text(encoding='utf-8-sig') for name in (main,'ConsumerAcceptance','PerfAcceptance')})
        self.source_text=source;self.result['java_source_bundle_sha256']=hashlib.sha256(source.encode()).hexdigest()
        return self.apply({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':self.tag+'-source'},'immutable':True,'data':{main+'.java':source}})

    def create_namespace(self):
        if not self.safe:raise RuntimeError('Disposable cluster preflight required')
        if k('get','namespace',self.monitor_ns,'--ignore-not-found','-o','json').strip():raise RuntimeError('Refuse adopting an existing monitoring namespace')
        manifest={'apiVersion':'v1','kind':'Namespace','metadata':{'name':self.monitor_ns,'labels':{'qa.kafka/test-owner':self.tag,'pod-security.kubernetes.io/enforce':'restricted','pod-security.kubernetes.io/enforce-version':'latest'}}}
        k('create','-f','-',data=json.dumps(manifest))
        self.namespace_uid=json.loads(k('get','namespace',self.monitor_ns,'-o','json'))['metadata']['uid']
        self.result['monitoring_namespace']={'name':self.monitor_ns,'uid':self.namespace_uid,'pod_security_enforce':'restricted'}

    def apply(self,manifest):
        if not self.safe:raise RuntimeError('Disposable cluster preflight required')
        if not manifest['metadata']['name'].startswith(self.tag+'-') or manifest['kind']=='Namespace' or manifest['metadata'].get('namespace',NS)!=NS:raise RuntimeError('Refuse unowned runtime manifest')
        name=super().apply(manifest)
        self.owned[-1]['uid']=k('get',manifest['kind'],name,'-o','jsonpath={.metadata.uid}').strip()
        return name

    def mk(self,*args,data=None,timeout=90):
        if self.monitor_ns!=monitoring_namespace(self.tag):raise RuntimeError('Refuse unowned monitoring namespace')
        result=subprocess.run(['kubectl','--context',CTX,'-n',self.monitor_ns,*args],input=data,capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise RuntimeError('Owned monitoring API '+args[0]+': '+result.stderr[-2500:])
        return result.stdout

    def mon_apply(self,manifest):
        metadata=manifest['metadata'];name=metadata['name']
        if not name.startswith(self.tag+'-') or metadata.get('namespace',self.monitor_ns)!=self.monitor_ns or manifest['kind'] in ('Namespace','ClusterRole','ClusterRoleBinding','CustomResourceDefinition'):
            raise RuntimeError('Refuse unowned/cluster-scoped monitoring manifest')
        if not self.safe or self.namespace_uid is None:raise RuntimeError('Monitoring namespace ownership not established')
        namespace=json.loads(k('get','namespace',self.monitor_ns,'-o','json'))
        if namespace['metadata']['uid']!=self.namespace_uid or namespace['metadata'].get('labels',{}).get('qa.kafka/test-owner')!=self.tag:raise RuntimeError('Monitoring namespace UID/owner drift')
        metadata['namespace']=self.monitor_ns;metadata.setdefault('labels',{})['qa.kafka/test-owner']=self.tag
        existing=next((item for item in self.mon_owned if item['kind']==manifest['kind'] and item['name']==name),None)
        actual=self.mk('get',manifest['kind'],name,'--ignore-not-found','-o','jsonpath={.metadata.uid}').strip()
        if actual and (existing is None or actual!=existing.get('uid')):raise RuntimeError('Refuse monitoring object adoption or UID drift')
        entry=existing or {'kind':manifest['kind'],'name':name,'namespace':self.monitor_ns}
        if existing is None:self.mon_owned.append(entry)
        self.mk('apply','-f','-',data=json.dumps(manifest))
        entry['uid']=self.mk('get',manifest['kind'],name,'-o','jsonpath={.metadata.uid}').strip()
        return name

    def mon_read(self,label,*args,timeout=40):
        text=self.mk(*args,timeout=timeout);self.out.mkdir(parents=True,exist_ok=True)
        (self.out/f'chapter-036-{label}.txt').write_text(text,encoding='utf-8');return text

    def record(self,label,value):
        self.out.mkdir(parents=True,exist_ok=True);(self.out/f'chapter-036-{label}.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        return value

    @contextlib.contextmanager
    def forward(self,name,port,namespace=None):
        namespace=namespace or self.monitor_ns
        if namespace not in (NS,self.monitor_ns) or not name.startswith(self.tag+'-') or port not in (8080,9090,9093,3000,9404):raise RuntimeError('Unapproved monitoring forward target')
        call=self.mk if namespace==self.monitor_ns else k
        service=json.loads(call('get','service',name,'-o','json'))
        if service['metadata']['name']!=name or service['spec'].get('type','ClusterIP')!='ClusterIP':raise RuntimeError('Expected owned internal monitoring Service')
        owned=self.mon_owned if namespace==self.monitor_ns else self.owned
        if not any(r['kind']=='Service' and r['name']==name and r.get('uid')==service['metadata']['uid'] for r in owned):raise RuntimeError('Service forward ownership/UID guard failed')
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));local=listener.getsockname()[1]
        self.out.mkdir(parents=True,exist_ok=True)
        with (self.out/f'chapter-036-forward-{name}.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(['kubectl','--context',CTX,'-n',namespace,'port-forward','--address=127.0.0.1','service/'+name,f'{local}:{port}'],stdout=log,stderr=subprocess.STDOUT)
            self.forwards.append(process)
            try:
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    if process.poll() is not None:raise RuntimeError('Owned monitoring port-forward exited before readiness')
                    try:
                        with socket.create_connection(('127.0.0.1',local),timeout=.2):
                            log.flush()
                            if ('Forwarding from 127.0.0.1:'+str(local)+' ->') in (self.out/f'chapter-036-forward-{name}.log').read_text(encoding='utf-8'):break
                    except OSError:time.sleep(.2)
                else:raise RuntimeError('Owned monitoring port-forward readiness timeout')
                yield 'http://127.0.0.1:'+str(local)
            finally:
                process.terminate()
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                self.forwards.remove(process)

    def finish(self,error=None):
        for process in list(self.forwards):
            if process.poll() is None:process.terminate()
        if self.safe:
            for suffix in ('synthetic','quorum-probe'):
                try:self.read(suffix+'-log','logs','deployment/'+self.tag+'-'+suffix,'--all-containers','--tail=200')
                except (OSError,RuntimeError,subprocess.SubprocessError) as exc:self.result.setdefault('diagnostic_errors',[]).append(str(exc))
        if self.safe and self.namespace_uid is not None:
            for label,args in [('monitoring-pods',('get','pods,deployments,statefulsets,pvc,prometheus,alertmanager,podmonitor,prometheusrule','-o','wide')),('monitoring-events',('get','events','--sort-by=.metadata.creationTimestamp'))]:
                try:self.mon_read(label,*args)
                except (OSError,RuntimeError,subprocess.SubprocessError) as exc:self.result.setdefault('diagnostic_errors',[]).append(str(exc))
            for suffix in ('operator','receiver','grafana'):
                try:self.mon_read(suffix+'-log','logs','deployment/'+self.tag+'-'+suffix,'--all-containers','--tail=200')
                except (OSError,RuntimeError,subprocess.SubprocessError) as exc:self.result.setdefault('diagnostic_errors',[]).append(str(exc))
            for entry in reversed(self.mon_owned):
                if entry['kind'] not in ('Prometheus','Alertmanager'):continue
                try:
                    current=json.loads(self.mk('get',entry['kind'],entry['name'],'-o','json'))
                    if current['metadata']['uid']!=entry.get('uid'):raise RuntimeError('Refuse cleanup after monitoring CR UID drift')
                    self.mk('delete',entry['kind'],entry['name'],'--wait=true','--timeout=90s',timeout=100)
                except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
                    self.result.setdefault('cleanup_errors',[]).append(str(exc));self.result['status']='FAIL'
            # Only the uniquely created namespace is removed; finalizers are never bypassed.
            try:
                namespace=json.loads(k('get','namespace',self.monitor_ns,'-o','json'))
                if namespace['metadata']['uid']!=self.namespace_uid:raise RuntimeError('Refuse namespace cleanup after UID drift')
                k('delete','namespace',self.monitor_ns,'--ignore-not-found','--wait=true','--timeout=120s',timeout=130)
            except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
                self.result.setdefault('cleanup_errors',[]).append(str(exc));self.result['status']='FAIL'
        if self.safe:
            self.result['all_registered_resources']=[dict(resource) for resource in self.owned]
            safe=[]
            for resource in self.owned:
                try:
                    uid=k('get',resource['kind'],resource['name'],'--ignore-not-found','-o','jsonpath={.metadata.uid}').strip()
                    if uid and uid!=resource.get('uid'):raise RuntimeError('Refuse cleanup after runtime resource UID drift: '+resource['name'])
                    safe.append(resource)
                except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
                    self.result.setdefault('cleanup_errors',[]).append(str(exc));self.result['status']='FAIL'
            self.owned[:]=safe
        return super().finish(error)
