"""Secret-safe projections, credential Job isolation and TLS listener contracts."""
import copy
import unittest
import json
import tempfile
from pathlib import Path
from runtime_acceptance import job_manifest
import security_acceptance as security
import run_chapter_027 as chapter
import select_changed_chapters as selector


class TlsTests(unittest.TestCase):
    def test_secret_inventory_accepts_only_metadata_and_key_names(self):
        text='name:client\nuid:opaque-uid\nresourceVersion:123\nkey:user.p12\nkey:user.password\n'
        data=security.parse_secret_metadata(text)
        self.assertEqual(data['keys'],['user.p12','user.password'])
        with self.assertRaises(RuntimeError):security.parse_secret_metadata('name:client\nvalue:not-allowed\n')
        self.assertNotIn('printf "%s" $value',security.SECRET_METADATA_TEMPLATE)

    def test_credential_mounts_are_non_root_read_only_without_api_token(self):
        job=job_manifest('test','pinned@sha256:abc','source','Main',[])
        secured=security.secure_client_job(job,'client-sa','cluster-ca-cert','identity',['user.p12','user.password'])
        pod=secured['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken']);self.assertEqual(pod['serviceAccountName'],'client-sa')
        self.assertTrue(pod['securityContext']['runAsNonRoot']);self.assertEqual(pod['securityContext']['fsGroup'],1001)
        secret_volumes=[v for v in pod['volumes'] if 'secret' in v]
        self.assertEqual(len(secret_volumes),2)
        self.assertTrue(all(v['secret']['defaultMode']==0o440 for v in secret_volumes))
        self.assertTrue(all(v['readOnly'] for v in pod['containers'][0]['volumeMounts']))
        self.assertNotIn('env',pod['containers'][0]);self.assertNotIn('serviceAccountName',job['spec']['template']['spec'])

    def test_only_pullable_verified_image_digest_is_accepted(self):
        image='quay.io/strimzi/kafka@sha256:'+'a'*64
        self.assertEqual(security.immutable_kafka_image('docker-pullable://'+image),image)
        for bad in ['quay.io/strimzi/kafka:latest','containerd://sha256:'+'a'*64,'other.example/image@sha256:'+'a'*64]:
            with self.assertRaises(RuntimeError):security.immutable_kafka_image(bad)

    def test_private_material_is_redacted_but_public_metadata_and_hidden_properties_are_safe(self):
        text='-----BEGIN PRIVATE KEY-----\nsynthetic-not-a-key\n-----END PRIVATE KEY-----\nuser.p12: encoded-fake\nssl.keystore.password = fake-password\n'
        clean,changed=security.redact_private_material(text)
        self.assertTrue(changed);self.assertNotIn('synthetic-not-a-key',clean);self.assertNotIn('fake-password',clean)
        self.assertNotIn('encoded-fake',clean)
        _,again=security.redact_private_material(clean);self.assertFalse(again)
        safe='OBS:CERT:client:sha256='+'a'*64+'\nssl.keystore.password = [hidden]\nkey:user.password\n'
        self.assertFalse(security.redact_private_material(safe)[1])
        self.assertTrue(security.redact_private_material('{"user.password":"encoded-fake"}')[1])

    def test_final_artifact_sanitizer_redacts_and_marks_runtime_failed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as directory:
            root=Path(directory)
            (root/'chapter-027-client.log').write_text('user.p12: synthetic-encoded-value',encoding='utf-8')
            report=root/'chapter-027-runtime.json'
            report.write_text(json.dumps({'status':'PASS','checks':{}}),encoding='utf-8')
            self.assertTrue(security.sanitize_evidence(root,'027'))
            self.assertNotIn('synthetic-encoded-value',(root/'chapter-027-client.log').read_text())
            self.assertEqual(json.loads(report.read_text())['status'],'FAIL')
            self.assertFalse(security.sanitize_evidence(root,'027'))
            self.assertEqual(json.loads(report.read_text())['checks']['artifact_private_material_guard'],'FAIL')

    def test_tls_bootstrap_requires_mtls_authorizer_and_preserved_listener(self):
        cluster={'spec':{'kafka':{'authorization':{'type':'simple'},'listeners':[
            {'name':'plain','port':9092,'type':'internal','tls':False},
            {'name':'tlslab','port':9094,'type':'internal','tls':True,'authentication':{'type':'tls'}}]}},
            'status':{'listeners':[{'name':'tlslab','bootstrapServers':'qa-kafka-ha-kafka-bootstrap.kafka-qa.svc:9094'}]}}
        self.assertEqual(chapter.bootstrap_from_status(cluster),'qa-kafka-ha-kafka-bootstrap.kafka-qa.svc:9094')
        broken=copy.deepcopy(cluster);broken['spec']['kafka']['listeners'][1]['authentication']={}
        with self.assertRaises(RuntimeError):chapter.bootstrap_from_status(broken)
        broken=copy.deepcopy(cluster);broken['status']['listeners'][0]['bootstrapServers']='public.example:9094'
        with self.assertRaises(RuntimeError):chapter.bootstrap_from_status(broken)

    def test_user_acl_is_literal_and_never_superuser_or_all(self):
        user=chapter.tls_user('client','allowed','group')
        acls=user['spec']['authorization']['acls']
        self.assertEqual(acls[0]['resource'],{'type':'topic','name':'allowed','patternType':'literal'})
        self.assertEqual(acls[1]['resource'],{'type':'group','name':'group','patternType':'literal'})
        self.assertFalse(any('All' in rule['operations'] for rule in acls))
        self.assertEqual(selector.fixture_for('027'),'strimzi-three-node-mtls-ch027.yaml')
        self.assertIn('027',selector.select(['kafka/qa/security_acceptance.py']))


if __name__=='__main__':unittest.main()
