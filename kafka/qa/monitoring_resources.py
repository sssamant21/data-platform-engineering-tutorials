"""Pure, namespace-restricted monitoring resource factories for Chapter036."""
import json
from runtime_acceptance import NS, CLUSTER
from monitoring_crds import OPERATOR, PROMETHEUS, ALERTMANAGER, GRAFANA


def labels(tag,role):return {'qa_owner':tag,'qa_kind':role}


def binding(name,role,account,namespace,cluster=False):
    return {'apiVersion':'rbac.authorization.k8s.io/v1','kind':'ClusterRoleBinding' if cluster else 'RoleBinding',
        'metadata':{'name':name},'roleRef':{'apiGroup':'rbac.authorization.k8s.io','kind':'ClusterRole' if cluster else 'Role','name':role},
        'subjects':[{'kind':'ServiceAccount','name':account,'namespace':namespace}]}


def service(tag,role,selector,port,name='web'):
    return {'apiVersion':'v1','kind':'Service','metadata':{'name':tag+'-'+role,'labels':labels(tag,role)},
        'spec':{'type':'ClusterIP','selector':selector,'ports':[{'name':name,'port':port,'targetPort':port}]}}


def pod_security(uid):return {'runAsNonRoot':True,'runAsUser':uid,'fsGroup':uid,'seccompProfile':{'type':'RuntimeDefault'}}


def container_security(readonly=False):return {'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']},'readOnlyRootFilesystem':readonly}


def operator_manifests(tag,namespace):
    sa=tag+'-operator-sa';role=tag+'-operator-role';reader=tag+'-operator-schema';name=tag+'-operator'
    monitored=['alertmanagers','alertmanagerconfigs','podmonitors','probes','prometheusagents','prometheuses','prometheusrules','scrapeconfigs','servicemonitors','thanosrulers']
    rules=[{'apiGroups':['monitoring.coreos.com'],'resources':monitored,'verbs':['get','list','watch','patch']},
        {'apiGroups':['monitoring.coreos.com'],'resources':[r+'/status' for r in monitored]+[r+'/finalizers' for r in ('alertmanagers','prometheuses','prometheusagents','thanosrulers')],'verbs':['get','create','update','patch','delete']},
        {'apiGroups':['apps'],'resources':['statefulsets'],'verbs':['get','list','watch','create','update','patch','delete']},
        {'apiGroups':[''],'resources':['configmaps','secrets'],'verbs':['get','list','watch','create','update','patch','delete']},
        {'apiGroups':[''],'resources':['pods'],'verbs':['get','list','watch','delete']},
        {'apiGroups':[''],'resources':['services','services/finalizers','endpoints'],'verbs':['get','list','watch','create','update','patch','delete']},
        {'apiGroups':['events.k8s.io'],'resources':['events'],'verbs':['create','patch']},
        {'apiGroups':['networking.k8s.io'],'resources':['ingresses'],'verbs':['get','list','watch']}]
    cluster=[{'apiVersion':'rbac.authorization.k8s.io/v1','kind':'ClusterRole','metadata':{'name':reader},'rules':[
        {'apiGroups':['apiextensions.k8s.io'],'resources':['customresourcedefinitions'],'verbs':['get','list','watch']},
        {'apiGroups':[''],'resources':['namespaces'],'verbs':['get','list','watch']},
        {'apiGroups':['storage.k8s.io'],'resources':['storageclasses'],'resourceNames':['standard'],'verbs':['get']}]},binding(tag+'-operator-schema-binding',reader,sa,namespace,True)]
    operator={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':name},'spec':{'replicas':1,'selector':{'matchLabels':labels(tag,'monitoring-operator')},
        'template':{'metadata':{'labels':labels(tag,'monitoring-operator')},'spec':{'serviceAccountName':sa,'automountServiceAccountToken':True,'securityContext':pod_security(65534),
        'containers':[{'name':'operator','image':'quay.io/prometheus-operator/prometheus-operator:v'+OPERATOR,
            'args':['--namespaces='+namespace,'--watch-referenced-objects-in-all-namespaces=false','--disable-unmanaged-prometheus-configuration=true',
                '--prometheus-config-reloader=quay.io/prometheus-operator/prometheus-config-reloader:v'+OPERATOR,'--kubelet-service=','--kubelet-endpoints=false','--kubelet-endpointslice=false'],
            'ports':[{'name':'http','containerPort':8080}],'readinessProbe':{'httpGet':{'path':'/metrics','port':'http'},'periodSeconds':3},
            'resources':{'requests':{'cpu':'100m','memory':'100Mi'},'limits':{'cpu':'200m','memory':'200Mi'}},'securityContext':container_security(True)}]}}}}
    namespaced=[{'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':sa}},
        {'apiVersion':'rbac.authorization.k8s.io/v1','kind':'Role','metadata':{'name':role},'rules':rules},binding(tag+'-operator-binding',role,sa,namespace),operator]
    return cluster,namespaced


def discovery_manifests(tag,namespace):
    sa=tag+'-prom-sa';role=tag+'-discovery'
    rules=[{'apiGroups':[''],'resources':['pods','services','endpoints'],'verbs':['get','list','watch']},
           {'apiGroups':['discovery.k8s.io'],'resources':['endpointslices'],'verbs':['get','list','watch']}]
    role_object={'apiVersion':'rbac.authorization.k8s.io/v1','kind':'Role','metadata':{'name':role},'rules':rules}
    return sa,[role_object,binding(tag+'-discovery-binding',role,sa,namespace)]


def monitors(tag,namespace):
    specs=[('brokers',NS,{'strimzi.io/pool-name':'dual-role'},'tcp-prometheus','broker'),
           ('strimzi',NS,{'strimzi.io/kind':'cluster-operator'},'http','strimzi-operator'),
           ('target',NS,labels(tag,'synthetic'),'http','synthetic'),
           ('monitoring-operator',namespace,labels(tag,'monitoring-operator'),'http','monitoring-operator')]
    result=[]
    for suffix,target_ns,selector,port,kind in specs:
        relabel=[{'targetLabel':'qa_owner','replacement':tag},{'targetLabel':'qa_kind','replacement':kind},
            {'targetLabel':'cluster','replacement':CLUSTER},{'sourceLabels':['__meta_kubernetes_namespace'],'targetLabel':'namespace'}]
        if kind=='broker':relabel.append({'sourceLabels':['__meta_kubernetes_pod_name'],'targetLabel':'broker'})
        result.append({'apiVersion':'monitoring.coreos.com/v1','kind':'PodMonitor','metadata':{'name':tag+'-monitor-'+suffix,'labels':{'qa_owner':tag}},
            'spec':{'namespaceSelector':{'matchNames':[target_ns]},'selector':{'matchLabels':selector},'podMetricsEndpoints':[{'port':port,'path':'/metrics','interval':'5s','scrapeTimeout':'3s','sampleLimit':5000,'relabelings':relabel}]}})
    return result


def rule_spec(tag):
    runbook='https://github.com/sssamant21/data-platform-engineering-tutorials/tree/main/kafka/08-monitoring-metrics-observability'
    match='qa_owner="'+tag+'"'
    return {'groups':[{'name':'owned-kafka-foundation','interval':'1s','rules':[
        {'record':'qa:under_min_isr:max','expr':'max by(cluster,namespace,broker,qa_owner) (qa_under_min_isr_partitions{'+match+'})'},
        {'record':'qa:produce_p99_ms:per_broker','expr':'qa_request_ms{'+match+',request="Produce",stage="TotalTimeMs",quantile="0.99"}'},
        {'alert':'KafkaQaSyntheticTargetDown','expr':'(up{'+match+',qa_kind="synthetic"} == 0) or absent(up{'+match+',qa_kind="synthetic"})','for':'10s',
            'labels':{'severity':'warning','owner':'kafka-qa','qa_owner':tag},'annotations':{'summary':'Owned synthetic metrics target is down','runbook_url':runbook}},
        {'alert':'KafkaQaKRaftSignalInvalid','expr':'(qa_raft_current_leader{'+match+'} < 0) or (qa_raft_number_of_voters{'+match+'} != 3)','for':'2s',
            'labels':{'severity':'critical','owner':'kafka-qa','qa_owner':tag},'annotations':{'summary':'Owned KRaft leader or configured membership signal is invalid','runbook_url':runbook}},
        {'alert':'KafkaQaUnderMinISR','expr':'qa_under_min_isr_partitions{'+match+'} > 0','for':'0s',
            'labels':{'severity':'critical','owner':'kafka-qa','qa_owner':tag},'annotations':{'summary':'Owned Kafka minimum ISR signal is unhealthy','runbook_url':runbook}},
        {'alert':'KafkaQaRequiredMetricMissing','expr':'((count(qa_under_min_isr_partitions{'+match+'}) or vector(0)) < 3) or ((count(qa_raft_current_leader{'+match+'}) or vector(0)) < 3) or ((count(qa_raft_number_of_voters{'+match+'}) or vector(0)) < 3)','for':'10s',
            'labels':{'severity':'critical','owner':'kafka-qa','qa_owner':tag,'qa_kind':'broker','cluster':CLUSTER,'namespace':NS},'annotations':{'summary':'Required owned Kafka metric series are missing','runbook_url':runbook}},
        {'alert':'KafkaQaBrokerMetricsMissing','expr':'(sum(up{'+match+',qa_kind="broker"}) or vector(0)) < 3','for':'10s',
            'labels':{'severity':'critical','owner':'kafka-qa','qa_owner':tag,'qa_kind':'broker','cluster':CLUSTER,'namespace':NS},'annotations':{'summary':'Owned Kafka metrics coverage is incomplete','runbook_url':runbook}}
    ]}]}


def prometheus_manifests(tag,namespace,receiver_token):
    selector={'matchLabels':{'qa_owner':tag}};ns_selector={'matchLabels':{'qa.kafka/test-owner':tag}}
    prometheus={'apiVersion':'monitoring.coreos.com/v1','kind':'Prometheus','metadata':{'name':tag+'-prom'},'spec':{
        'replicas':1,'version':'v'+PROMETHEUS,'image':'quay.io/prometheus/prometheus:v'+PROMETHEUS,'serviceAccountName':tag+'-prom-sa',
        'retention':'1h','retentionSize':'100MB','scrapeInterval':'5s','evaluationInterval':'1s','enableAdminAPI':False,
        'podMonitorSelector':selector,'serviceMonitorSelector':selector,'ruleSelector':selector,
        'podMonitorNamespaceSelector':ns_selector,'serviceMonitorNamespaceSelector':ns_selector,'ruleNamespaceSelector':ns_selector,
        'resources':{'requests':{'cpu':'100m','memory':'200Mi'},'limits':{'cpu':'500m','memory':'512Mi'}},'securityContext':pod_security(65534),
        'storage':{'volumeClaimTemplate':{'spec':{'storageClassName':'standard','accessModes':['ReadWriteOnce'],'resources':{'requests':{'storage':'512Mi'}}}}},
        'alerting':{'alertmanagers':[{'namespace':namespace,'name':tag+'-am','port':'web','scheme':'http'}]}}}
    alertmanager={'apiVersion':'monitoring.coreos.com/v1','kind':'Alertmanager','metadata':{'name':tag+'-am'},'spec':{
        'replicas':1,'serviceAccountName':tag+'-am-sa','automountServiceAccountToken':False,'version':'v'+ALERTMANAGER,'image':'quay.io/prometheus/alertmanager:v'+ALERTMANAGER,'configSecret':tag+'-am-config',
        'volumes':[{'name':'receiver-auth','secret':{'secretName':tag+'-receiver-auth','defaultMode':0o440}}],
        'volumeMounts':[{'name':'receiver-auth','mountPath':'/receiver-auth','readOnly':True}],
        'resources':{'requests':{'cpu':'50m','memory':'64Mi'},'limits':{'cpu':'200m','memory':'128Mi'}},'securityContext':pod_security(65534)}}
    route={'global':{'resolve_timeout':'30s'},'route':{'receiver':'owned-local-webhook','group_by':['alertname','qa_owner'],'group_wait':'1s','group_interval':'1s','repeat_interval':'1m'},
        'receivers':[{'name':'owned-local-webhook','webhook_configs':[{'url':f'http://{tag}-receiver.{namespace}.svc:8080/alerts','send_resolved':True,'http_config':{'authorization':{'type':'Bearer','credentials_file':'/receiver-auth/token'}}}]}]}
    return [{'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':tag+'-prom-sa'}},
        {'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':tag+'-am-sa'},'automountServiceAccountToken':False},
        {'apiVersion':'v1','kind':'Secret','metadata':{'name':tag+'-receiver-auth'},'type':'Opaque','stringData':{'token':receiver_token}},
        {'apiVersion':'v1','kind':'Secret','metadata':{'name':tag+'-am-config'},'type':'Opaque','stringData':{'alertmanager.yaml':json.dumps(route)}},
        alertmanager,prometheus,service(tag,'am',{'alertmanager':tag+'-am'},9093),service(tag,'prom',{'prometheus':tag+'-prom'},9090),
        {'apiVersion':'monitoring.coreos.com/v1','kind':'PrometheusRule','metadata':{'name':tag+'-rules','labels':{'qa_owner':tag}},'spec':rule_spec(tag)}]


def server_deployment(tag,role,image,source,account,args):
    return {'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':tag+'-'+role},'spec':{'replicas':1,'selector':{'matchLabels':labels(tag,role)},
        'template':{'metadata':{'labels':labels(tag,role)},'spec':{'serviceAccountName':account,'automountServiceAccountToken':False,'securityContext':pod_security(1001),
            'terminationGracePeriodSeconds':20,'volumes':[{'name':'source','configMap':{'name':source}},{'name':'tmp','emptyDir':{}}],
            'containers':[{'name':'server','image':image,'command':['java','--add-modules','jdk.httpserver','-Xmx128m','-cp','/opt/kafka/libs/*','/qa/ObservabilityTarget.java',*args],
                'volumeMounts':[{'name':'source','mountPath':'/qa','readOnly':True},{'name':'tmp','mountPath':'/tmp'}],'ports':[{'name':'http','containerPort':8080}],
                'startupProbe':{'httpGet':{'path':'/healthz','port':'http'},'failureThreshold':45,'periodSeconds':2,'timeoutSeconds':2},
                'readinessProbe':{'httpGet':{'path':'/healthz','port':'http'},'periodSeconds':2,'timeoutSeconds':2},
                'securityContext':container_security(True),'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'500m','memory':'384Mi'}}}]}}}}


def grafana_manifests(tag,namespace,password):
    name=tag+'-grafana';uid=tag+'-prom';dashboard_uid=tag+'-foundation'
    expressions=[('Broker scrape availability','up{qa_owner="'+tag+'",qa_kind="broker"}','short'),
        ('KRaft leader ID','qa_raft_current_leader{qa_owner="'+tag+'"}','short'),
        ('Under minimum ISR','qa_under_min_isr_partitions{qa_owner="'+tag+'"}','short'),
        ('Produce p99 per broker','qa:produce_p99_ms:per_broker{qa_owner="'+tag+'"}','ms'),
        ('Broker heap used','qa_jvm_heap_bytes{qa_owner="'+tag+'",measure="used"}','bytes'),
        ('Client produced and processed','qa_client_processed_records_total{qa_owner="'+tag+'"}','short')]
    panels=[]
    for index,(title,expr,unit) in enumerate(expressions):
        panels.append({'id':index+1,'type':'timeseries','title':title,'datasource':{'type':'prometheus','uid':uid},'gridPos':{'x':index%2*12,'y':index//2*8,'w':12,'h':8},
            'targets':[{'refId':'A','expr':expr,'legendFormat':'{{broker}} {{instance}}'}],'fieldConfig':{'defaults':{'unit':unit},'overrides':[]}})
    panels[-1]['targets'][0]['legendFormat']='processed {{instance}}'
    panels[-1]['targets'].append({'refId':'B','expr':'qa_client_produced_records_total{qa_owner="'+tag+'"}','legendFormat':'produced {{instance}}'})
    panels.append({'id':7,'type':'text','title':'Coverage limits','gridPos':{'x':0,'y':24,'w':24,'h':5},'options':{'mode':'markdown','content':'Provider disk latency/IOPS, attributed page cache, node/cAdvisor telemetry, production SSO/paging and independent acceptance: **Pending**. Missing series are not healthy zeros. Combined-role handler MeanRate is not an isolated broker fraction.'}})
    dashboard={'uid':dashboard_uid,'title':'Kafka QA observability foundation','schemaVersion':39,'version':1,'editable':False,'timezone':'utc','time':{'from':'now-5m','to':'now'},'refresh':'5s','panels':panels}
    datasource={'apiVersion':1,'datasources':[{'name':'Kafka QA Prometheus','uid':uid,'type':'prometheus','access':'proxy','url':f'http://{tag}-prom.{namespace}.svc:9090','isDefault':True,'editable':False,'jsonData':{'httpMethod':'POST','timeInterval':'5s'}}]}
    provider={'apiVersion':1,'providers':[{'name':'Kafka QA','orgId':1,'folder':'Kafka QA','type':'file','disableDeletion':True,'editable':False,'updateIntervalSeconds':5,'options':{'path':'/var/lib/grafana/dashboards/qa'}}]}
    deployment={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':name},'spec':{'replicas':1,'selector':{'matchLabels':labels(tag,'grafana')},
        'template':{'metadata':{'labels':labels(tag,'grafana')},'spec':{'serviceAccountName':tag+'-grafana-sa','automountServiceAccountToken':False,'securityContext':pod_security(472),
            'volumes':[{'name':'data','emptyDir':{}},{'name':'tmp','emptyDir':{}},{'name':'credentials','secret':{'secretName':tag+'-grafana-auth','defaultMode':0o440}},
                {'name':'datasources','configMap':{'name':tag+'-grafana-datasource'}},{'name':'providers','configMap':{'name':tag+'-grafana-provider'}},{'name':'dashboard','configMap':{'name':tag+'-grafana-dashboard'}}],
            'containers':[{'name':'grafana','image':'grafana/grafana:'+GRAFANA,'ports':[{'name':'http','containerPort':3000}],
                'env':[{'name':'GF_SECURITY_ADMIN_USER','value':'qa-admin'},{'name':'GF_SECURITY_ADMIN_PASSWORD__FILE','value':'/grafana-credentials/password'},
                       {'name':'GF_AUTH_ANONYMOUS_ENABLED','value':'false'},{'name':'GF_USERS_ALLOW_SIGN_UP','value':'false'},
                       {'name':'GF_PLUGINS_PREINSTALL_DISABLED','value':'true'},{'name':'GF_ANALYTICS_REPORTING_ENABLED','value':'false'},
                       {'name':'GF_ANALYTICS_CHECK_FOR_UPDATES','value':'false'},{'name':'GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES','value':'false'}],
                'volumeMounts':[{'name':'data','mountPath':'/var/lib/grafana'},{'name':'tmp','mountPath':'/tmp'},{'name':'credentials','mountPath':'/grafana-credentials','readOnly':True},
                    {'name':'datasources','mountPath':'/etc/grafana/provisioning/datasources','readOnly':True},{'name':'providers','mountPath':'/etc/grafana/provisioning/dashboards','readOnly':True},{'name':'dashboard','mountPath':'/var/lib/grafana/dashboards/qa','readOnly':True}],
                'readinessProbe':{'httpGet':{'path':'/api/health','port':'http'},'periodSeconds':3,'timeoutSeconds':2},
                'securityContext':container_security(True),'resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'500m','memory':'384Mi'}}}]}}}}
    manifests=[{'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':tag+'-grafana-sa'},'automountServiceAccountToken':False},
        {'apiVersion':'v1','kind':'Secret','metadata':{'name':tag+'-grafana-auth'},'type':'Opaque','stringData':{'password':password}},
        {'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':tag+'-grafana-datasource'},'data':{'datasources.yaml':json.dumps(datasource)}},
        {'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':tag+'-grafana-provider'},'data':{'providers.yaml':json.dumps(provider)}},
        {'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':tag+'-grafana-dashboard'},'data':{'foundation.json':json.dumps(dashboard)}},
        deployment,service(tag,'grafana',labels(tag,'grafana'),3000)]
    return manifests,{'dashboard_uid':dashboard_uid,'datasource_uid':uid,'dashboard':dashboard,'datasource':datasource}


def rule_test_documents(tag):
    spec=rule_spec(tag);alerts={rule['alert']:rule for rule in spec['groups'][0]['rules'] if 'alert' in rule}
    brokers=[{'series':f'up{{qa_owner="{tag}",qa_kind="broker",broker="broker-{i}"}}','values':'1x30'} for i in range(3)]
    gauges=[{'series':f'qa_under_min_isr_partitions{{qa_owner="{tag}",cluster="{CLUSTER}",namespace="{NS}",broker="broker-{i}",qa_kind="broker"}}','values':'0x30'} for i in range(3)]
    client={'series':f'up{{qa_owner="{tag}",qa_kind="synthetic"}}','values':'1x30'}
    raft=[{'series':f'{name}{{qa_owner="{tag}",cluster="{CLUSTER}",namespace="{NS}",broker="broker-{i}",qa_kind="broker"}}','values':str(value)+'x30'} for name,value in (('qa_raft_current_leader',1),('qa_raft_number_of_voters',3)) for i in range(3)]
    healthy=brokers+gauges+raft
    def expected(name,extra=None):
        rule=alerts[name];return {'exp_labels':{**(extra or {}),**rule['labels']},'exp_annotations':rule['annotations']}
    unhealthy={**gauges[0],'values':'1x30'}
    tests=[{'interval':'1s','input_series':healthy+[client], 'alert_rule_test':[
        {'eval_time':'15s','alertname':name,'exp_alerts':[]} for name in alerts]},
        {'interval':'1s','input_series':healthy+[{'series':client['series'],'values':'0x15 1x15'}],
         'alert_rule_test':[{'eval_time':'5s','alertname':'KafkaQaSyntheticTargetDown','exp_alerts':[]},
            {'eval_time':'15s','alertname':'KafkaQaSyntheticTargetDown','exp_alerts':[expected('KafkaQaSyntheticTargetDown',{'qa_kind':'synthetic'})]},
            {'eval_time':'25s','alertname':'KafkaQaSyntheticTargetDown','exp_alerts':[]}]},
        {'interval':'1s','input_series':healthy,'alert_rule_test':[{'eval_time':'15s','alertname':'KafkaQaSyntheticTargetDown','exp_alerts':[expected('KafkaQaSyntheticTargetDown',{'qa_kind':'synthetic'})]}]},
        {'interval':'1s','input_series':gauges+raft+[client], 'alert_rule_test':[{'eval_time':'15s','alertname':'KafkaQaBrokerMetricsMissing','exp_alerts':[expected('KafkaQaBrokerMetricsMissing')]}]},
        {'interval':'1s','input_series':brokers+[client], 'alert_rule_test':[{'eval_time':'15s','alertname':'KafkaQaRequiredMetricMissing','exp_alerts':[expected('KafkaQaRequiredMetricMissing')]}]},
        {'interval':'1s','input_series':brokers+raft+[client,unhealthy,*gauges[1:]],
         'alert_rule_test':[{'eval_time':'1s','alertname':'KafkaQaUnderMinISR','exp_alerts':[expected('KafkaQaUnderMinISR',{'cluster':CLUSTER,'namespace':NS,'broker':'broker-0','qa_kind':'broker'})]}],
         'promql_expr_test':[{'expr':'qa:under_min_isr:max{broker="broker-0"}','eval_time':'2s','exp_samples':[{'labels':f'qa:under_min_isr:max{{cluster="{CLUSTER}",namespace="{NS}",broker="broker-0",qa_owner="{tag}"}}','value':1}]}]}]
    tests.append({'interval':'1s','input_series':brokers+gauges+[client,{**raft[0],'values':'-1x30'},*raft[1:]],'alert_rule_test':[{'eval_time':'5s','alertname':'KafkaQaKRaftSignalInvalid','exp_alerts':[expected('KafkaQaKRaftSignalInvalid',{'cluster':CLUSTER,'namespace':NS,'broker':'broker-0','qa_kind':'broker'})]}]})
    return {'rules.yaml':json.dumps(spec),'tests.yaml':json.dumps({'rule_files':['/qa/rules.yaml'],'evaluation_interval':'1s','tests':tests})}


def promtool_manifests(tag):
    cm=tag+'-rule-tests';image='quay.io/prometheus/prometheus:v'+PROMETHEUS
    common={'image':image,'volumeMounts':[{'name':'rules','mountPath':'/qa','readOnly':True},{'name':'tmp','mountPath':'/tmp'}],
        'securityContext':container_security(True),'resources':{'requests':{'cpu':'100m','memory':'64Mi'},'limits':{'cpu':'500m','memory':'192Mi'}}}
    return [{'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':cm},'data':rule_test_documents(tag)},
        {'apiVersion':'batch/v1','kind':'Job','metadata':{'name':tag+'-promtool'},'spec':{'backoffLimit':0,'activeDeadlineSeconds':120,
            'template':{'spec':{'restartPolicy':'Never','automountServiceAccountToken':False,'securityContext':pod_security(65534),
                'volumes':[{'name':'rules','configMap':{'name':cm}},{'name':'tmp','emptyDir':{'sizeLimit':'64Mi'}}],
                'initContainers':[{**common,'name':'lint','command':['/bin/promtool','check','rules','/qa/rules.yaml']}],
                'containers':[{**common,'name':'unit','command':['/bin/promtool','test','rules','/qa/tests.yaml']}]}}}}]
