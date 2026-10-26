"""Composite acceptance rejects stale/mismatched evidence and preserves pending assessment."""
import copy
import unittest
from datetime import datetime, timezone, timedelta
import run_chapter_030 as chapter
import select_changed_chapters as selector


class CapstoneTests(unittest.TestCase):
    def test_only_fresh_matching_runtime_head_and_run_count_as_child_pass(self):
        started=datetime.now(timezone.utc)
        report={'chapter':'028','status':'PASS','head_commit':'full-head','run_id':'run','timestamp_utc':(started+timedelta(seconds=1)).isoformat(),
                'checks':{'actual_auth':'PASS'},'certification':'NOT_CERTIFIED','runtime_scope':'supported_only','limitations':['OAuth not executed']}
        self.assertEqual(chapter.validate_child(report,'028','full-head','run',started)['passed_checks'],1)
        for field,value in [('status','FAIL'),('chapter','027'),('head_commit','old-head'),('run_id','old-run'),
                            ('timestamp_utc',(started-timedelta(seconds=1)).isoformat()),('certification','CERTIFIED'),('checks',{'actual_auth':'NOT_RUN'})]:
            bad=copy.deepcopy(report);bad[field]=value
            with self.assertRaises(RuntimeError):chapter.validate_child(bad,'028','full-head','run',started)
        report['checks']={}
        with self.assertRaises(RuntimeError):chapter.validate_child(report,'028','full-head','run',started)

    def test_network_identity_retains_only_scoped_acl_and_sasl_ssl_identity(self):
        user=chapter.network_identity('network','owned-topic','owned-group')
        self.assertEqual(user['spec']['authentication'],{'type':'scram-sha-512'})
        self.assertNotIn('All',str(user));self.assertNotIn('superUsers',str(user))
        self.assertEqual({a['resource'].get('name') for a in user['spec']['authorization']['acls'] if a['resource']['type']!='cluster'}, {'owned-topic','owned-group'})

    def test_dependency_selector_covers_all_composite_sources(self):
        for path in ['kafka/qa/run_chapter_026.py','kafka/qa/run_chapter_027.py','kafka/qa/run_chapter_028.py','kafka/qa/run_chapter_029.py',
                     'kafka/qa/runtime/TlsAcceptance.java','kafka/qa/runtime/ScramAcceptance.java','kafka/qa/security_acceptance.py']:
            self.assertIn('030',selector.select([path]))
        self.assertEqual(selector.select(['kafka/qa/runtime/ScramAcceptance.java']),['028','029','030'])
        self.assertEqual(selector.fixture_for('030'),'strimzi-three-node-scram-ch028.yaml')
        self.assertEqual(selector.select(['kafka/qa/run_chapter_030.py']),['030'])


if __name__=='__main__':unittest.main()
