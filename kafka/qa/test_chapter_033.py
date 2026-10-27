"""Consumer-source contracts, exact planned-fault evidence and actual resource mapping."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime_acceptance import ROOT, NS, job_manifest
from java_sources import bundle_java_sources
from consumer_acceptance import ConsumerLab, consumer_arguments, expected_crash, sink_binding, group_pod_mapping, json_observation
from performance_acceptance import client_metric
from performance_lab import PerformanceLab, TrialDriver
import run_chapter_033 as chapter
import select_changed_chapters as selector


class ConsumerTests(unittest.TestCase):
    def test_actual_bundle_launches_consumer_first_with_one_public_class(self):
        sources={name:(ROOT/'kafka/qa/runtime'/(name+'.java')).read_text(encoding='utf-8-sig') for name in ('ConsumerAcceptance','PerfAcceptance')}
        result=bundle_java_sources('ConsumerAcceptance',sources)
        self.assertEqual(result.count('public class '),1);self.assertLess(result.index('public class ConsumerAcceptance'),result.index('class PerfAcceptance'))
        self.assertIn('static Properties security()',result);self.assertIn('static void replay(',result)
        imports=[line for line in result.splitlines() if line.startswith('import ')]
        self.assertEqual(len(imports),len(set(imports)))
        with self.assertRaises(RuntimeError):bundle_java_sources('../Private',sources)
        with self.assertRaises(RuntimeError):bundle_java_sources('ConsumerAcceptance',{'ConsumerAcceptance':'package external;\npublic class ConsumerAcceptance {}'})

    def test_fetch_comparison_preserves_controlled_ingress_and_validates_limits(self):
        plan=chapter.fetch_plan();self.assertEqual(len(plan),9)
        self.assertEqual(len({p['trial'] for p in plan}),9)
        for left,right in [(0,1),(1,2)]:
            self.assertEqual(sum(chapter.PROFILES[left][key]!=chapter.PROFILES[right][key] for key in ('fetch_min_bytes','fetch_max_wait_ms')),1)
        trial={**plan[0],'topic':'owned','group':'owned'}
        args=consumer_arguments('bootstrap','user',trial);self.assertEqual(args[0],'fetch');self.assertEqual(len(args),13)
        for key,value in [('target_records_per_second',-1),('compression','gzip'),('partitions',3),('fetch_min_bytes',999999),('fetch_max_wait_ms',-1),('poll_records',100000)]:
            with self.assertRaises(RuntimeError):consumer_arguments('bootstrap','user',{**trial,key:value})

    def test_default_driver_retains_original_031_arguments(self):
        trial={'trial':'baseline','topic':'owned','group':'owned','records':1200,'record_size':1024,'target_records_per_second':400}
        self.assertIs(TrialDriver().lab_class,PerformanceLab);self.assertEqual(TrialDriver().main,'PerfAcceptance')
        self.assertEqual(len(TrialDriver().arguments('bootstrap','user',trial)),8)

    def test_global_consumer_metric_does_not_sum_or_alias_topic_series(self):
        text='consumer-fetch-manager-metrics:records-consumed-total:{client-id=test} : 1200.000\nconsumer-fetch-manager-metrics:records-consumed-total:{client-id=test, topic=owned} : 1200.000\n'
        self.assertEqual(client_metric(text,'consumer-fetch-manager-metrics','records-consumed-total'),1200)
        with self.assertRaises(RuntimeError):client_metric(text+text,'consumer-fetch-manager-metrics','records-consumed-total')

    def test_expected_process_halt_requires_checkpoint_job_owner_and_exit23(self):
        job={'metadata':{'uid':'job-uid'},'status':{'conditions':[{'type':'Failed','status':'True'}]}}
        pod={'metadata':{'uid':'pod-uid','ownerReferences':[{'kind':'Job','uid':'job-uid','controller':True}]},'status':{'phase':'Failed','containerStatuses':[{'name':'client','state':{'terminated':{'exitCode':23}}}]}}
        self.assertEqual(expected_crash(job,[pod],True)['exit_code'],23)
        for code in (0,1,137):
            wrong=copy.deepcopy(pod);wrong['status']['containerStatuses'][0]['state']['terminated']['exitCode']=code
            with self.assertRaises(RuntimeError):expected_crash(job,[wrong],True)
        with self.assertRaises(RuntimeError):expected_crash(job,[pod],False)
        with self.assertRaises(RuntimeError):expected_crash(job,[pod,pod],True)
        wrong=copy.deepcopy(pod);wrong['metadata']['ownerReferences'][0]['uid']='unrelated'
        with self.assertRaises(RuntimeError):expected_crash(job,[wrong],True)

    def test_sink_mount_guard_rejects_unowned_or_broker_claim(self):
        lab=ConsumerLab('033',[]);job=job_manifest('test','image','source','ConsumerAcceptance',[])
        lab.sink_claim='data-0-qa-kafka-ha-dual-role-0'
        with self.assertRaises(RuntimeError):lab.apply(copy.deepcopy(job))
        claim='ch033-'+'a'*12+'-sink';lab.sink_claim=claim
        with self.assertRaises(RuntimeError):lab.apply(copy.deepcopy(job))
        lab.owned.append({'kind':'PersistentVolumeClaim','name':claim})
        with patch.object(PerformanceLab,'apply',side_effect=lambda m:m):secured=lab.apply(copy.deepcopy(job))
        self.assertEqual(secured['spec']['template']['spec']['volumes'][-1]['persistentVolumeClaim']['claimName'],claim)
        self.assertEqual(secured['spec']['template']['spec']['containers'][0]['volumeMounts'][-1]['mountPath'],'/sink')

    def test_sink_binding_requires_real_pv_claim_uid_and_actual_pod_mount(self):
        name='ch033-'+'a'*12+'-sink'
        claim={'metadata':{'name':name,'uid':'claim'},'status':{'phase':'Bound'},'spec':{'storageClassName':'standard','accessModes':['ReadWriteOnce'],'volumeName':'pv'}}
        pv={'metadata':{'name':'pv','uid':'volume'},'status':{'phase':'Bound'},'spec':{'claimRef':{'namespace':NS,'name':name,'uid':'claim'}}}
        pod={'spec':{'nodeName':'kind-node','volumes':[{'name':'owned-sink','persistentVolumeClaim':{'claimName':name}}],
                     'containers':[{'volumeMounts':[{'name':'owned-sink','mountPath':'/sink'}]}]}}
        self.assertEqual(sink_binding(claim,pv,pod,name)['pvc_uid'],'claim')
        wrong=copy.deepcopy(pv);wrong['spec']['claimRef']['uid']='other'
        with self.assertRaises(RuntimeError):sink_binding(claim,wrong,pod,name)
        wrong=copy.deepcopy(pod);wrong['spec']['containers'][0]['volumeMounts'][0]['mountPath']='/var/lib/kafka/data'
        with self.assertRaises(RuntimeError):sink_binding(claim,pv,wrong,name)

    def test_group_members_map_to_distinct_actual_pod_uids_and_ips(self):
        pods=[{'metadata':{'name':f'pod-{i}','uid':f'uid-{i}'},'status':{'podIP':f'10.0.0.{i+1}'}} for i in range(2)]
        assignment={'member_count':2,'members':[{'client_id':f'pod-{i}','member_id':str(i),'host':f'/10.0.0.{i+1}','partitions':[i]} for i in range(2)]}
        self.assertEqual(len(group_pod_mapping(assignment,pods)),2)
        wrong=copy.deepcopy(assignment);wrong['members'][1]['host']='/10.0.0.1'
        with self.assertRaises(RuntimeError):group_pod_mapping(wrong,pods)
        wrong=copy.deepcopy(assignment);wrong['members'][1]['client_id']='foreign'
        with self.assertRaises(RuntimeError):group_pod_mapping(wrong,pods)

    def test_observation_requires_unique_json_and_deployment_credentials_are_restricted(self):
        self.assertEqual(json_observation(['OBS:PROOF:{"count":1}'],'PROOF'),{'count':1})
        with self.assertRaises(RuntimeError):json_observation(['OBS:PROOF:{}','OBS:PROOF:{}'],'PROOF')
        class Lab:image='approved@sha256:abc';client_service_account='sa';ca_secret='ca';identity_secret='user'
        manifest=chapter.deployment_manifest(Lab(),'owned','source',{'topic':'topic','group':'group','prefix':'owned'},{'bootstrap':'bootstrap','username':'user'})
        pod=manifest['spec']['template']['spec'];self.assertFalse(pod['automountServiceAccountToken']);self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertTrue(all(v['readOnly'] for v in pod['containers'][0]['volumeMounts']));self.assertEqual(pod['containers'][0]['env'][0]['valueFrom']['fieldRef']['fieldPath'],'metadata.name')

    def test_actual_dependency_matrix_preserves_031_032_regressions(self):
        self.assertTrue({'031','032','033'}.issubset(selector.select(['kafka/qa/performance_lab.py'])))
        self.assertTrue({'031','032','033'}.issubset(selector.select(['kafka/qa/runtime/PerfAcceptance.java'])))
        for path in ('kafka/qa/runtime/ConsumerAcceptance.java','kafka/qa/consumer_acceptance.py'):
            self.assertTrue({'033'}.issubset(selector.select([path])))
        self.assertTrue({'033'}.issubset(selector.select(['kafka/qa/java_sources.py'])))
        self.assertEqual(selector.select(['kafka/qa/run_chapter_020.py']),['020','025','033'])
        self.assertEqual(selector.fixture_for('033'),'strimzi-three-node-scram-ch028.yaml')


if __name__=='__main__':unittest.main()
