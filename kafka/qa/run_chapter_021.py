#!/usr/bin/env python3
"""Chapter 021: persistent kind storage inventory and read-only segment acceptance."""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import PurePosixPath
from runtime_acceptance import Lab, k, CTX, NS, CLUSTER

CONFIG = {'min.insync.replicas': 2, 'cleanup.policy': 'delete', 'retention.ms': 3600000,
          'retention.bytes': 16777216, 'segment.bytes': 1048576, 'segment.ms': 60000}
CLIENT_CHECKS = ['effective_retention_segment_and_durability_config',
                 '96_idempotent_acks_all_records_acknowledged',
                 '96_exact_payloads_and_partition_order_reconciled',
                 'all_records_retained_during_bounded_test', 'final_full_isr_and_config_unchanged']
STORAGE_CHECKS = ['persistent_storage_inventory', 'kafka_cli_configs_match', 'quorum_leader_valid',
                  'kafka_log_dirs_9_healthy_replicas', 'physical_segments_rolled_all_replicas',
                  'filesystem_capacity_observed', 'pvc_bindings_unchanged', 'storage_node_pressure_clear']
LIMITATIONS = [
    'Single-node kind local-path host storage is not independently replicated storage or a CSI backend; host/node loss, zone failure and attach/detach failover are NOT_VALIDATED.',
    'PVC requests/bound capacity are allocation metadata; local-path does not enforce a per-volume quota. Filesystem df readings describe the shared host filesystem.',
    'No broker restart, PVC/PV deletion, expansion/shrink, disk fill, corruption, fsync/power-loss or backup/restore test is performed.',
    'Retention configuration and preservation during this bounded run are validated; asynchronous retention deletion timing and consumer replay loss after expiration are NOT_VALIDATED.',
    'No IOPS, throughput, latency, production capacity forecast or storage SLO certification; no installed Prometheus/CSI metrics are assumed.',
    'Broker and controller roles share each local PVC in this disposable fixture; separate controller-volume recovery is NOT_VALIDATED.',
    'Plaintext disposable listener; independent TLS/ACL/security review and enterprise certification remain pending.']


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def quantity_bytes(value):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?', str(value))
    if not match:
        raise ValueError('Unsupported storage quantity: ' + str(value))
    unit = match[2] or ''
    powers = {'': 1, 'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
              'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}
    return Decimal(match[1]) * powers[unit]


def storage_inventory(pool, pods, claims, volumes, classes):
    spec = pool['spec']
    storage = spec['storage']
    require(set(spec['roles']) == {'broker', 'controller'} and spec['replicas'] == 3,
            'Expected three dual-role KRaft nodes')
    require(all(storage.get(key) == value for key, value in {'type': 'persistent-claim', 'size': '1Gi', 'class': 'standard', 'deleteClaim': False}.items()),
            'Expected explicit persistent-claim, 1Gi, standard and deleteClaim=false')
    require(len(pods) == 3, 'Expected exactly three pool Pods')
    mappings, seen = [], set()
    for pod in pods:
        require(pod['metadata'].get('labels', {}).get('strimzi.io/pool-name') == pool['metadata']['name'],
                'Pod does not belong to the verified node pool')
        require(any(c.get('name') == 'kafka' and c.get('ready') for c in pod['status'].get('containerStatuses', [])),
                'Broker container is not Ready')
        data = [v for v in pod['spec']['volumes'] if 'persistentVolumeClaim' in v]
        require(len(data) == 1, 'Expected one actual data PVC reference per broker')
        ref = data[0]
        claim_name = ref['persistentVolumeClaim']['claimName']
        claim = claims[claim_name]
        require(claim_name not in seen, 'Broker PVC unexpectedly shared by Pods')
        seen.add(claim_name)
        require(claim['status']['phase'] == 'Bound' and not claim['metadata'].get('deletionTimestamp'), 'PVC not stably Bound')
        require(claim['spec']['storageClassName'] == storage['class'], 'PVC StorageClass differs from pool')
        require(claim['spec'].get('volumeMode', 'Filesystem') == 'Filesystem' and 'ReadWriteOnce' in claim['spec']['accessModes'],
                'Expected RWO filesystem PVC')
        request = quantity_bytes(claim['spec']['resources']['requests']['storage'])
        require(request == quantity_bytes(storage['size']) and quantity_bytes(claim['status']['capacity']['storage']) >= request,
                'PVC request or bound capacity mismatch')
        pv = volumes[claim['spec']['volumeName']]
        require(pv['status']['phase'] == 'Bound' and pv['spec']['storageClassName'] == storage['class'], 'PV not Bound to expected StorageClass')
        bound = pv['spec']['claimRef']
        require((bound['namespace'], bound['name'], bound['uid']) == (NS, claim_name, claim['metadata']['uid']), 'PV claim UID/reference mismatch')
        require(quantity_bytes(pv['spec']['capacity']['storage']) >= request, 'PV capacity below PVC request')
        sc = classes[storage['class']]
        require(sc['provisioner'] == 'rancher.io/local-path' and sc.get('volumeBindingMode') == 'WaitForFirstConsumer',
                'Expected kind local-path StorageClass with WaitForFirstConsumer')
        require('hostPath' in pv['spec'] or 'local' in pv['spec'], 'Expected known local-path PV backend')
        container = next(c for c in pod['spec']['containers'] if c['name'] == 'kafka')
        mounts = [m for m in container['volumeMounts'] if m['name'] == ref['name']]
        require(len(mounts) == 1 and not mounts[0].get('readOnly', False), 'Kafka data volume mount missing/not writable')
        mount = mounts[0]['mountPath']
        require(PurePosixPath(mount).is_absolute() and '..' not in PurePosixPath(mount).parts, 'Invalid data mount path')
        mappings.append({'pod': pod['metadata']['name'], 'pod_uid': pod['metadata']['uid'],
                         'node': pod['spec']['nodeName'], 'mount': mount,
                         'pvc': claim_name, 'pvc_uid': claim['metadata']['uid'],
                         'pv': pv['metadata']['name'], 'pv_uid': pv['metadata']['uid'],
                         'requested_capacity': claim['spec']['resources']['requests']['storage'],
                         'bound_capacity': claim['status']['capacity']['storage'],
                         'storage_class': sc['metadata']['name'], 'provisioner': sc['provisioner'],
                         'binding_mode': sc['volumeBindingMode'], 'reclaim_policy': sc.get('reclaimPolicy'),
                         'allow_volume_expansion': sc.get('allowVolumeExpansion', False),
                         'pv_node_affinity': pv['spec'].get('nodeAffinity'),
                         'backend': 'hostPath' if 'hostPath' in pv['spec'] else 'local'})
    return sorted(mappings, key=lambda item: item['pod'])


def safe_partition_path(directory, mount, topic, partition, chapter="021"):
    root, base = PurePosixPath(directory), PurePosixPath(mount)
    require(root.is_absolute() and '..' not in root.parts and root.is_relative_to(base),
            'Kafka log directory is outside verified PVC mount')
    require(re.fullmatch(r'\d{3}', chapter) is not None and re.fullmatch(rf'ch{chapter}-[a-f0-9]{{12}}-storage', topic) and partition in range(3), 'Unowned topic/partition inspection target')
    return str(root / f'{topic}-{partition}')


def log_dirs(output, topic):
    # Kafka's supported CLI emits an informational preamble before the JSON object.
    decoder = json.JSONDecoder()
    for line in output.splitlines():
        if line.lstrip().startswith('{'):
            parsed = decoder.decode(line)
            break
    else:
        raise RuntimeError('No Kafka log-dir JSON in CLI output')
    replicas, ids = [], set()
    for broker in parsed['brokers']:
        require(broker['broker'] not in ids, 'Duplicate broker in log-dir metadata')
        ids.add(broker['broker'])
        for directory in broker['logDirs']:
            require(directory.get('error') is None, 'Kafka reported a storage error')
            for partition in directory['partitions']:
                if partition['partition'].startswith(topic + '-'):
                    number = int(partition['partition'][len(topic) + 1:])
                    require(number in range(3) and partition['size'] > 0 and not partition['isFuture'], 'Invalid/future/empty replica log')
                    replicas.append({'broker': broker['broker'], 'directory': directory['logDir'], 'partition': number,
                                     'bytes': partition['size'], 'offset_lag': partition['offsetLag']})
    require(len(ids) == 3 and len(replicas) == 9 and len({(r['broker'], r['partition']) for r in replicas}) == 9,
            'Expected three healthy replicas of each of three topic partitions')
    return replicas


def segment_files(output):
    files = {}
    for line in output.splitlines():
        name, size = line.split()
        if re.fullmatch(r'\d{20}\.(?:log|index|timeindex|txnindex)', name):
            files[name] = int(size)
    logs = {name: size for name, size in files.items() if name.endswith('.log')}
    require(len([size for size in logs.values() if size > 0]) >= 2, 'Physical segment rolling not observed')
    for name in logs:
        stem = name[:-4]
        require(stem + '.index' in files and stem + '.timeindex' in files, 'Missing matching segment index metadata')
    return files


class StorageLab(Lab):
    def __init__(self, chapter='021', limitations=None):
        super().__init__(chapter, LIMITATIONS if limitations is None else limitations)
        self.result['checks'].update({name: 'NOT_RUN' for name in STORAGE_CHECKS + CLIENT_CHECKS})

    def read(self, label, *args):
        self.out.mkdir(parents=True, exist_ok=True)
        event = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                 'command': ['kubectl', '--context', CTX, '-n', NS, *args],
                 'expected': 'successful read-only observation: ' + label,
                 'reviewer': 'automated-harness; independent assessment pending',
                 'evidence_path': f'chapter-{self.chapter}-{label}.txt', 'status': 'FAIL'}
        self.result['actions'].append(event)
        try:
            output = k(*args, timeout=90)
            (self.out / event['evidence_path']).write_text(output, encoding='utf-8')
            event.update({'status': 'PASS', 'observed': 'captured in evidence_path'})
            return output
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            event['observed'] = str(exc)
            raise

    def inventory(self, label):
        pool = json.loads(self.read(label + '-pool', 'get', 'kafkanodepool', 'dual-role', '-o', 'json'))
        pods = json.loads(self.read(label + '-pods', 'get', 'pods', '-l', f'strimzi.io/cluster={CLUSTER},strimzi.io/pool-name=dual-role', '-o', 'json'))['items']
        claims, volumes, classes = {}, {}, {}
        for pod in pods:
            for ref in pod['spec']['volumes']:
                if 'persistentVolumeClaim' not in ref:
                    continue
                name = ref['persistentVolumeClaim']['claimName']
                claim = json.loads(self.read(label + '-' + name, 'get', 'pvc', name, '-o', 'json'))
                claims[name] = claim
                pv_name = claim['spec']['volumeName']
                volumes[pv_name] = json.loads(self.read(label + '-' + pv_name, 'get', 'pv', pv_name, '-o', 'json'))
                sc_name = claim['spec']['storageClassName']
                if sc_name not in classes:
                    classes[sc_name] = json.loads(self.read(label + '-storageclass', 'get', 'storageclass', sc_name, '-o', 'json'))
        return storage_inventory(pool, pods, claims, volumes, classes)


def main():
    lab, error, phase = StorageLab(), None, 'persistent_storage_inventory'
    try:
        lab.prepare()
        before = lab.inventory('before')
        lab.result['storage_before'] = before
        lab.result['checks'][phase] = 'PASS'
        topic = lab.tag + '-storage'
        lab.apply({'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
                   'metadata': {'name': topic, 'labels': {'strimzi.io/cluster': CLUSTER}},
                   'spec': {'partitions': 3, 'replicas': 3, 'config': CONFIG}})
        k('wait', f'kafkatopic/{topic}', '--for=condition=Ready', '--timeout=240s', timeout=260)
        phase = 'client_job_complete'
        lab.run_job('StorageAcceptance', [topic, lab.tag], CLIENT_CHECKS)
        lab.result['checks'][phase] = 'PASS'
        def cli(label, tool, *args):
            return lab.read(label, 'exec', lab.pod, '-c', 'kafka', '--',
                            f'/opt/kafka/bin/kafka-{tool}.sh', '--bootstrap-server', CLUSTER + '-kafka-bootstrap:9092', *args)
        phase = 'kafka_cli_configs_match'
        configs = cli('effective-config', 'configs', '--entity-type', 'topics', '--entity-name', topic, '--describe')
        actual = dict(re.findall(r'(?:^|\s)([a-z][a-z0-9.]+)=([^,\s]+)', configs))
        require(all(actual.get(name) == str(value) for name, value in CONFIG.items()), 'Kafka CLI effective config differs from manifest')
        lab.result['checks'][phase] = 'PASS'
        cli('topic-description', 'topics', '--describe', '--topic', topic)
        phase = 'quorum_leader_valid'
        quorum = cli('quorum', 'metadata-quorum', 'describe', '--status')
        leader = re.search(r'LeaderId:\s+(\d+)', quorum)
        nodes = {}
        for observation in lab.result['client_observations']:
            if observation.startswith('OBS:NODE:'):
                _, _, broker_id, host = observation.split(':', 3)
                nodes[int(broker_id)] = host.split('.')[0]
        require(len(nodes) == 3 and leader is not None and int(leader[1]) in nodes, 'Invalid quorum leader/broker map')
        lab.result['checks'][phase] = 'PASS'
        phase = 'kafka_log_dirs_9_healthy_replicas'
        replicas = log_dirs(cli('log-dirs', 'log-dirs', '--describe', '--topic-list', topic), topic)
        lab.result['replica_storage'] = replicas
        lab.result['checks'][phase] = 'PASS'
        phase = 'physical_segments_rolled_all_replicas'
        mappings = {item['pod']: item for item in before}
        observations = []
        for replica in replicas:
            require(replica['broker'] in nodes and nodes[replica['broker']] in mappings, 'Broker not mapped to verified PVC Pod')
            mapping = mappings[nodes[replica['broker']]]
            path = safe_partition_path(replica['directory'], mapping['mount'], topic, replica['partition'])
            listing = lab.read(f'segments-{replica["broker"]}-{replica["partition"]}', 'exec', mapping['pod'], '-c', 'kafka', '--',
                               'find', path, '-maxdepth', '1', '-type', 'f', '-printf', '%f %s\n')
            observations.append({'pod': mapping['pod'], 'pvc_uid': mapping['pvc_uid'], 'partition_path': path, 'files': segment_files(listing)})
        lab.result['physical_segment_observations'] = observations
        lab.result['checks'][phase] = 'PASS'
        phase = 'filesystem_capacity_observed'
        for mapping in before:
            for flag, suffix in (('-Pk', 'blocks'), ('-Pi', 'inodes')):
                output = lab.read(f'df-{mapping["pod"]}-{suffix}', 'exec', mapping['pod'], '-c', 'kafka', '--', 'df', flag, mapping['mount'])
                require(len(output.splitlines()) >= 2, 'No filesystem capacity observation')
        lab.result['checks'][phase] = 'PASS'
        phase = 'pvc_bindings_unchanged'
        after = lab.inventory('after')
        lab.result['storage_after'] = after
        require(before == after, 'PVC/PV identity or storage mapping changed during workload')
        lab.result['checks'][phase] = 'PASS'
        phase = 'storage_node_pressure_clear'
        for name in sorted({mapping['node'] for mapping in before}):
            node = json.loads(lab.read('node-' + name, 'get', 'node', name, '-o', 'json'))
            conditions = {c['type']: c['status'] for c in node['status']['conditions']}
            require(conditions.get('Ready') == 'True' and conditions.get('DiskPressure') == 'False', 'Node not Ready or reports DiskPressure')
        lab.result['checks'][phase] = 'PASS'
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'SUPPORTED_ACCEPTANCE_PASS'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError, StopIteration) as exc:
        lab.result['checks'][phase] = 'FAIL'
        error = exc
        print(str(exc), file=sys.stderr)
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
