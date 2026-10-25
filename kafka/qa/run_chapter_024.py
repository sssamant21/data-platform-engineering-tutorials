#!/usr/bin/env python3
"""Chapter 024 local compatibility preflight; remote integration explicitly unexecuted."""
import json
import re
import subprocess
import sys
from runtime_acceptance import k, CLUSTER
from run_chapter_021 import StorageLab, LIMITATIONS

CHECKS = ['all_brokers_remote_feature_disabled_no_toggles', 'local_baseline_topic_rf3_isr3_remote_disabled',
          'six_local_records_reconciled_not_remote_read_proof']
REQUIRED_REVIEW = ('reviewed_plugin_artifact_digest', 'reviewed_metadata_manager', 'approved_disposable_bucket',
                   'approved_workload_identity', 'approved_private_endpoint', 'kms_and_audit_review',
                   'supported_image_build_and_upgrade_plan', 'reviewed_remote_local_retention_relationship')


def integration_gate(review):
    missing = [name for name in REQUIRED_REVIEW if not review.get(name)]
    digest = review.get('reviewed_plugin_artifact_digest', '')
    if digest and not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        missing.append('valid_immutable_plugin_digest')
    return {'ready_for_conditional_integration': not missing, 'missing_prerequisites': missing,
            'status': 'REVIEW_INPUTS_COMPLETE_NOT_RUNTIME_PROOF' if not missing else 'NOT_EXECUTED_MISSING_REVIEWED_PREREQUISITES'}


def capacity_example(rate=8*1024**2, retention_days=30, copy_factor=1):
    if min(rate, retention_days, copy_factor) <= 0:
        raise ValueError('Positive forecast inputs required')
    daily = rate*86400*copy_factor
    return {'daily_logical_bytes': daily, 'retained_logical_bytes_before_overhead': daily*retention_days,
            'classification': 'ILLUSTRATIVE_NOT_MEASURED_OR_PRICED', 'provider_request_egress_kms_costs': 'NOT_ESTIMATED_NO_PROVIDER_INPUTS'}


def main():
    limits = [item for item in LIMITATIONS if not item.startswith('Retention configuration')]
    limits += ['Labs G/H/I: no reviewed RemoteStorageManager artifact or isolated cloud bucket has been supplied; offload, remote reads, IAM denial tests and disaster recovery are NOT_EXECUTED.',
               'Passing preflight means local metadata and disabled-feature gates only. Kafka/Strimzi feature support does not establish plugin/provider compatibility.',
               'No cloud-cost bill, legal/security approval, remote-copy/read latency, RPO/RTO or enterprise certification is established.']
    lab = StorageLab('024', limits)
    lab.result['checks'] = {}
    error, phase = None, 'persistent_storage_baseline'
    try:
        lab.prepare()
        before = lab.inventory('before')
        lab.result['storage_before'] = before
        lab.result['checks'][phase] = 'PASS'
        phase = 'exact_operator_broker_client_and_crd_inventory'
        deployment = json.loads(lab.read('operator', 'get', 'deployment', 'strimzi-cluster-operator', '-o', 'json'))
        operator_images = [c['image'] for c in deployment['spec']['template']['spec']['containers']]
        if not any(image.endswith('/operator:0.47.0') for image in operator_images):
            raise RuntimeError('Unexpected operator image/version')
        version = lab.read('client-version', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-topics.sh', '--version')
        if not re.search(r'\b4\.0\.0\b', version):
            raise RuntimeError('Client version is not 4.0.0')
        pods = json.loads(lab.read('broker-images', 'get', 'pods', '-l', f'strimzi.io/cluster={CLUSTER},strimzi.io/pool-name=dual-role', '-o', 'json'))['items']
        images = []
        for pod in pods:
            status = next(c for c in pod['status']['containerStatuses'] if c['name']=='kafka')
            image = next(c['image'] for c in pod['spec']['containers'] if c['name']=='kafka')
            if 'sha256:' not in status.get('imageID', ''):
                raise RuntimeError('Missing immutable broker image identity')
            images.append({'pod': pod['metadata']['name'], 'image': image, 'image_id': status['imageID']})
        crd = json.loads(lab.read('topic-crd', 'get', 'crd', 'kafkatopics.kafka.strimzi.io', '-o', 'json'))
        served = [v['name'] for v in crd['spec']['versions'] if v.get('served')]
        if 'v1beta2' not in served:
            raise RuntimeError('Fixture KafkaTopic API not served')
        lab.result['compatibility_inventory'] = {'broker_version_from_cr': '4.0.0', 'client_version': version.strip(),
            'operator_images': operator_images, 'broker_images': images, 'served_topic_apis': served,
            'plugin_provider_compatibility': 'NOT_ESTABLISHED_NO_REVIEWED_ARTIFACT',
            'metadata_manager_recovery_compatibility': 'NOT_REVIEWED'}
        lab.result['checks'][phase] = 'PASS'
        phase = 'local_only_client_preflight'
        topic = lab.topic('local-baseline')
        lab.run_job('TieredPreflight', [topic, lab.tag], CHECKS)
        lab.result['checks'][phase] = 'PASS'
        phase = 'missing_prerequisites_fail_closed'
        gate = integration_gate({})
        if gate['ready_for_conditional_integration']:
            raise RuntimeError('Missing review must never enable conditional integration')
        lab.result['conditional_integration'] = {'gate': gate, 'lab_G_bucket_identity': 'NOT_EXECUTED',
            'lab_H_offload': 'NOT_EXECUTED', 'lab_I_remote_read_recovery': 'NOT_EXECUTED',
            'dr_rpo_rto': 'NOT_TESTED', 'feature_toggles_performed': False, 'cloud_operations_performed': False}
        lab.result['checks'][phase] = 'PASS'
        phase = 'storage_identity_and_read_only_headroom'
        after = lab.inventory('after')
        if before != after:
            raise RuntimeError('Storage identities changed during preflight')
        lab.result['storage_after'] = after
        for mapping in after:
            lab.read('df-' + mapping['pod'], 'exec', mapping['pod'], '-c', 'kafka', '--', 'df', '-Pk', mapping['mount'])
        lab.result['checks'][phase] = 'PASS'
        phase = 'kraft_quorum_read_only'
        quorum = lab.read('quorum', 'exec', lab.pod, '-c', 'kafka', '--', '/opt/kafka/bin/kafka-metadata-quorum.sh',
                          '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', 'describe', '--status')
        if not re.search(r'LeaderId:\s+\d+', quorum):
            raise RuntimeError('No valid KRaft leader in preflight')
        lab.result['checks'][phase] = 'PASS'
        lab.result['capacity_example'] = capacity_example()
        lab.result['dr_dependencies_not_restored'] = ['KRaft identity/metadata', 'consumer offsets and transaction state',
            'topic/ACL/GitOps definitions', 'remote-log metadata', 'KMS and workload identity', 'active segments not yet copied']
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'LOCAL_BASELINE_AND_COMPATIBILITY_GATE_ONLY'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError, StopIteration) as exc:
        error = exc
        lab.result['checks'][phase] = 'FAIL'
        print(str(exc), file=sys.stderr)
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
