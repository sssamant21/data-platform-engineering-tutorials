#!/usr/bin/env python3
"""Fresh integrated security runtimes plus secure network failure/recovery; no certification."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from runtime_acceptance import k, ROOT, CLUSTER
from security_acceptance import SecurityLab, immutable_kafka_image
from run_chapter_026 import bootstrap_endpoints, advertised_mappings, normalized_ips
from run_chapter_027 import tls_user
from run_chapter_028 import bootstrap_from_status
from run_chapter_029 import ready_identity

NETWORK_CHECKS=['dns_tcp_sasl_ssl_all_brokers_hostname_verified','invalid_dns_classified_client_side_only','unused_port_classified_tcp_failure',
    'wrong_endpoint_metadata_failure_classified','secure_recovery_exact_acks_all_records_commits_within_budget','secure_kraft_quorum_and_final_isr']
LIMITS=['This is supported integrated runtime evidence, not the manuscript full mandatory-gate assessment. Independent security signoff, real incident owner/alert routing and signed governance are pending; no numeric capstone score or enterprise certification.',
    'All secure clients use one namespace on a single kind host. CNI-enforced NetworkPolicy, cross-namespace admission, external endpoints, cloud IAM/firewalls, storage failure domains and multi-zone continuity are not validated.',
    'Fresh child runtimes execute during this Actions run, not imported historical passes. Synthetic client failures change only client configuration; no broker listener, CA, ACL, NetworkPolicy or production configuration is changed for fault injection.',
    'Credential replacement and fresh Job reload are measured, not seamless overlap or continuous production availability. The network drill has a predeclared 120-second synthetic completion budget; no production percentile SLO is claimed.',
    'Live CA/key rotation, expired-client rejection and certificate renewal are not executed. CA rotation/tabletop and ACL rollback/break-glass plans require independent review, not invented approval.',
    'OAuth remains conditional NOT_EXECUTED with no supported reviewed IdP/plugin; issuer/audience/JWKS/refresh behavior receives no live integration credit.']


def validate_child(report,chapter,head,run_id,started):
    timestamp=datetime.fromisoformat(report['timestamp_utc'])
    if report.get('chapter')!=chapter or report.get('status')!='PASS' or report.get('head_commit')!=head or report.get('run_id')!=run_id or timestamp<started:
        raise RuntimeError('Child evidence is failed, stale or from another chapter/head/run')
    checks=report.get('checks',{})
    if not checks or any(state!='PASS' for state in checks.values()):raise RuntimeError('Child supported checks did not all pass')
    if report.get('certification')!='NOT_CERTIFIED':raise RuntimeError('Unexpected child certification claim')
    return {'chapter':chapter,'runtime_scope':report.get('runtime_scope'),'passed_checks':len(checks),'timestamp_utc':report['timestamp_utc'],
            'head_commit':head,'run_id':run_id,'certification':'NOT_CERTIFIED','limitations':report.get('limitations',[])}


def network_identity(name,topic,group):
    user=tls_user(name,topic,group);user['spec']['authentication']={'type':'scram-sha-512'}
    return user


def main():
    lab=SecurityLab('030',LIMITS);error,phase=None,'fresh_composite_security_runtimes';started=datetime.now(timezone.utc)
    try:
        lab.prepare()
        head=os.environ.get('QA_HEAD_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=10).strip()
        lab.result['head_commit']=head;run_id=os.environ.get('GITHUB_RUN_ID');children=[]
        for chapter in ('027','028','029'):
            report_path=lab.out/f'chapter-{chapter}-runtime.json'
            if report_path.exists():raise RuntimeError('Existing child report would risk stale evidence; use a fresh disposable evidence directory')
            child_started=datetime.now(timezone.utc);before=time.monotonic()
            command=[sys.executable,str(ROOT/'kafka/qa'/f'run_chapter_{chapter}.py')]
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=600,env={**os.environ,'QA_HEAD_SHA':head})
            lab.out.mkdir(parents=True,exist_ok=True)
            (lab.out/f'chapter-030-child-{chapter}-process.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
            if not report_path.exists():raise RuntimeError('Child runtime did not create evidence: '+chapter)
            report=json.loads(report_path.read_text(encoding='utf-8'))
            if result.returncode:raise RuntimeError('Child runtime failed: '+chapter+'; inspect its sanitized runtime report')
            summary=validate_child(report,chapter,head,run_id,child_started);summary['completion_seconds']=round(time.monotonic()-before,3)
            summary['evidence']=report_path.name;children.append(summary);lab.result['checks']['fresh_'+chapter+'_supported_runtime']='PASS'
        lab.result['fresh_child_runtimes']=children
        phase='secure_service_and_ready_endpoint_mapping';cluster=json.loads(k('get','kafka',CLUSTER,'-o','json'));bootstrap=bootstrap_from_status(cluster)
        service=json.loads(lab.read('secure-bootstrap-service','get','service',CLUSTER+'-kafka-bootstrap','-o','json'))
        slices=json.loads(lab.read('secure-endpointslices','get','endpointslices','-l','kubernetes.io/service-name='+CLUSTER+'-kafka-bootstrap','-o','json'))['items']
        pods=json.loads(lab.read('secure-broker-pods','get','pods','-l','strimzi.io/pool-name=dual-role','-o','json'))['items']
        ready=bootstrap_endpoints(service,slices,pods,9095)
        bad_port=19095
        if any(p['port']==bad_port for p in service['spec']['ports']):raise RuntimeError('Refuse negative probe against a published Service port')
        lab.result['ready_endpoints']=ready;lab.result['network_drill_contract']={'client_only':True,'reserved_invalid_dns':'capstone-ch030.invalid','unused_service_port':bad_port,'completion_budget_seconds':120,'production_slo':False}
        lab.image=immutable_kafka_image(next(c['imageID'] for c in pods[0]['status']['containerStatuses'] if c['name']=='kafka'));lab.result['client_image']=lab.image
        lab.result['checks'][phase]='PASS';phase='secure_network_negative_and_recovery_client'
        topic=lab.topic('secure-network');username,group=lab.tag+'-network',lab.tag+'-network-group'
        lab.apply(network_identity(username,topic,group));lab.result['network_identity']=ready_identity(lab,username,'network-secret-metadata')
        lab.identity_secret=username;lab.identity_items=['password'];lab.ca_secret=CLUSTER+'-cluster-ca-cert';lab.client_service_account=lab.tag+'-network-sa'
        lab.apply({'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':lab.client_service_account},'automountServiceAccountToken':False})
        lab.run_job('ScramAcceptance',['network',bootstrap,username,topic,group,str(bad_port)],['network_'+check for check in NETWORK_CHECKS])
        lab.result['checks'][phase]='PASS';phase='secure_advertised_dns_matches_ready_pod_uids'
        observations=lab.result['client_observations'];lab.result['advertised_brokers']=advertised_mappings(observations,ready,9095)
        dns=[line.split(':',2)[2].split(',') for line in observations if line.startswith('OBS:BOOTSTRAP_DNS:')]
        if len(dns)!=1 or not normalized_ips(dns[0]).issubset(normalized_ips(service['spec'].get('clusterIPs',[service['spec']['clusterIP']]))):raise RuntimeError('Bootstrap DNS differs from Service addresses')
        lab.result['checks'][phase]='PASS'
        lab.result['conditional_oauth_integration']={'status':'NOT_EXECUTED','reason':'No reviewed supported external IdP/plugin; SCRAM is not OAuth proof'}
        lab.result['capstone_assessment']={'status':'NOT_YET_ACCEPTED','score':None,'independent_security_review':'PENDING',
            'mandatory_gaps':['CNI/namespace enforcement','continuous workload availability and production SLO/alerts','signed change/rollback/break-glass governance','independent assessor signoff'],
            'certificate_rotation':'NOT_EXECUTED; separate approved plan required','oauth':'CONDITIONAL_NOT_EXECUTED'}
        lab.result['runtime_scope']='FRESH_TLS_SCRAM_ROTATION_TENANT_ACLS_AND_SECURE_NETWORK_RECOVERY_COMPOSITE_CAPSTONE_NOT_YET_ACCEPTED';lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print('Chapter 030 '+phase+' failed: '+type(exc).__name__+'; sanitized evidence has details',file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
