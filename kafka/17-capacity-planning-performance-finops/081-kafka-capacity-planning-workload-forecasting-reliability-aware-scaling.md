# Chapter 081 — Kafka Capacity Planning, Workload Forecasting and Reliability-Aware Scaling

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 17 — Capacity Planning, Performance and FinOps (1/5)  
**Primary platform:** Kubernetes + Strimzi KRaft, with EKS/Amazon MSK comparison  
**Prerequisites:** Chapters 001–080; Prometheus/Grafana, Kafka metrics, Kubernetes storage and replication  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Capacity planning is read-only by default. Never scale KafkaNodePools, alter partition counts, retention, minISR, broker storage or MSK capacity in production without reviewed failure-domain analysis, backup/recovery, maintenance approval and SLO gates. Estimates are models, not measured performance.

## 1. Mission and outcomes

Develop evidence-based Kafka capacity forecasts that combine ingress/egress, retention, replication, partition metadata, KRaft quorum, broker CPU/memory, disk IOPS/throughput, network and consumer backlog. Evaluate reliability-aware scaling and cloud costs across Strimzi/Kubernetes and Amazon MSK.

At the end, readers can calculate per-broker storage demand, project failure-zone headroom, estimate replication and cross-AZ traffic, interpret bottlenecks, build demand scenarios and design safe scaling gates.

## 2. Architecture and bottleneck model

```text
Application producers -> partition leaders -> follower replicas
          |                    |                  |
     batch/compress        broker CPU           network/AZ
          |                    |                  |
       acks=all           log storage <--- replication traffic
                               |
                         retention/compaction
                               |
                  consumer fetch + downstream processing
                               |
                    lag, freshness and error budget

KRaft controller quorum: metadata and availability boundary
Strimzi KafkaNodePools: brokers/controllers + PVC lifecycle
Kubernetes nodes: CPU, memory, disk throughput, AZ placement
```

**Key principle:** storage, throughput, partition metadata, latency and failure tolerance are different dimensions. A cluster with free disk may still be CPU-, network-, partition- or consumer-bound.

## 3. Input data contract

| Metric | Unit | Source | Window |
|---|---|---|---|
| Ingress | compressed bytes/s and events/s | broker topic bytes-in / client | 30+ days |
| Egress | bytes/s | broker topic bytes-out | 30+ days |
| Topic partition count | count | Kafka Admin API | current and forecast |
| Replication factor | count | topic configs | current |
| Retention | hours/days or size | topic configs | current and policy |
| Broker disk | GiB used/free | PVC and broker metrics | daily + peak |
| Disk throughput/IOPS | MB/s, ops/s | node/cloud metrics | peak |
| CPU/heap/page cache | cores, GiB | Kubernetes/JMX/node | peak |
| Network and AZ transfer | MB/s, GB/month | node/cloud | peak + billing |
| Under-replicated partitions | count | Kafka JMX | continuous |
| Consumer lag/freshness | events, seconds | exporter/client | continuous |
| Availability/SLO | success rate, latency, lag | client telemetry | SLO window |

Do not treat a single broker's average as a cluster peak. Record skew, seasonality, uncertainty and missing telemetry.

## 4. Storage and retention formulas

For a topic with average **compressed** ingress rate \(r\) MiB/s, retention \(T\) seconds and replication factor \(RF\):

\[
D_{\text{logical}}=rT,\quad D_{\text{replicated}}\approx rT\,RF
\]

Convert MiB to GiB by dividing by 1024. Add explicit factors for index files, segments, compaction, temporary reassignment and uneven partition distribution. **This is an approximation**, not a guaranteed disk reservation.

For example, an illustrative topic at 20 MiB/s, seven days and RF=3:

- Logical retained bytes: 20 × 604,800 MiB = 11,812.5 GiB (about 11.54 TiB).
- Replicated log storage: about 35,437.5 GiB (34.61 TiB), before overhead.
- With six equally loaded brokers: approximately 5,906 GiB per broker **before** overhead and imbalance.

Retention.bytes, compaction, compression, changing ingress and segment deletion timing may invalidate a simple time-based model. Capacity must be calculated per topic and partition, not only globally.

## 5. Failure-zone and reliability headroom

Evaluate normal, N-1 broker and AZ-loss scenarios. A broker failure changes leader placement and replication/recovery traffic; an AZ failure can remove multiple replicas and threaten minISR.

```text
Usable capacity = min(
  storage after reserve,
  CPU-limited throughput,
  disk IOPS/throughput capacity,
  network bandwidth,
  partition/controller metadata capacity
)
```

Choose reserves from **measured** failover, reassignment and recovery behavior. Do not assume one universal safe utilization percentage. Validate that RF, minISR, rack/AZ placement, KRaft controller quorum and client `acks` meet the required fault tolerance.

## 6. Network, replication and consumer costs

A rough baseline for replicated writes is leader ingress plus \((RF-1)\) follower replication copies, excluding protocol overhead, retries and placement. Cross-AZ cost depends on replica placement, client AZ, cloud pricing and network architecture. Consumer egress and mirror/CDC traffic can exceed producer ingress.

Track **useful MB** (successfully consumed/processed application data) separately from raw broker bytes to avoid misleading cost-per-byte metrics.

## 7. CPU, memory and disk throughput

Kafka writes primarily use sequential append but fetch, compaction, retention deletion, recovery, TLS, compression and page-cache misses can drive random I/O and CPU pressure. Examine request handler idle, network processor idle, JVM GC, page cache, broker disk latency, throttles and under-replicated partitions.

Avoid scaling solely on Kubernetes Pod CPU percentage. Compare Kafka client P95/P99 latency and ISR before/after.

## 8. Consumer backlog and drain-time modeling

If producer arrival rate is \(\lambda\) events/s and consumer processing rate is \(\mu\) events/s:

- Backlog grows when \(\lambda > \mu\).
- When \(\mu > \lambda\), approximate drain time as backlog / \((\mu-\lambda)\).
- Consumer parallelism is bounded by partition count for a conventional consumer group; adding Pods beyond available partitions may not increase throughput.

Use event freshness, not lag count alone, when event sizes or processing cost vary.

## 9. Forecast scenarios and uncertainty

Build three demand cases: current baseline, seasonal peak and high-growth (e.g. 2×). For each, forecast compressed ingest, retained storage, partition count, broker CPU, disk/network utilization, recovery time, consumer lag and monthly costs. Include an uncertainty band and a date for reforecast.

**Illustrative model assumptions, not live measurements:**

| Scenario | Compressed ingest | Retention | RF | Approx. replicated retained log |
|---|---:|---:|---:|---:|
| Baseline | 5 MiB/s | 3 days | 3 | 3,797 GiB |
| Seasonal peak | 7.5 MiB/s | 3 days | 3 | 5,695 GiB |
| 2× growth | 10 MiB/s | 3 days | 3 | 7,594 GiB |

These values exclude indexes, skew, overhead and reassignments. Storage numbers are **not** per-broker values.

## 10. Strimzi and MSK scaling choices

**Strimzi:** Review KafkaNodePool roles, broker count, storage class, PVC expansion support, rack awareness, KRaft controller quorum, partition assignment and rebalance cost. Use the supported operator workflow for broker expansion and safe partition movement; never delete a PVC to "resize" it.

**MSK:** Compare broker count/size, storage, quotas, supported API operations, managed updates and AWS charges. MSK provisioned and serverless pricing/limits differ. Do not assume all settings or scaling actions are supported by both.

## 11. Read-only baseline commands

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl get pvc -A -l strimzi.io/kind=Kafka
kubectl top pods -A
kubectl top nodes
```

Metrics-server is required for `kubectl top`. Kafka metrics and topic configs require separately configured authenticated access; Kubernetes inventory alone cannot prove broker headroom.

## 12. Twenty Kubernetes-first capacity labs

### Lab 01 — Establish Kafka inventory

**Procedure:** Collect broker count, KRaft controllers, KafkaNodePools, AZs, instance types, PVC classes and storage.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 02 — Define service demand

**Procedure:** Document producer MB/s, consumer MB/s, events/s, peak multiplier, partition counts and retention.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 03 — Collect 30-day traffic baseline

**Procedure:** Extract time-series ingress/egress, per-topic variance, peak-to-mean and confidence intervals.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 04 — Measure compression

**Procedure:** Compare uncompressed payload bytes to compressed bytes per representative workload.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 05 — Model replication write amplification

**Procedure:** Estimate disk and cross-zone bytes for RF and replica placement, noting leader/follower flows.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 06 — Forecast retained storage

**Procedure:** Calculate ingestion × retention × replication × overhead and uncertainty.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 07 — Assess broker disk headroom

**Procedure:** Compare projected per-broker use, growth, rebalance overhead and alert thresholds.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 08 — Assess partition and controller scale

**Procedure:** Inventory partitions/broker, leaders, metadata and KRaft quorum capacity.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 09 — Assess network throughput

**Procedure:** Estimate producer ingress, follower replication, consumer egress and cross-AZ traffic.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 10 — Assess disk IOPS and throughput

**Procedure:** Correlate produce/fetch request rates, log flush, compaction, recovery and throttling.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 11 — Assess CPU and memory

**Procedure:** Review request handlers, TLS/compression, page cache, heap and GC metrics.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 12 — Assess consumer lag and freshness

**Procedure:** Model drain time from peak backlog and consumer processing throughput.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 13 — Model failure-zone capacity

**Procedure:** Validate N-1 broker and AZ-loss placement, ISR/minISR and reserve capacity.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 14 — Model partition growth

**Procedure:** Estimate topic partitions, ordering constraints, future splits and reassignment cost.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 15 — Evaluate KafkaNodePool expansion

**Procedure:** Draft Strimzi node-pool capacity change and safe broker placement plan.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 16 — Evaluate MSK scaling alternatives

**Procedure:** Compare broker size/count, storage and service limits without creating AWS resources.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 17 — Design load-test protocol

**Procedure:** Specify isolated namespace, fixed event IDs, payload distribution, duration and abort criteria.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 18 — Calculate three demand scenarios

**Procedure:** Produce baseline, +50% peak and 2x growth projections with assumptions.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 19 — Prepare cost-and-reliability decision

**Procedure:** Compare cost per useful MB, AZ transfer, retention and error-budget risk.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

### Lab 20 — Independent forecast acceptance

**Procedure:** Review formulas, raw metrics, failure headroom, SLO, assumptions and reviewer signoff.

**Expected evidence:** UTC time, environment, Strimzi/Kafka/Kubernetes versions, data window and source, unit-consistent formula, raw/peak values, uncertainty, RF/minISR/AZ placement, broker/PVC utilization, client SLO, scenario output, decision/abort and independent reviewer. **Status: Pending** until executed. Scaling and stress tests remain **Tabletop** without an approved disposable cluster.

## 13. Reproducible offline forecast calculator

Save as `capacity_forecast.py`. Uses only the Python standard library and **does not** connect to a cluster.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("--ingress-mib-s", type=float, required=True)
p.add_argument("--retention-days", type=float, required=True)
p.add_argument("--replicas", type=int, required=True)
p.add_argument("--brokers", type=int, required=True)
p.add_argument("--overhead-factor", type=float, default=1.2)
args = p.parse_args()

if (args.ingress_mib_s < 0 or args.retention_days <= 0
        or args.replicas < 1 or args.brokers < 1
        or args.overhead_factor < 1):
    p.error("invalid nonnegative ingress, positive retention/brokers/RF and overhead >= 1")
logical_gib = args.ingress_mib_s * args.retention_days * 86400 / 1024
replicated_gib = logical_gib * args.replicas
planned_gib = replicated_gib * args.overhead_factor
print(json.dumps({
    "logical_gib": round(logical_gib, 2),
    "replicated_gib": round(replicated_gib, 2),
    "planned_gib": round(planned_gib, 2),
    "balanced_per_broker_gib": round(planned_gib / args.brokers, 2),
    "warning": "Average only; excludes skew, reassignment and fault-zone reserves"
}, indent=2))
```

Example (offline):

```bash
python capacity_forecast.py --ingress-mib-s 5 --retention-days 3 --replicas 3 --brokers 6
```

Expected logical ≈1,265.625 GiB, replicated ≈3,796.875 GiB and planned ≈4,556.25 GiB with default 20% modeling overhead. This factor is an **assumption**, not a validated safety reserve. Model peak, skew and AZ loss separately.

## 14. Twelve capacity failure scenarios

### Scenario 01 — Storage forecast ignores replication

**Diagnosis:** Recalculate RF and broker/AZ distribution, preserve failure headroom. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 02 — Consumer lag grows despite spare disk

**Diagnosis:** Check consumer CPU, partitions, fetch, downstream rate and rebalance. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 03 — Broker CPU high but network low

**Diagnosis:** Inspect TLS/compression, GC, request handler saturation and hot partitions. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 04 — High disk utilization during reassignment

**Diagnosis:** Stop risky moves, inspect free capacity and recovery bandwidth. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 05 — Partition count grows faster than traffic

**Diagnosis:** Review metadata/controller and file-handle overhead. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 06 — Cross-AZ egress exceeds forecast

**Diagnosis:** Inspect replica placement, client routing and traffic accounting. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 07 — MSK storage autoscaling surprises budget

**Diagnosis:** Inspect storage policy, forecast and broker cost before approval. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 08 — KafkaNodePool scaling risks quorum

**Diagnosis:** Separate controller and broker roles; preserve KRaft quorum and ISR. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 09 — Forecast based only on average ingress

**Diagnosis:** Use p95/p99 peak, seasonal bursts and failure scenarios. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 10 — Compression ratio changes unexpectedly

**Diagnosis:** Inspect payload distribution, codecs, CPU and batch size. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 11 — Replica lag rises during broker failure

**Diagnosis:** Check disk/network saturation, throttles, minISR and producer acks. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

### Scenario 12 — Benchmark passes but production latency fails

**Diagnosis:** Compare realistic payload, partition skew, TLS, AZ and client behavior. Correlate producer/consumer bytes, partition skew, KRaft quorum, ISR, PVC growth, disk IOPS/latency, CPU/GC, network/AZ, client P99 and cost. **Response:** Protect Kafka durability and customer SLO, stop unsafe changes, choose reviewed capacity or workload mitigation. **Exit:** Stable ISR, acceptable client freshness, updated forecast, RCA and reviewer.

## 15. Eight production runbooks

### Runbook A — Capacity saturation incident

**Trigger/actions:** Identify bottleneck, protect ISR, slow producers safely and prioritize SLO. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook B — Disk growth emergency

**Trigger/actions:** Validate retention and compaction, stop unsafe reassignments, add approved capacity. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook C — Consumer lag and freshness breach

**Trigger/actions:** Measure arrival/processing rate, partition parallelism, backlog and drain time. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook D — Broker/AZ failure capacity review

**Trigger/actions:** Check N-1/AZ headroom, placement, quorum, ISR and approved recovery. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook E — KafkaNodePool expansion

**Trigger/actions:** Review broker roles, PVCs, rack awareness, rebalance and post-change smoke. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook F — MSK broker/storage scaling

**Trigger/actions:** Check quotas, cost, maintenance state, client SLO and rollback limitations. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook G — Cost anomaly triage

**Trigger/actions:** Reconcile ingest, retention, cross-AZ, storage, egress and compression changes. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

### Runbook H — Quarterly capacity acceptance

**Trigger/actions:** Review trends, forecast errors, scenarios, budget, SLO and signoff. **No-go:** unreviewed broker/PVC change, degraded quorum/ISR, missing fault-zone headroom, unknown data correctness or unapproved cloud cost. **Exit:** Observed Kafka/client SLO, approved capacity, audited change and independent signoff.

## 16. Evidence package

```text
evidence-ch081/
  inventory.md
  workload-demand.md
  ingress-baseline.csv
  compression.md
  replication-model.md
  storage-forecast.json
  disk-headroom.md
  partition-controller-scale.md
  network-az.md
  disk-iops-throughput.md
  cpu-memory.md
  consumer-lag-drain.md
  failure-zone-model.md
  partition-growth.md
  strimzi-scaling-tabletop.md
  msk-scaling-tabletop.md
  benchmark-design.md
  scenarios.csv
  finops-decision.md
  independent-acceptance.md
  scorecard.md
```

Every artifact must record data provenance, units, UTC timestamp, tool versions, expected/observed result, **Live** versus **Tabletop**, assumptions, uncertainty, abort/rollback, owner and reviewer.

## 17. 100-point capacity and reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Workload measurements and forecast quality | 20 | Yes |
| Replication, retention and disk headroom | 20 | Yes |
| CPU, network, partitions and consumer capacity | 15 | Yes |
| Failure-zone reserve, quorum and ISR safety | 20 | Yes |
| Scaling options and FinOps tradeoffs | 15 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic Fail:** fabricated measurements, omitted RF/AZ risk, destructive scaling without approval, unexplained ISR loss, incorrect units causing unsafe capacity or missing independent review.

## 18. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 082 — Kafka Storage, Partition and Broker Capacity Engineering for Production Workloads.

---

**Verification boundary:** Publication proves document availability only. Live metrics collection, stress testing, capacity changes and independent technical/security review remain Pending.
