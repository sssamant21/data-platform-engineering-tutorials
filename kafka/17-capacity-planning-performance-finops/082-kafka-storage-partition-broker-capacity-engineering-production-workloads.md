# Chapter 082 — Kafka Storage, Partition and Broker Capacity Engineering for Production Workloads

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 17 — Capacity Planning, Performance and FinOps (2/5)  
**Primary platform:** Kubernetes + Strimzi Kafka in KRaft mode; AWS EKS/MSK comparisons  
**Prerequisites:** Chapters 001–081; Prometheus/JMX, Kubernetes PVC/CSI, Kafka topic administration  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** All examples are read-only or offline planning. Do not change retention, increase partitions, delete PVCs, alter KafkaNodePool replicas, run reassignments, enable tiered storage or change MSK broker/storage settings in production without independent approval, recovery evidence and Kafka durability gates. Partition count increases cannot be reversed by Git rollback.

## 1. Mission and outcomes

Engineer Kafka capacity across **storage, partitions, brokers, controller metadata and failure domains**. Quantify per-partition skew, retained replicated bytes, segment overhead, compaction/recovery I/O, disk latency, KRaft controller pressure and the impact of node-pool or MSK capacity changes.

By the end, readers can build broker-level disk/IOPS forecasts, identify hot partitions, distinguish throughput bottlenecks from capacity limits, evaluate safe scaling choices and design incident response around ISR/minISR and client correctness.

## 2. Production architecture

```text
Producers -> partition leaders -> follower replicas
                |                     |
          segment files           replica fetch
          index/timeindex         catch-up I/O
          retention/cleaner       AZ traffic
                |
           broker PVC / CSI / disk
                |
          CPU, cache, IOPS, MB/s
                |
        consumer fetch + lag/freshness

KRaft controller quorum -> partition metadata, leadership and assignments
Strimzi KafkaNodePool -> broker/controller roles, storage, AZ scheduling
```

Capacity planning must cover **normal**, **single-broker failure**, **AZ failure** and **recovery/reassignment** modes. A cluster with sufficient total disk can fail when one broker or partition is skewed.

## 3. Inventory and measurement contract

| Dimension | Required metrics | Source |
|---|---|---|
| Storage | used/free GiB, disk latency, IOPS, throughput | PVC/node/cloud |
| Topic logs | partitions, size, retention, compaction, RF | Kafka admin/JMX |
| Partition skew | per-partition bytes, leader, follower lag | Kafka metrics |
| Broker resources | CPU, heap, page cache, network, requests | JMX/Prometheus |
| KRaft | quorum status, metadata growth, controller load | Kafka admin/JMX |
| Failure domain | rack/AZ, RF/minISR, ISR, offline partitions | Kafka/Strimzi |
| Consumers | fetch bytes, lag, event freshness | clients/exporters |
| FinOps | storage class, IOPS provision, AZ traffic, broker hours | cloud billing |

Record at least 30 days where possible, and preserve 95th/99th percentile and burst behavior. Metrics and quotas vary by Kafka, Strimzi, Kubernetes and MSK version.

## 4. Storage capacity equations

For compressed ingress \(r\) MiB/s, retention \(T\) seconds and replication factor \(RF\):

\[
S_{logical}=rT/1024\quad\text{GiB}
\]
\[
S_{replicated}\approx S_{logical}\times RF
\]

For balanced placement across \(B\) brokers, mean per broker is \(S_{replicated}/B\), but real provisioning must account for **skew**, active segment overhead, cleaner/compaction work, recovery, PVC reservations and AZ loss.

**Illustrative workload:** 8 MiB/s compressed ingress, 5-day retention, RF=3, 6 brokers:
- Logical retained log: 3,375 GiB.
- Replicated log: 10,125 GiB.
- Balanced average: 1,687.5 GiB per broker **before** overhead, imbalance and failure reserve.

A compacted topic does not follow simple time-based retention; model key churn, tombstones, cleaner backlog and segment lifecycle separately.

## 5. Broker disk headroom and skew

Per-broker sizing should use observed maximum partition assignment, not just total bytes / brokers. Calculate:

```text
required_broker_disk =
  assigned_replica_logs
  + segment_and_index_overhead
  + temporary_recovery_or_reassignment
  + operational_reserve
```

Use measured worst-case assignment and failure simulations. A fixed 80% disk alert is a useful **illustrative early warning**, not a universal safe operating threshold. Escalate based on days-to-full, ISR, recovery demand and actual volume limits.

## 6. Segments, retention and compaction

Kafka deletes closed log segments according to retention policy and log lifecycle. Lowering retention does not instantly remove the active segment. Compaction reclaims obsolete keys asynchronously, depends on dirty ratio and cleaner throughput, and can compete with replication/fetch I/O.

**Risks:** aggressive retention can cause permanent data loss; compaction changes effective storage but not consumer processing guarantees. Require application owner approval and replay/recovery assessment.

## 7. Partition and controller metadata engineering

Partition count affects consumer parallelism, file descriptors, open segments, controller metadata, leadership changes and broker request overhead. A high partition count with tiny payloads can stress KRaft controllers despite low bytes/s.

Do not choose a universal partitions-per-broker limit without benchmarking the specific Kafka version, hardware, metadata workload and failure scenario. A partition count increase is one-way and can alter key-based ordering behavior.

## 8. Disk IOPS and throughput engineering

Correlate broker disk read/write throughput, queue depth, latency, volume throttling, log cleaner, follower catch-up and consumer fetch. Distinguish:
- **capacity bottleneck:** disk full or approaching limit;
- **throughput bottleneck:** MB/s capped despite free disk;
- **IOPS/latency bottleneck:** queued requests and high await;
- **metadata bottleneck:** controller/partition churn despite low disk usage.

A volume size upgrade does not necessarily fix CPU, network or partition skew.

## 9. Strimzi KafkaNodePool and PVC safety

Review broker/controller roles, replicas, node scheduling, rack awareness, PVC requests and StorageClass capabilities. For PVC expansion, confirm CSI support, `allowVolumeExpansion`, filesystem resize behavior and version-specific Strimzi reconciliation.

**Do not delete PVCs** as a resize or repair strategy. Scale-out requires new broker placement, partition movement, replication recovery bandwidth, healthy ISR and SLO monitoring. Preserve controller quorum during all changes.

## 10. AWS MSK storage and broker choices

Compare MSK provisioned broker instance size/count, EBS volume and supported throughput features, cluster storage autoscaling where configured, service quotas and maintenance implications. MSK Serverless differs materially in limits, capacity model and pricing.

Do not assume broker replacement, downscaling, storage decrease or version downgrade are reversible. Validate against the actual MSK cluster type and AWS documentation before planning changes.

## 11. Read-only inventory commands

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pvc -A
kubectl get storageclass
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl top nodes
```

Authenticated Kafka admin examples (use an approved client configuration and bootstrap endpoint):

```bash
kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --command-config "$CLIENT_CONFIG" --describe
kafka-configs.sh --bootstrap-server "$BOOTSTRAP" --command-config "$CLIENT_CONFIG" --entity-type topics --describe
```

Do not print private client configuration. Kubernetes inventory alone cannot measure Kafka segment size, quorum health or partition lag.

## 12. Twenty Kubernetes-first storage and broker labs

### Lab 01 — Inventory KafkaNodePools and PVCs

**Procedure:** Capture KafkaNodePool roles, broker count, volumes, storage class, PVC requests and observed usage.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 02 — Inventory topic configurations

**Procedure:** Record topic partitions, RF, minISR, retention.ms, retention.bytes and cleanup.policy.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 03 — Measure per-partition skew

**Procedure:** Compare log size, leader distribution, ingress, fetch and replica lag by partition.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 04 — Calculate retained log footprint

**Procedure:** Apply compressed ingest × retention × RF, adjusted for compaction and topic-level limits.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 05 — Model segment/index overhead

**Procedure:** Estimate index/timeindex, active segments and filesystem safety margin.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 06 — Measure disk throughput

**Procedure:** Correlate read/write MB/s, IOPS, await, utilization and Kafka request latency.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 07 — Inspect PVC expansion support

**Procedure:** Read StorageClass allowVolumeExpansion and filesystem resize constraints.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 08 — Audit local vs network storage

**Procedure:** Compare persistence guarantees, AZ placement, throughput and failure semantics.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 09 — Assess KRaft controller load

**Procedure:** Review controller roles, metadata log health, partition churn and quorum membership.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 10 — Assess partition metadata scale

**Procedure:** Count partitions, replicas, leaders and open-file/metadata overhead.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 11 — Assess partition leader skew

**Procedure:** Review uneven broker leaders, hot keys and potential reassignment costs.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 12 — Model broker failure headroom

**Procedure:** Estimate N-1 disk/throughput reserve and replica catch-up requirements.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 13 — Model AZ failure placement

**Procedure:** Check rack-aware replicas, minISR and KRaft controller fault domains.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 14 — Review log compaction capacity

**Procedure:** Assess dirty ratio, tombstones, cleaner I/O and competing client load.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 15 — Review tiered storage eligibility

**Procedure:** Check Kafka distribution, version, feature support, costs and operational tradeoffs.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 16 — Evaluate Strimzi scale-out design

**Procedure:** Draft KafkaNodePool expansion and approved partition rebalance plan.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 17 — Evaluate storage scale-up design

**Procedure:** Draft PVC expansion and filesystem validation plan without mutation.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 18 — Evaluate MSK broker/storage options

**Procedure:** Compare provisioned MSK instance, storage throughput, scaling restrictions and quotas.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 19 — Build capacity incident simulation

**Procedure:** Tabletop 80% disk, failed broker, replica catch-up and slow consumer scenarios.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

### Lab 20 — Perform independent sizing review

**Procedure:** Verify units, skew, failure reserves, client SLO, recovery, costs and signoff.

**Expected evidence:** UTC time, cluster context, Kafka/Strimzi/Kubernetes version, raw measurement and units, topic RF/minISR, AZ/rack assignment, partition skew, PVC/IOPS utilization, Kafka ISR/quorum, client SLO, forecast assumptions, abort/recovery and reviewer. **Status: Pending** until executed. Mutating storage, partitions, node pools or MSK remains **Tabletop** unless approved in disposable infrastructure.

## 13. Offline partition-aware storage sizing calculator

Save as `broker_storage_model.py`. It does not connect to Kafka or Kubernetes.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("--ingress-mib-s", type=float, required=True)
p.add_argument("--retention-days", type=float, required=True)
p.add_argument("--replicas", type=int, required=True)
p.add_argument("--brokers", type=int, required=True)
p.add_argument("--skew-factor", type=float, default=1.25)
p.add_argument("--overhead-factor", type=float, default=1.20)
args = p.parse_args()
if (args.ingress_mib_s < 0 or args.retention_days <= 0 or args.replicas < 1
        or args.brokers < 1 or args.skew_factor < 1 or args.overhead_factor < 1):
    p.error("invalid input: positive retention, RF, brokers and factors >= 1")
logical_gib = args.ingress_mib_s * args.retention_days * 86400 / 1024
replicated_gib = logical_gib * args.replicas
balanced_gib = replicated_gib / args.brokers
sized_gib = balanced_gib * args.skew_factor * args.overhead_factor
print(json.dumps({
    "logical_gib": round(logical_gib, 2),
    "replicated_gib": round(replicated_gib, 2),
    "balanced_per_broker_gib": round(balanced_gib, 2),
    "modeled_peak_broker_gib": round(sized_gib, 2),
    "warning": "Illustrative only: validate measured skew, recovery, IOPS, AZ and free-space reserve"
}, indent=2))
```

Example:

```bash
python broker_storage_model.py --ingress-mib-s 8 --retention-days 5 --replicas 3 --brokers 6
```

Expected: logical 3,375 GiB; replicated 10,125 GiB; balanced 1,687.5 GiB/broker; modeled peak broker 2,531.25 GiB with default skew/overhead assumptions. These factors are **not** validated operational reserves.

## 14. Twelve storage and partition failure scenarios

### Scenario 01 — Disk growth exceeds forecast

**Diagnosis:** Check retention, compression, RF, replica skew and topic-level limits. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 02 — Broker out of disk despite average free capacity

**Diagnosis:** Inspect partition skew, leader placement and local filesystem/PVC metrics. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 03 — High IOPS latency without high CPU

**Diagnosis:** Check volume throughput/IOPS caps, queue depth and log flush/recovery. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 04 — Replica catch-up saturates storage

**Diagnosis:** Review reassignment/recovery throttle, ISR, network and failure reserves. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 05 — PVC expansion request does not resize filesystem

**Diagnosis:** Check StorageClass, CSI driver, filesystem and pod restart requirements. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 06 — Retention reduction does not reclaim immediately

**Diagnosis:** Inspect segment roll, active segment, retention check interval and compaction. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 07 — Compacted topic retains unexpected bytes

**Diagnosis:** Inspect cleaner backlog, dirty ratio, tombstones and segment lifecycle. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 08 — Partition increase worsens broker performance

**Diagnosis:** Review metadata, controller load, file descriptors and hot-key distribution. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 09 — Controller quorum degrades during broker scale

**Diagnosis:** Separate controller/broker roles and preserve KRaft quorum. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 10 — AZ failure violates minISR

**Diagnosis:** Audit replica placement, rack-awareness, ISR and producer acks. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 11 — MSK storage throughput throttle

**Diagnosis:** Inspect broker/storage metrics, provisioned throughput settings and quotas. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

### Scenario 12 — Tiered storage changes recovery assumptions

**Diagnosis:** Check feature compatibility, object storage access, cost and RTO. Correlate topic/partition size, Kafka ISR/minISR, KRaft quorum, PVC metrics, disk latency/IOPS, AZ placement, consumer freshness and client P99. **Response:** Stop unsafe storage or partition changes, protect data and ISR, apply reviewed capacity/recovery action. **Exit:** Stable Kafka durability, acceptable client SLO, revised model, RCA and reviewer.

## 15. Eight production runbooks

### Runbook A — Disk saturation response

**Trigger/actions:** Stop risky moves, check ISR, preserve data, add approved capacity and monitor client SLO. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook B — Partition hot spot response

**Trigger/actions:** Identify keys/leaders, review producers and plan compatible partition strategy. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook C — Storage latency and IOPS response

**Trigger/actions:** Correlate cloud/PVC metrics, broker requests, cleaner and replication traffic. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook D — KafkaNodePool scale-out

**Trigger/actions:** Approve placement, storage, quorum, rebalance and post-change validation. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook E — PVC expansion change

**Trigger/actions:** Confirm CSI support, backups, rollback limits and filesystem verification. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook F — Replica recovery capacity

**Trigger/actions:** Assess ISR/minISR, recovery throughput, throttle and fault-domain reserves. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook G — MSK capacity change

**Trigger/actions:** Validate AWS quotas, instance/storage options, maintenance and client health. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

### Runbook H — Quarterly storage/partition review

**Trigger/actions:** Update demand model, skew, costs, recovery time and independent signoff. **No-go:** unreviewed PVC or broker mutation, insufficient ISR/quorum, unmeasured recovery headroom, data correctness gaps or unapproved cloud cost. **Exit:** Measured broker/client health, audited change and independent signoff.

## 16. Evidence package

```text
evidence-ch082/
  kafka-nodepool-pvc-inventory.md
  topic-config-inventory.csv
  partition-skew.csv
  retained-storage.json
  segment-index-overhead.md
  disk-iops-throughput.csv
  pvc-expansion-support.md
  storage-class-risk.md
  kraft-controller-capacity.md
  partition-metadata-scale.md
  leader-skew.md
  broker-failure-headroom.md
  az-failure-placement.md
  compaction-capacity.md
  tiered-storage-eligibility.md
  strimzi-scaleout-tabletop.md
  pvc-scaleup-tabletop.md
  msk-scaling-tabletop.md
  capacity-incident-tabletop.md
  independent-sizing-review.md
  scorecard.md
```

Evidence must include UTC timestamp, source/version, unit-consistent calculations, **Live** vs **Tabletop**, observed versus expected result, data/ISR risk, abort/recovery, owner and independent reviewer.

## 17. 100-point production storage capacity assessment

| Domain | Points | Critical |
|---|---:|---|
| Topic/partition inventory and skew | 20 | Yes |
| Retention, compaction and storage forecasts | 20 | Yes |
| Disk IOPS/throughput and PVC engineering | 20 | Yes |
| KRaft quorum, ISR and failure-zone headroom | 20 | Yes |
| Strimzi/MSK scaling and cost governance | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** fabricated metrics, unsafe PVC deletion, unapproved partition change, ignored ISR/quorum risk, missing fault-zone reserve or absent independent review.

## 18. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 083 — Kafka Performance Benchmarking, Load Testing and Capacity Validation Engineering.

---

**Verification boundary:** Publication proves document availability only. Live metrics collection, storage benchmarking, scaling changes and independent technical/security review remain Pending.
