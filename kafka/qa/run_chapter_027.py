#!/usr/bin/env python3
"""Chapter 027 actual TLS/mTLS/ACL checks; no private Secret exports or CA mutation."""
import json
import re
import subprocess
import sys
from runtime_acceptance import k, CTX, NS, CLUSTER
from security_acceptance import SecurityLab, immutable_kafka_image

COMMON=['safe_valid_certificate_metadata_and_identity_binding','bootstrap_and_all_brokers_chain_san_mtls_metadata',
        'untrusted_ca_rejected','wrong_hostname_rejected_with_verification_enabled',
        'missing_client_certificate_authentication_rejected','valid_identity_denied_unapproved_topic',
        'authorized_tls_acks_all_records_offsets_and_resume']
LIMITS=['No expired test-client certificate, on-demand client certificate renewal, live CA renewal/key rotation, trust-overlap outage or revocation test is performed.',
       'The pinned Strimzi 0.47.0 does not provide the later user-level force-renew feature. Automatic renewal is not accelerated by Secret deletion, CA changes or clock manipulation.',
       'A fresh client reload/reconnect uses the same mounted identity; it is not certificate renewal or Secret rotation proof.',
       'Simple ACLs are scoped to owned topics/group plus diagnostic Cluster Describe and IdempotentWrite; host wildcard is not a network restriction, and kind CNI isolation is not certified.',
       'No production TLS migration, PKI expiry alert pipeline, encryption-at-rest policy, cloud identity, multi-zone resilience, independent security signoff or enterprise certification.']


def tls_user(name, topic, group):
    return {'apiVersion':'kafka.strimzi.io/v1beta2','kind':'KafkaUser','metadata':{'name':name,'labels':{'strimzi.io/cluster':CLUSTER}},
        'spec':{'authentication':{'type':'tls'},'authorization':{'type':'simple','acls':[
            {'resource':{'type':'topic','name':topic,'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'},
            {'resource':{'type':'group','name':group,'patternType':'literal'},'operations':['Read','Describe'],'host':'*'},
            {'resource':{'type':'cluster'},'operations':['Describe','IdempotentWrite'],'host':'*'}]}}}


def bootstrap_from_status(cluster):
    declarations=cluster['spec']['kafka']['listeners']
    if not any(l['name']=='tlslab' and l['port']==9094 and l.get('tls') is True and l.get('authentication',{}).get('type')=='tls' for l in declarations):
        raise RuntimeError('Expected separate TLS listener with certificate authentication')
    if not any(l['port']==9092 and l.get('tls') is False for l in declarations):raise RuntimeError('Original lab listener declaration was not preserved')
    if cluster['spec']['kafka'].get('authorization',{}).get('type')!='simple':raise RuntimeError('Simple authorizer must be explicitly enabled')
    listeners=[l for l in cluster['status']['listeners'] if l['name']=='tlslab']
    if len(listeners)!=1:raise RuntimeError('TLS listener status missing')
    bootstrap=listeners[0]['bootstrapServers']
    if not re.fullmatch(r'qa-kafka-ha-kafka-bootstrap(?:\.kafka-qa\.svc(?:\.[a-z0-9.-]+)?)?:9094',bootstrap):
        raise RuntimeError('Unexpected external/incorrect TLS bootstrap')
    return bootstrap


def main():
    lab=SecurityLab('027',LIMITS);error,phase=None,'secure_listener_and_authorizer_inventory'
    try:
        lab.prepare()
        cluster=json.loads(k('get','kafka',CLUSTER,'-o','json'))
        bootstrap=bootstrap_from_status(cluster)
        lab.result['listener_inventory']={'declarations':cluster['spec']['kafka']['listeners'],'tls_bootstrap':bootstrap,
            'authorizer':'simple','plaintext_anonymous_access':'NOT_GRANTED; declaration retained only in separate disposable fixture'}
        pod=json.loads(k('get','pod',lab.pod,'-o','json'));image_id=next(c['imageID'] for c in pod['status']['containerStatuses'] if c['name']=='kafka')
        lab.image=immutable_kafka_image(image_id);lab.result['client_image']=lab.image
        lab.result['checks'][phase]='PASS'
        for crd in ('kafkas.kafka.strimzi.io','kafkausers.kafka.strimzi.io'):
            versions=json.loads(k('get','crd',crd,'-o','json'))['spec']['versions']
            if not any(v['name']=='v1beta2' and v.get('served') for v in versions):raise RuntimeError('Required served CRD API missing')
        phase='scoped_user_and_secret_metadata_only'
        allowed,denied=lab.topic('allowed'),lab.topic('denied')
        username,group=lab.tag+'-client',lab.tag+'-group'
        lab.apply(tls_user(username,allowed,group))
        k('wait',f'kafkauser/{username}','--for=condition=Ready','--timeout=240s',timeout=260)
        lab.identity_secret=username;lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.client_service_account=lab.tag+'-client-sa'
        identity=lab.secret_metadata(username,'client-secret-metadata');ca=lab.secret_metadata(lab.ca_secret,'cluster-ca-secret-metadata')
        if not {'user.p12','user.password','user.crt'}.issubset(identity['keys']) or 'ca.crt' not in ca['keys']:
            raise RuntimeError('Required mounted identity/trust keys absent')
        lab.result['secret_inventory']={'client':identity,'cluster_ca_certificate_only':ca,'exported_private_values':False}
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        lab.result['checks'][phase]='PASS'
        phase='client_service_account_secret_api_denied'
        access=[]
        for verb in ('get','list','watch'):
            command=['kubectl','--context',CTX,'-n',NS,'auth','can-i',verb,'secrets','--as',f'system:serviceaccount:{NS}:{lab.client_service_account}']
            result=subprocess.run(command,capture_output=True,text=True,timeout=20)
            if result.returncode!=1 or result.stdout.strip()!='no':raise RuntimeError('Secret API deny not established; an impersonation error is not proof of denial')
            access.append({'verb':verb,'result':'DENIED','source':'authorized SubjectAccessReview impersonation in disposable kind'})
        lab.result['client_secret_api_access']=access;lab.result['checks'][phase]='PASS'
        stages=[]
        for stage,start in [('initial',0),('reconnect',6)]:
            phase=stage+'_tls_client'
            child=SecurityLab('027',LIMITS)
            child.tag,child.image,child.out,child.owned=lab.tag+'-'+stage,lab.image,lab.out/stage,lab.owned
            child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,lab.identity_secret
            try:child.run_job('TlsAcceptance',[bootstrap,allowed,denied,group,username,stage,str(start)],[stage+'_'+check for check in COMMON])
            finally:lab.result['checks'].update(child.result['checks'])
            stages.append({'stage':stage,'job':child.tag+'-client','observations':child.result['client_observations']})
            lab.result['checks'][phase]='PASS'
        lab.result['stages']=stages
        lab.result['pending_certificate_gates']={'expired_test_client':'NOT_EXECUTED','on_demand_user_certificate_renewal':'NOT_EXECUTED_PINNED_VERSION_GATE',
            'live_ca_renewal_or_key_rotation':'NOT_EXECUTED_NO_SEPARATE_APPROVAL','secret_rotation_proof':'NOT_EXECUTED_RECONNECT_USES_SAME_IDENTITY',
            'revocation_ocsp_crl':'NOT_EXECUTED','production_expiry_alerts':'NOT_TESTED','independent_security_signoff':'PENDING'}
        lab.result['status']='PASS';lab.result['runtime_scope']='ACTUAL_TLS_MTLS_HOSTNAME_AND_SCOPED_ACL_CHECKS_RENEWAL_NOT_EXECUTED'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print('Chapter 027 '+phase+' failed: '+type(exc).__name__+'; details are sanitized in evidence',file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
