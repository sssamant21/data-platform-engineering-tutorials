"""Shared secret-safe client Job controls for disposable security acceptance."""
import copy
import json
import re
from pathlib import Path
from run_chapter_021 import StorageLab

SECRET_METADATA_TEMPLATE = ('go-template={{printf "name:%s\\n" .metadata.name}}{{printf "uid:%s\\n" .metadata.uid}}'
    '{{printf "resourceVersion:%s\\n" .metadata.resourceVersion}}{{range $key,$value := .data}}{{printf "key:%s\\n" $key}}{{end}}')


def parse_secret_metadata(text):
    result={'keys':[]}
    for line in text.splitlines():
        field,value=line.split(':',1)
        if field=='key':result['keys'].append(value)
        elif field in ('name','uid','resourceVersion'):result[field]=value
        else:raise RuntimeError('Unexpected Secret metadata field')
    if not all(result.get(field) for field in ('name','uid','resourceVersion')):
        raise RuntimeError('Incomplete Secret metadata inventory')
    return result


def immutable_kafka_image(image_id):
    value=image_id.removeprefix('docker-pullable://')
    if not re.fullmatch(r'quay\.io/strimzi/kafka@sha256:[a-f0-9]{64}',value):
        raise RuntimeError('No verified pullable immutable Kafka image identity')
    return value


def secure_client_job(manifest, service_account, ca_secret, identity_secret, identity_items):
    result=copy.deepcopy(manifest);pod=result['spec']['template']['spec']
    pod['serviceAccountName']=service_account;pod['automountServiceAccountToken']=False
    pod['securityContext']={'runAsNonRoot':True,'runAsUser':1001,'fsGroup':1001,'seccompProfile':{'type':'RuntimeDefault'}}
    pod['volumes'] += [
        {'name':'cluster-trust','secret':{'secretName':ca_secret,'defaultMode':0o440,'items':[{'key':'ca.crt','path':'ca.crt'}]}},
        {'name':'client-identity','secret':{'secretName':identity_secret,'defaultMode':0o440,'items':[{'key':key,'path':key} for key in identity_items]}}]
    container=pod['containers'][0]
    container['volumeMounts'] += [{'name':'cluster-trust','mountPath':'/trust','readOnly':True},
                                {'name':'client-identity','mountPath':'/identity','readOnly':True}]
    container['securityContext']={'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}
    return result


def redact_private_material(text):
    changed=False
    pattern=r'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----.*?(?:-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----|\Z)'
    text,count=re.subn(pattern,'[REDACTED_PRIVATE_KEY]',text,flags=re.DOTALL);changed|=bool(count)
    def yaml_value(match):
        nonlocal changed
        if match[2]=='[REDACTED]':return match[0]
        changed=True;return match[1]+' [REDACTED]'
    text=re.sub(r'(?m)^(\s*user\.(?:key|p12|password):)\s*(\S.*)$',yaml_value,text)
    def json_value(match):
        nonlocal changed
        if match[2]=='[REDACTED]':return match[0]
        changed=True;return match[1]+'[REDACTED]'+match[3]
    text=re.sub(r'("user\.(?:key|p12|password)"\s*:\s*")([^"\r\n]+)(")',json_value,text)
    text,count=re.subn(r'(?m)((?:ssl\.(?:keystore|key)\.password|sasl\.jaas\.config)\s*=\s*)(?!\[hidden\]|\[REDACTED\]|null)(\S[^\r\n]*)',r'\1[REDACTED]',text);changed|=bool(count)
    return text,changed


def sanitize_evidence(directory, chapter):
    root=Path(directory);redacted_any=False
    for path in root.rglob('chapter-'+chapter+'*'):
        if not path.is_file():continue
        text=path.read_text(encoding='utf-8',errors='replace');cleaned,redacted=redact_private_material(text)
        if redacted:path.write_text(cleaned,encoding='utf-8');redacted_any=True
    report=root/f'chapter-{chapter}-runtime.json'
    if report.exists():
        result=json.loads(report.read_text(encoding='utf-8'))
        previous_failure=result.get('checks',{}).get('artifact_private_material_guard')=='FAIL'
        result.setdefault('checks',{})['artifact_private_material_guard']='FAIL' if redacted_any or previous_failure else 'PASS'
        if redacted_any:result['status']='FAIL';result['error']='Private material was redacted from evidence; review required'
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return redacted_any


class SecurityLab(StorageLab):
    def __init__(self, chapter, limitations):
        super().__init__(chapter,limitations)
        self.result['checks']={}
        self.identity_items=['user.p12','user.password']

    def apply(self, manifest):
        if manifest['kind']=='Job':
            manifest=secure_client_job(manifest,self.client_service_account,self.ca_secret,self.identity_secret,self.identity_items)
        return super().apply(manifest)

    def secret_metadata(self, name, label):
        text=self.read(label,'get','secret',name,'-o',SECRET_METADATA_TEMPLATE)
        result=parse_secret_metadata(text)
        if result['name']!=name:raise RuntimeError('Secret metadata name mismatch')
        return result

    def finish(self,error=None):
        safe_error=None
        if error is not None:
            message,redacted=redact_private_material(str(error))
            safe_error=RuntimeError('Private output redacted; security evidence check failed') if redacted else RuntimeError(message)
        super().finish(safe_error)
        sanitize_evidence(self.out,self.chapter)
        self.result=json.loads((self.out/f'chapter-{self.chapter}-runtime.json').read_text(encoding='utf-8'))
        return 0 if self.result['status']=='PASS' else 1


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--chapter',required=True);parser.add_argument('--path',required=True)
    args=parser.parse_args()
    if sanitize_evidence(args.path,args.chapter):
        raise SystemExit('Private outputs were redacted; evidence check failed closed')
