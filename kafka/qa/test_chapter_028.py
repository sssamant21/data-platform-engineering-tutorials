"""Credential secrecy, actual principal mapping and current-generation rotation guards."""
import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_chapter_028 as chapter
import security_acceptance as security
import select_changed_chapters as selector
from runtime_acceptance import job_manifest


class ScramTests(unittest.TestCase):
    def test_secure_listener_requires_tls_scram_and_retained_mtls(self):
        cluster={'spec':{'kafka':{'authorization':{'type':'simple'},'listeners':[
            {'name':'tlslab','port':9094,'tls':True,'authentication':{'type':'tls'}},
            {'name':'scramlab','port':9095,'tls':True,'authentication':{'type':'scram-sha-512'}}]}},
            'status':{'listeners':[{'name':'scramlab','bootstrapServers':'qa-kafka-ha-kafka-bootstrap.kafka-qa.svc:9095'}]}}
        self.assertTrue(chapter.bootstrap_from_status(cluster).endswith(':9095'))
        for field,value in [('tls',False),('authentication',{'type':'plain'}),('port',9092)]:
            wrong=copy.deepcopy(cluster);wrong['spec']['kafka']['listeners'][1][field]=value
            with self.assertRaises(RuntimeError):chapter.bootstrap_from_status(wrong)

    def test_rotation_changes_only_supported_password_reference(self):
        old=chapter.scram_user('user','topic','group','old-source');new=chapter.scram_user('user','topic','group','new-source')
        self.assertEqual(old['spec']['authorization'],new['spec']['authorization'])
        self.assertNotIn('All',json.dumps(new));self.assertNotIn('superUsers',json.dumps(new))
        self.assertNotIn('password-value',json.dumps(new))
        self.assertEqual(new['spec']['authentication']['password']['valueFrom']['secretKeyRef'],{'name':'new-source','key':'password'})
        self.assertTrue(all(acl['resource'].get('patternType','literal')=='literal' for acl in new['spec']['authorization']['acls']))

    def test_ready_requires_current_generation_not_old_ready_condition(self):
        user=chapter.scram_user('user','topic','group','new-source');user['metadata'].update({'uid':'uid','generation':2})
        user['status']={'observedGeneration':1,'username':'user','conditions':[{'type':'Ready','status':'True'}]}
        current=copy.deepcopy(user);current['status']['observedGeneration']=2
        with patch.object(chapter,'k',side_effect=[json.dumps(user),json.dumps(current)]),patch.object(chapter.time,'sleep') as sleep:
            result=chapter.ready_user('user','new-source')
        self.assertEqual(result['observed_generation'],2);sleep.assert_called_once()
        with patch.object(chapter,'k',return_value=json.dumps(current)):
            with self.assertRaises(RuntimeError):chapter.ready_user('user','unexpected-source')

    def test_principal_must_be_native_exact_identity_and_resource(self):
        line='broker Principal = User:expected is Denied operation = DESCRIBE from host = 1.2.3.4 on resource = Topic:LITERAL:denied-topic for request = Metadata'
        self.assertEqual(chapter.principal_denial(line,'expected','denied-topic'),[line])
        self.assertFalse(chapter.principal_denial(line,'expect','denied-topic'))
        self.assertFalse(chapter.principal_denial(line,'expected','denied'))
        self.assertFalse(chapter.principal_denial(line.replace('Denied','Allowed'),'expected','denied-topic'))

    def test_scram_projection_has_only_password_and_no_api_token(self):
        pod=security.secure_client_job(job_manifest('client','image','source','Main',[]),'sa','ca','identity',['password'])['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['volumes'][-1]['secret']['items'],[{'key':'password','path':'password'}])
        self.assertEqual(pod['volumes'][-1]['secret']['defaultMode'],0o440)

    def test_secret_password_and_jaas_exports_fail_closed(self):
        for text in ['password: fake-encoded-secret\n','sasl.jaas.config: fake-encoded-jaas\n','{"password": "fake-encoded-secret"}']:
            clean,redacted=security.redact_private_material(text)
            self.assertTrue(redacted);self.assertNotIn('fake-',clean)
            self.assertFalse(security.redact_private_material(clean)[1])
        jaas=json.dumps({'sasl.jaas.config':'LoginModule required username="synthetic" password="private-fake-value";'})
        clean,redacted=security.redact_private_material(jaas)
        self.assertTrue(redacted);self.assertEqual(json.loads(clean)['sasl.jaas.config'],'[REDACTED]')
        self.assertNotIn('private-fake-value',clean)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            secret='synthetic-random-private-password'
            path=Path(directory)/'chapter-028-diagnostic.txt';path.write_text('opaque '+base64.b64encode(secret.encode()).decode())
            self.assertTrue(security.sanitize_evidence(directory,'028',(secret,)))
            self.assertNotIn(base64.b64encode(secret.encode()).decode(),path.read_text())

    def test_source_secret_boundary_prevents_unowned_creation(self):
        class Lab:tag='ch028-owned';owned=[]
        with patch.object(chapter,'k') as api:
            with self.assertRaises(RuntimeError):chapter.source_secret(Lab(),'unrelated','synthetic')
            api.assert_not_called()

    def test_shared_security_dependency_regresses_both_chapters(self):
        self.assertTrue({'027','028'}.issubset(selector.select(['kafka/qa/security_acceptance.py'])))
        self.assertIn('028',selector.select(['kafka/qa/runtime/ScramAcceptance.java']))
        self.assertEqual(selector.fixture_for('028'),'strimzi-three-node-scram-ch028.yaml')


if __name__=='__main__':unittest.main()
