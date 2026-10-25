#!/usr/bin/env python3
"""Chapter 020: transactional application scaling, rollout and Pod recovery."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from runtime_acceptance import Lab, k, CTX, NS
from run_chapter_019 import CHECKS as TRANSACTION_CHECKS, LIMITATIONS


def worker_manifest(name, image, source, args):
    return {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': name},
            'spec': {'replicas': 1, 'selector': {'matchLabels': {'app': name}},
                     'strategy': {'type': 'RollingUpdate', 'rollingUpdate': {'maxUnavailable': 0, 'maxSurge': 1}},
                     'template': {'metadata': {'labels': {'app': name}}, 'spec': {
                         'terminationGracePeriodSeconds': 60, 'automountServiceAccountToken': False,
                         'volumes': [{'name': 'source', 'configMap': {'name': source}}],
                         'containers': [{'name': 'consumer', 'image': image,
                             'command': ['java', '-Xmx256m', '-cp', '/opt/kafka/libs/*', '/qa/TransactionAcceptance.java', *args, 'worker'],
                             'volumeMounts': [{'name': 'source', 'mountPath': '/qa', 'readOnly': True}],
                             'readinessProbe': {'exec': {'command': ['test', '-f', '/tmp/qa-ready']}, 'periodSeconds': 3, 'timeoutSeconds': 2},
                             'resources': {'requests': {'cpu': '100m', 'memory': '256Mi'}, 'limits': {'cpu': '1', 'memory': '512Mi'}}}]}}}}


def verify_pod_owner(pod, replica_set, deployment):
    refs = pod['metadata'].get('ownerReferences', [])
    owners = replica_set['metadata'].get('ownerReferences', [])
    return (not pod['metadata'].get('deletionTimestamp')
            and any(r.get('controller') and r['kind'] == 'ReplicaSet' and r['uid'] == replica_set['metadata']['uid'] for r in refs)
            and any(r.get('controller') and r['kind'] == 'Deployment' and r['uid'] == deployment['metadata']['uid'] for r in owners))


def main():
    lab = Lab('020', LIMITATIONS + ['Measured recovery includes test observation overhead; no business RTO/SLO target or independent assessor signoff.',
                                 'Application is a bounded Kafka-to-Kafka test workload; no external sink or production application certification.'])
    error = None
    stream = None
    stream_file = None
    try:
        lab.prepare()
        txn_input, txn_output = lab.topic('txn-input'), lab.topic('txn-output')
        lab.run_job('TransactionAcceptance', [txn_input, txn_output, lab.tag + '-txn-group', lab.tag + '-txn'], TRANSACTION_CHECKS)
        source = lab.tag + '-source'
        source_topic, output = lab.topic('app-input'), lab.topic('app-output')
        group, name = lab.tag + '-app-group', lab.tag + '-app'
        args = [source_topic, output, group, lab.tag]
        observer = lab.tag + '-observer'
        lab.apply({'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': observer}, 'spec': {
            'automountServiceAccountToken': False, 'restartPolicy': 'Never',
            'volumes': [{'name': 'source', 'configMap': {'name': source}}],
            'containers': [{'name': 'observer', 'image': lab.image, 'command': ['sleep', '3600'],
                            'volumeMounts': [{'name': 'source', 'mountPath': '/qa', 'readOnly': True}],
                            'resources': {'requests': {'cpu': '100m', 'memory': '128Mi'}, 'limits': {'cpu': '1', 'memory': '512Mi'}}}]}})
        k('wait', f'pod/{observer}', '--for=condition=Ready', '--timeout=180s', timeout=200)
        lab.out.mkdir(parents=True, exist_ok=True)

        def observed(label, command, expected, operation):
            event = {'planned_action': label, 'command': command,
                     'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'expected': expected,
                     'reviewer': 'automated-harness; independent review pending', 'status': 'FAIL',
                     'evidence_path': f'chapter-020-{label}.txt'}
            lab.result['actions'].append(event)
            value = operation()
            (lab.out / event['evidence_path']).write_text(str(value), encoding='utf-8')
            event.update({'observed': str(value)[-3000:], 'status': 'PASS'})
            lab.result['checks'][label] = 'PASS'
            return value

        def client(mode, total, start=None):
            command = ['exec', observer, '--', 'java', '-Xmx256m', '-cp', '/opt/kafka/libs/*',
                       '/qa/TransactionAcceptance.java', *args, mode, str(total)]
            if start is not None:
                command.append(str(start))
            return k(*command, timeout=100)

        def await_client(mode, total, marker, timeout=120):
            deadline, last = time.monotonic() + timeout, ''
            while time.monotonic() < deadline:
                try:
                    last = client(mode, total)
                    if marker + str(total) in last:
                        return last
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    last = str(exc)
                time.sleep(2)
            raise RuntimeError(f'{mode} did not converge: {last}')

        def members(count):
            return observed(f'members-{len(lab.result["actions"])}-{count}',
                            ['Admin.describeConsumerGroups', group], f'{count} stable members, three exclusive assignments',
                            lambda: await_client('members', count, 'MEMBERS_OK:'))

        def reconcile(total):
            return observed(f'reconcile-{len(lab.result["actions"])}-{total}',
                            ['read_committed', source_topic, output, 'Admin.listConsumerGroupOffsets', group],
                            f'{total} exact input/output IDs, partition order and matching transactional offsets',
                            lambda: await_client('verify', total, 'VERIFIED_OK:'))

        def scale(count):
            k('scale', f'deployment/{name}', f'--replicas={count}')
            k('rollout', 'status', f'deployment/{name}', '--timeout=240s', timeout=260)
            members(count)

        lab.apply(worker_manifest(name, lab.image, source, args))
        k('rollout', 'status', f'deployment/{name}', '--timeout=240s', timeout=260)
        members(1)
        observed('seed-baseline', ['KafkaProducer', source_topic, '0..5'], 'six acknowledged events', lambda: client('seed', 6, 0))
        reconcile(6)
        scale(2)
        reconcile(6)
        observed('seed-scale', ['KafkaProducer', source_topic, '6..11'], 'six more acknowledged events', lambda: client('seed', 12, 6))
        scale(3)
        reconcile(12)
        # Follow the existing Pods before replacement, preserving their shutdown evidence.
        stream_file = (lab.out / 'chapter-020-rollout-shutdown.log').open('w', encoding='utf-8')
        stream = subprocess.Popen(['kubectl', '--context', CTX, '-n', NS, 'logs', '-f', '-l', f'app={name}',
                                   '--prefix', '--max-log-requests=5', '--tail=100'], stdout=stream_file, stderr=subprocess.STDOUT, text=True)
        time.sleep(2)
        if stream.poll() is not None:
            raise RuntimeError('Could not start application log capture before rollout')
        observed('rolling-update', ['kubectl', 'rollout', 'restart', f'deployment/{name}'],
                 'replacement Pods ready, stable group and reconciled progress',
                 lambda: k('rollout', 'restart', f'deployment/{name}'))
        k('rollout', 'status', f'deployment/{name}', '--timeout=240s', timeout=260)
        members(3)
        reconcile(12)
        try:
            stream.wait(timeout=20)
        except subprocess.TimeoutExpired:
            stream.terminate()
            stream.wait(timeout=10)
        stream_file.close()
        shutdown = (lab.out / 'chapter-020-rollout-shutdown.log').read_text()
        if shutdown.count('GRACEFUL_CLOSE') < 3:
            raise RuntimeError('Missing graceful shutdown evidence for three replaced consumers: ' + shutdown[-3000:])
        lab.result['checks']['rolling_update_three_graceful_closes'] = 'PASS'
        scale(1)
        reconcile(12)
        pods = json.loads(k('get', 'pods', '-l', f'app={name}', '-o', 'json'))['items']
        active = [p for p in pods if not p['metadata'].get('deletionTimestamp')]
        if len(active) != 1:
            raise RuntimeError('Expected one active disposable application Pod')
        pod = active[0]
        rs_name = next(r['name'] for r in pod['metadata']['ownerReferences'] if r['kind'] == 'ReplicaSet' and r.get('controller'))
        rs = json.loads(k('get', 'replicaset', rs_name, '-o', 'json'))
        deploy = json.loads(k('get', 'deployment', name, '-o', 'json'))
        if not verify_pod_owner(pod, rs, deploy):
            raise RuntimeError('Application Pod ownership verification failed')
        pod_name, old_uid = pod['metadata']['name'], pod['metadata']['uid']
        k('exec', pod_name, '--', 'touch', '/tmp/qa-hold')
        observed('seed-recovery', ['KafkaProducer', source_topic, '12..17'], 'six acknowledged records held before processing', lambda: client('seed', 18, 12))
        until = time.monotonic() + 60
        while 'INFLIGHT_READY' not in k('logs', pod_name, '--tail=100'):
            if time.monotonic() > until:
                raise RuntimeError('Consumer did not reach controlled pre-commit hold')
            time.sleep(1)
        observed('no-premature-progress', ['Admin.listConsumerGroupOffsets', group, 'read_committed', output],
                 'offsets and output stay at 12 while six new inputs await completion',
                 lambda: await_client('progress', 12, 'PROGRESS_OK:'))
        started = time.monotonic()
        observed('delete-one-owned-application-pod', ['kubectl', 'delete', 'pod', pod_name],
                 'only selected disposable consumer Pod deleted', lambda: k('delete', 'pod', pod_name, '--wait=true', '--timeout=90s', timeout=100))
        k('rollout', 'status', f'deployment/{name}', '--timeout=240s', timeout=260)
        members(1)
        reconcile(18)
        replacements = json.loads(k('get', 'pods', '-l', f'app={name}', '-o', 'json'))['items']
        new_uids = [p['metadata']['uid'] for p in replacements if not p['metadata'].get('deletionTimestamp')]
        if len(new_uids) != 1 or new_uids[0] == old_uid:
            raise RuntimeError('Application Pod was not replaced')
        lab.result['recovery'] = {'old_pod_uid': old_uid, 'new_pod_uid': new_uids[0],
                                  'measured_seconds_including_observation': round(time.monotonic() - started, 3),
                                  'production_rto_status': 'NOT_ASSESSED'}
        lab.result['checks']['application_pod_replaced_uncommitted_input_recovered'] = 'PASS'
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'SUPPORTED_ACCEPTANCE_PASS'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError, StopIteration) as exc:
        error = exc
        print(str(exc), file=sys.stderr)
    finally:
        if stream is not None and stream.poll() is None:
            stream.terminate()
            stream.wait(timeout=10)
        if stream_file is not None and not stream_file.closed:
            stream_file.close()
    if lab.safe and 'name' in locals():
        try:
            (lab.out / 'chapter-020-application.log').write_text(k('logs', '-l', f'app={name}', '--prefix', '--tail=1000', '--max-log-requests=5', timeout=25), encoding='utf-8')
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            lab.result.setdefault('diagnostic_errors', []).append(str(exc))
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
