#!/usr/bin/env python3
"""Chapter 023 real tombstones and independent empty-state bootstrap Jobs."""
import json
import re
import subprocess
import sys
from runtime_acceptance import Lab, k, CLUSTER
from run_chapter_021 import StorageLab, LIMITATIONS, log_dirs

CONFIG = {'min.insync.replicas': 2, 'cleanup.policy': 'compact', 'min.cleanable.dirty.ratio': 0.1,
          'min.compaction.lag.ms': 0, 'delete.retention.ms': 86400000,
          'segment.bytes': 1048576, 'segment.ms': 60000}
COMMON = ['effective_compaction_rf3_isr3', 'exact_empty_store_rebuild_to_captured_end',
          'null_tombstone_distinct_from_literal_string', 'final_full_isr_and_config_unchanged']
LIMITS = [item for item in LIMITATIONS if not item.startswith('Retention configuration')] + ['Fresh isolated Jobs rebuild empty in-memory state; no production consumer Deployment/state-PVC crash or atomic checkpoint recovery claim.',
                       'Cleaner progress is observational; no compaction completion, tombstone expiration, legal erasure, installed monitoring metrics or production bootstrap SLO is certified.']


def cleaner_observation(observations):
    matches = [o for o in observations if o.startswith('OBS:CLEANER_PROGRESS:')]
    if not matches:
        raise RuntimeError('Missing cleaner observation')
    match = re.fullmatch(r'OBS:CLEANER_PROGRESS:(OBSERVED|NOT_OBSERVED_WITHIN_BOUND):visible_records=(\d+):acknowledged_records=108', matches[-1])
    if not match:
        raise RuntimeError('Malformed cleaner observation')
    status, count = match[1], int(match[2])
    if not 0 < count <= 108 or (status == 'OBSERVED') != (count < 108):
        raise RuntimeError('Cleaner observation contradicts captured record counts')
    return {'status': status, 'visible_records': count, 'acknowledged_records': 108,
            'completion_guarantee': False, 'source': 'captured-end Kafka consumer snapshots; no JMX metric assumed'}


def main():
    lab = StorageLab('023', LIMITS)
    lab.result['checks'] = {}
    error, phase = None, 'persistent_storage_baseline'
    try:
        lab.prepare()
        before = lab.inventory('before')
        lab.result['storage_before'] = before
        lab.result['checks'][phase] = 'PASS'
        topic = lab.tag + '-compacted'
        lab.apply({'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
                   'metadata': {'name': topic, 'labels': {'strimzi.io/cluster': CLUSTER},
                                'annotations': {'sre.example.com/owner': 'kafka-qa', 'sre.example.com/change-ticket': 'LAB-CH23', 'sre.example.com/data-classification': 'synthetic'}},
                   'spec': {'partitions': 3, 'replicas': 3, 'config': CONFIG}})
        k('wait', f'kafkatopic/{topic}', '--for=condition=Ready', '--timeout=240s', timeout=260)
        stages = []
        for stage in ('seed', 'rebuild'):
            phase = stage + '_client'
            client = Lab('023', LIMITS)
            client.tag, client.image, client.out, client.owned = lab.tag + '-' + stage, lab.image, lab.out / stage, lab.owned
            required = [stage + '_' + check for check in COMMON]
            if stage == 'seed':
                required += ['seed_108_keyed_updates_and_real_null_tombstone_acknowledged',
                             'seed_cleaner_observation_recorded_without_completion_sla']
            try:
                client.run_job('CompactionAcceptance', [topic, lab.tag, stage], required)
            finally:
                lab.result['checks'].update(client.result['checks'])
            stages.append({'stage': stage, 'job': client.tag + '-client', 'observations': client.result['client_observations']})
            lab.result['checks'][phase] = 'PASS'
        lab.result['stages'] = stages
        lab.result['cleaner_progress'] = cleaner_observation(stages[0]['observations'])
        lab.result['pending_assessments'] = {'compaction_completion_deadline': 'NOT_VALIDATED',
                                           'production_state_checkpoint_crash_recovery': 'NOT_VALIDATED',
                                           'tombstone_expiration': 'NOT_VALIDATED', 'independent_security_review': 'PENDING'}
        phase = 'independent_empty_store_rebuild_after_original_job_exit'
        if stages[0]['job'] == stages[1]['job']:
            raise RuntimeError('State rebuild must run in a fresh Job')
        lab.result['checks'][phase] = 'PASS'
        phase = 'effective_cli_policy_and_full_replica_metadata'
        effective = lab.read('effective-config', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-configs.sh',
                             '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', '--entity-type', 'topics', '--entity-name', topic, '--describe')
        actual = dict(re.findall(r'(?:^|\s)([a-z][a-z0-9.]+)=([^,\s]+)', effective))
        if any(actual.get(key) != str(value) for key, value in CONFIG.items()):
            raise RuntimeError('CLI compaction configuration differs from approved manifest')
        raw = lab.read('log-dirs', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-log-dirs.sh',
                       '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', '--describe', '--topic-list', topic)
        lab.result['replica_storage'] = log_dirs(raw, topic)
        lab.result['checks'][phase] = 'PASS'
        phase = 'storage_identity_and_headroom_observed'
        after = lab.inventory('after')
        if before != after:
            raise RuntimeError('Persistent storage identity changed')
        lab.result['storage_after'] = after
        for mapping in after:
            lab.read('df-' + mapping['pod'], 'exec', mapping['pod'], '-c', 'kafka', '--', 'df', '-Pk', mapping['mount'])
        lab.result['checks'][phase] = 'PASS'
        phase = 'kraft_quorum_leader_valid'
        pool = json.loads(lab.read('pool-final', 'get', 'kafkanodepool', 'dual-role', '-o', 'json'))
        quorum = lab.read('quorum', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-metadata-quorum.sh',
                          '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', 'describe', '--status')
        leader = re.search(r'LeaderId:\s+(\d+)', quorum)
        if leader is None or int(leader[1]) not in pool['status']['nodeIds']:
            raise RuntimeError('Invalid KRaft leader')
        lab.result['checks'][phase] = 'PASS'
        lab.result['latest_value_footprint_example'] = {'keys': 50000000, 'bytes_per_latest_record': 300,
            'logical_bytes_lower_bound': 15000000000, 'rf3_bytes_lower_bound': 45000000000,
            'classification': 'ILLUSTRATIVE_LOWER_BOUND_NOT_MEASURED_CAPACITY'}
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'SUPPORTED_ACCEPTANCE_PASS'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError, StopIteration) as exc:
        error = exc
        lab.result['checks'][phase] = 'FAIL'
        print(str(exc), file=sys.stderr)
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
