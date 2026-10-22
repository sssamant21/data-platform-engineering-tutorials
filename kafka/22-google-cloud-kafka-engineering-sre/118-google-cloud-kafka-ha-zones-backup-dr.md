# Chapter 118 — Google Cloud Kafka HA, Zones, Backup and DR

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (8/10)  
**Primary platform:** GKE Standard + Strimzi Kafka KRaft  
**Managed alternative:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–117, isolated GKE/Kafka lab, monitoring and synthetic pipeline  
**Publication:** Published · **Live labs:** Pending · **Independent review:** Pending · **Runtime certification:** Not claimed

> **Safety:** Do not delete PVCs, force leader elections, terminate production brokers, modify live replication settings or perform DR cutover in shared environments. Snapshotting an individual Kafka disk is not automatically a consistent recoverable Kafka backup. Verify version-specific Strimzi, GKE CSI, Google Cloud snapshot and managed Kafka DR capabilities against official documentation.

## 1. Mission and learning outcomes

Design and validate high availability across GKE zones, durable recovery of Kafka data and configuration, and regional disaster recovery with measurable RPO/RTO. Distinguish replication, snapshots, off-cluster backup, event replay and cross-region replication. Establish fencing and event-ID reconciliation to prevent split brain and silent loss.

**Deliverables:** failure-domain matrix, backup/restore design, DR topology, synthetic event recovery evidence, 20 labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Reference architecture

```text
Google Cloud region A — GKE Standard
  Zone A       Zone B       Zone C
  broker 0     broker 1     broker 2
  controller 0 controller 1 controller 2
    |               |            |
  CSI PVCs      CSI PVCs     CSI PVCs
          Kafka replication + ISR
                     |
         producers/consumers on GKE
                     |
      off-cluster backup + config export
                     |
      independent event-ID reconciliation
                     |
       regional DR replication/replay
                     |
Google Cloud region B — standby Kafka + consumers
             (fenced until cutover)
```

Three controller replicas do not guarantee a surviving quorum if scheduling places them in the same failure domain. Three broker replicas do not guarantee three-zone distribution. Inspect Pod zones, PVC topology, partition replica assignment and quorum state.

## 3. Availability and durability fundamentals

- **KRaft quorum:** A majority of configured voting controllers must remain available for metadata operations; validate the exact controller quorum model of the deployed Kafka version.
- **Partition ISR:** Acknowledged write durability depends on producer `acks`, topic replica placement, `min.insync.replicas` and broker health.
- **PodDisruptionBudget:** Helps limit voluntary disruptions; does not protect against an entire zone outage.
- **Zonal PVC:** Typically cannot be attached arbitrarily in another zone. Replacement Pods must honor volume topology.
- **Replication:** Protects against selected broker failures, not mistaken deletion, malicious changes, corruption or all-region loss.
- **Backup:** Must include a tested restore of Kafka data and relevant metadata, identities, topic configs, application checkpoints and external dependencies.
- **DR:** Requires application cutover, DNS/network/credentials, offset translation or checkpointing, fencing, and a measured event-loss budget.

## 4. Read-only HA inventory

```powershell
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -n kafka -o wide
kubectl get pvc,pv -A
kubectl get pdb -n kafka
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -n kafka
kubectl get events -n kafka --sort-by=.lastTimestamp
gcloud config get-value project
```

Record Kafka/Strimzi versions, controller voters, broker count, zone distribution, replica factor, ISR, storage class, disk reclaim policy, retention, consumer group checkpoints and client bootstrap dependencies. Do not print Secret values.

## 5. KRaft and broker zone-aware placement

Use Strimzi-supported scheduling configuration, Kubernetes topology spread and rack awareness to distribute controllers and brokers. For a three-controller quorum, test that any **single-zone** loss leaves a majority of voters when the intended zone distribution is one voter per zone. Verify broker partition replicas across zones and remaining capacity under zone loss. `min.insync.replicas=2` with three replicas and `acks=all` is a common baseline, but only valid if application durability and availability requirements approve it.

Avoid changing node-pool roles, scaling controllers or modifying storage without the installed Strimzi release's supported procedure.

## 6. Backup design

Define recoverable assets explicitly:

| Asset | Backup/recovery method | Consistency requirement |
|---|---|---|
| Topic payloads | Supported cross-cluster replication or coordinated backup/replay | Consistent event log and ordering contract |
| Topic configs | Version-controlled manifests or API export | Version and ACL compatibility |
| KafkaUser/ACL policies | GitOps + secure credential source | No private keys in Git |
| KRaft metadata | Kafka/Strimzi-supported recovery design | Quorum metadata compatibility |
| Consumer offsets | Tested checkpoint/translation procedure | No skipped acknowledged events |
| Producer state | Idempotency/fencing and accepted-ID ledger | Avoid duplicate side effects |
| External sink | Database backup and checkpoint | Durable idempotent recovery |
| Encryption keys | Approved key-management recovery | Key availability and access audit |

**Warning:** Per-PVC CSI snapshots may capture brokers at different instants. Restoring arbitrary independent snapshots into one Kafka cluster can create inconsistent state. Use a documented, supported, tested recovery approach rather than assuming snapshots alone satisfy RPO.

## 7. Cross-region DR patterns

Evaluate asynchronous topic replication, active-passive standby, producer replay from an independent durable source and application rebuild. Select based on ordering, replication lag, data sovereignty, cost, bandwidth and target RPO/RTO. Cross-region asynchronous replication can lose acknowledged events that have not reached the DR site; measure this exposure.

**Cutover sequence:** declare incident → freeze/fence old writers and consumers → capture source and destination checkpoints → verify destination topic/schema/security compatibility → promote standby only under change authority → restart clients against approved bootstrap → reconcile event IDs and sink effects → monitor error budget → document failback conditions.

Never operate two writable primaries for the same logical event stream without an explicitly designed conflict and deduplication protocol.

## 8. RPO and RTO measurement

```text
RPO = last acknowledged source event time
      minus last durably recoverable destination event time

RTO = time validated service was restored
      minus time recovery-impacting incident began
```

RPO should also be validated using **sets of accepted event IDs**, not only timestamps, to catch gaps. Record exact measurement start/stop criteria and independent evidence. A recovered broker process does not mean consumers and downstream sinks are healthy.

## 9. Managed Kafka DR differences

For Google Cloud Managed Service for Apache Kafka, verify documented zone availability, backups, replication, region support, restore APIs, operational responsibilities and quotas. Do not assume customer-controlled KRaft controllers, CSI snapshots or Strimzi node pools exist. Customers still own client recovery, event contracts, downstream checkpointing, incident communications and DR acceptance.

## 10. Hands-on labs (20)

Each lab requires version, prerequisites, exact commands/queries, expected and observed results, timestamped evidence, rollback and PASS/FAIL. No lab is marked executed by publication.

| # | Lab | Evidence |
|---|---|---|
| 01 | Verify GKE zone topology | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 02 | Inspect controller KRaft quorum | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 03 | Inspect broker replica placement | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 04 | Check topic replication and ISR | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 05 | Review min.insync.replicas policy | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 06 | Measure failure-domain headroom | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 07 | Verify topology spread and PDB | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 08 | Inventory PV and StorageClass | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 09 | Document snapshot consistency risks | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 10 | Verify object storage backup IAM | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 11 | Export topic and ACL configuration | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 12 | Capture consumer offset checkpoint | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 13 | Create synthetic event reconciliation set | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 14 | Simulate isolated broker Pod loss | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 15 | Simulate bounded node maintenance | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 16 | Test recovery from durable sink checkpoint | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 17 | Test region DR connectivity | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 18 | Rehearse fenced consumer cutover | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 19 | Measure actual RPO and RTO | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |
| 20 | Restore baseline and cost evidence | Quorum/ISR evidence, recovery checkpoint, measured RPO/RTO and rollback |

### Lab execution protocol

1. Confirm isolated GCP project, cost owner, cluster context and disaster recovery scope.
2. Capture healthy controller quorum, broker ISR, topic configs and accepted synthetic IDs.
3. Validate backup inventory and destination connectivity without mutating shared systems.
4. Run one approved bounded failure or restore experiment.
5. Verify quorum, replica catch-up, consumer offsets, sink correctness and no unexplained missing IDs.
6. Calculate observed RPO/RTO from timestamped evidence.
7. Revert temporary routing and cleanup only lab-owned resources.

## 11. Failure scenarios (12)

| # | Scenario | Recovery objective |
|---|---|---|
| 1 | Controller quorum loss | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 2 | Zone-wide broker outage | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 3 | Replica under-replication | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 4 | Unclean leader election risk | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 5 | PV bound to unavailable zone | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 6 | PVC snapshot unusable for consistent restore | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 7 | Lost topic/ACL configuration | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 8 | Consumer offset checkpoint mismatch | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 9 | Cross-region replication lag | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 10 | Dual-active producer split brain | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 11 | Failover DNS/authentication failure | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |
| 12 | Recovered cluster missing acknowledged events | Contain failure domain, preserve state, restore service, reconcile IDs and verify RPO/RTO |

For every scenario record severity, trigger, blast radius, expected alarm, evidence, stop condition, decision owner, rollback and preventive action. Simulate only in a disposable environment.

## 12. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Controller quorum recovery | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 2 | Broker/ISR degradation | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 3 | GKE zone outage | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 4 | Persistent volume restore | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 5 | Configuration and ACL restore | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 6 | Regional DR failover | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 7 | Failback and offset reconciliation | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |
| 8 | Backup integrity and DR audit | Impact → read-only triage → approved recovery/fencing → integrity validation → RCA |

Every runbook must specify authority, escalation, safe diagnostics, prerequisites, recovery sequencing, abort criteria, communication and audit evidence.

## 13. 100-point HA/DR acceptance

| Gate | Points |
|---|---:|
| Controller quorum and zone placement | 15 |
| Broker replicas, ISR and failover capacity | 15 |
| Persistent storage and backup design | 15 |
| Configuration and identity recovery | 10 |
| Regional DR/fencing and cutover | 15 |
| Event correctness and offset reconciliation | 15 |
| Measured RPO/RTO and observability | 10 |
| Evidence and independent review | 5 |
| **Total** | **100** |

**Proposed pass:** ≥85/100, no unexplained missing acknowledged IDs, demonstrable controller quorum under the approved failure scenario, tested restore/cutover, measured RPO/RTO within approved objectives, no critical security issue and independent review. Publication does not certify DR readiness.

## 14. Evidence manifest

```yaml
chapter: 118
environment: isolated-gke-kafka-dr
backend: REPLACE_STRIMZI_OR_MANAGED
primary_region: REPLACE
dr_region: REPLACE
controller_zones: []
broker_zones: []
replication_factor: null
min_insync_replicas: null
backup_inventory: []
restore_test: pending
accepted_event_ids: null
recovered_event_ids: null
missing_accepted_ids: null
rpo_seconds_observed: null
rto_seconds_observed: null
fencing_test: pending
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 15. Next chapter

**Chapter 119 — Google Cloud Kafka Incident Response, Security and Upgrade Operations.**
