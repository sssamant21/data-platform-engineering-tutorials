"""Install only content-pinned monitoring CRDs in the disposable kind cluster."""
import concurrent.futures
import hashlib
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from runtime_acceptance import CTX, ROOT, k

OPERATOR='0.94.2'
PROMETHEUS='3.14.0'
ALERTMANAGER='0.34.0'
GRAFANA='13.3.0'
COMMIT='0db90444c4e6fa5672be5bf7d2b15ca9dd1c5ace'
CRDS={
 'alertmanagerconfigs':'591761d583e6a896afc2828054770bb3655e3ac9',
 'alertmanagers':'a3d95d77e07deb84dd79ac4f097e56748a85abb2',
 'podmonitors':'65b5c43752e43aaab2e199e1412208910225c1ac',
 'probes':'fb66c0195b8a9e808deb714ef7bc8fe95999224a',
 'prometheusagents':'907555966b588b31508d6193db6217cef6914d96',
 'prometheuses':'9a491b67d2262b073522acbb4194134b5fcdf39c',
 'prometheusrules':'66527eaa35950c4cc2723defd0730ded823dd877',
 'scrapeconfigs':'a978f262628444cad099d9a9b815bb240af1a692',
 'servicemonitors':'e9b38f05d3e8a57b1ced6205d3dfb813f7ece7be',
 'thanosrulers':'b45cac8ece9e2a4c45d21501e978c5c50b001486'}


def verify_blob(data,expected):
    actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if actual!=expected:raise RuntimeError('Official CRD content differs from pinned Git blob')
    if not 0<len(data)<2*1024*1024:raise RuntimeError('Unexpected CRD size')
    return hashlib.sha256(data).hexdigest()


def fetch(name):
    if name not in CRDS:raise RuntimeError('Unapproved monitoring CRD name')
    filename='monitoring.coreos.com_'+name+'.yaml'
    url=f'https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/{COMMIT}/example/prometheus-operator-crd/{filename}'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read(2*1024*1024+1)
            return data,{'resource':name+'.monitoring.coreos.com','url':url,'git_blob_sha1':CRDS[name],'sha256':verify_blob(data,CRDS[name])}
        except (urllib.error.URLError,TimeoutError):
            if attempt==2:raise
            time.sleep(2*(attempt+1))
    raise RuntimeError('CRD retrieval failed')


def main():
    current=subprocess.run(['kubectl','config','current-context'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    if current!=CTX:raise RuntimeError('Refuse monitoring installation outside disposable kind context')
    node=json.loads(k('get','node','kafka-qa-control-plane','-o','json'))
    if node['metadata'].get('labels',{}).get('kubernetes.io/hostname')!='kafka-qa-control-plane':raise RuntimeError('Expected disposable kind node')
    observations=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        prepared=dict(zip(CRDS,executor.map(fetch,CRDS)))
    # Validate the whole immutable package before the first cluster mutation.
    with tempfile.TemporaryDirectory(prefix='qa-monitoring-crds-') as folder:
        for name in CRDS:
            data,evidence=prepared[name];path=Path(folder)/(name+'.yaml');path.write_bytes(data)
            k('apply','--server-side','--field-manager=kafka-qa-monitoring-crds','-f',str(path),timeout=90)
            k('wait','crd/'+evidence['resource'],'--for=condition=Established','--timeout=60s',timeout=70)
            installed=json.loads(k('get','crd',evidence['resource'],'-o','json'))
            evidence['uid']=installed['metadata']['uid'];evidence['served_versions']=[v['name'] for v in installed['spec']['versions'] if v['served']]
            if not evidence['served_versions'] or (name in ('prometheuses','alertmanagers','podmonitors','prometheusrules','servicemonitors') and 'v1' not in evidence['served_versions']):raise RuntimeError('Required monitoring CRD API version not served')
            observations.append(evidence)
    out=ROOT/'kafka/qa/evidence';out.mkdir(parents=True,exist_ok=True)
    (out/'chapter-036-monitoring-crds.json').write_text(json.dumps({'operator':OPERATOR,'commit':COMMIT,'crds':observations},indent=2)+'\n')
    print('Installed10 content-pinned monitoring CRDs on disposable kind only')
    return 0


if __name__=='__main__':raise SystemExit(main())
