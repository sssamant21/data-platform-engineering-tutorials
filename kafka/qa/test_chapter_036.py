"""Offline contract tests; actual discovery, PromQL and notification delivery require CI."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import monitoring_acceptance as acceptance
import monitoring_crds as crds
import monitoring_resources as resources
from monitoring_lab import monitoring_namespace, MonitoringLab
from java_sources import bundle_java_sources
import select_changed_chapters as selector

TAG='ch036-0123456789ab'

class MonitoringTests(unittest.TestCase):
    def test_content_pin_rejects_changed_bytes_and_unknown_download(self):
        data=b'apiVersion: v1\n';blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        self.assertEqual(crds.verify_blob(data,blob),hashlib.sha256(data).hexdigest())
        with self.assertRaises(RuntimeError):crds.verify_blob(data+b' ',blob)
        with patch.object(crds.urllib.request,'urlopen') as request:
            with self.assertRaises(RuntimeError):crds.fetch('../../production')
            request.assert_not_called()

    def test_namespace_and_mutation_guards_fail_before_api_calls(self):
        self.assertEqual(monitoring_namespace(TAG),TAG+'-monitoring')
        for name in ('production','ch035-0123456789ab',TAG+'-extra'):
            with self.assertRaises(RuntimeError):monitoring_namespace(name)
        lab=MonitoringLab('036',[])
        with self.assertRaises(RuntimeError):lab.apply({'kind':'Service','metadata':{'name':lab.tag+'-service'}})
        lab.safe=True
        for manifest in ({'kind':'Namespace','metadata':{'name':lab.tag+'-namespace'}},{'kind':'Service','metadata':{'name':'production'}},{'kind':'Service','metadata':{'name':lab.tag+'-service','namespace':'production'}}):
            with self.assertRaises(RuntimeError):lab.apply(manifest)
        with self.assertRaises(RuntimeError):lab.mon_apply({'kind':'ClusterRole','metadata':{'name':lab.tag+'-role'}})

    def test_discovery_rbac_has_no_secret_or_write_access(self):
        _,manifests=resources.discovery_manifests(TAG,monitoring_namespace(TAG))
        role=next(m for m in manifests if m['kind']=='Role')
        for rule in role['rules']:
            self.assertNotIn('secrets',rule['resources']);self.assertEqual(set(rule['verbs']),{'get','list','watch'})
        cluster,namespaced=resources.operator_manifests(TAG,monitoring_namespace(TAG))
        for rule in cluster[0]['rules']:self.assertNotIn('secrets',rule['resources'])
        operator=next(m for m in namespaced if m['kind']=='Deployment')
        args=operator['spec']['template']['spec']['containers'][0]['args']
        self.assertIn('--namespaces='+monitoring_namespace(TAG),args)
        self.assertIn('--watch-referenced-objects-in-all-namespaces=false',args)

    def test_missing_nan_and_infinite_query_samples_do_not_become_zero(self):
        payload={'status':'success','data':{'resultType':'vector','result':[]}}
        with self.assertRaises(RuntimeError):acceptance.vector(payload)
        self.assertEqual(acceptance.vector(payload,True),[])
        for value in ('NaN','+Inf','-Inf'):
            payload['data']['result']=[{'metric':{},'value':[100,value]}]
            with self.assertRaises(RuntimeError):acceptance.vector(payload)

    def test_targets_require_actual_broker_ip_freshness_and_exact_coverage(self):
        now=1000000;stamp=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat()
        pods=[{'metadata':{'name':'broker-'+str(i)},'status':{'podIP':'10.0.0.'+str(i+1)}} for i in range(3)]
        rows=[]
        for i,role in enumerate(('broker','broker','broker','synthetic','strimzi-operator','monitoring-operator')):
            labels={'qa_owner':TAG,'qa_kind':role,'namespace':'kafka-qa'}
            if role=='broker':labels['broker']='broker-'+str(i)
            rows.append({'labels':labels,'health':'up','lastError':'','lastScrape':stamp,'lastScrapeDuration':.01,'scrapeUrl':'http://10.0.0.'+str(i+1)+(':9404' if role=='broker' else ':8080')+'/metrics'})
        payload={'status':'success','data':{'activeTargets':rows}}
        self.assertEqual(len(acceptance.targets(payload,TAG,pods,now)),6)
        for edit in (lambda r:r[0].update({'scrapeUrl':'http://10.9.9.9:9404/metrics'}),lambda r:r[0].update({'health':'down'}),lambda r:r.append(copy.deepcopy(r[0]))):
            bad=copy.deepcopy(payload);edit(bad['data']['activeTargets'])
            with self.assertRaises(RuntimeError):acceptance.targets(bad,TAG,pods,now)
        with self.assertRaises(RuntimeError):acceptance.targets(payload,TAG,pods,now+31)

    def test_http_destination_guards_run_before_network(self):
        for base,path in (('https://production.example','/api'),('http://127.0.0.1:9090','//production.example'),('http://10.0.0.1:9090','/api')):
            with self.assertRaises(RuntimeError):acceptance.http_json(base,path)
        with self.assertRaises(RuntimeError):acceptance.http_text('http://127.0.0.1:9090','/admin')

    def test_grafana_requires_actual_number_not_time_or_missing(self):
        frame={'schema':{'fields':[{'type':'time'},{'type':'number'}]},'data':{'values':[[12345],[3]]}}
        self.assertEqual(acceptance.grafana_number({'results':{'A':{'frames':[frame]}}}),[3])
        frame['data']['values'][1]=[None]
        with self.assertRaises(RuntimeError):acceptance.grafana_number({'results':{'A':{'frames':[frame]}}})

    def test_secret_files_and_internal_authenticated_delivery(self):
        manifests=resources.prometheus_manifests(TAG,monitoring_namespace(TAG),'private-test-token')
        text=json.dumps(manifests)
        self.assertNotIn('LoadBalancer',text);self.assertIn('credentials_file',text)
        self.assertIn('send_resolved',text)
        _,metadata=resources.grafana_manifests(TAG,monitoring_namespace(TAG),'private-password')
        text=json.dumps(metadata)
        self.assertNotIn('private-password',text)
        self.assertNotIn('histogram_quantile',text);self.assertNotIn('avg(',text)

    def test_rule_fixtures_cover_missing_series_firing_and_resolution(self):
        documents=resources.rule_test_documents(TAG);tests=json.loads(documents['tests.yaml'])['tests']
        self.assertGreaterEqual(len(tests),7)
        lifecycle=tests[1]['alert_rule_test']
        self.assertEqual([len(row['exp_alerts']) for row in lifecycle],[0,1,0])
        self.assertIn('absent(',documents['rules.yaml'])
        self.assertNotIn('histogram_quantile',documents['rules.yaml'])

    def test_non_api_pods_cannot_receive_implicit_tokens(self):
        pod={'metadata':{'name':'receiver','uid':'uid'},'spec':{'serviceAccountName':'receiver','automountServiceAccountToken':False,'securityContext':{'runAsNonRoot':True},'containers':[{'securityContext':resources.container_security(True)}]}}
        self.assertEqual(len(acceptance.pod_security_inventory([pod],set())),1)
        pod['spec']['automountServiceAccountToken']=True
        with self.assertRaises(RuntimeError):acceptance.pod_security_inventory([pod],set())

    def test_source_bundle_has_one_public_main_and_real_kafka_operations(self):
        directory=Path(__file__).parent/'runtime';names=('ObservabilityTarget','ConsumerAcceptance','PerfAcceptance')
        bundle=bundle_java_sources(names[0],{name:(directory/(name+'.java')).read_text(encoding='utf-8-sig') for name in names})
        self.assertEqual(bundle.count('public class '),1)
        self.assertIn('describeMetadataQuorum',bundle);self.assertIn('commitSync',bundle)

    def test_selector_scopes_new_files_and_tracks_shared_helpers(self):
        for path in ('monitoring_crds.py','monitoring_lab.py','monitoring_resources.py','monitoring_acceptance.py','runtime/ObservabilityTarget.java','runtime/strimzi-three-node-observability-ch036.yaml'):
            self.assertEqual(selector.select(['kafka/qa/'+path]),['036'])
        for path in ('broker_acceptance.py','performance_lab.py','java_sources.py','runtime/ConsumerAcceptance.java','runtime/PerfAcceptance.java'):
            self.assertIn('036',selector.select(['kafka/qa/'+path]))
        self.assertEqual(selector.fixture_for('036'),'strimzi-three-node-observability-ch036.yaml')

if __name__=='__main__':unittest.main()
