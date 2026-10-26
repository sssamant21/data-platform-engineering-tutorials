"""Ready endpoint identity and all-advertised-broker mapping contracts."""
import copy
import unittest
import run_chapter_026 as chapter
import select_changed_chapters as selector


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.service={'metadata':{'uid':'svc'},'spec':{'type':'ClusterIP','clusterIP':'10.96.0.10','selector':{'app':'brokers'},
                      'ports':[{'name':'tcp-clients','port':9092,'targetPort':'tcp-clients'}]}}
        self.pods=[];endpoints=[]
        for i in range(3):
            self.pods.append({'metadata':{'name':f'broker-{i}','uid':f'pod-{i}','labels':{'app':'brokers'}},
                'spec':{'containers':[{'name':'kafka','ports':[{'name':'tcp-clients','containerPort':9092}]}]},
                'status':{'podIP':f'10.0.0.{i+1}','containerStatuses':[{'name':'kafka','ready':True}]}})
            endpoints.append({'conditions':{'ready':True},'addresses':[f'10.0.0.{i+1}'],
                'targetRef':{'kind':'Pod','name':f'broker-{i}','uid':f'pod-{i}','namespace':chapter.NS}})
        self.slices=[{'metadata':{'ownerReferences':[{'kind':'Service','uid':'svc'}]},'ports':[{'name':'tcp-clients','port':9092}], 'endpoints':endpoints}]

    def mapping(self):return chapter.bootstrap_endpoints(self.service,self.slices,self.pods)

    def test_named_service_target_and_actual_ready_pod_mapping(self):
        mapped=self.mapping()
        self.assertEqual(len(mapped),3);self.assertEqual(mapped[1]['uid'],'pod-1');self.assertEqual(mapped[1]['port'],9092)
        self.service['spec']['ports'][0]['targetPort']=9092
        self.assertEqual(len(self.mapping()),3)

    def test_unready_or_stale_endpoint_cannot_count_as_ready(self):
        for key,value in [('ready',False),('ready',None),('terminating',True)]:
            original=copy.deepcopy(self.slices)
            self.slices[0]['endpoints'][0]['conditions'][key]=value
            with self.assertRaises(RuntimeError):self.mapping()
            self.slices=original
        self.slices[0]['endpoints'][0]['targetRef']['uid']='stale-pod'
        with self.assertRaisesRegex(RuntimeError,'stale'):self.mapping()

    def test_wrong_ip_port_service_uid_or_external_exposure_fails(self):
        original=copy.deepcopy(self.slices)
        self.slices[0]['endpoints'][0]['addresses']=['10.0.99.99']
        with self.assertRaises(RuntimeError):self.mapping()
        self.slices=copy.deepcopy(original);self.slices[0]['ports'][0]['port']=19092
        with self.assertRaises(RuntimeError):self.mapping()
        self.slices=copy.deepcopy(original);self.slices[0]['metadata']['ownerReferences'][0]['uid']='other'
        with self.assertRaises(RuntimeError):self.mapping()
        self.slices=original;self.service['spec']['externalIPs']=['203.0.113.1']
        with self.assertRaises(RuntimeError):self.mapping()

    def test_every_distinct_advertised_broker_must_match_real_pod(self):
        ready=self.mapping()
        observations=[f'OBS:BROKER_ENDPOINT:{i}|broker-{i}.service.namespace.svc|9092|10.0.0.{i+1}' for i in range(3)]
        self.assertEqual(len(chapter.advertised_mappings(observations,ready)),3)
        observations[2]='OBS:BROKER_ENDPOINT:2|broker-0.service.namespace.svc|9092|10.0.0.1'
        with self.assertRaisesRegex(RuntimeError,'aliased'):chapter.advertised_mappings(observations,ready)

    def test_ipv6_spelling_does_not_create_false_address_mismatch(self):
        self.assertEqual(chapter.normalized_ips(['fd00::1']),chapter.normalized_ips(['fd00:0:0:0:0:0:0:1']))

    def test_runtime_dispatch_is_scoped_to_network_client(self):
        self.assertEqual(selector.select(['kafka/qa/runtime/NetworkAcceptance.java']),['026'])
        self.assertEqual(selector.fixture_for('026'),'strimzi-three-node-persistent-ch021.yaml')
        self.assertIn('026',selector.select(['kafka/qa/run_chapter_021.py']))


if __name__=='__main__':unittest.main()
