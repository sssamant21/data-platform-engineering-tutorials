#!/usr/bin/env python3
"""Chapter 026 bounded in-cluster discovery, ready endpoints and negative clients."""
import json
import ipaddress
import re
import subprocess
import sys
import time
from runtime_acceptance import k, CLUSTER, NS
from run_chapter_021 import StorageLab

CHECKS=['bootstrap_dns_and_resolver_observed','all_advertised_broker_dns_tcp_and_kafka_metadata',
        'topic_leaders_rf3_full_isr','invalid_dns_classified_without_cluster_change',
        'unused_port_dns_valid_tcp_and_metadata_failure_classified',
        'six_acknowledged_records_reconciled_after_negative_probes','positive_kafka_metadata_recovers_after_negative_probes']
LIMITS=['Internal plaintext listener in an isolated kind lab only; TLS/SASL/ACL and certificate validation are NOT_EXECUTED here and receive no secure-client execution credit.',
       'No external LoadBalancer/Ingress/Route, cloud firewall, cross-zone routing or production client-network validation.',
       'NetworkPolicy resources are inventoried, not modified; kind CNI policy enforcement, deny tests, cross-namespace least privilege and CNI flow logs are NOT_VALIDATED.',
       'Sample DNS/TCP timings and bounded request budgets are not production p95/p99 SLOs or packet-loss/recovery certification.',
       'Dual-role KRaft nodes are used; controller quorum is checked through Kafka metadata without pretending controllers are client listeners.',
       'Single-host local-path storage and independent security/assessor review remain outside enterprise certification.']


def normalized_ips(values):
    return {str(ipaddress.ip_address(value)) for value in values if value is not None}


def bootstrap_endpoints(service, slices, pods, client_port=9092):
    spec=service['spec'];selector=spec.get('selector',{})
    if spec.get('type','ClusterIP')!='ClusterIP' or spec.get('externalIPs') or not selector or spec.get('clusterIP') in (None, 'None'):
        raise RuntimeError('Expected selector-backed internal-only bootstrap Service')
    ports=[p for p in spec['ports'] if p['port']==client_port and p.get('protocol','TCP')=='TCP']
    if len(ports)!=1:raise RuntimeError('Missing/ambiguous bootstrap client port')
    port=ports[0];target=port.get('targetPort',client_port)
    brokers={p['metadata']['name']:p for p in pods}
    ready={}
    for item in slices:
        if not any(ref.get('kind')=='Service' and ref.get('uid')==service['metadata']['uid'] for ref in item['metadata'].get('ownerReferences',[])):
            raise RuntimeError('EndpointSlice belongs to a different Service UID')
        published=[p['port'] for p in item.get('ports',[]) if p.get('name')==port.get('name') and p.get('protocol','TCP')=='TCP']
        if len(published)!=1:raise RuntimeError('EndpointSlice client port missing')
        for endpoint in item.get('endpoints',[]):
            conditions=endpoint.get('conditions',{})
            if conditions.get('ready') is not True or conditions.get('terminating') is True:continue
            ref=endpoint.get('targetRef',{});pod=brokers.get(ref.get('name'))
            if pod is None or ref.get('kind')!='Pod' or ref.get('uid')!=pod['metadata']['uid'] or ref.get('namespace',NS)!=NS:
                raise RuntimeError('Ready endpoint targets an unknown/stale broker Pod')
            if pod['metadata'].get('deletionTimestamp') or not any(c.get('name')=='kafka' and c.get('ready') for c in pod['status'].get('containerStatuses',[])):
                raise RuntimeError('Ready endpoint points at an unready/terminating broker')
            if any(pod['metadata'].get('labels',{}).get(key)!=value for key,value in selector.items()):
                raise RuntimeError('Broker Pod does not match bootstrap Service selector')
            container=next(c for c in pod['spec']['containers'] if c['name']=='kafka')
            resolved=target if isinstance(target,int) else next((p['containerPort'] for p in container.get('ports',[]) if p.get('name')==target),None)
            if resolved!=published[0]:raise RuntimeError('Service targetPort and EndpointSlice port disagree')
            ips={v['ip'] for v in pod['status'].get('podIPs',[])}|{pod['status'].get('podIP')}
            if not endpoint.get('addresses') or not normalized_ips(endpoint['addresses']).issubset(normalized_ips(ips)):
                raise RuntimeError('Endpoint addresses differ from actual broker Pod IPs')
            current=ready.setdefault(ref['uid'],{'pod':ref['name'],'uid':ref['uid'],'port':resolved,'addresses':[]})
            current['addresses']=sorted(set(current['addresses'])|set(endpoint['addresses']))
    if len(ready)!=3:raise RuntimeError('Expected three actual ready bootstrap broker endpoints')
    return sorted(ready.values(),key=lambda item:item['pod'])


def advertised_mappings(observations, ready, expected_port=9092):
    by_pod={p['pod']:p for p in ready};actual=[];ids=set()
    for observation in observations:
        if not observation.startswith('OBS:BROKER_ENDPOINT:'):continue
        match=re.fullmatch(r'OBS:BROKER_ENDPOINT:(\d+)\|([^|]+)\|(\d+)\|(.+)',observation)
        if not match:raise RuntimeError('Malformed advertised broker observation')
        broker_id,host,port,ips=int(match[1]),match[2],int(match[3]),match[4].split(',')
        pod=by_pod.get(host.split('.')[0])
        if broker_id in ids or pod is None or port!=expected_port or not normalized_ips(ips).issubset(normalized_ips(pod['addresses'])):
            raise RuntimeError('Advertised endpoint does not match ready broker Pod/IP/port')
        ids.add(broker_id);actual.append({'id':broker_id,'host':host,'port':port,'resolved_ips':ips,'pod_uid':pod['uid']})
    if len(actual)!=3 or {item['pod_uid'] for item in actual}!={item['uid'] for item in ready}:raise RuntimeError('Incomplete or aliased advertised broker mapping')
    return actual


def main():
    lab=StorageLab('026',LIMITS);lab.result['checks']={}
    error,phase=None,'listener_and_service_inventory'
    try:
        lab.prepare()
        cluster=json.loads(lab.read('kafka-listeners','get','kafka',CLUSTER,'-o','json'))
        listeners=cluster['spec']['kafka']['listeners']
        if not any(item['type']=='internal' and item['port']==9092 and item.get('tls') is False for item in listeners):
            raise RuntimeError('Expected existing isolated internal listener; never disable security to adapt a different cluster')
        lab.result['listener_inventory']=listeners
        services=json.loads(lab.read('services','get','services','-l',f'strimzi.io/cluster={CLUSTER}','-o','json'))
        policies=json.loads(lab.read('networkpolicies','get','networkpolicy','-o','json'))
        lab.result['network_policy_scope']={'objects':len(policies['items']),'enforcement':'NOT_VALIDATED_NO_POLICY_MUTATION','external_cloud_controls':'NOT_TESTED'}
        lab.read('storage-context','get','kafkanodepool,pvc','-o','wide')
        lab.result['checks'][phase]='PASS'
        phase='service_ready_endpoint_uid_ip_port_mapping'
        deadline=time.monotonic()+60;last_error=''
        while time.monotonic()<deadline:
            service=json.loads(lab.read('bootstrap-service','get','service',CLUSTER+'-kafka-bootstrap','-o','json'))
            slices=json.loads(lab.read('bootstrap-endpointslices','get','endpointslices','-l','kubernetes.io/service-name='+CLUSTER+'-kafka-bootstrap','-o','json'))['items']
            pods=json.loads(lab.read('broker-pods','get','pods','-l',f'strimzi.io/cluster={CLUSTER},strimzi.io/pool-name=dual-role','-o','json'))['items']
            try:ready=bootstrap_endpoints(service,slices,pods);break
            except RuntimeError as exc:last_error=str(exc);time.sleep(2)
        else:raise RuntimeError('Ready endpoint mapping did not converge: '+last_error)
        wrong_port=19092
        if any(p['port']==wrong_port for p in service['spec']['ports']):raise RuntimeError('Negative-test port is published; refuse probe')
        lab.result['ready_bootstrap_endpoints']=ready
        lab.result['negative_probe']={'invalid_dns':'nonexistent-ch026.invalid','unused_service_port':wrong_port,'client_side_only':True}
        lab.result['checks'][phase]='PASS'
        phase='diagnostic_client_protocol_and_negative_probes'
        topic=lab.topic('network')
        lab.run_job('NetworkAcceptance',[topic,lab.tag,str(wrong_port)],CHECKS)
        lab.result['checks'][phase]='PASS'
        phase='metadata_advertised_endpoints_match_kubernetes'
        lab.result['advertised_brokers']=advertised_mappings(lab.result['client_observations'],ready)
        dns=[o.split(':',2)[2].split(',') for o in lab.result['client_observations'] if o.startswith('OBS:BOOTSTRAP_DNS:')]
        cluster_ips=set(service['spec'].get('clusterIPs',[service['spec']['clusterIP']]))
        if len(dns)!=1 or not normalized_ips(dns[0]).issubset(normalized_ips(cluster_ips)):raise RuntimeError('Bootstrap DNS differs from actual Service IPs')
        lab.result['checks'][phase]='PASS'
        phase='final_kraft_quorum_and_broker_api_discovery'
        lab.read('broker-api-versions','exec',lab.pod,'-c','kafka','--','/opt/kafka/bin/kafka-broker-api-versions.sh','--bootstrap-server',CLUSTER+'-kafka-bootstrap:9092')
        quorum=lab.read('quorum','exec',lab.pod,'-c','kafka','--','/opt/kafka/bin/kafka-metadata-quorum.sh','--bootstrap-server',CLUSTER+'-kafka-bootstrap:9092','describe','--status')
        if not re.search(r'LeaderId:\s+\d+',quorum):raise RuntimeError('KRaft quorum leader missing')
        lab.result['checks'][phase]='PASS'
        lab.result['pending_secure_and_external_gates']={'tls_handshake':'NOT_EXECUTED','sasl_authentication':'NOT_EXECUTED','topic_acls':'NOT_EXECUTED',
            'cross_namespace_policy_enforcement':'NOT_VALIDATED','external_routing':'NOT_EXECUTED','production_p99_slo':'NOT_ASSESSED'}
        lab.result['status']='PASS';lab.result['runtime_scope']='IN_CLUSTER_PLAINTEXT_DISCOVERY_AND_CLIENT_NEGATIVE_PROBES_ONLY'
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        error=exc;lab.result['checks'][phase]='FAIL';print(str(exc),file=sys.stderr)
    return lab.finish(error)


if __name__=='__main__':sys.exit(main())
