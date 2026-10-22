# Chapter 111 — Google Cloud Kafka Architecture: GKE + Strimzi vs Managed Service for Apache Kafka

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (1/10)  
**Primary execution platform:** Google Kubernetes Engine (GKE), Strimzi-managed Apache Kafka KRaft  
**Managed-service alternative:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 001–070 and 101–110; Kubernetes administration, Kafka client semantics, cloud networking  
**Publication:** Published on commit · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use a disposable GCP project or isolated lab with billing alerts, least-privilege IAM and explicit cleanup ownership. Do not deploy chargeable GKE or managed Kafka resources without approval. Validate exact region, feature availability, quotas, Kafka/Strimzi versions and service APIs against current Google documentation. Managed Kafka is not assumed to expose every self-managed broker setting or operational capability.

## 1. Mission and learning outcomes

Select a Kafka architecture on Google Cloud using measurable workload and operational requirements. Compare self-managed Kafka on GKE with Strimzi KRaft against Google Cloud Managed Service for Apache Kafka. Identify differences in cluster lifecycle, storage, IAM, networking, security, observability, failure domains, DR, operational control and cost.

**Deliverables:** architecture decision record (ADR), responsibilities matrix, GKE/KRaft reference design, managed-service fit assessment, security and network diagrams, SLO/capacity assumptions, migration gates, 20 lab exercises, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Architecture alternatives

```text
                        GCP VPC / private networking
        ┌─────────────────────────┴────────────────────────┐
        │                                                  │
  Option A: GKE + Strimzi                           Option B: Managed Kafka
  ┌────────────────────────────┐                    ┌────────────────────────┐
  │ GKE node pools across zones│                    │ Google-managed Kafka   │
  │ Strimzi Operator           │                    │ broker infrastructure  │
  │ Kafka KRaft controllers    │                    │ managed lifecycle      │
  │ Kafka brokers + PVCs       │                    │ service APIs + IAM     │
  │ KafkaTopic/KafkaUser CRs   │                    │ client connectivity    │
  │ Kubernetes clients         │                    │ GKE-hosted clients     │
  └─────────────┬──────────────┘                    └────────────┬───────────┘
                │                                              │
         Prometheus / Grafana                          Cloud Monitoring
                └──────────────────┬───────────────────────────┘
                          event-ID reconciliation
                         SLO, cost, and DR gates
```

**Architecture principle:** Both options can support Kafka client workloads, but control-plane and security boundaries differ. For managed Kafka, validate supported Kafka APIs, authentication methods, topic administration, client versions, connector support and configuration limits before migration approval.

## 3. Decision matrix

| Dimension | GKE + Strimzi KRaft | Managed Service for Apache Kafka |
|---|---|---|
| Broker lifecycle | Team operates brokers and operator | Provider-managed infrastructure |
| KRaft controllers | Team manages quorum and upgrades | Managed implementation; no customer quorum operations assumed |
| Kubernetes | Kafka and clients on GKE | Clients may run on GKE; brokers managed |
| Storage | Team chooses PVCs, disk classes, headroom | Service-specific capacity controls |
| Network | Kubernetes Services/listeners, VPC, TLS | Provider endpoints, VPC and supported connectivity |
| Security | Kubernetes RBAC, Kafka ACL/auth, workload identity | Provider IAM/auth controls plus client security |
| Observability | Broker JMX, exporters, Prometheus, GKE metrics | Supported Cloud Monitoring/service metrics and client metrics |
| Availability | Team designs zone placement and recovery | Managed availability features; validate region/tier |
| DR | Team engineers replication, backups and failover | Validate service-supported backup/replication and DR |
| FinOps | GKE compute, disk, network, monitoring, on-call | Service charges, network, monitoring, client compute |

Do not equate lower infrastructure administration with zero customer operational responsibility. Client correctness, schema governance, consumer lag, data contracts, credentials and incident ownership remain essential.

## 4. GKE + Strimzi KRaft baseline

Design separate or appropriately isolated KafkaNodePools for broker and controller roles, subject to supported Strimzi releases. Prefer zone-aware scheduling, adequate failure headroom, persistent volumes, encryption, least-privilege network paths and operator-managed rolling operations.

**Read-only preflight:**

```powershell
gcloud config get-value project
gcloud auth list
gcloud container clusters list
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic -A
kubectl get storageclass
kubectl get pvc -A
kubectl get pods -A
```

The Strimzi resource queries require installed CRDs. Validate actual cluster context before use. If no cluster is configured, do not infer deployment failure from missing resources.

## 5. Topic durability policy

Example **lab-only** KafkaTopic; apply only after confirming Strimzi Topic Operator and at least three brokers:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: gke-orders-v1
  namespace: kafka
  labels:
    strimzi.io/cluster: lab-kafka
spec:
  topicName: gke.orders.v1
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

```powershell
kubectl apply --dry-run=server -f gke-orders-topic.yaml
kubectl get kafkatopic -n kafka
```

Do not change production partitions or replication policy without owner review. Keyed ordering, ISR safety and available broker count must be verified.

## 6. GCP identity and networking

Document GKE Workload Identity Federation, Kubernetes service accounts, IAM roles, Kafka client authentication, TLS trust and private networking separately. GCP IAM does not automatically replace Kafka ACLs in self-managed Strimzi clusters. For managed Kafka, verify supported IAM-to-Kafka authorization mapping and supported SASL/TLS mechanisms from current documentation.

Validate VPC routes, private endpoint connectivity, DNS, firewall policies, authorized networks, certificate chains and client bootstrap metadata resolution. Kafka clients must reach advertised broker addresses, not merely the bootstrap endpoint.

## 7. Managed-service fit and migration assessment

Before approving migration, capture:
- Kafka client versions, authentication and authorization.
- Topic count, partitions, replication/durability assumptions and retention.
- Admin API usage, custom broker settings, compaction, transactions, Kafka Streams and Connect dependencies.
- Throughput, latency, quotas, regional availability and network paths.
- Consumer offsets, schema registry, DLQ, replay, backup and DR.
- Operational monitoring, billing, security and rollback.

Classify every dependency as **verified supported**, **verified unsupported**, or **unknown**. Unknown is not migration-approved. Build a synthetic dual-pipeline test with stable event IDs and independent checkpoints; do not assume source and target offsets are interchangeable.

## 8. Capacity and cost engineering

Use measured events/sec, encoded event sizes, partition skew, consumer fanout, retention, replica factor, network egress, storage IOPS and failure headroom. For self-managed Kafka estimate GKE nodes, persistent disks, snapshots, network, Cloud Monitoring and operations. For managed Kafka use actual region-specific service pricing, capacity units, network, client compute and monitoring. Include recovery testing and operational overhead. Never invent a current SKU price or assume regional availability.

## 9. Observability and SLOs

Instrument producer acknowledged-event rate, error rate, retries, p99 latency, consumer lag, processing latency, DLQ and event-ID reconciliation. On GKE/Strimzi monitor KRaft quorum, broker ISR, PVCs, disk latency, CPU, GC, node zones and operator health. On managed Kafka monitor only supported service-exposed metrics plus client-side signals. Define request-based availability, correctness, latency and recovery SLOs independently.

**Illustrative lab goals, not measured results:** producer success ≥99.9%, zero unexplained missing accepted IDs, p99 end-to-end latency <5 s at a stated synthetic load, and bounded single-broker recovery.

## 10. Kubernetes-first labs (20)

For each lab record prerequisites, expected output, actual output, version, timestamp, PASS/FAIL, rollback and cleanup. No live execution is claimed by publication.

| # | Lab | Evidence |
|---|---|---|
| 01 | Confirm GCP project, billing and cluster context | Sanitized command/metric output, result, rollback |
| 02 | Inspect GKE regional/zonal node placement | Sanitized command/metric output, result, rollback |
| 03 | Inventory Kubernetes StorageClasses and PVCs | Sanitized command/metric output, result, rollback |
| 04 | Inspect Strimzi CRD and operator version | Sanitized command/metric output, result, rollback |
| 05 | Inspect Kafka and KafkaNodePool KRaft roles | Sanitized command/metric output, result, rollback |
| 06 | Verify broker and controller failure domains | Sanitized command/metric output, result, rollback |
| 07 | Review Kafka listener TLS and authentication | Sanitized command/metric output, result, rollback |
| 08 | Audit Kubernetes service accounts and IAM | Sanitized command/metric output, result, rollback |
| 09 | Map private networking and DNS paths | Sanitized command/metric output, result, rollback |
| 10 | Inventory KafkaTopic and KafkaUser CRs | Sanitized command/metric output, result, rollback |
| 11 | Baseline producer and consumer metrics | Sanitized command/metric output, result, rollback |
| 12 | Inspect Prometheus scrape and alerts | Sanitized command/metric output, result, rollback |
| 13 | Discover managed Kafka regional availability | Sanitized command/metric output, result, rollback |
| 14 | Review managed Kafka cluster provisioning APIs | Sanitized command/metric output, result, rollback |
| 15 | Compare authentication and authorization models | Sanitized command/metric output, result, rollback |
| 16 | Assess topic and client API compatibility | Sanitized command/metric output, result, rollback |
| 17 | Estimate broker/partition/storage capacity | Sanitized command/metric output, result, rollback |
| 18 | Compare HA and recovery responsibilities | Sanitized command/metric output, result, rollback |
| 19 | Build workload-specific TCO decision matrix | Sanitized command/metric output, result, rollback |
| 20 | Perform architecture acceptance and rollback review | Sanitized command/metric output, result, rollback |

### Lab execution procedure

1. Confirm GCP project, billing budget, GKE context, namespace and RBAC.
2. Capture architecture baseline and source topic/client inventory.
3. Validate Strimzi/GKE topology, identity and storage assumptions.
4. Run bounded synthetic producer/consumer workload with stable event IDs.
5. Compare managed-service compatibility using documented API/tier support and approved test resources.
6. Measure latency, lag, correctness and cost; record gaps.
7. Clean up chapter-owned resources only, preserving evidence and the architecture decision.

## 11. Failure scenarios (12)

| # | Scenario | Investigation and recovery objective |
|---|---|---|
| 1 | GKE node/pod scheduling failure | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 2 | KRaft controller quorum loss | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 3 | Broker ISR degradation | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 4 | PVC zone binding mismatch | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 5 | DNS/private connectivity outage | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 6 | Client TLS authentication failure | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 7 | IAM authorization denial | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 8 | Producer timeout under load | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 9 | Consumer lag and rebalances | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 10 | Storage throughput saturation | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 11 | Managed service quota or API mismatch | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |
| 12 | Cross-region recovery assumption failure | Correlate GKE, Kafka/client and Google Cloud signals; contain in lab; recover; reconcile accepted IDs |

Each scenario needs a trigger, blast radius, expected alert, actual evidence, mitigation, rollback, RPO/RTO implications and prevention.

## 12. SRE runbooks (8)

| # | Runbook | Standard workflow |
|---|---|---|
| 1 | GKE Kafka availability triage | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 2 | KRaft quorum incident | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 3 | Broker storage/ISR incident | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 4 | Client connectivity and identity | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 5 | Managed Kafka service incident | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 6 | Capacity and throttling | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 7 | Migration cutover/rollback | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |
| 8 | Architecture review and acceptance | Identify owner → assess user impact → collect read-only evidence → approve remediation → recover → reconcile → document RCA |

Runbooks require severity, escalation, monitoring queries, safe command boundaries, recovery criteria, stakeholder communications and audit evidence.

## 13. Security, compliance and FinOps gates

Use least-privilege IAM, Kubernetes RBAC, workload identity, TLS and Kafka-level authorization where applicable. Protect credentials in Secret Manager or approved secret tooling, avoid storing PII in logs/metrics and document encryption, retention and audit controls. Set GCP budgets and alerts before provisioning. Do not treat cost optimization as justification for unsafe replication or recovery headroom.

## 14. 100-point architecture acceptance

| Gate | Points |
|---|---:|
| GKE/Strimzi KRaft architecture | 15 |
| Managed Kafka feature/operational comparison | 15 |
| Identity, TLS, IAM and networking | 15 |
| Topic, partition, storage and capacity | 10 |
| Producer/consumer compatibility | 10 |
| Observability and SLO design | 10 |
| HA, backup and DR boundaries | 10 |
| FinOps, migration, rollback and evidence | 15 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 with no unreviewed high-risk compatibility gaps, no critical security findings, a costed recovery plan and independent technical/security sign-off. Written architecture review is not runtime certification.

## 15. Evidence manifest

```yaml
chapter: 111
environment: isolated-gke-lab
gcp_project: REDACTED
region: REPLACE
gke_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
managed_kafka_tier_or_cluster: NOT_PROVISIONED
client_compatibility_matrix: []
lab_results: []
architecture_decision: pending
cost_assessment: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 112 — Provision GKE, Networking, Storage and Strimzi KRaft.**
