# Chapter 117 — Google Cloud Kafka Performance, Capacity, Storage and FinOps

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (7/10)  
**Primary platform:** GKE Standard + Strimzi Kafka KRaft  
**Managed alternative:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–116, approved GKE lab, synthetic producer/consumer and monitoring  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending · **Runtime certification:** Not claimed

> **Safety:** Run stress tests only in an isolated, budget-approved project. Disk resizing, partition changes, broker downscaling and retention changes can affect availability or permanently remove data. Confirm current GKE, Google Cloud Persistent Disk and managed Kafka pricing, limits and feature availability rather than assuming universal SKU numbers.

## 1. Mission and outcomes

Establish a defensible Kafka capacity model for throughput, latency, retention, partition count, disk performance, broker and controller headroom, consumer recovery and cloud cost. Benchmark synthetic workloads on GKE/Strimzi and compare managed Kafka economics and service quotas.

**Deliverables:** baseline report, workload envelope, capacity forecast, benchmark evidence, disk/partition analysis, TCO comparison, FinOps guardrails, 20 labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Architecture and bottlenecks

```text
GKE producer Pods → TLS → Kafka brokers across zones → consumer Pods → sink
       |                      |                           |
  batching/retries       CPU/JVM/GC                   lag/processing
  event size             partitions/ISR              backpressure
  compression            disk IOPS/MBps               sink durability
                         network/zone egress
                         PVC space/retention
                                |
                       Prometheus / Cloud Monitoring
                                |
                     SLO + FinOps decision gates
```

Kafka throughput is limited by the narrowest resource in the end-to-end path. Increasing partitions does not repair a saturated sink, slow disk or overloaded broker by itself.

## 3. Read-only capacity inventory

From PowerShell, confirm the correct GKE context and Kafka namespace:

```powershell
gcloud config get-value project
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl top nodes
kubectl top pods -n kafka
kubectl get kafka,kafkanodepool,kafkatopic -n kafka
kubectl get pods -n kafka -o wide
kubectl get pvc -n kafka -o wide
kubectl get storageclass
kubectl get events -n kafka --sort-by=.lastTimestamp
```

`kubectl top` requires Metrics Server or equivalent metrics integration. These commands provide a baseline but not disk latency or sustained throughput; collect those through GKE/Cloud Monitoring and exporter telemetry.

## 4. Workload capacity model

Record measured average and p99 encoded event size, incoming events/sec, peak multiplier, partitions, replication factor, retention, compression, consumer fanout, safety margin and recovery objective.

**Illustrative planning equations** (not a replacement for measured on-disk compression, segment/index overhead or replica placement):

```text
logical_ingest_bytes_per_day =
    events_per_second × avg_encoded_bytes × 86,400

logical_retention_bytes =
    logical_ingest_bytes_per_day × retention_days

cluster_replica_storage_bytes ≈
    logical_retention_bytes × replication_factor

planned_storage_bytes =
    cluster_replica_storage_bytes × (1 + overhead_fraction)
    ÷ target_max_utilization_fraction

producer_network_bytes_per_second ≈
    events_per_second × avg_encoded_bytes

replication_network_bytes_per_second ≈
    producer_network_bytes_per_second × (replication_factor - 1)
```

These approximations exclude producer compression differences, consumer traffic, internal topics, log index overhead, rebalancing, replication retransmits, cross-zone topology and snapshots. Model each separately and validate with actual broker metrics.

**Example:** 10,000 events/sec × 1 KiB × 86,400 ≈ 824 GiB/day of logical payload. At 3 replicas and 7 days, raw replica payload is approximately 16.9 TiB before overhead and headroom. Do not size storage from this alone.

## 5. Partition and broker sizing

Estimate partitions from measured per-partition producer throughput, consumer concurrency, key distribution and failover behavior. Keep partition count within tested controller, broker and client limits. Over-partitioning increases metadata, file handles, recovery and rebalance work. Use explicit key-skew measurements; Kafka only guarantees ordering within a partition, not globally.

For resilience, confirm actual rack/zone placement, ISR health and remaining broker capacity after the loss of the largest failure domain. Controller-only KRaft nodes do not store broker partition replicas.

## 6. GKE Persistent Disk engineering

Choose supported GKE CSI-backed disk classes based on actual region/zone support, IOPS, MBps, latency, disk size, machine type ceilings and pricing. Validate volume binding mode and PVC placement. Provisioned disk performance can be bounded by node and disk limits, so selecting a faster disk type is not sufficient without end-to-end testing.

Measure:
- disk read/write latency, IOPS, throughput and saturation;
- broker request queue and produce/fetch latency;
- Kafka log directory utilization and free-space runway;
- throttling, page cache behavior and recovery under replica catch-up.

Avoid interpreting filesystem space or disk queue depth as a single universal threshold; use workload baselines and SLO impact.

## 7. Producer and consumer tuning

Test one variable at a time: `linger.ms`, `batch.size`, compression, `acks=all`, idempotence, delivery timeout and in-flight requests. Measure throughput against p99 latency, retry rates and accepted-event correctness. For consumers, measure fetch sizes, poll interval, processing concurrency, rebalance frequency, max lag and sink capacity. Do not sacrifice durability or offset discipline for benchmark throughput.

## 8. Autoscaling and capacity planning

GKE Cluster Autoscaler can provision nodes for eligible pending Pods; it does not automatically resize Kafka broker replicas, partitions or PVCs. Kafka scaling requires Strimzi-supported operations, capacity review and data redistribution planning. HPA on a consumer Deployment may increase group members, but parallelism is bounded by partitions and application behavior. Avoid reactive broker autoscaling without a tested safety design.

## 9. Managed Kafka comparison

Google Cloud Managed Service for Apache Kafka removes some broker lifecycle duties but still requires workload sizing, client tuning, quota analysis, regional availability checks, cost modeling and service-specific monitoring. Verify documented capacity and storage controls and do not assume Kafka broker-level settings or metrics are exposed. Benchmark the same synthetic workload and record feature compatibility before recommending migration.

## 10. FinOps and reliability-aware optimization

Cost model:

```text
monthly_total_cost =
  GKE node compute + Kafka persistent disks + snapshots/backups
  + cross-zone/region traffic + load balancing/NAT
  + monitoring/logging + DR standby + operations
```

For managed Kafka, replace self-managed broker compute/storage with actual service billing dimensions and include client GKE costs, networking, monitoring and operational responsibilities.

Require a change proposal with before/after p99 latency, throughput, cost, durability, ISR headroom, recovery capacity and rollback. Never reduce replica factor, min ISR or retention below approved business requirements merely to improve cost.

## 11. Benchmark execution protocol

1. Pin Kafka/Strimzi/client versions, node/disk SKUs and topology.
2. Record idle baseline, then warm up at a bounded load.
3. Run steady-state and controlled peak tests with multiple repetitions.
4. Capture producer acknowledgements, latency, broker CPU/GC, disk metrics, network, consumer lag and sink throughput.
5. Run a safe one-broker failure capacity scenario only in an isolated lab.
6. Reconcile accepted IDs with sink effects and DLQ.
7. Compare costs using dated billing data and document confidence intervals/limitations.

Stop on critical data-integrity failure, unsafe ISR, storage exhaustion or exceeded budget.

## 12. Hands-on labs (20)

Every lab requires version, prerequisites, exact commands/queries, expected and actual results, timestamped metrics, PASS/FAIL, rollback and cleanup. Publication does not imply execution.

| # | Lab | Evidence |
|---|---|---|
| 01 | Capture GKE and Kafka baseline | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 02 | Measure synthetic message size distribution | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 03 | Inventory topic partitions and replicas | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 04 | Inspect broker zone placement | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 05 | Inspect broker CPU and JVM heap | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 06 | Measure producer p95/p99 latency | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 07 | Measure producer batch and compression | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 08 | Measure consumer throughput and lag | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 09 | Measure hot partitions and key skew | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 10 | Inventory PVC size and disk class | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 11 | Measure disk IOPS and throughput | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 12 | Measure disk latency under steady load | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 13 | Forecast retention and growth | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 14 | Test controlled burst workload | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 15 | Evaluate one-zone capacity headroom | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 16 | Inspect network egress and cross-zone costs | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 17 | Compare managed Kafka quotas and metrics | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 18 | Build workload-based monthly TCO | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 19 | Simulate rightsizing without unsafe changes | Timestamped benchmark, capacity metric, cost estimate and rollback |
| 20 | Capacity acceptance and rollback review | Timestamped benchmark, capacity metric, cost estimate and rollback |

## 13. Failure scenarios (12)

| # | Scenario | Recovery objective |
|---|---|---|
| 1 | Broker CPU saturation | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 2 | JVM GC pauses | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 3 | Persistent Disk IOPS throttling | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 4 | Persistent Disk throughput throttling | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 5 | PVC nearly full | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 6 | Partition skew | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 7 | Producer timeout | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 8 | Consumer backlog | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 9 | Broker ISR loss during burst | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 10 | GKE node pool scheduling failure | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 11 | Managed Kafka quota throttling | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |
| 12 | FinOps change removes recovery headroom | Correlate Kafka/GKE/Cloud metrics, contain, restore SLO and reconcile IDs |

For each scenario document trigger, severity, blast radius, expected alarm, observed bottleneck, rollback, recovery timeline and preventive action.

## 14. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Kafka performance regression | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 2 | Broker CPU/GC pressure | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 3 | Persistent Disk saturation | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 4 | Partition skew and hot keys | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 5 | Consumer lag and sink bottleneck | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 6 | Capacity expansion | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 7 | Managed Kafka quota escalation | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |
| 8 | Cost optimization change review | Baseline → isolate bottleneck → approved change → validate correctness and SLO → RCA |

Every runbook needs owner, escalation, safe commands, stop criteria, rollback authority and evidence retention.

## 15. 100-point performance and FinOps acceptance

| Gate | Points |
|---|---:|
| Measured workload and baseline | 15 |
| Producer/consumer throughput and latency | 15 |
| Broker, KRaft and partition sizing | 15 |
| Persistent Disk performance and capacity | 15 |
| HA/failure headroom and data correctness | 15 |
| GKE vs managed Kafka cost comparison | 10 |
| FinOps guardrails and rollback | 10 |
| Independent review and evidence | 5 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 with no unexplained missing accepted IDs, approved ISR/durability, measured recovery headroom, no critical security issues and independent review. Publication is not runtime certification.

## 16. Evidence manifest

```yaml
chapter: 117
environment: isolated-gke-kafka-performance
backend: REPLACE_STRIMZI_OR_MANAGED
gcp_project: REDACTED
region: REPLACE
broker_count: null
partition_count: null
replication_factor: null
avg_encoded_event_bytes: null
events_per_second: null
retention_days: null
p99_producer_latency_ms: null
p99_pipeline_latency_ms: null
disk_iops_observed: null
disk_throughput_mbps_observed: null
disk_latency_ms_observed: null
consumer_lag_max: null
missing_accepted_ids: null
monthly_cost_estimate: null
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 17. Next chapter

**Chapter 118 — Google Cloud Kafka HA, Zones, Backup and DR.**
