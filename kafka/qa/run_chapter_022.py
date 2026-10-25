#!/usr/bin/env python3
"""Chapter 022: governed disposable retention extension/restoration and replay evidence."""
import copy
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import Lab, k, CLUSTER
from run_chapter_021 import StorageLab, CLIENT_CHECKS, LIMITATIONS, log_dirs, safe_partition_path, segment_files

BASE_CONFIG = {'min.insync.replicas': 2, 'cleanup.policy': 'delete', 'retention.ms': 3600000,
               'retention.bytes': 104857600, 'segment.bytes': 1048576, 'segment.ms': 60000}
ANNOTATIONS = {'sre.example.com/owner': 'kafka-qa', 'sre.example.com/change-ticket': 'LAB-CH22',
               'sre.example.com/data-classification': 'synthetic'}


def validate_policy_change(before, after, *, synthetic_lab_authorized, record_age_seconds):
    if not synthetic_lab_authorized or not 0 <= record_age_seconds < 3000:
        raise RuntimeError('Retention change requires authorized synthetic scope and a safe retained-record age')
    name = before['metadata']['name']
    if not re.fullmatch(r'ch022-[a-f0-9]{12}-storage', name):
        raise RuntimeError('Unowned topic')
    if before['metadata'] != after['metadata'] or before['metadata']['annotations'] != ANNOTATIONS:
        raise RuntimeError('Governance metadata changed or missing')
    if before['metadata']['labels'].get('strimzi.io/cluster') != CLUSTER:
        raise RuntimeError('Wrong cluster ownership')
    left, right = copy.deepcopy(before['spec']), copy.deepcopy(after['spec'])
    a, b = left['config'].pop('retention.ms'), right['config'].pop('retention.ms')
    if left != right or left['replicas'] != 3 or left['partitions'] != 3 or left['config']['min.insync.replicas'] != 2:
        raise RuntimeError('Only retention.ms may change; durability and other policy settings must remain intact')
    if (a, b) not in ((3600000, 7200000), (7200000, 3600000)):
        raise RuntimeError('Only the reviewed one-hour/two-hour lab transition is allowed')


def capacity_forecast(ingest_bytes_per_second, retention_seconds, partitions, replicas, per_partition_bytes):
    if min(ingest_bytes_per_second, retention_seconds, partitions, replicas, per_partition_bytes) <= 0:
        raise ValueError('Forecast inputs must be positive')
    logical = ingest_bytes_per_second * retention_seconds
    budget = partitions * per_partition_bytes
    return {'classification': 'ILLUSTRATIVE_CALCULATION_NOT_MEASURED_CAPACITY',
            'logical_bytes': logical, 'replicated_bytes_before_overhead': logical * replicas,
            'configured_logical_size_budget': budget, 'size_budget_satisfies_time_window': budget >= logical,
            'nominal_size_limited_replay_seconds': budget / ingest_bytes_per_second}


def await_reconciliation(name, generation, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        topic = json.loads(k('get', 'kafkatopic', name, '-o', 'json'))
        ready = any(c['type'] == 'Ready' and c['status'] == 'True' for c in topic.get('status', {}).get('conditions', []))
        if ready and topic['status'].get('observedGeneration', 0) >= generation:
            return topic
        time.sleep(2)
    raise RuntimeError('KafkaTopic did not reconcile the requested generation')


def main():
    lab = StorageLab('022', LIMITATIONS + ['Governance annotations and Python policy guards are lab controls, not deployed admission/GitOps enforcement or legal approval.'])
    lab.result['checks'] = {}
    error, phase = None, 'storage_baseline'
    try:
        lab.prepare()
        before = lab.inventory('before')
        lab.result['storage_before'] = before
        lab.result['checks'][phase] = 'PASS'
        topic = lab.tag + '-storage'
        baseline = {'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
                    'metadata': {'name': topic, 'labels': {'strimzi.io/cluster': CLUSTER,
                                 'app.kubernetes.io/part-of': 'kafka-sre-curriculum'}, 'annotations': ANNOTATIONS},
                    'spec': {'partitions': 3, 'replicas': 3, 'config': BASE_CONFIG}}
        lab.apply(baseline)
        created = json.loads(k('get', 'kafkatopic', topic, '-o', 'json'))
        await_reconciliation(topic, created['metadata']['generation'])
        started = time.monotonic()
        observations = []
        for stage, retention_ms in [('baseline', 3600000), ('extended', 7200000), ('restored', 3600000)]:
            phase = stage + '_policy_reconciled'
            if stage != 'baseline':
                desired = copy.deepcopy(baseline)
                desired['spec']['config']['retention.ms'] = retention_ms
                previous = copy.deepcopy(baseline)
                previous['spec']['config']['retention.ms'] = 3600000 if stage == 'extended' else 7200000
                validate_policy_change(previous, desired, synthetic_lab_authorized=True, record_age_seconds=time.monotonic()-started)
                k('apply', '-f', '-', '--dry-run=server', data=json.dumps(desired))
                k('apply', '-f', '-', data=json.dumps(desired))
                updated = json.loads(k('get', 'kafkatopic', topic, '-o', 'json'))
                await_reconciliation(topic, updated['metadata']['generation'])
                lab.result.setdefault('policy_changes', []).append({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'stage': stage, 'before_ms': previous['spec']['config']['retention.ms'], 'after_ms': retention_ms,
                    'authorization': 'user-authorized synthetic disposable lab only', 'server_dry_run': 'PASS',
                    'generation': updated['metadata']['generation'], 'observed_record_age_seconds': time.monotonic()-started,
                    'command': ['kubectl', 'apply', '-f', '<recorded-stage-manifest>'], 'status': 'PASS'})
            captured = json.loads(lab.read(stage + '-topic', 'get', 'kafkatopic', topic, '-o', 'json'))
            if captured['spec']['config']['retention.ms'] != retention_ms or any(captured['metadata'].get('annotations', {}).get(key) != value for key, value in ANNOTATIONS.items()):
                raise RuntimeError('Desired policy/governance metadata mismatch')
            lab.result['checks'][phase] = 'PASS'
            phase = stage + '_runtime'
            client = Lab('022', lab.result['limitations'])
            client.tag, client.image, client.out, client.owned = lab.tag + '-' + stage, lab.image, lab.out / stage, lab.owned
            required = [stage + '_' + check for check in CLIENT_CHECKS if stage == 'baseline' or 'acknowledged' not in check]
            required.append(stage + '_committed_offsets_match_retained_window')
            try:
                client.run_job('StorageAcceptance', [topic, lab.tag, 'seed' if stage == 'baseline' else 'audit',
                               str(retention_ms), str(BASE_CONFIG['retention.bytes']), stage], required)
            finally:
                lab.result['checks'].update(client.result['checks'])
            observations.extend(client.result['client_observations'])
            effective = lab.read(stage + '-effective-config', 'exec', lab.pod, '-c', 'kafka', '--',
                                 '/opt/kafka/bin/kafka-configs.sh', '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092',
                                 '--entity-type', 'topics', '--entity-name', topic, '--describe')
            actual = dict(re.findall(r'(?:^|\s)([a-z][a-z0-9.]+)=([^,\s]+)', effective))
            expected = {**BASE_CONFIG, 'retention.ms': retention_ms}
            if any(actual.get(key) != str(value) for key, value in expected.items()):
                raise RuntimeError('Kafka CLI effective policy did not match desired state')
            lab.result['checks'][phase] = 'PASS'
        lab.result['client_observations'] = observations
        phase = 'physical_segment_rolls_without_forced_deletion'
        nodes = {int(o.split(':',3)[2]): o.split(':',3)[3].split('.')[0] for o in observations if o.startswith('OBS:NODE:')}
        raw = lab.read('log-dirs', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-log-dirs.sh',
                       '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', '--describe', '--topic-list', topic)
        replicas = log_dirs(raw, topic)
        mappings = {item['pod']: item for item in before}
        physical = []
        for replica in replicas:
            mapping = mappings[nodes[replica['broker']]]
            path = safe_partition_path(replica['directory'], mapping['mount'], topic, replica['partition'], chapter='022')
            listing = lab.read(f'segments-{replica["broker"]}-{replica["partition"]}', 'exec', mapping['pod'], '-c', 'kafka', '--',
                               'find', path, '-maxdepth', '1', '-type', 'f', '-printf', '%f %s\n')
            physical.append({'pod': mapping['pod'], 'path': path, 'files': segment_files(listing)})
        lab.result['physical_segment_observations'] = physical
        lab.result['checks'][phase] = 'PASS'
        phase = 'storage_identity_and_headroom_observed'
        after = lab.inventory('after')
        if before != after:
            raise RuntimeError('Storage identity changed during retention lifecycle')
        lab.result['storage_after'] = after
        for mapping in after:
            lab.read('df-' + mapping['pod'], 'exec', mapping['pod'], '-c', 'kafka', '--', 'df', '-Pk', mapping['mount'])
        lab.result['checks'][phase] = 'PASS'
        lab.result['capacity_scenario'] = capacity_forecast(20*1024**2, 48*3600, 12, 3, 50*1024**3)
        if lab.result['capacity_scenario']['size_budget_satisfies_time_window']:
            raise RuntimeError('Expected illustrative size policy to violate the 48-hour replay requirement')
        lab.result['checks']['illustrative_capacity_policy_conflict_detected'] = 'PASS'
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'SUPPORTED_ACCEPTANCE_PASS'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError, StopIteration) as exc:
        error = exc
        lab.result['checks'][phase] = 'FAIL'
        print(str(exc), file=sys.stderr)
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
