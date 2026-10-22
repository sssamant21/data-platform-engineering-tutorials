# Chapter 107 — Azure Kafka Performance, Capacity, Disk and FinOps

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (7/10)  
**Primary platform:** AKS + Strimzi-managed Apache Kafka KRaft  
**Comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–106; isolated Azure subscription/AKS lab, Prometheus/Grafana  
**Publication:** Published after commit · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Benchmark only an isolated approved cluster with spending caps and workload limits. Verify Azure disk/VM SKU performance, burst rules, Event Hubs tier limits and Strimzi CRD version against current documentation before making claims. Never change production PVCs, broker placement, partition counts or quotas without approved rollback. Performance results in this chapter are illustrative hypotheses, not measured evidence.

## 1. Mission and learning outcomes

Establish a reproducible baseline and size Kafka on AKS for peak traffic, retention, broker failure and recovery, with explicit Azure infrastructure costs. Distinguish Kafka-on-AKS broker/storage limits from Event Hubs namespace/tier limits. Identify the first bottleneck using latency, queueing, throughput, utilization and backpressure evidence rather than CPU alone.

**Deliverables:** workload model, resource inventory, benchmark protocol, capacity spreadsheet assumptions, bottleneck diagnosis, cost comparison, 20 labs, 12 failure scenarios, 8 runbooks and acceptance score.

## 2. Reference architecture

```text
 AKS client Deployments
   producers: batching, acks, compression, retries
   consumers: fetch, processing, offset commits
                   |
                   v
   Strimzi Kafka KRaft / AKS broker node pools
   ├─ partition leaders / followers / replication
   ├─ CPU, heap, page cache, network and NIC limits
   ├─ Azure managed-disk PVCs: IOPS / MBps / latency
   └─ Prometheus, Grafana, Azure Monitor
                   |
             cost and SLO model

 Alternative: Event Hubs Kafka endpoint
   namespace tier/capacity units, ingress/egress quotas,
   partition count, retention, throttling, Azure Monitor
```

**Rule:** Event Hubs is not an interchangeable Kafka broker. Do not infer broker disk sizing, Kafka partition reassignment, ISR or KRaft metrics for Event Hubs.

## 3. Workload and capacity model

Record peak and steady events/s, mean/p95/p99 encoded record size, key distribution, replication factor (RF), partitions, retention, consumer fanout, compression, producer acks, retry rates, schema overhead, RPO/RTO, availability zones and expected growth.

A first-order model, **not a disk procurement quote**:

```text
ingress_bytes_per_sec = events_per_sec × average_encoded_bytes
logical_retained_bytes = ingress_bytes_per_sec × retention_seconds
physical_log_bytes ≈ logical_retained_bytes × replication_factor
capacity_with_headroom ≈ physical_log_bytes / target_disk_utilization
network_replication ≈ ingress_bytes_per_sec × (replication_factor - 1)
```

Adjust for actual compression, segment overhead, compaction, indexing, tiered storage, reassignments, recovery traffic, producer/consumer fanout and uneven placement. Disk **IOPS** and **throughput** must both satisfy peak workloads; capacity in GiB alone is not sufficient.

**Example only:** 20,000 events/s × 2 KiB = ~39.1 MiB/s logical ingress; one-day retention ≈3.30 TiB logical data (binary units); RF=3 ≈9.89 TiB before headroom/overhead. At 70% target disk utilization this is ≈14.1 TiB across broker volumes. Verify all calculations against measured encoded sizes and observed disk consumption.

## 4. AKS/Kafka read-only discovery

```powershell
kubectl config current-context
kubectl get kafka -A
kubectl get nodes -o wide
kubectl top nodes
kubectl top pods -n kafka
kubectl get pvc -n kafka -o wide
kubectl get storageclass
kubectl get pods -n kafka -o wide
kubectl get kafkatopic -n kafka
az account show --query '{subscription:id,tenant:tenantId}' -o json
```

Inspect Strimzi KafkaNodePool and Kafka CRs and correlate broker PVCs with Azure disks and VM sizes. Validate `kubectl top` availability (metrics-server required). For Azure disk IOPS and throughput, consult the actual disk SKU and performance configuration; do not treat observed cloud throttling as a Kafka broker setting.

## 5. Benchmark protocol

1. Establish a healthy cluster baseline with no active recovery or reassignment.
2. Capture image digests, Kafka/Strimzi/client versions, node SKU, disk SKU, partitions, RF, acks, batch settings and monitoring dashboards.
3. Generate synthetic records with a documented key distribution and size histogram. No real patient/financial records.
4. Warm up; then run bounded steady and burst phases, measuring client p50/p95/p99, throughput, retries, consumer lag, broker saturation, disk latency and Azure throttling.
5. Change **one variable per run**; repeat runs to distinguish noise from improvement.
6. Test one broker or zone failure only in a disposable cluster with explicit approval and rollback.
7. Reconcile unique event IDs and record cost assumptions for each candidate configuration.

Use supported `kafka-producer-perf-test.sh` and `kafka-consumer-perf-test.sh` from a version-matched Kafka client Pod where permitted. Check the version-specific CLI flags with `--help`. For representative producer tests, configure `acks=all`, idempotence and security properties in a mounted config file, not inline secrets. Producer-only tests do not establish end-to-end sink correctness.

## 6. Broker, storage and network bottleneck diagnosis

| Signal | Likely bottleneck | Confirm with |
|---|---|---|
| p99 rises, CPU low, disk latency high | Managed disk IOPS/MBps ceiling | Azure disk metrics, node iostat, PVC placement |
| High CPU throttling | Requests/limits or noisy neighbor | cAdvisor, node pressure, scheduling |
| Long GC pauses | Heap/object churn | JVM metrics and GC logs |
| One leader/partition dominates | Key skew | Per-partition rates, keys, leader placement |
| Lag grows while producers stable | Consumer throughput insufficient | Poll time, processing latency, partition count |
| ISR shrinks under load | Replication/network/disk pressure | Broker/ISR metrics, network, storage |
| Event Hubs throttled requests | Tier or quota ceiling | Azure Monitor, actual tier settings |

Never increase broker heap reflexively: Kafka benefits from OS page cache. Verify JVM heap, node memory, pod memory limits and disk read patterns together.

## 7. Partition, replica and recovery sizing

Partition count controls consumer parallelism but also metadata, open files and recovery overhead. Evaluate partition distribution, leader skew and broker count. Increasing partitions can change keyed ordering; plan data-contract review. RF=3 with `min.insync.replicas=2` and `acks=all` is a common durability starting point, **not a universal requirement**. Capacity must include failure headroom: remaining brokers must carry the load after a broker/AZ outage without violating latency and availability SLOs.

## 8. Event Hubs cost/performance comparison

For Event Hubs, discover current tier-specific throughput/processing capacity, partition quotas, retention, availability features, ingress/egress rules and billing from Microsoft documentation and the actual namespace configuration. Benchmark Kafka client interoperability, authentication, throughput, request throttling and consumer restart semantics.

Compare monthly cost on equivalent workload/SLO assumptions:
- **AKS Kafka:** VM/node pools, OS/data disks, snapshots/backups, networking/egress, monitoring ingestion, operations/on-call.
- **Event Hubs:** namespace/tier capacity charges, retention/storage where applicable, networking/egress, Azure Monitor, client migration and operational changes.

Do not invent Azure prices; capture region, SKU, reservation assumptions, billing date and pricing source.

## 9. Kubernetes-first hands-on labs (20)

Each lab must record preconditions, commands, baseline, isolated change, expected result, actual metrics, event reconciliation and rollback. A chapter's publication is not proof the lab passed.

| # | Lab | Acceptance evidence |
|---|---|---|
| 01 | AKS and Strimzi baseline inventory | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 02 | Broker node/pod requests and limits | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 03 | PVC and StorageClass inventory | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 04 | Azure disk SKU/IOPS discovery | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 05 | Partition count and RF audit | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 06 | Producer batch-size benchmark | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 07 | Producer linger and compression benchmark | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 08 | Idempotent producer throughput | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 09 | Consumer fetch tuning | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 10 | Consumer parallelism versus partitions | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 11 | Key skew/hot-partition analysis | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 12 | Broker CPU/GC analysis | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 13 | Network throughput and throttling | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 14 | Disk latency and saturation | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 15 | Retention storage forecasting | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 16 | Failure headroom benchmark | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 17 | Event Hubs tier/quota comparison | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 18 | Cost baseline and allocation | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 19 | Safe right-sizing scenario | Timestamped metrics, configuration, PASS/FAIL and rollback |
| 20 | Rollback and final evidence | Timestamped metrics, configuration, PASS/FAIL and rollback |

### Lab commands and repeatability

```powershell
# Read-only evidence collection
kubectl get kafkanodepool -n kafka -o yaml
kubectl get kafka -n kafka -o yaml
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka -o yaml
kubectl describe nodes
kubectl get events -n kafka --sort-by=.lastTimestamp
```

Benchmark client example (illustrative; requires a prepared image, secure client properties and approved synthetic topic):

```bash
kafka-producer-perf-test.sh \
  --topic perf-lab \
  --num-records 100000 \
  --record-size 1024 \
  --throughput 1000 \
  --producer.config /etc/kafka/client.properties
```

Verify CLI availability, topic ownership and limits before running. The rate limit above is a bounded starting point, not a capacity recommendation. Track both producer acknowledgments and independently consumed IDs.

## 10. Failure scenarios (12)

| # | Failure | Investigation and safe recovery |
|---|---|---|
| 1 | Disk IOPS ceiling | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 2 | Disk throughput ceiling | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 3 | PVC nearly full | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 4 | CPU throttling | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 5 | Heap pressure and GC pauses | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 6 | Hot partition | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 7 | Under-replicated partitions | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 8 | Consumer lag growth | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 9 | Broker network saturation | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 10 | Producer request timeouts | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 11 | Event Hubs quota throttling | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |
| 12 | Capacity shortfall during AZ failure | Verify client SLI impact, AKS/Strimzi/Azure metrics, contain in lab, roll back, reconcile IDs |

For each scenario include severity, blast radius, expected alerts, actual evidence, recovery timeline and preventive action. No unapproved destructive experiments.

## 11. SRE runbooks (8)

| # | Runbook | Standard steps |
|---|---|---|
| 1 | Disk saturation and latency | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 2 | Storage capacity emergency | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 3 | Producer p99 latency regression | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 4 | Consumer lag/catch-up | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 5 | Broker CPU/GC pressure | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 6 | Partition imbalance | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 7 | Event Hubs quota incident | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |
| 8 | Rightsizing and rollback | Assess impact → inspect telemetry → identify limiting resource → approve change → mitigate → validate → record RCA |

Every runbook must specify owner, escalation, rollback criteria, monitoring queries, RPO/RTO impact and post-incident reconciliation.

## 12. Reliability-aware FinOps

Cost reduction is valid only when latency, durability, security, capacity headroom and recovery objectives remain satisfied. Right-size idle clients and node pools before reducing broker durability; do not reduce RF, ISR safety or disk headroom solely to meet a savings target. Review Azure Savings Plans/Reservations applicability to eligible compute separately from managed-disk and Event Hubs billing. Maintain a change ledger with before/after cost, p99, lag, disk latency, failure capacity and rollback.

## 13. 100-point acceptance assessment

| Gate | Points |
|---|---:|
| Workload model and baseline | 15 |
| Producer/consumer benchmarks | 15 |
| Partition/replica/recovery capacity | 15 |
| Azure disk IOPS, throughput and storage | 15 |
| CPU, JVM and network diagnosis | 10 |
| Event Hubs tier/capacity comparison | 10 |
| FinOps and cost traceability | 10 |
| Security, runbooks, rollback and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100, no unexplained lost IDs, acceptable p99/lag at peak, recovery headroom demonstrated and no critical security findings. Independent review and live lab evidence are mandatory before runtime certification.

## 14. Evidence manifest

```yaml
chapter: 107
environment: isolated-aks-lab
aks_context: REPLACE
kafka_version: REPLACE
strimzi_version: REPLACE
azure_region: REPLACE
vm_sku: REPLACE
disk_sku: REPLACE
workload_profile: REPLACE
benchmark_runs: []
monthly_cost_assumptions: []
lab_results: []
failure_recovery: pending
event_reconciliation: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 15. Next chapter

**Chapter 108 — Azure Kafka HA, Availability Zones, Backup and DR.**
