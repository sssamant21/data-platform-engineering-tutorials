# Chapter 108 — Azure Kafka HA, Availability Zones, Backup and DR

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (8/10)  
**Primary platform:** Azure AKS, Strimzi-managed Apache Kafka in KRaft mode  
**Comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–107; isolated AKS lab, monitoring and approved recovery targets  
**Publication:** Published upon GitHub commit · **Live execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Run failure injection, storage recovery, failover and restore only in disposable, isolated environments with explicit approval, a budget and an exit plan. Never delete production PVCs, force KRaft controller quorum changes, or initiate a real regional failover from this chapter. Kafka replication is not a backup; Azure Event Hubs geo-disaster recovery is not necessarily event-data replication. Verify current service-tier capabilities before planning production recovery.

## 1. Mission and outcomes

Engineer and validate Kafka availability through broker, controller, node and zone failures; establish defensible backup and disaster recovery procedures; compare self-managed Kafka on AKS with Azure Event Hubs. Measure RPO, RTO, replay correctness and operational risk.

**Deliverables:** zone-aware topology, HA design review, RPO/RTO matrix, recoverable configuration backups, data protection strategy, recovery drills, 20 labs, 12 failure scenarios, 8 runbooks, and 100-point assessment.

## 2. Architecture and failure domains

```text
                  AKS regional cluster
      Zone 1             Zone 2             Zone 3
  broker A / PVC     broker B / PVC     broker C / PVC
  controller A       controller B       controller C
        \                 |                /
         +--- Strimzi Kafka KRaft quorum ---+
                       |
             producers / consumers
                       |
              replication strategy
                       v
       Secondary region / independent Kafka
       + checkpoints + client cutover plan

  Azure Event Hubs alternative:
  namespace + supported AZ resilience and DR features
  (metadata alias vs event-data replication must be verified)
```

Zone resilience requires both zone-aware infrastructure and correct placement of broker replicas, controllers, persistent volumes and application clients. A 3-controller KRaft quorum tolerates one controller failure; losing a majority prevents metadata quorum progress. Do not assume 3 brokers always mean 3 distinct zones.

## 3. Recovery objectives and durability contract

Define **RPO** (maximum acceptable lost committed business events) and **RTO** (maximum acceptable service restoration time) separately for:
- Broker crash with intact replicas.
- Zone outage and degraded ISR.
- Region loss requiring secondary-cluster promotion.
- Corrupted data, operator misconfiguration or credential loss.
- Client offsets and external sink consistency.

Kafka `acks=all` with an appropriate `min.insync.replicas` reduces certain data-loss risks but does not guarantee zero loss under every disaster, nor replace immutable backups and application reconciliation.

| Protection mechanism | Protects against | Important limitation |
|---|---|---|
| Kafka replica replication | Broker/disk failure within cluster | Same-cluster corruption and region loss |
| Cross-region topic replication | Regional outage when preconfigured | Async lag and offset translation |
| CR/IaC/Secret backup | Configuration reconstruction | Not a copy of Kafka event logs |
| Application source replay | Rebuilding a derived stream | Requires durable source and retention |
| Disk snapshots | Some storage recovery cases | Crash consistency, topology and broker coordination must be validated |

## 4. Kubernetes-first preflight

```powershell
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic -A
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka -o wide
kubectl get storageclass
kubectl get pdb -A
kubectl get events -n kafka --sort-by=.lastTimestamp
az account show --query '{subscription:id,tenant:tenantId}' -o json
```

Confirm actual namespace, cluster name, Strimzi version, storage topology and cloud subscription. Preserve sanitized outputs as baseline evidence. Never assume Azure disk volumes can be mounted freely across availability zones; check CSI and disk SKU constraints.

## 5. AKS and Strimzi high-availability design

Use distinct zone-capable node pools where available, node affinity and topology spread policies compatible with the installed Strimzi KafkaNodePool CRD, and rack awareness mapped to `topology.kubernetes.io/zone`. Validate supported Strimzi scheduling configuration against the actual CRD before applying. Broker placement and controller placement must both be verified after scheduling; a manifest expressing preferences is not evidence of actual separation.

Suggested **starting point for evaluation**, not universal policy:
- At least 3 brokers across 3 zones when supported.
- Three or five KRaft controllers with quorum-safe maintenance.
- Topic replication factor 3, `min.insync.replicas=2`, producers using `acks=all`.
- Zone-aware PVC provisioning and recovery capacity on surviving nodes.
- Controlled rolling changes, PDBs and observability for ISR, quorum and latency.

Avoid relying on PDBs alone for availability: PDBs constrain voluntary evictions, not infrastructure failure.

## 6. Topic policy example

Use only after confirming at least three suitable brokers and the Strimzi topic operator configuration:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: ha-orders-v1
  namespace: kafka
  labels:
    strimzi.io/cluster: lab-kafka
spec:
  topicName: ha.orders.v1
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

Save as `ha-orders-topic.yaml` and run:

```powershell
kubectl apply --dry-run=server -f ha-orders-topic.yaml
kubectl get kafkatopic -n kafka
```

Applying is an approved lab-only operation. Confirm replica placement, not just configured replication factor.

## 7. Backup architecture and restore sequencing

**Backup scopes:**
1. GitOps/IaC: AKS, node pools, storage classes, network policy, Strimzi version and Kafka/KafkaNodePool/KafkaTopic/KafkaUser CRs.
2. Security: encrypted Key Vault/Secret references, TLS issuer configuration, recovery credentials and RBAC.
3. Data: approved cross-region Kafka replication or application source replay; optional validated broker-consistent snapshots with explicit vendor/version support.
4. Consumer state: group offsets, sink checkpoints, deduplication store and schema registry artifacts.

**Recovery order:** establish clean infrastructure → restore identity/network/storage prerequisites → deploy compatible Strimzi/operator version → provision healthy KRaft cluster → restore topic definitions and policies → restore/replay data using a validated strategy → restore or translate consumer checkpoints → reconcile event IDs and downstream effects → authorize traffic cutover.

Do not restore arbitrary live broker disk snapshots into a new cluster or copy KRaft metadata directories between clusters without a validated, version-specific recovery procedure. A KafkaTopic YAML export alone cannot restore topic messages.

## 8. Cross-region DR and failover fencing

Use a supported cross-cluster replication mechanism (for example a validated MirrorMaker 2 topology) with independently monitored replication lag. Map topic names, consumer groups, schema IDs and offset translation explicitly. Avoid dual-active writers to the same logical data stream unless a conflict-resolution design exists.

Before promoting a secondary, **fence the old primary writers**, capture replication checkpoint and last known accepted event IDs, update client routing through an approved change, verify data consistency, and only then resume consumers. After recovery, treat failback as a separate migration with new reconciliation gates.

## 9. Azure Event Hubs HA and DR distinctions

Event Hubs is a managed service with tier- and region-dependent availability and disaster-recovery capabilities. A namespace alias/metadata recovery mechanism may not replicate event payloads. Features that do replicate event data must be evaluated separately for supported tier, regions, consistency, failover semantics, retention, offsets and cost. Do not claim an RPO of zero based solely on a geo-DR alias. Check current Microsoft documentation and exercise a non-production failover path before approving production.

## 10. Kubernetes-first labs (20)

Each lab needs an owner, prerequisites, read-only baseline, approved mutation, expected signals, actual results, rollback, event-ID reconciliation and timestamped PASS/FAIL evidence.

| # | Lab | Acceptance evidence |
|---|---|---|
| 01 | Inspect AKS node zones and node pools | Topology, command/metrics output, RPO/RTO observation, rollback |
| 02 | Verify Strimzi KafkaNodePool placement | Topology, command/metrics output, RPO/RTO observation, rollback |
| 03 | Audit broker rack awareness | Topology, command/metrics output, RPO/RTO observation, rollback |
| 04 | Check broker replication factor and ISR | Topology, command/metrics output, RPO/RTO observation, rollback |
| 05 | Inspect KRaft controller quorum | Topology, command/metrics output, RPO/RTO observation, rollback |
| 06 | Validate PodDisruptionBudget and drain plan | Topology, command/metrics output, RPO/RTO observation, rollback |
| 07 | Verify zone-aware PVC binding | Topology, command/metrics output, RPO/RTO observation, rollback |
| 08 | Audit StorageClass reclaim and expansion | Topology, command/metrics output, RPO/RTO observation, rollback |
| 09 | Capture KafkaTopic configuration backups | Topology, command/metrics output, RPO/RTO observation, rollback |
| 10 | Capture Strimzi CR and Secret references | Topology, command/metrics output, RPO/RTO observation, rollback |
| 11 | Create application-consistent recovery manifest | Topology, command/metrics output, RPO/RTO observation, rollback |
| 12 | Validate Kafka data replication strategy | Topology, command/metrics output, RPO/RTO observation, rollback |
| 13 | Test bounded broker pod failure | Topology, command/metrics output, RPO/RTO observation, rollback |
| 14 | Test controller pod restart | Topology, command/metrics output, RPO/RTO observation, rollback |
| 15 | Simulate a single-zone outage in isolated lab | Topology, command/metrics output, RPO/RTO observation, rollback |
| 16 | Measure producer and consumer failover | Topology, command/metrics output, RPO/RTO observation, rollback |
| 17 | Validate event ID and offset reconciliation | Topology, command/metrics output, RPO/RTO observation, rollback |
| 18 | Evaluate Event Hubs DR and alias capabilities | Topology, command/metrics output, RPO/RTO observation, rollback |
| 19 | Conduct controlled cross-region restore drill | Topology, command/metrics output, RPO/RTO observation, rollback |
| 20 | Record RPO/RTO and rollback evidence | Topology, command/metrics output, RPO/RTO observation, rollback |

### Standard drill procedure

1. Establish baseline health: broker placement, ISR, quorum, client p99 and consumer lag.
2. Generate bounded synthetic events with immutable `event_id` and aggregate key.
3. Record last acknowledged producer event and consumer/sink checkpoint.
4. Inject one fault only in an isolated lab; capture alert and impact times.
5. Recover through documented operator/Kubernetes controls.
6. Compare accepted IDs against recovered log and sink IDs; identify missing, duplicate and reordered records.
7. Calculate observed RPO/RTO, clean up chapter-owned resources, and document lessons.

## 11. Failure scenarios (12)

| # | Failure | Detection and recovery |
|---|---|---|
| 1 | Single broker crash | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 2 | KRaft controller leader failure | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 3 | Loss of quorum | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 4 | Availability-zone loss | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 5 | PVC unavailability | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 6 | Disk corruption | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 7 | ISR below min.insync.replicas | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 8 | Consumer offset divergence | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 9 | Cross-region replication lag | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 10 | Expired backup or missing key | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 11 | Event Hubs geo-failover misconfiguration | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |
| 12 | Split-brain during regional cutover | Identify affected failure domain; preserve evidence; fence unsafe writers; recover via approved runbook; reconcile event IDs |

Never perform destructive cluster or region tests without an approved, isolated lab and rollback.

## 12. Production SRE runbooks (8)

| # | Runbook | Required workflow |
|---|---|---|
| 1 | Broker failure and ISR recovery | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 2 | KRaft quorum degradation | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 3 | AKS zone outage | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 4 | PVC/disk recovery | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 5 | Backup restore verification | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 6 | Cross-region Kafka failover | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 7 | Event Hubs geo-DR invocation | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |
| 8 | Failback and data reconciliation | Assess blast radius → validate telemetry → declare owner → contain/fence → recover → reconcile → document RCA |

Every runbook includes escalation, commands to gather evidence, authorization boundaries, RPO/RTO target, go/no-go, rollback and recovery sign-off.

## 13. Monitoring, security and FinOps

Monitor offline/under-replicated partitions, ISR shrink/expand, KRaft controller health, PVC pressure, node zone distribution, cross-region replication lag, backup age, recovery test age, client retry/latency and event reconciliation mismatches. Protect backup encryption keys and restrict cross-region identity/network access. Price secondary infrastructure, egress, storage, monitoring, test runs and operational overhead; a DR plan without cost ownership is incomplete.

## 14. 100-point acceptance assessment

| Gate | Points |
|---|---:|
| Zone-aware AKS and broker/controller placement | 15 |
| ISR, replication and durability policy | 15 |
| KRaft quorum and maintenance safety | 10 |
| Backup completeness and restore validation | 15 |
| Cross-region replication and fencing | 15 |
| Event Hubs HA/DR compatibility assessment | 10 |
| RPO/RTO and event reconciliation | 10 |
| Security, runbooks, rollback and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 plus mandatory successful isolated restore, no unexplained missing accepted IDs, demonstrated fencing, approved RPO/RTO and independent review. A written chapter is not a completed DR certification.

## 15. Evidence manifest

```yaml
chapter: 108
environment: isolated-aks-lab
aks_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
availability_zones: []
replication_strategy: REPLACE
backup_method: REPLACE
restore_test_utc: null
rpo_target_seconds: null
rpo_observed_seconds: null
rto_target_seconds: null
rto_observed_seconds: null
accepted_event_ids: null
missing_event_ids: null
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 109 — Azure Kafka Incident Response, Security and Upgrade Operations.**
