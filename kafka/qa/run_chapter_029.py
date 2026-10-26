#!/usr/bin/env python3
"""Symmetric real tenant ACL enforcement; kind networking is not tenant isolation proof."""
import json
import subprocess
import sys
import time
from runtime_acceptance import k, CTX, NS, CLUSTER
from security_acceptance import SecurityLab, immutable_kafka_image
from run_chapter_028 import bootstrap_from_status, principal_denial

TENANT_CHECKS=['own_topic_group_exact_records_before_denials','foreign_topic_describe_denied','foreign_topic_produce_denied',
    'foreign_topic_consume_denied','foreign_group_denied_on_allowed_topic','resource_without_any_acl_denied',
    'own_topic_group_exact_records_after_denials','foreign_transactional_id_denied','own_transactional_id_commit_and_read_committed']
LIMITS=['All test workloads run in one disposable namespace on a single kind host. Kafka ACL and RBAC checks do not certify cross-namespace admission, node security, CNI-enforced NetworkPolicy, external firewalls or multi-zone isolation.',
    'Only synthetic SCRAM identities are tested. OAuth principal mapping, signed independent security review, production tenant onboarding/offboarding, break-glass approval and external alert routing remain NOT_EXECUTED/PENDING.',
    'The read-only diagnostic identity has Cluster Describe for effective ACL inventory; it is not an application superuser and has no ACL mutation permission. Synthetic tenant cluster permission is only IdempotentWrite.',
    'No out-of-band ACL is introduced or deleted. Desired-versus-effective drift checks cover owned identities, not a production-wide recertification.',
    'Literal resources are enforced; prefix and wildcard admission governance is not proven by this lab. Host wildcard is not a network flow restriction. Enterprise certification remains NOT_CERTIFIED.']
CONFIG_SCRIPT='while IFS= read -r line; do case "$line" in authorizer.class.name=*|allow.everyone.if.no.acl.found=*|super.users=*) printf "%s\\n" "$line";; esac; done < /tmp/strimzi.properties'


def tenant_user(name,topic,group,transaction):
    return {'apiVersion':'kafka.strimzi.io/v1beta2','kind':'KafkaUser','metadata':{'name':name,'labels':{'strimzi.io/cluster':CLUSTER}},
        'spec':{'authentication':{'type':'scram-sha-512'},'authorization':{'type':'simple','acls':[
            {'resource':{'type':'topic','name':topic,'patternType':'literal'},'operations':['Read','Write','Describe'],'host':'*'},
            {'resource':{'type':'group','name':group,'patternType':'literal'},'operations':['Read','Describe'],'host':'*'},
            {'resource':{'type':'transactionalId','name':transaction,'patternType':'literal'},'operations':['Write','Describe'],'host':'*'},
            {'resource':{'type':'cluster'},'operations':['IdempotentWrite'],'host':'*'}]}}}


def diagnostic_user(name):
    user=tenant_user(name,'unused','unused','unused')
    user['spec']['authorization']['acls']=[{'resource':{'type':'cluster'},'operations':['Describe'],'host':'*'}]
    return user


def ready_identity(lab,name,label):
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        user=json.loads(k('get','kafkauser',name,'-o','json'));status=user.get('status',{})
        if status.get('observedGeneration')==user['metadata']['generation'] and any(c['type']=='Ready' and c['status']=='True' for c in status.get('conditions',[])):
            if status.get('username')!=name:raise RuntimeError('SCRAM principal status mismatch')
            metadata=lab.secret_metadata(name,label)
            if 'password' not in metadata['keys']:raise RuntimeError('SCRAM generated password missing')
            return {'username':name,'uid':user['metadata']['uid'],'generation':user['metadata']['generation'],'secret':metadata}
        time.sleep(3)
    raise RuntimeError('KafkaUser current generation did not become Ready')


def authorizer_config(text,app_users):
    values={}
    for line in text.splitlines():
        key,sep,value=line.partition('=')
        if not sep or key not in ('authorizer.class.name','allow.everyone.if.no.acl.found','super.users') or key in values:raise RuntimeError('Unexpected or duplicate authorizer configuration output')
        values[key]=value
    if values.get('authorizer.class.name')!='org.apache.kafka.metadata.authorizer.StandardAuthorizer':raise RuntimeError('Effective KRaft StandardAuthorizer not established')
    if values.get('allow.everyone.if.no.acl.found','false').lower()!='false':raise RuntimeError('Default-open authorizer is forbidden')
    superusers=values.get('super.users','').split(';')
    if any('User:'+user in superusers for user in app_users):raise RuntimeError('Application identity is an effective superuser')
    return {'effective':values,'absent_default_property':'Kafka 4.0 default false; also verified by live ungranted-resource denial',
            'application_superusers':False}


def rbac_denials(service_account):
    observations=[]
    for verb,resource in [('get','secrets'),('list','secrets'),('watch','secrets'),('patch','kafkas.kafka.strimzi.io'),
                          ('patch','kafkausers.kafka.strimzi.io'),('patch','kafkatopics.kafka.strimzi.io')]:
        result=subprocess.run(['kubectl','--context',CTX,'-n',NS,'auth','can-i',verb,resource,'--as',f'system:serviceaccount:{NS}:{service_account}'],capture_output=True,text=True,timeout=20)
        if result.returncode!=1 or result.stdout.strip()!='no':raise RuntimeError('Authorized RBAC deny check failed; impersonation errors are not proof')
        observations.append({'verb':verb,'resource':resource,'outcome':'DENIED'})
    return observations


def main():
    lab=SecurityLab('029',LIMITS);error,phase=None,'effective_authorizer_default_deny_and_durability'
    try:
        lab.prepare();cluster=json.loads(k('get','kafka',CLUSTER,'-o','json'));bootstrap=bootstrap_from_status(cluster)
        pod=json.loads(k('get','pod',lab.pod,'-o','json'));lab.image=immutable_kafka_image(next(c['imageID'] for c in pod['status']['containerStatuses'] if c['name']=='kafka'))
        lab.result['client_image']=lab.image;lab.result['listeners']=cluster['spec']['kafka']['listeners']
        if cluster['spec']['kafka']['authorization'].get('superUsers'):raise RuntimeError('Application fixture must not add declared superusers')
        names={tenant:{'user':lab.tag+'-'+tenant,'topic':lab.tag+'-'+tenant+'-topic','group':lab.tag+'-'+tenant+'-group','transaction':lab.tag+'-'+tenant+'-txn',
                       'service_account':lab.tag+'-'+tenant+'-sa'} for tenant in ('a','b')}
        broker_names=[p['metadata']['name'] for p in json.loads(k('get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items']]
        if len(broker_names)!=3:raise RuntimeError('Expected all three broker configurations')
        lab.result['authorizer_configs']={}
        for broker in broker_names:
            config=lab.read('authorizer-config-'+broker,'exec',broker,'-c','kafka','--','/bin/bash','-c',CONFIG_SCRIPT)
            lab.result['authorizer_configs'][broker]=authorizer_config(config,[n['user'] for n in names.values()])
        lab.result['checks'][phase]='PASS';phase='scoped_tenants_and_kubernetes_rbac'
        ungranted=lab.topic('no-acl')
        for tenant,info in names.items():
            # Same topic helper enforces RF3/minISR2; names are generated from the owned prefix.
            actual=lab.topic(tenant+'-topic')
            if actual!=info['topic']:raise RuntimeError('Owned topic mismatch')
            lab.apply(tenant_user(info['user'],info['topic'],info['group'],info['transaction']))
            info['identity']=ready_identity(lab,info['user'],tenant+'-secret-metadata')
            lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':info['service_account']},'automountServiceAccountToken':False})
            info['rbac_denials']=rbac_denials(info['service_account'])
        admin,admin_sa=lab.tag+'-inventory',lab.tag+'-inventory-sa';lab.apply(diagnostic_user(admin));admin_metadata=ready_identity(lab,admin,'inventory-secret-metadata')
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':admin_sa},'automountServiceAccountToken':False})
        lab.result['diagnostic_rbac']=rbac_denials(admin_sa);lab.result['tenants']=names;lab.result['diagnostic_identity']=admin_metadata
        lab.result['checks'][phase]='PASS';lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.result['trust_secret']=lab.secret_metadata(lab.ca_secret,'cluster-ca-metadata')
        phase='read_only_effective_acl_inventory';inventory=[]
        for info in names.values():inventory.extend([info['user'],info['topic'],info['group'],info['transaction']])
        stages=[]
        def run(stage,username,sa,args,checks):
            child=SecurityLab('029',LIMITS);child.tag,child.image,child.out,child.owned=lab.tag+'-'+stage,lab.image,lab.out/stage,lab.owned
            child.client_service_account,child.ca_secret,child.identity_secret=sa,lab.ca_secret,username;child.identity_items=['password']
            try:child.run_job('ScramAcceptance',['acl',bootstrap,username,stage,*args],[stage+'_'+name for name in checks])
            finally:lab.result['checks'].update(child.result['checks'])
            stages.append({'stage':stage,'job':child.tag+'-client','observations':child.result['client_observations']})
        run('inventory',admin,admin_sa,[*inventory,ungranted],['effective_literal_acls_exact_no_cross_grants_or_default_topic_acl']);lab.result['checks'][phase]='PASS'
        for tenant,other in [('a','b'),('b','a')]:
            phase='tenant_'+tenant+'_symmetric_enforcement';own,foreign=names[tenant],names[other]
            run(tenant,own['user'],own['service_account'],[own['topic'],foreign['topic'],own['group'],foreign['group'],own['transaction'],foreign['transaction'],ungranted],TENANT_CHECKS)
            lab.result['checks'][phase]='PASS'
        phase='independent_broker_principal_and_denial_mapping'
        logs=lab.read('broker-principal-denials','logs','-l','strimzi.io/pool-name=dual-role','-c','kafka','--prefix','--tail=1000','--max-log-requests=3')
        mappings={}
        for tenant,other in [('a','b'),('b','a')]:
            matches=principal_denial(logs,names[tenant]['user'],names[other]['topic'])
            if not matches:raise RuntimeError('Native broker principal mapping absent for tenant '+tenant)
            mappings[tenant]={'principal':'User:'+names[tenant]['user'],'denied_foreign_topic':names[other]['topic'],'records':matches}
        lab.result['principal_evidence']=mappings;lab.result['checks'][phase]='PASS';lab.result['stages']=stages
        lab.read('networkpolicy-rbac-inventory','get','role,rolebinding,networkpolicy','-o','wide')
        lab.result['pending_governance_gates']={'cross_namespace_admission':'NOT_EXECUTED','cni_networkpolicy_enforcement':'NOT_VALIDATED_ON_DEFAULT_KIND',
            'oauth_principal_mapping':'NOT_EXECUTED','signed_gitops_approval_and_break_glass':'PENDING','production_alert_routing':'NOT_TESTED','independent_security_assessment':'PENDING'}
        lab.result['runtime_scope']='ACTUAL_SYMMETRIC_TOPIC_GROUP_TRANSACTION_ACLS_EFFECTIVE_DRIFT_AND_RBAC_CHECKS_NETWORK_ISOLATION_NOT_CERTIFIED';lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print('Chapter 029 '+phase+' failed: '+type(exc).__name__+'; sanitized evidence has details',file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
