"""Reject default-open/superuser drift and preserve exact tenant resource boundaries."""
import json
import unittest
from unittest.mock import patch
import run_chapter_029 as chapter
import select_changed_chapters as selector


class AuthorizationTests(unittest.TestCase):
    def test_default_open_and_application_superuser_are_rejected(self):
        safe='authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer\nsuper.users=User:CN=operator\n'
        self.assertFalse(chapter.authorizer_config(safe,['tenant-a'])['application_superusers'])
        for extra in ['allow.everyone.if.no.acl.found=true\n','super.users=User:tenant-a\n','password=must-never-be-read\n']:
            with self.assertRaises(RuntimeError):chapter.authorizer_config(safe+extra,['tenant-a'])
        with self.assertRaises(RuntimeError):chapter.authorizer_config('allow.everyone.if.no.acl.found=false\n',['tenant-a'])
        with self.assertRaises(RuntimeError):chapter.authorizer_config(safe.replace('StandardAuthorizer','OtherAuthorizer'),['tenant-a'])

    def test_effective_application_superuser_fails_without_duplicate_key(self):
        with self.assertRaises(RuntimeError):chapter.authorizer_config('authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer\nsuper.users=User:tenant-a;User:CN=operator\n',['tenant-a'])

    def test_tenant_acls_do_not_overlap_and_admin_is_read_only(self):
        a=chapter.tenant_user('a','a-topic','a-group','a-txn');b=chapter.tenant_user('b','b-topic','b-group','b-txn')
        for user,prefix in [(a,'a-'),(b,'b-')]:
            for acl in user['spec']['authorization']['acls']:
                self.assertNotIn('All',acl['operations']);resource=acl['resource']
                if resource['type']!='cluster':
                    self.assertTrue(resource['name'].startswith(prefix));self.assertEqual(resource['patternType'],'literal')
                else:self.assertEqual(acl['operations'],['IdempotentWrite'])
        self.assertEqual(chapter.diagnostic_user('inventory')['spec']['authorization']['acls'],[{'resource':{'type':'cluster'},'operations':['Describe'],'host':'*'}])

    def test_impersonation_error_is_not_secret_access_denial(self):
        class Response:returncode=1;stdout='';stderr='impersonation forbidden'
        with patch.object(chapter.subprocess,'run',return_value=Response()):
            with self.assertRaises(RuntimeError):chapter.rbac_denials('tenant-sa')
        Response.stdout='no\n'
        with patch.object(chapter.subprocess,'run',return_value=Response()):
            denials=chapter.rbac_denials('tenant-sa')
        self.assertEqual(len(denials),6);self.assertIn({'verb':'patch','resource':'kafkas.kafka.strimzi.io','outcome':'DENIED'},denials)

    def test_observed_user_generation_and_principal_required(self):
        class Lab:
            def secret_metadata(self,*args):return {'keys':['password'],'name':'tenant','uid':'secret','resourceVersion':'1'}
        user={'metadata':{'uid':'u','generation':2},'status':{'observedGeneration':1,'username':'tenant','conditions':[{'type':'Ready','status':'True'}]}}
        current=json.loads(json.dumps(user));current['status']['observedGeneration']=2
        with patch.object(chapter,'k',side_effect=[json.dumps(user),json.dumps(current)]),patch.object(chapter.time,'sleep') as sleep:
            self.assertEqual(chapter.ready_identity(Lab(),'tenant','label')['generation'],2)
        sleep.assert_called_once()
        current['status']['username']='wrong'
        with patch.object(chapter,'k',return_value=json.dumps(current)):
            with self.assertRaises(RuntimeError):chapter.ready_identity(Lab(),'tenant','label')

    def test_shared_client_and_runner_dependencies_preserve_regressions(self):
        self.assertEqual(selector.select(['kafka/qa/runtime/ScramAcceptance.java']),['028','029'])
        self.assertEqual(selector.select(['kafka/qa/run_chapter_028.py']),['028','029'])
        self.assertEqual(selector.fixture_for('029'),'strimzi-three-node-scram-ch028.yaml')
        self.assertEqual(selector.select(['kafka/qa/run_chapter_029.py']),['029'])


if __name__=='__main__':unittest.main()
