"""Bounded disposable-kind harness shared by Chapters 019 and 020."""
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CTX, NS, CLUSTER = 'kind-kafka-qa', 'kafka-qa', 'qa-kafka-ha'


def k(*args, data=None, timeout=90):
    result = subprocess.run(['kubectl', '--context', CTX, '-n', NS, *args],
                            input=data, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'kubectl {args[0]}: {result.stderr[-4000:]} {result.stdout[-4000:]}')
    return result.stdout


def job_manifest(name, image, sources, main, args):
    return {'apiVersion': 'batch/v1', 'kind': 'Job', 'metadata': {'name': name},
            'spec': {'backoffLimit': 0, 'activeDeadlineSeconds': 600, 'template': {'metadata': {'labels': {'app': name}}, 'spec': {
                'restartPolicy': 'Never', 'automountServiceAccountToken': False,
                'terminationGracePeriodSeconds': 30,
                'volumes': [{'name': 'source', 'configMap': {'name': sources}}],
                'containers': [{'name': 'client', 'image': image,
                    'command': ['java', '-Xmx256m', '-cp', '/opt/kafka/libs/*', '/qa/' + main + '.java', *args],
                    'volumeMounts': [{'name': 'source', 'mountPath': '/qa', 'readOnly': True}],
                    'resources': {'requests': {'cpu': '100m', 'memory': '256Mi'},
                                  'limits': {'cpu': '1', 'memory': '512Mi'}}}]}}}}


class Lab:
    def __init__(self, chapter, limitations):
        self.chapter = chapter
        self.tag = f'ch{chapter}-' + uuid.uuid4().hex[:12]
        self.out = ROOT / 'kafka/qa/evidence'
        self.owned = []
        self.safe = False
        self.result = {'chapter': chapter, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                       'head_commit': os.environ.get('QA_HEAD_SHA', os.environ.get('GITHUB_SHA')),
                       'checkout_commit': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('GITHUB_RUN_ID'),
                       'status': 'FAIL', 'certification': 'NOT_CERTIFIED', 'checks': {},
                       'versions': {'kafka': '4.0.0', 'strimzi': '0.47.0', 'mode': 'KRaft'},
                       'limitations': limitations, 'resources': self.owned, 'actions': []}

    def prepare(self):
        context = subprocess.run(['kubectl', 'config', 'current-context'], check=True,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError('Unsafe Kubernetes context')
        node = json.loads(k('get', 'node', 'kafka-qa-control-plane', '-o', 'json'))
        if node['metadata'].get('labels', {}).get('kubernetes.io/hostname') != 'kafka-qa-control-plane':
            raise RuntimeError('Expected disposable kind control plane')
        self.safe = True
        k('wait', f'kafka/{CLUSTER}', '--for=condition=Ready', '--timeout=600s', timeout=630)
        kafka = json.loads(k('get', 'kafka', CLUSTER, '-o', 'json'))['spec']['kafka']
        expected = {'default.replication.factor': 3, 'min.insync.replicas': 2,
                    'offsets.topic.replication.factor': 3, 'transaction.state.log.replication.factor': 3,
                    'transaction.state.log.min.isr': 2}
        if kafka['version'] != '4.0.0' or any(kafka['config'].get(key) != value for key, value in expected.items()):
            raise RuntimeError('Unexpected Kafka version or durability settings')
        pods = json.loads(k('get', 'pods', '-l', f'strimzi.io/cluster={CLUSTER}', '-o', 'json'))['items']
        brokers = [p for p in pods if '-dual-role-' in p['metadata']['name'] and
                   any(c.get('name') == 'kafka' and c.get('ready') for c in p['status'].get('containerStatuses', []))]
        if len(brokers) != 3:
            raise RuntimeError('Expected three ready brokers')
        self.pod = brokers[0]['metadata']['name']
        self.image = next(c['image'] for c in brokers[0]['spec']['containers'] if c['name'] == 'kafka')
        self.result['client_image'] = self.image
        self.result['checks']['pinned_version_and_durability_preflight'] = 'PASS'

    def apply(self, manifest):
        name = manifest['metadata']['name']
        # Register before creation so cleanup also covers ambiguous API timeouts.
        self.owned.append({'kind': manifest['kind'], 'name': name})
        k('apply', '-f', '-', data=json.dumps(manifest))
        return name

    def topic(self, suffix):
        name = self.tag + '-' + suffix
        self.apply({'apiVersion': 'kafka.strimzi.io/v1beta2', 'kind': 'KafkaTopic',
                    'metadata': {'name': name, 'labels': {'strimzi.io/cluster': CLUSTER}},
                    'spec': {'partitions': 3, 'replicas': 3, 'config': {'min.insync.replicas': 2, 'retention.ms': 600000}}})
        k('wait', f'kafkatopic/{name}', '--for=condition=Ready', '--timeout=240s', timeout=260)
        return name

    def source(self, main):
        name = self.tag + '-source'
        self.apply({'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': name},
                    'data': {main + '.java': (ROOT / 'kafka/qa/runtime' / (main + '.java')).read_text(encoding='utf-8-sig')}})
        return name

    def run_job(self, main, args, required):
        source = self.source(main)
        name = self.tag + '-client'
        self.apply(job_manifest(name, self.image, source, main, args))
        deadline = time.monotonic() + 610
        while time.monotonic() < deadline:
            job = json.loads(k('get', 'job', name, '-o', 'json'))
            conditions = {c['type']: c['status'] for c in job.get('status', {}).get('conditions', [])}
            if conditions.get('Failed') == 'True':
                raise RuntimeError('Client Job failed: ' + k('logs', 'job/' + name, '--tail=150', timeout=20))
            if conditions.get('Complete') == 'True':
                break
            time.sleep(3)
        else:
            raise RuntimeError('Client Job exceeded bounded deadline')
        log = k('logs', 'job/' + name, '--tail=1500', timeout=25)
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / f'chapter-{self.chapter}-client.log').write_text(log, encoding='utf-8')
        for check in required:
            if f'CHECK:{check}:PASS' not in log:
                raise RuntimeError('Missing client assertion: ' + check)
            self.result['checks'][check] = 'PASS'
        self.result['client_observations'] = [x for x in log.splitlines() if x.startswith(('OBS:', 'CHECK:'))]

    def finish(self, error=None):
        if error:
            self.result['error'] = str(error)
        self.out.mkdir(parents=True, exist_ok=True)
        if self.safe:
            for label, args in [('resources', ('get', 'pods,jobs,deployments,kafka,kafkatopic', '-o', 'wide')),
                                ('events', ('get', 'events', '--sort-by=.metadata.creationTimestamp')),
                                ('operator', ('logs', 'deployment/strimzi-cluster-operator', '--tail=150')),
                                ('clients', ('logs', '-l', f'app={self.tag}-client', '--all-containers', '--tail=1500'))]:
                try:
                    (self.out / f'chapter-{self.chapter}-{label}.txt').write_text(k(*args, timeout=25), encoding='utf-8')
                except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    self.result.setdefault('diagnostic_errors', []).append(str(exc))
            for resource in reversed(self.owned):
                try:
                    k('delete', resource['kind'], resource['name'], '--ignore-not-found', '--wait=false', timeout=20)
                except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    self.result.setdefault('cleanup_errors', []).append(str(exc))
                    self.result['status'] = 'FAIL'
        (self.out / f'chapter-{self.chapter}-runtime.json').write_text(json.dumps(self.result, indent=2) + '\n', encoding='utf-8')
        return 0 if self.result['status'] == 'PASS' else 1
