#!/usr/bin/env python3
"""Actual SASL_SSL/SCRAM and supported disposable password-reference rotation."""
import base64
import json
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import k, CTX, NS, CLUSTER
from security_acceptance import SecurityLab, immutable_kafka_image

CHECKS=['sasl_ssl_all_advertised_brokers_hostname_verified','wrong_password_classified_sasl_failure',
        'wrong_username_classified_sasl_failure','wrong_ca_classified_tls_failure_before_sasl',
        'authenticated_identity_unauthorized_topic_denied','deterministic_records_acks_all_consumption_commits_and_resume']
LIMITS=['OAuth/OIDC/JWKS, token refresh, issuer/audience/expiry rejection and federated workload identity are NOT_EXECUTED: no reviewed supported external IdP/plugin is supplied.',
       'Password replacement is coordinated between independent Jobs; no continuous production traffic, seamless overlap or zero downtime is claimed. The measured interval is a harness completion interval, not a production recovery SLO.',
       'Only synthetic password source Secrets and the owned KafkaUser reference change. No broker or operator-managed Secret is edited or deleted.',
       'ServiceAccount Secret API denial does not prove admission restrictions, encryption at rest, CNI isolation or absence of privileged node administrators.',
       'Production client migration, authentication alert routing, independent IAM review and enterprise certification remain pending.']


def scram_user(name,topic,group,source):
    return {'apiVersion':'kafka.strimzi.io/v1beta2','kind':'KafkaUser','metadata':{'name':name,'labels':{'strimzi.io/cluster':CLUSTER}},
        'spec':{'authentication':{'type':'scram-sha-512','password':{'valueFrom':{'secretKeyRef':{'name':source,'key':'password'}}}},
        'authorization':{'type':'simple','acls':[
            {'resource':{'type':'topic','name':topic,'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'},
            {'resource':{'type':'group','name':group,'patternType':'literal'},'operations':['Read','Describe'],'host':'*'},
            {'resource':{'type':'cluster'},'operations':['Describe','IdempotentWrite'],'host':'*'}]}}}


def bootstrap_from_status(cluster):
    listeners=cluster['spec']['kafka']['listeners']
    if not any(l['name']=='scramlab' and l['port']==9095 and l.get('tls') is True and l.get('authentication',{}).get('type')=='scram-sha-512' for l in listeners):
        raise RuntimeError('Expected TLS/SCRAM-SHA-512 listener')
    if not any(l['name']=='tlslab' and l['port']==9094 and l.get('tls') is True and l.get('authentication',{}).get('type')=='tls' for l in listeners):
        raise RuntimeError('Parallel mTLS listener was not retained')
    if cluster['spec']['kafka'].get('authorization',{}).get('type')!='simple':raise RuntimeError('Expected simple authorizer')
    status=[l for l in cluster['status']['listeners'] if l['name']=='scramlab']
    if len(status)!=1 or not re.fullmatch(r'qa-kafka-ha-kafka-bootstrap(?:\.kafka-qa\.svc(?:\.[a-z0-9.-]+)?)?:9095',status[0]['bootstrapServers']):
        raise RuntimeError('Internal SASL_SSL bootstrap status missing or unexpected')
    return status[0]['bootstrapServers']


def ready_user(name, expected_source):
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        user=json.loads(k('get','kafkauser',name,'-o','json'))
        if user['spec']['authentication']['password']['valueFrom']['secretKeyRef']['name']!=expected_source:
            raise RuntimeError('KafkaUser desired credential source drift')
        status=user.get('status',{})
        if status.get('observedGeneration')==user['metadata']['generation'] and any(c['type']=='Ready' and c['status']=='True' for c in status.get('conditions',[])):
            if status.get('username')!=name:raise RuntimeError('Reconciled SCRAM principal mismatch')
            return {'uid':user['metadata']['uid'],'generation':user['metadata']['generation'],'observed_generation':status['observedGeneration'],'username':status['username']}
        time.sleep(3)
    raise RuntimeError('KafkaUser did not reconcile current credential generation within deadline')


def principal_denial(log,username,topic):
    # Native broker authorizer output binds the authenticated principal to the exact denied resource.
    return [line for line in log.splitlines() if re.search(r'Principal = User:'+re.escape(username)+r' is Denied operation = (?:DESCRIBE|WRITE)\b',line)
            and ('on resource = Topic:LITERAL:'+topic+' ') in line]


def source_secret(lab,name,password):
    if not name.startswith(lab.tag+'-'):raise RuntimeError('Source Secret outside owned resource prefix')
    lab.owned.append({'kind':'Secret','name':name})
    manifest={'apiVersion':'v1','kind':'Secret','metadata':{'name':name,'labels':{'qa.kafka/chapter':'028'}},'type':'Opaque','immutable':True,
              'data':{'password':base64.b64encode(password.encode()).decode()}}
    try:k('create','-f','-',data=json.dumps(manifest))
    except (RuntimeError,subprocess.SubprocessError):raise RuntimeError('Disposable source Secret creation failed; payload withheld') from None


def main():
    lab=SecurityLab('028',LIMITS);error,phase=None,'secure_listener_inventory'
    lab.private_values=(secrets.token_urlsafe(48),secrets.token_urlsafe(48))
    try:
        lab.prepare();cluster=json.loads(k('get','kafka',CLUSTER,'-o','json'));bootstrap=bootstrap_from_status(cluster)
        pod=json.loads(k('get','pod',lab.pod,'-o','json'));lab.image=immutable_kafka_image(next(c['imageID'] for c in pod['status']['containerStatuses'] if c['name']=='kafka'))
        lab.result['client_image']=lab.image;lab.result['listener_inventory']={'declarations':cluster['spec']['kafka']['listeners'],'sasl_bootstrap':bootstrap,'authorizer':'simple'}
        for crd in ('kafkas.kafka.strimzi.io','kafkausers.kafka.strimzi.io'):
            if not any(v['name']=='v1beta2' and v.get('served') for v in json.loads(k('get','crd',crd,'-o','json'))['spec']['versions']):raise RuntimeError('Required served API absent')
        lab.result['checks'][phase]='PASS';phase='owned_scram_identity_and_secret_api_boundary'
        allowed,denied=lab.topic('allowed'),lab.topic('denied');username,group=lab.tag+'-client',lab.tag+'-group'
        old_source,new_source=lab.tag+'-password-v1',lab.tag+'-password-v2'
        source_secret(lab,old_source,lab.private_values[0]);source_secret(lab,new_source,lab.private_values[1])
        user=scram_user(username,allowed,group,old_source);lab.apply(user);initial=ready_user(username,old_source)
        before=lab.secret_metadata(username,'initial-user-secret-metadata')
        if 'password' not in before['keys']:raise RuntimeError('Generated password key missing')
        lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.identity_secret=username;lab.identity_items=['password'];lab.client_service_account=lab.tag+'-client-sa'
        ca=lab.secret_metadata(lab.ca_secret,'cluster-ca-metadata')
        if 'ca.crt' not in ca['keys']:raise RuntimeError('Cluster CA missing')
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        for verb in ('get','list','watch'):
            result=subprocess.run(['kubectl','--context',CTX,'-n',NS,'auth','can-i',verb,'secrets','--as',f'system:serviceaccount:{NS}:{lab.client_service_account}'],capture_output=True,text=True,timeout=20)
            if result.returncode!=1 or result.stdout.strip()!='no':raise RuntimeError('Secret API denial unproven; impersonation errors are not denial evidence')
        lab.result['identity_inventory']={'initial_user':initial,'initial_secret':before,'cluster_ca':ca,'private_values_exported':False,'secret_api_get_list_watch':'DENIED'}
        lab.result['checks'][phase]='PASS';stages=[]
        def run(stage,start,identity=None):
            child=SecurityLab('028',LIMITS);child.tag,child.image,child.out,child.owned=lab.tag+'-'+stage,lab.image,lab.out/stage,lab.owned
            child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,identity or username
            child.identity_items=['password']
            required=[stage+'_'+check for check in CHECKS] if stage!='stale' else ['stale_old_password_rejected_after_rotation']
            try:child.run_job('ScramAcceptance',[bootstrap,username,allowed,denied,group,stage,str(start)],required)
            finally:lab.result['checks'].update(child.result['checks'])
            stages.append({'stage':stage,'job':child.tag+'-client','observations':child.result['client_observations']})
        phase='initial_sasl_ssl_client';run('initial',0);lab.result['checks'][phase]='PASS'
        phase='supported_password_reference_rotation';started=time.monotonic();started_utc=datetime.now(timezone.utc).isoformat()
        updated=scram_user(username,allowed,group,new_source)
        # Only the owned KafkaUser's supported password source changes; ACLs stay identical.
        if user['spec']['authorization']!=updated['spec']['authorization']:raise RuntimeError('Rotation changed ACLs')
        k('apply','-f','-',data=json.dumps(updated));after_user=ready_user(username,new_source)
        after=lab.secret_metadata(username,'rotated-user-secret-metadata')
        if before['uid']!=after['uid'] or before['resourceVersion']==after['resourceVersion'] or after_user['generation']<=initial['generation']:
            raise RuntimeError('Expected same generated Secret with changed version and reconciled user generation')
        lab.result['checks'][phase]='PASS';phase='rotated_sasl_ssl_client';run('rotated',6);lab.result['checks'][phase]='PASS'
        phase='stale_credential_revoked';run('stale',12,old_source);lab.result['checks'][phase]='PASS'
        lab.result['rotation']={'started_utc':started_utc,'completion_seconds':round(time.monotonic()-started,3),
            'scope':'KafkaUser password reference replaced, fresh Job reloaded, old source password rejected; no continuous traffic SLO',
            'before_secret':before,'after_secret':after,'reconciled_user':after_user,'same_principal':True}
        phase='broker_authenticated_principal_independently_observed'
        logs=lab.read('broker-authorizer-identity','logs','-l','strimzi.io/pool-name=dual-role','-c','kafka','--prefix','--tail=1000','--max-log-requests=3')
        matches=principal_denial(logs,username,denied)
        if not matches:raise RuntimeError('Broker authorizer evidence did not establish the expected authenticated principal and denied topic')
        lab.result['principal_evidence']={'source':'native broker authorizer denial','principal':'User:'+username,'resource':denied,'matching_records':matches}
        lab.result['checks'][phase]='PASS';lab.result['stages']=stages
        lab.result['pending_identity_gates']={'oauth_live_integration':'NOT_EXECUTED_NO_REVIEWED_IDP','oauth_issuer_audience_jwks_expiry_refresh':'NOT_EXECUTED',
            'federated_workload_identity':'NOT_EXECUTED','continuous_migration_availability':'NOT_TESTED','production_alert_routing':'NOT_TESTED','independent_iam_review':'PENDING'}
        lab.result['runtime_scope']='ACTUAL_SASL_SSL_SCRAM_ROTATION_STALE_REJECTION_AND_PRINCIPAL_ACL_CHECKS_OAUTH_NOT_EXECUTED';lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print('Chapter 028 '+phase+' failed: '+type(exc).__name__+'; sanitized evidence has details',file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
