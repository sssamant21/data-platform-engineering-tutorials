#!/usr/bin/env python3
"""Bounded application performance capstone; full production capacity gates stay pending."""
import json
from runtime_acceptance import k
from capstone_performance import CapstoneLab, application_observations, capacity_model
from consumer_acceptance import expected_crash, sink_binding, json_observation
from performance_lab import execute_benchmark, TrialDriver, create_performance_topic
from performance_acceptance import cgroup_observations
from broker_acceptance import broker_arguments, broker_observations
from run_chapter_034 import broker_plan, compare_brokers, LIMITS as BROKER_LIMITS

LIMITS=[*BROKER_LIMITS,
    'This CI capstone integrates short application phases and the six matched broker microbenchmarks, not the published production SLO examples or30-minute soak. No production capacity acceptance is issued.',
    'Application event age uses explicit Kafka CreateTime and forced-file completion on a shared clock. The sink is a single-writer synthetic local-path PVC, not an external business database, host/power-loss or CSI failure guarantee.',
    'Three actual application repetitions each use120warmup/360baseline/360paused-burst/360recovery records at offered caps100/200/400/100. Acknowledgment wait, handler+force, event age and committed lag are separate; native fetch throughput never substitutes for business processing.',
    'A real client exit23 before commit and fresh-process replay deduplication reuse the accepted consumer helper. No production offsets are reset; only the owned synthetic sink PVC is written.',
    'Application phases use one actual consumer per fresh group. The full producer/consumer candidate matrices and1/3/6/8member scaling sweep are not rerun as fresh capstone measurements; their historical chapter reports do not satisfy those full capstone gates.',
    'Representative30-minute soak/provider storage latency/page-cache/independent assessor/business SLO approval remain BLOCKED_OR_PENDING. Historical chapter success is not reused as a fresh capstone check or enterprise certification.'
]
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'capacity_decision':'NOT_APPROVED_PRODUCTION_CAPACITY',
    'thirty_minute_soak':{'status':'BLOCKED_NOT_EXECUTED','reason':'required representative provider latency/page-cache and approved production telemetry are unavailable on single-host kind'},
    'sample_manuscript_slos':'ILLUSTRATIVE_NOT_ADOPTED_OR_REPORTED_AS_PASSED',
    'full_producer_consumer_matrices_and_scaling':'NOT_EXECUTED_IN_FULL_ON_THIS_CAPSTONE_RUN','independent_assessor_signoff':'PENDING','critical_gaps':['production workload/SLO approval','provider latency/IOPS and page-cache attribution','representative soak','broker-only handler saturation isolation','independent review']}


def setup(lab):
    apps=[{'topic':create_performance_topic(lab,'app-r'+str(i),6),'group':lab.tag+'-app-r'+str(i)+'-group','trial':'r'+str(i)} for i in (1,2,3)]
    replay={'topic':create_performance_topic(lab,'replay',6),'group':lab.tag+'-replay-group','event_id':lab.tag+'-replay'}
    sink=lab.tag+'-sink'
    lab.apply({'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':{'name':sink,'labels':{'qa.kafka/test-owner':lab.tag},'annotations':{'qa.kafka/purpose':'synthetic application/replay sink; never broker data'}},
        'spec':{'accessModes':['ReadWriteOnce'],'volumeMode':'Filesystem','storageClassName':'standard','resources':{'requests':{'storage':'1Gi'}}}})
    return {'apps':apps,'replay':replay,'sink':sink,'topics':[app['topic'] for app in apps]+[replay['topic']],
        'groups':[app['group'] for app in apps]+[replay['group']]}


def stage(lab,suffix,main,args,checks,sink=None,planned_crash=False):
    child=CapstoneLab('035',LIMITS);child.tag,child.out,child.image,child.owned=lab.tag+'-'+suffix,lab.out/suffix,lab.image,lab.owned
    child.client_service_account,child.ca_secret,child.identity_secret=lab.client_service_account,lab.ca_secret,lab.identity_secret;child.identity_items=['password']
    if sink:child.sink_claim=sink
    failure=None
    try:child.run_job(main,args,checks)
    except RuntimeError as exc:
        if not planned_crash:raise
        failure=exc
    finally:lab.result['checks'].update(child.result['checks'])
    path=child.out/'chapter-035-client.log';lines=[line for line in path.read_text(encoding='utf-8').splitlines() if line.startswith(('OBS:','CHECK:'))]
    job=child.tag+'-client';pods=json.loads(k('get','pods','-l','app='+job,'-o','json'))['items']
    if len(pods)!=1:raise RuntimeError('Expected one owned application/replay Pod')
    result={'job':job,'pod_uid':pods[0]['metadata']['uid'],'source_bundle_sha256':child.result['java_source_bundle_sha256'],'evidence':str(path.relative_to(lab.out))}
    if planned_crash:
        manifest=json.loads(k('get','job',job,'-o','json'));result['expected_fault']=expected_crash(manifest,pods,failure is not None and all(child.result['checks'].get(name)=='PASS' for name in checks))
    return result,lines,pods[0]


def binding(lab,claim,pod,label):
    pvc=json.loads(lab.read(label+'-pvc','get','pvc',claim,'-o','json'));pv=json.loads(lab.read(label+'-pv','get','pv',pvc['spec']['volumeName'],'-o','json'))
    return sink_binding(pvc,pv,pod,claim)


def extra(lab,context):
    cfg=context['extras'];sink=cfg['sink'];bootstrap,username=context['bootstrap'],context['username'];rows=[];initial_binding=None
    for app in cfg['apps']:
        trial=app['trial'];proof,lines,pod=stage(lab,'app-'+trial,'CapstoneAcceptance',['phases',bootstrap,username,app['topic'],app['group'],lab.tag+'-'+trial,trial],
            [trial+'_'+name for name in ('actual_application_phases_ack_force_commit_and_no_missing_ids','paused_burst_backlog_drains_with_new_ingress_and_final_commits','secure_full_isr_quorum_and_bounded_application_shutdown')],sink)
        actual_binding=binding(lab,sink,pod,'application-'+trial)
        if initial_binding is None:initial_binding=actual_binding
        if actual_binding!=initial_binding:raise RuntimeError('Application sink binding changed')
        proof['outcome']=application_observations(lines);proof['client_cgroup']=cgroup_observations(lines);rows.append(proof)
    lab.result['application_repetitions']=rows
    replay=cfg['replay'];base=[bootstrap,username,replay['topic']]
    seed,_,_=stage(lab,'replay-seed','ConsumerAcceptance',['seed',*base,replay['event_id'],'120'],['seed_bounded_six_partition_seed_acks_all'])
    crash,checkpoint,pod=stage(lab,'replay-crash','ConsumerAcceptance',['replay-crash',*base,replay['group'],replay['event_id']],['replay-crash_forced_sink_checkpoint_before_commit_expected_halt'],sink,True)
    before=binding(lab,sink,pod,'crash')
    recovery,lines,pod=stage(lab,'replay-recover','ConsumerAcceptance',['replay-recover',*base,replay['group'],replay['event_id']],
        ['replay-recover_replayed_uncommitted_ids_deduplicated_and_no_missing_ids','replay-recover_commit_after_success_reaches_captured_ends'],sink)
    after=binding(lab,sink,pod,'recover')
    if before!=after or after!=initial_binding:raise RuntimeError('Same owned sink PVC/PV binding not preserved through all application and replay Jobs')
    lab.result['consumer_replay']={'seed':seed,'crash':crash,'checkpoint':json_observation(checkpoint,'REPLAY_CHECKPOINT'),'recovery':recovery,
        'outcome':json_observation(lines,'REPLAY_RECOVERY'),'same_owned_sink_binding':after,'scope':'process crash before commit, fresh process forced-file reload and event-ID deduplication; not external DB exactly-once'}
    lab.result['checks']['same_owned_capstone_sink_binding_all_jobs']='PASS'
    lab.result['capacity_model']=capacity_model(5000,1024,.6,3,24,3)
    lab.result['additional_workload_budget']={'application_repetitions':3,'application_records_per_repetition':1200,'replay_records':120,
        'additional_logical_payload_bytes':3720*1024,'additional_replicated_payload_bytes':3720*1024*3,'scope':'in addition to separately reported native trial budget; no uncontrolled soak'}
    lab.result['capstone_assessment']=ASSESSMENT


def main():
    driver=TrialDriver(lab_class=CapstoneLab,main='BrokerAcceptance',arguments=broker_arguments,analyze=broker_observations,profile_fields=(('io_threads','num.io.threads'),))
    return execute_benchmark('035',broker_plan(),LIMITS,{'partitions':6,'broker_metrics':'actual per-broker JMX; inherited validated metrics fixture'},ASSESSMENT,compare_brokers,
        'broker_tuning_comparison',setup,extra,runtime_scope='ACTUAL_SHORT_APPLICATION_PHASES_FORCED_SINK_LAG_RECOVERY_REPLAY_AND_SECURE_BROKER_TUNING_ROLLBACK_NOT_FULL_CAPACITY_ACCEPTANCE',driver=driver)


if __name__=='__main__':raise SystemExit(main())
