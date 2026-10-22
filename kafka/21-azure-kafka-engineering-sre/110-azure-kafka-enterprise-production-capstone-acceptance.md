# Chapter 110 — Azure Kafka Enterprise Production Capstone and Acceptance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (10/10)  
**Primary platform:** Azure AKS + Strimzi-managed Apache Kafka KRaft  
**Managed alternative:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–109; isolated Azure subscription, approved test budget, observability and DR plans  
**Publication:** Published after GitHub commit · **Live lab execution:** Pending · **Independent technical/security review:** Pending · **Runtime certification:** Not claimed

> **Safety:** This is a production-readiness *simulation* in a disposable lab, not authorization to modify a live Kafka environment. No destructive production tests, unreviewed upgrades, real patient data or unapproved regional failovers. Use synthetic event IDs, least-privilege access, encrypted secrets and a documented stop/rollback decision for each experiment.

## 1. Capstone mission

Build, operate, observe, secure, benchmark and recover a Kubernetes-first Kafka platform on AKS. Prove the platform can meet a declared synthetic workload's delivery, latency, recovery and cost objectives. Evaluate whether Azure Event Hubs can satisfy the same application contract without assuming full Kafka feature compatibility.

**Capstone deliverables:** architecture decision record; version-pinned IaC/GitOps inventory; Kafka/KRaft health evidence; security and topic policies; producer/consumer synthetic pipeline; dashboards and alerts; load and capacity report; HA/DR test; incident timeline; RPO/RTO evidence; cost model; rollback plan; independent review sign-off.

## 2. End-to-end reference architecture

```text
                      Azure region / AKS
  ┌───────────────────────────────────────────────────────┐
  │ Synthetic producer Deployment (stable event_id/key)  │
  │                    | TLS/SASL                         │
  │  Strimzi Kafka KRaft, broker + controller node pools │
  │   Zone A         Zone B           Zone C              │
  │   broker/vol     broker/vol       broker/vol           │
  │   controller     controller       controller           │
  │                    |                                  │
  │ Consumer Deployment → idempotent sink + DLQ           │
  │                    |                                  │
  │ Prometheus/Grafana + Azure Monitor + SLO alerts       │
  └────────────────────┬──────────────────────────────────┘
                       |
             Cross-region DR design
           replication + checkpoints
                       |
             secondary recovery site

  Candidate alternative: Azure Event Hubs Kafka endpoint
  independently validate client APIs, limits, offsets,
  authentication, event retention and recovery behavior
```

**Control-plane boundary:** Strimzi/AKS operators manage broker and KRaft lifecycle. Event Hubs is Azure-managed; do not transpose broker administration, Kafka log compaction, transactions or recovery semantics without explicit feature testing.

## 3. Capstone acceptance contract

Before execution, record:
- **Workload:** events/s, encoded size distribution, key skew, partitions, replication factor, producer acks, consumer fanout, retention and growth.
- **Delivery:** accepted event IDs, unique sink effects, duplicates, missing IDs, ordering per key and DLQ records.
- **Reliability:** service SLO, producer error budget, p99 end-to-end latency, maximum acceptable lag, RPO/RTO and recovery headroom.
- **Security:** identity model, Kafka ACLs, TLS, Kubernetes RBAC, Key Vault/Secret references, NetworkPolicy and audit retention.
- **Cost:** region, VM/disk SKUs, disk IOPS/MBps, Event Hubs tier assumptions, network egress, monitoring, DR and operational costs.

Illustrative *lab-only* goals: producer success ≥99.9%, p99 pipeline latency <5 s under declared load, zero unexplained missing accepted IDs, 10-minute controlled single-broker recovery, and no critical security findings. Do not present these as measured or universal production SLOs.

## 4. Kubernetes-first environment inventory

```powershell
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka -o wide
kubectl get pdb -A
kubectl get storageclass
kubectl get events -n kafka --sort-by=.lastTimestamp
az account show --query '{subscription:id,tenant:tenantId}' -o json
```

Validate actual namespaces, RBAC, operator release, CRD schema, AKS context and Azure subscription. Treat read-only inventory as evidence, not proof of availability.

## 5. Deployment and GitOps gates

1. Pin compatible Strimzi, Kafka and client versions and immutable application image digests.
2. Review AKS node pool zones, topology spread, KafkaNodePool role placement and storage class binding.
3. Provision approved KafkaTopic and KafkaUser resources via GitOps with peer-reviewed PRs.
4. Apply least-privilege NetworkPolicies, TLS and identity; keep secret material outside Git.
5. Deploy synthetic producer and consumer as Kubernetes workloads with probes, resource requests/limits, graceful termination and disruption controls.
6. Confirm topic replication/ISR, KRaft quorum, client connection and event ID reconciliation before benchmarking.
7. Maintain explicit revert commits, recovery points and rollback authority.

**Suggested durability starting point:** 3 zone-separated brokers, replication factor 3, min.insync.replicas 2, producer acks=all and idempotence enabled, subject to actual cluster capacity and failure domain support. PDBs alone do not guarantee resilience.

## 6. Correctness test protocol

Generate bounded synthetic events containing `event_id`, `aggregate_id`, `schema_version`, `event_time` and a deterministic payload hash. Producer records acknowledged IDs; consumer writes to an idempotent durable sink and commits offsets only after successful sink effects or durable DLQ quarantine.

Compare sets of accepted IDs and sink IDs; calculate missing IDs, duplicates, hash mismatches and per-key ordering violations. A simple record-count match is insufficient. For Event Hubs migration tests, maintain independent checkpoints and do not equate Kafka offsets across source and target.

## 7. Performance and capacity acceptance

Benchmark producer batching, compression and acknowledgements; consumer fetch/concurrency; partition distribution; broker CPU/heap/GC; Azure disk latency/IOPS/MBps; network saturation; and recovery under reduced capacity. Use measured event size and actual SKU ceilings. Track p50/p95/p99 latency, throughput, retries, lag and event correctness at steady and peak loads. Record test duration, repetitions and warm-up. Stop on declared SLO breach or data-integrity failure.

## 8. Observability and security acceptance

Require Prometheus scrape health, Kafka broker/ISR and KRaft metrics, producer and consumer instrumentation, consumer lag, AKS pod/PVC metrics, Azure Monitor coverage, actionable alerts and documented escalation. Test at least one alert end-to-end. Review KafkaUser ACLs, TLS chain and expiration, RBAC, secret rotation procedure, network segmentation and redaction. Keep regulated or personal data out of logs and labels.

## 9. HA, DR and upgrade acceptance

Verify controller quorum, broker replica placement, surviving-zone capacity, ISR recovery and client continuity during an isolated single-broker fault. Validate backups of IaC, Kafka/Strimzi CRs, security references, schema artifacts and the chosen event-data protection mechanism. Perform an isolated restore/replay and measure observed RPO/RTO. For regional cutover, fence old writers, verify replication checkpoint, and reconcile data before allowing traffic.

Review Strimzi/Kafka upgrade compatibility and irreversible KRaft metadata/feature transitions. An upgrade plan without an independently validated recovery strategy is **not** an accepted rollback.

## 10. Hands-on capstone labs (20)

Every lab requires prerequisites, owner, exact version, commands, expected result, observed result, sanitized evidence, rollback and PASS/FAIL.

| # | Lab | Evidence gate |
|---|---|---|
| 01 | Confirm lab scope, ownership and cost cap | Timestamped commands/metrics, event reconciliation, rollback result |
| 02 | Inventory AKS zones and node pools | Timestamped commands/metrics, event reconciliation, rollback result |
| 03 | Validate Strimzi and Kafka versions | Timestamped commands/metrics, event reconciliation, rollback result |
| 04 | Verify KRaft controller quorum | Timestamped commands/metrics, event reconciliation, rollback result |
| 05 | Audit KafkaNodePool rack-aware placement | Timestamped commands/metrics, event reconciliation, rollback result |
| 06 | Check storage, PVCs and disk limits | Timestamped commands/metrics, event reconciliation, rollback result |
| 07 | Verify KafkaTopic durability policy | Timestamped commands/metrics, event reconciliation, rollback result |
| 08 | Validate KafkaUser ACL and TLS | Timestamped commands/metrics, event reconciliation, rollback result |
| 09 | Deploy synthetic producer | Timestamped commands/metrics, event reconciliation, rollback result |
| 10 | Deploy idempotent sink consumer | Timestamped commands/metrics, event reconciliation, rollback result |
| 11 | Verify schema and DLQ | Timestamped commands/metrics, event reconciliation, rollback result |
| 12 | Baseline throughput and p99 latency | Timestamped commands/metrics, event reconciliation, rollback result |
| 13 | Measure consumer lag and SLOs | Timestamped commands/metrics, event reconciliation, rollback result |
| 14 | Validate Prometheus/Grafana alerts | Timestamped commands/metrics, event reconciliation, rollback result |
| 15 | Compare Event Hubs client compatibility | Timestamped commands/metrics, event reconciliation, rollback result |
| 16 | Test controlled broker failure | Timestamped commands/metrics, event reconciliation, rollback result |
| 17 | Test controlled node/zone impairment | Timestamped commands/metrics, event reconciliation, rollback result |
| 18 | Execute approved restore or DR drill | Timestamped commands/metrics, event reconciliation, rollback result |
| 19 | Perform credential/upgrade readiness review | Timestamped commands/metrics, event reconciliation, rollback result |
| 20 | Reconcile IDs and complete go/no-go | Timestamped commands/metrics, event reconciliation, rollback result |

### Standard drill workflow

1. Capture baseline health and last acknowledged synthetic event ID.
2. Declare test scope, stop conditions and rollback authority.
3. Perform one bounded, approved lab action.
4. Capture detection, SLO impact, mitigation and recovery timeline.
5. Reconcile accepted IDs, sink effects, DLQ and consumer offsets.
6. Record RPO/RTO where applicable; clean up only chapter-owned resources.
7. Mark PASS only when actual execution evidence exists.

## 11. Failure scenarios (12)

| # | Failure | Required verification |
|---|---|---|
| 1 | Broker crash | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 2 | Controller quorum degradation | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 3 | Zone/node outage | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 4 | PVC disk saturation | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 5 | Producer timeout | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 6 | Consumer lag and retention risk | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 7 | Poison record/DLQ surge | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 8 | TLS expiry or credential failure | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 9 | NetworkPolicy/DNS disruption | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 10 | Event Hubs quota throttling | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 11 | Cross-region replication lag | Alert → incident classification → safe containment → recovery → event-ID reconciliation |
| 12 | Rollback/restore failure | Alert → incident classification → safe containment → recovery → event-ID reconciliation |

For each scenario record blast radius, expected versus actual signals, root-cause hypothesis, mitigation, rollback and preventive follow-up. Never run destructive failure injection on shared or production systems.

## 12. Production SRE runbooks (8)

| # | Runbook | Required workflow |
|---|---|---|
| 1 | Sev-1 incident command | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 2 | Broker/ISR recovery | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 3 | KRaft controller quorum | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 4 | Storage saturation | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 5 | Consumer lag/data integrity | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 6 | Security credential rotation | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 7 | Regional failover and fencing | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |
| 8 | Capstone rollback and acceptance | Owner and severity → read-only triage → approved remediation → rollback gates → recovery validation → RCA |

Runbooks include escalation, on-call ownership, commands, decision points, customer impact, change record, RPO/RTO implications and evidence retention.

## 13. Azure Event Hubs migration decision

Approve a migration only if exact client versions, supported Kafka APIs, partition/key ordering, consumer-group behavior, retention/replay, authentication, throughput/quotas, security, cost, recovery and operational ownership pass independent testing. Treat compaction, Kafka Streams state stores, transactions, Connect internals and broker administration as **high-risk until proven supported**. A namespace disaster-recovery alias alone must not be described as event-data replication.

## 14. 100-point enterprise acceptance

| Gate | Points |
|---|---:|
| AKS/Strimzi KRaft architecture and GitOps | 15 |
| Producer/consumer correctness and topics | 15 |
| Security, identity, TLS and ACLs | 10 |
| Observability, alerts and SLOs | 10 |
| Performance, disk and capacity | 10 |
| HA, quorum and AZ resilience | 10 |
| Backup, DR, RPO/RTO and rollback | 15 |
| Event Hubs compatibility and FinOps | 5 |
| Incident runbooks, evidence and independent review | 10 |
| **Total** | **100** |

**Suggested pass threshold:** ≥85/100, with mandatory no unexplained accepted-event loss, validated recovery, no critical security findings, approved migration decision and independent technical/security review. Failure of a mandatory gate overrides numeric score.

## 15. Evidence and sign-off

```yaml
chapter: 110
environment: isolated-aks-capstone
azure_subscription: REDACTED
aks_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
git_commit: REPLACE
test_window_utc: null
lab_results: []
producer_accepted_ids: null
sink_unique_ids: null
missing_ids: null
duplicate_effects: null
p99_latency_ms: null
consumer_lag_max: null
rpo_target_seconds: null
rpo_observed_seconds: null
rto_target_seconds: null
rto_observed_seconds: null
security_review: pending
technical_review: pending
operations_signoff: pending
runtime_certified: false
```

**Publication status is not execution or certification.** Complete this evidence record only after independent test runs.

## 16. Part 21 completion and next track

With Chapters 101–110 published, **Part 21 — Microsoft Azure Kafka Engineering & SRE** is content-complete (10/10). Live labs, technical review and security acceptance remain outstanding.

**Next:** Chapter 111 — Google Cloud Kafka Architecture: GKE + Strimzi vs Managed Service for Apache Kafka, beginning Part 22.
