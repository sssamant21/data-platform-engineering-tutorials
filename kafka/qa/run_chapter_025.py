#!/usr/bin/env python3
"""Chapter 025 live local storage capstone with a real state-consumer rollout."""
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import Lab, k, CTX, NS, CLUSTER
from run_chapter_020 import verify_pod_owner
from run_chapter_021 import StorageLab, CLIENT_CHECKS, LIMITATIONS, log_dirs, safe_partition_path, segment_files
from run_chapter_022 import BASE_CONFIG, validate_policy_change
from run_chapter_023 import CONFIG as COMPACT_CONFIG, COMMON as COMPACT_CHECKS, cleaner_observation
from run_chapter_024 import integration_gate

ANNOTATIONS = {'sre.example.com/owner': 'kafka-qa', 'sre.example.com/change-ticket': 'LAB-CH25', 'sre.example.com/data-classification': 'synthetic'}
RECOVERY_BUDGET_SECONDS = 180
MIN_FREE_BYTES = 64*1024**2
LIMITS = LIMITATIONS + ['Frozen synthetic-data bootstrap consumer; no continuous-update/state-checkpoint crash, production consumer group rebalance or business throughput SLO certification.',
    'Recovery timing measures rolling replacement/bootstrap completion including observation; it is not observed service downtime or a production RTO.',
    'No installed alerting/Prometheus, signed independent assessment, production retention/legal/security approval, remote plugin/bucket, remote reads or disaster recovery validation.']


def available_bytes(output):
    rows = output.strip().splitlines()
    if len(rows)<2:
        raise RuntimeError('Missing filesystem headroom observation')
    columns = rows[-1].split()
    if len(columns)<6 or not columns[3].isdigit():
        raise RuntimeError('Malformed POSIX df observation')
    return int(columns[3])*1024


def state_checksum(log):
    values = set(re.findall(r'^OBS:STATE_CHECKSUM:([a-f0-9]{64})$', log, re.MULTILINE))
    if len(values)!=1:
        raise RuntimeError('Missing or divergent state checksum')
    return values.pop()


def consumer_manifest(name, image, source, args):
    return {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': name}, 'spec': {
        'replicas': 1, 'selector': {'matchLabels': {'app': name}},
        'strategy': {'type': 'RollingUpdate', 'rollingUpdate': {'maxUnavailable': 0, 'maxSurge': 1}},
        'template': {'metadata': {'labels': {'app': name}}, 'spec': {
            'automountServiceAccountToken': False, 'terminationGracePeriodSeconds': 30,
            'volumes': [{'name': 'source', 'configMap': {'name': source}}],
            'containers': [{'name': 'consumer', 'image': image,
                'command': ['java', '-Xmx256m', '-cp', '/opt/kafka/libs/*', '/qa/CompactionAcceptance.java', *args, 'serve'],
                'volumeMounts': [{'name': 'source', 'mountPath': '/qa', 'readOnly': True}],
                'readinessProbe': {'exec': {'command': ['test', '-f', '/tmp/compaction-ready']}, 'periodSeconds': 2, 'timeoutSeconds': 2},
                'resources': {'requests': {'cpu': '100m', 'memory': '256Mi'}, 'limits': {'cpu': '1', 'memory': '512Mi'}}}]}}}}


def main():
    lab = StorageLab('025', LIMITS)
    lab.result['checks'] = {}
    error, phase, stream, stream_file = None, 'storage_baseline', None, None
    try:
        lab.prepare()
        before = lab.inventory('before')
        lab.result['storage_before'] = before
        lab.result['checks'][phase] = 'PASS'
        lab.result['approved_test_contract'] = {'authorization': 'user-authorized disposable synthetic lab',
            'context': CTX, 'namespace': NS, 'recovery_operator': 'automated-harness',
            'recovery_budget_seconds': RECOVERY_BUDGET_SECONDS, 'minimum_observed_filesystem_free_bytes': MIN_FREE_BYTES,
            'criteria_classification': 'HARNESS_SAFETY_AND_COMPLETION_BOUNDS_NOT_PRODUCTION_SLOS',
            'forbidden': ['broker/controller/PVC deletion', 'segment edits', 'disk fill', 'remote object operations', 'durability/security weakening'],
            'independent_signed_approval': 'PENDING'}
        def headroom(label):
            observed = []
            for mapping in before:
                free = available_bytes(lab.read(label+'-'+mapping['pod'], 'exec', mapping['pod'], '-c', 'kafka', '--', 'df', '-Pk', mapping['mount']))
                if free<MIN_FREE_BYTES:
                    raise RuntimeError('Insufficient harness safety headroom; stop without filling/altering storage')
                observed.append({'pod': mapping['pod'], 'observed_shared_filesystem_free_bytes': free})
            return observed
        phase = 'observed_headroom_before_workload'
        lab.result['headroom_before'] = headroom('df-before')
        lab.result['checks'][phase] = 'PASS'
        retention_topic, compacted = lab.tag+'-storage', lab.tag+'-compacted'
        baseline = {'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
            'metadata': {'name': retention_topic, 'labels': {'strimzi.io/cluster': CLUSTER}, 'annotations': ANNOTATIONS},
            'spec': {'partitions': 3, 'replicas': 3, 'config': BASE_CONFIG}}
        lab.apply(baseline)
        lab.apply({'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
            'metadata': {'name': compacted, 'labels': {'strimzi.io/cluster': CLUSTER}, 'annotations': ANNOTATIONS},
            'spec': {'partitions': 3, 'replicas': 3, 'config': COMPACT_CONFIG}})
        for topic in (retention_topic, compacted):
            k('wait', f'kafkatopic/{topic}', '--for=condition=Ready', '--timeout=240s', timeout=260)
        started_data = time.monotonic()
        lab.out.mkdir(parents=True, exist_ok=True)
        ledger = [{'id': lab.tag+f'-event-{i:03d}', 'partition': i%3, 'offset': i//3,
                   'expected_value_sha256': hashlib.sha256((lab.tag+f'-event-{i:03d}'+'|'+'x'*65536).encode()).hexdigest()} for i in range(96)]
        (lab.out/'chapter-025-expected-ledger.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
        jobs = []
        def client(stage, main, args, required):
            child = Lab('025', LIMITS)
            child.tag, child.image, child.out, child.owned = lab.tag+'-'+stage, lab.image, lab.out/stage, lab.owned
            try:
                child.run_job(main,args,required)
            finally:
                lab.result['checks'].update(child.result['checks'])
            jobs.append({'stage': stage, 'job': child.tag+'-client', 'observations': child.result['client_observations']})
            return child
        for stage, retention_ms in [('retention_baseline',3600000),('retention_extended',7200000),('retention_restored',3600000)]:
            phase = stage
            if stage!='retention_baseline':
                desired, previous = copy.deepcopy(baseline),copy.deepcopy(baseline)
                desired['spec']['config']['retention.ms'] = retention_ms
                previous['spec']['config']['retention.ms'] = 3600000 if retention_ms==7200000 else 7200000
                validate_policy_change(previous,desired,synthetic_lab_authorized=True,record_age_seconds=time.monotonic()-started_data,chapter='025',annotations=ANNOTATIONS)
                k('apply','-f','-','--dry-run=server',data=json.dumps(desired))
                k('apply','-f','-',data=json.dumps(desired))
                # Exact effective-state assertions below must converge before the client passes.
                deadline = time.monotonic()+180
                while time.monotonic()<deadline:
                    topic=json.loads(k('get','kafkatopic',retention_topic,'-o','json'))
                    if topic.get('status',{}).get('observedGeneration',0)>=topic['metadata']['generation'] and any(c['type']=='Ready' and c['status']=='True' for c in topic.get('status',{}).get('conditions',[])):
                        break
                    time.sleep(2)
                else:raise RuntimeError('Retention policy did not reconcile')
            required=[stage+'_'+c for c in CLIENT_CHECKS if stage=='retention_baseline' or 'acknowledged' not in c]
            required.append(stage+'_committed_offsets_match_retained_window')
            child=client(stage,'StorageAcceptance',[retention_topic,lab.tag,'seed' if stage=='retention_baseline' else 'audit',str(retention_ms),str(BASE_CONFIG['retention.bytes']),stage],required)
            lab.result['checks'][phase]='PASS'
        phase='compaction_seed_and_fresh_rebuild'
        seed=client('state-seed','CompactionAcceptance',[compacted,lab.tag,'seed'],['seed_'+c for c in COMPACT_CHECKS]+['seed_108_keyed_updates_and_real_null_tombstone_acknowledged','seed_cleaner_observation_recorded_without_completion_sla'])
        seed_log=(seed.out/'chapter-025-client.log').read_text(encoding='utf-8')
        checksum=state_checksum(seed_log)
        client('state-rebuild','CompactionAcceptance',[compacted,lab.tag,'rebuild'],['rebuild_'+c for c in COMPACT_CHECKS])
        lab.result['cleaner_progress']=cleaner_observation(seed.result['client_observations'])
        lab.result['checks'][phase]='PASS'
        phase='retention_segment_rolls_on_all_replicas'
        raw=lab.read('retention-log-dirs','exec',lab.pod,'-c','kafka','--','/opt/kafka/bin/kafka-log-dirs.sh',
                     '--bootstrap-server',CLUSTER+'-kafka-bootstrap:9092','--describe','--topic-list',retention_topic)
        replicas=log_dirs(raw,retention_topic)
        node_map={int(o.split(':',3)[2]):o.split(':',3)[3].split('.')[0] for o in jobs[0]['observations'] if o.startswith('OBS:NODE:')}
        mapping_by_pod={m['pod']:m for m in before};physical=[]
        for replica in replicas:
            mapping=mapping_by_pod[node_map[replica['broker']]]
            path=safe_partition_path(replica['directory'],mapping['mount'],retention_topic,replica['partition'],chapter='025')
            listing=lab.read(f'segments-{replica["broker"]}-{replica["partition"]}','exec',mapping['pod'],'-c','kafka','--','find',path,'-maxdepth','1','-type','f','-printf','%f %s\n')
            physical.append({'pod':mapping['pod'],'path':path,'files':segment_files(listing)})
        lab.result['physical_segment_observations']=physical;lab.result['checks'][phase]='PASS'
        phase='real_consumer_bootstrap_readiness'
        name=lab.tag+'-consumer'
        lab.apply(consumer_manifest(name,lab.image,seed.tag+'-source',[compacted,lab.tag]))
        k('rollout','status',f'deployment/{name}','--timeout=180s',timeout=200)
        def active_pod():
            pods=json.loads(k('get','pods','-l',f'app={name}','-o','json'))['items']
            active=[p for p in pods if not p['metadata'].get('deletionTimestamp')]
            if len(active)!=1:raise RuntimeError('Expected one active lab consumer Pod')
            p=active[0];rs_name=next(r['name'] for r in p['metadata']['ownerReferences'] if r.get('controller') and r['kind']=='ReplicaSet')
            rs=json.loads(k('get','replicaset',rs_name,'-o','json'));deployment=json.loads(k('get','deployment',name,'-o','json'))
            if not verify_pod_owner(p,rs,deployment):raise RuntimeError('Consumer controller ownership mismatch')
            return p
        original=active_pod();original_name=original['metadata']['name']
        initial_log=lab.read('consumer-before','logs',original_name,'--tail=200')
        if state_checksum(initial_log)!=checksum:raise RuntimeError('Consumer bootstrap state checksum mismatch')
        lab.result['checks'][phase]='PASS'
        phase='consumer_rolling_recovery_same_checksum'
        stream_file=(lab.out/'chapter-025-consumer-shutdown.log').open('w',encoding='utf-8')
        stream=subprocess.Popen(['kubectl','--context',CTX,'-n',NS,'logs','-f',original_name,'--tail=100'],stdout=stream_file,stderr=subprocess.STDOUT,text=True)
        time.sleep(1)
        if stream.poll() is not None:raise RuntimeError('Shutdown evidence stream failed before rollout')
        recovery_started=time.monotonic()
        k('rollout','restart',f'deployment/{name}')
        k('rollout','status',f'deployment/{name}','--timeout=150s',timeout=170)
        replacement=active_pod();replacement_log=lab.read('consumer-after','logs',replacement['metadata']['name'],'--tail=200')
        elapsed=time.monotonic()-recovery_started
        if replacement['metadata']['uid']==original['metadata']['uid'] or state_checksum(replacement_log)!=checksum:
            raise RuntimeError('Consumer was not replaced with the same rebuilt state')
        if elapsed>RECOVERY_BUDGET_SECONDS:raise RuntimeError('Consumer replacement exceeded declared test completion budget')
        try:stream.wait(timeout=20)
        except subprocess.TimeoutExpired:stream.terminate();stream.wait(timeout=10)
        stream_file.close()
        if 'GRACEFUL_CLOSE' not in (lab.out/'chapter-025-consumer-shutdown.log').read_text(encoding='utf-8'):
            raise RuntimeError('No graceful completion evidence from original consumer')
        lab.result['recovery']={'old_uid':original['metadata']['uid'],'new_uid':replacement['metadata']['uid'],'state_sha256_before_and_after':checksum,
            'measured_rollout_bootstrap_completion_seconds':round(elapsed,3),'declared_harness_budget_seconds':RECOVERY_BUDGET_SECONDS,
            'production_rto_status':'NOT_ASSESSED','interpretation':'rolling replacement/bootstrap upper bound including observation; not measured service downtime'}
        lab.result['checks'][phase]='PASS'
        phase='post_recovery_exact_event_ledger_and_offsets'
        required=['post_recovery_'+c for c in CLIENT_CHECKS if 'acknowledged' not in c]+['post_recovery_committed_offsets_match_retained_window']
        client('post-recovery','StorageAcceptance',[retention_topic,lab.tag,'audit','3600000',str(BASE_CONFIG['retention.bytes']),'post_recovery'],required)
        lab.result['checks'][phase]='PASS'
        phase='final_storage_identity_headroom_and_quorum'
        after=lab.inventory('after')
        if before!=after:raise RuntimeError('Storage identities changed across capstone')
        lab.result['storage_after']=after;lab.result['headroom_after']=headroom('df-after')
        quorum=lab.read('quorum','exec',lab.pod,'-c','kafka','--','/opt/kafka/bin/kafka-metadata-quorum.sh','--bootstrap-server',CLUSTER+'-kafka-bootstrap:9092','describe','--status')
        if not re.search(r'LeaderId:\s+\d+',quorum):raise RuntimeError('No KRaft leader')
        lab.result['checks'][phase]='PASS';lab.result['jobs']=jobs
        lab.result['conditional_tiered_integration']={'gate':integration_gate({}),'offload':'NOT_EXECUTED','remote_reads':'NOT_EXECUTED','iam_denial_recovery':'NOT_EXECUTED','dr_rpo_rto':'NOT_TESTED'}
        lab.result['pending_assessments']={'independent_signed_change_and_assessor_review':'PENDING','production_security':'PENDING',
            'installed_alert_rules_and_metric_tests':'NOT_EXECUTED','business_rpo_rto_and_capacity_forecast':'NOT_ASSESSED'}
        lab.result['capacity_example']={'logical_bytes':12*1024**2*86400,'rf3_bytes_before_overhead':12*1024**2*86400*3,'classification':'ILLUSTRATIVE_NOT_MEASURED_PER_BROKER_FORECAST'}
        lab.result['capstone_assessment']='NOT_YET_ACCEPTED_INDEPENDENT_REVIEW_AND_PRODUCTION_GATES_PENDING'
        lab.result['runtime_scope']='SUPPORTED_LOCAL_STORAGE_AND_APPLICATION_RECOVERY_GATES_PASS_REMOTE_INTEGRATION_NOT_EXECUTED'
        lab.result['status']='PASS'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print(str(exc),file=sys.stderr)
    finally:
        if stream is not None and stream.poll() is None:stream.terminate();stream.wait(timeout=10)
        if stream_file is not None and not stream_file.closed:stream_file.close()
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
