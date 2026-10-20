# Chapter 034 — Kafka Broker Performance Tuning, JVM, Network, Storage and Kubernetes Resource Optimization

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 07 — Performance Tuning and Benchmarking (4/5)  
**Platform:** Kubernetes + Strimzi Operator + Apache Kafka KRaft  
**Prerequisites:** Chapters 011–015, 021–025, 026–033; approved disposable Strimzi cluster and monitoring  
**Audience:** Kafka SRE, platform engineer, DBRE, performance engineer and on-call lead  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety boundary:** Broker tuning changes can cause cluster-wide outages. Use a dedicated, disposable Kafka cluster for all experiments. Do not restart production brokers, change JVM heaps, alter KafkaNodePool resources, delete PVCs, tune host kernel settings, reduce replication safety or edit KRaft controller configuration without a reviewed change and rollback plan. Do not infer production capacity from a single-node kind cluster. Internal plaintext examples are isolated-lab baselines only; production-like results require TLS/SASL.

## 1. Outcomes and acceptance criteria

This chapter teaches evidence-driven broker tuning, not copy-and-paste magic settings. By the end you can:

1. Trace Kafka broker request handling, page cache, disk append and replica fetch paths.
2. Distinguish broker throughput, produce/fetch latency, request queue time and network processor saturation.
3. Size JVM heap versus container memory, OS page cache and native overhead.
4. Interpret JVM GC pause, allocation and CPU throttling metrics.
5. Investigate `num.network.threads`, `num.io.threads`, socket buffers and request handler utilization.
6. Correlate broker PVC latency, IOPS, throughput, storage queue depth and retention/compaction activity.
7. Review partition/leader balance, ISR, quotas and broker hot spots.
8. Validate Strimzi KafkaNodePool resource changes with CRD/version checks and GitOps rollback.
9. Benchmark controlled baseline and one-variable tuning candidates under bounded load.
10. Produce a reproducible SRE performance report, runbooks and 100-point assessment.

**Critical acceptance:** no unapproved data-loss risk, no KRaft quorum loss, no ignored under-replicated partitions, and no false claim of live results.

## 2. Architecture: Kafka broker performance path

```text
Producer / Consumer Kubernetes Pods
   | TLS/SASL + TCP + advertised broker endpoints
   v
Kafka broker Pod (Strimzi KafkaNodePool)
   |
   +-- network processors / request queue
   +-- request handler threads / authorizer
   +-- partition leader / replica state
   +-- log append + OS page cache
   +-- PVC-backed log segments / disk IOPS
   +-- follower replication / ISR / acks=all
   +-- consumer fetch / page cache / disk reads
   |
   +-- JVM heap + GC / native memory
   +-- container CPU quotas + throttling
   +-- node network / storage / NUMA constraints
   |
   v
Metrics: request latency p95/p99, queue time,
        CPU, GC, page cache, network, disk,
        ISR, partition leaders, controller health
```

Kafka relies heavily on OS page cache for log I/O. Allocating all container memory to Java heap can starve page cache and degrade performance. Conversely, undersized heap can increase allocation/GC pressure. Measure both.

## 3. Core SRE metrics

| Metric | Interpretation | Investigation |
|---|---|---|
| `kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce` | Produce request total time | Separate queue, local, remote, response stages |
| `RequestQueueTimeMs` per request | Wait before handler execution | Network/IO handler saturation |
| `LocalTimeMs` per request | Broker local processing time | CPU, page cache, disk |
| `RemoteTimeMs` for Produce | Time waiting on replication when applicable | ISR/follower network/storage |
| `ResponseQueueTimeMs` | Wait to send response | Network processor pressure |
| `kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent` | Request handler idle fraction | Near-zero suggests saturation |
| `kafka.network:type=SocketServer,name=NetworkProcessorAvgIdlePercent` | Network processor idle fraction | Check per listener if available |
| `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` | Replica health | Any sustained rise is a stop signal |
| `kafka.server:type=ReplicaManager,name=UnderMinIsrPartitionCount` | Partitions below minimum ISR | Durability/availability critical |
| `kafka.controller:type=KafkaController,name=ActiveControllerCount` | Historical metric; KRaft instrumentation differs | Use KRaft-specific metrics in installed release |
| JVM GC pause / heap usage | Allocation and pause pressure | Correlate with client p99 |
| Container CPU throttling | CPU quota pressure | Distinguish from broker bottleneck |
| PVC read/write latency | Storage service time | Compare provider limits/credits |
| KRaft metadata quorum status | Controller liveness and voters | Never trade away quorum for throughput |

**Metric compatibility:** JMX object names, exporter mappings and KRaft/controller metrics vary by Kafka/Strimzi release. Validate actual exported series and labels; the names above describe investigation targets, not a guarantee that Prometheus exposes those exact strings.

## 4. Broker performance configuration families

| Family | Examples | Operational risk |
|---|---|---|
| Network processors | `num.network.threads`, socket receive/send buffers | CPU/context switching, listener behavior |
| Request handlers | `num.io.threads`, queued requests | Latency and queue pressure |
| Log/storage | `log.segment.bytes`, `log.retention.*`, `log.cleaner.*` | Retention, compaction and recovery behavior |
| Replication | `num.replica.fetchers`, replica fetch limits | ISR instability, inter-broker load |
| Quotas | Producer/consumer request and bandwidth quotas | Tenant fairness versus throttling |
| JVM | `-Xms`, `-Xmx`, GC logging and metrics | OOM, long pauses, page cache starvation |
| Kubernetes | CPU/memory requests/limits, Pod placement, PVC class | Scheduling, throttling, storage latency |
| Partition placement | Leader balance, hot partitions, skewed keys | Uneven CPU/network/disk usage |
| Security | TLS/SASL authentication and ACLs | CPU overhead and connection churn |

**Version-sensitive settings:** Kafka and Strimzi support dynamic versus restart-required settings differently. Verify Kafka config mutability and Strimzi CRD before applying; never assume a field is valid because it appears in another release's tutorial.

## 5. Capacity and reliability invariants

- Maintain RF3/minISR2 on synthetic benchmark topics unless a specific approved experiment justifies a change.
- Keep KRaft controller quorum healthy and isolate controller workloads from broker saturation where supported.
- Observe **all** broker Pods, not just a cluster average.
- Preserve JVM heap plus native memory, direct buffers and page cache headroom inside Pod/node budgets.
- Reserve disk space for log growth, segment rolling, recovery and compaction; retention is not an immediate free-space guarantee.
- Do not treat `kubectl top` as a source of CPU throttling, disk latency or page-cache evidence.
- Reconcile desired state through Strimzi/GitOps; direct Pod edits will be overwritten.
- Measure at identical offered load and workload characteristics; run repeated trials and preserve failures.

## 6. Lab 01 — Confirm cluster context, approvals and topology

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch34
kubectl config current-context | tee evidence-ch34/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch34/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch34/listeners.txt
```

**Acceptance:** disposable context, owner/change ticket, three eligible brokers for RF3, healthy controllers and storage headroom. **Abort:** wrong context, degraded ISR, no monitoring or insufficient rollback plan.

## 7. Lab 02 — Inspect Strimzi CRD and KafkaNodePool resources

```bash
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch34/kafka-crd.txt
kubectl get crd kafkanodepools.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch34/nodepool-crd.txt
kubectl -n kafka-lab get kafkanodepool -o yaml \
  > evidence-ch34/nodepools.yaml
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch34/kafka-cr.yaml
```

Review `KafkaNodePool.spec.resources`, `jvmOptions` placement for installed Strimzi version, node roles, storage, rack awareness and disruption behavior. Sanitize metadata before public sharing. **Acceptance:** supported tuning fields and restart implications documented.

## 8. Lab 03 — Baseline KRaft quorum, ISR and partition health

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch34/quorum.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 --list \
  | tee evidence-ch34/topics-before.txt
```

Capture KRaft leader/voters, ISR/under-minISR and leader counts from actual Kafka metrics. **Acceptance:** no pre-existing health violations.

## 9. Lab 04 — Inventory Pod CPU, memory and placement

```bash
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch34/pod-placement.txt
kubectl -n kafka-lab top pods \
  | tee evidence-ch34/pod-top.txt
kubectl top nodes | tee evidence-ch34/node-top.txt
kubectl -n kafka-lab describe pods \
  > evidence-ch34/pod-descriptions.txt
```

Inspect CPU requests/limits, throttling metrics, memory working set/RSS, OOMKills, node allocatable and co-located workloads. Metrics Server may be absent; use approved Prometheus/cAdvisor metrics instead. **Acceptance:** broker-by-broker utilization and resource constraints documented.

## 10. Lab 05 — JVM heap, GC and page-cache baseline

Record configured JVM heap and container memory budget via supported Strimzi resources and broker metrics. Use JMX exporter dashboards for heap used/max, GC pause time, allocation rate, thread count and direct buffer pools. For node page cache, use node-exporter or cloud OS telemetry with correct container/node attribution.

```bash
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.jvmOptions}{"\n"}' \
  | tee evidence-ch34/jvm-options.txt
kubectl -n kafka-lab get kafkanodepool \
  -o custom-columns=NAME:.metadata.name,CPU_REQUEST:.spec.resources.requests.cpu,MEM_REQUEST:.spec.resources.requests.memory,CPU_LIMIT:.spec.resources.limits.cpu,MEM_LIMIT:.spec.resources.limits.memory \
  | tee evidence-ch34/nodepool-resources.txt
```

**Acceptance:** documented heap-to-container budget and GC/OS memory observations. Avoid `jcmd`/heap dumps in production because they may expose sensitive data and add overhead.

## 11. Lab 06 — Provision bounded synthetic benchmark topic

Save `kafkatopic-broker-ch34.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-broker-perf-ch34
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 3600000
```

```bash
kubectl apply --dry-run=server -f kafkatopic-broker-ch34.yaml
# After approval in disposable cluster:
kubectl apply -f kafkatopic-broker-ch34.yaml
kubectl -n kafka-lab get kafkatopic sre-broker-perf-ch34 -o wide \
  | tee evidence-ch34/topic.txt
```

**Acceptance:** KafkaTopic Ready, RF3/minISR2 and synthetic data only.

## 12. Lab 07 — Baseline bounded producer workload

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic sre-broker-perf-ch34 \
  --num-records 100000 \
  --record-size 1024 \
  --throughput 1000 \
  --producer-props \
    bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
    acks=all \
    enable.idempotence=true \
  | tee evidence-ch34/producer-baseline.txt
```

**Acceptance:** successful bounded load with throughput, average/p95/p99 when reported, errors and per-broker metrics. A producer tool success is not proof of no cluster impact.

## 13. Lab 08 — Broker request queue and handler analysis

Capture request total time, queue time, local time, remote/replication time, response send time, request handler idle fraction and network processor idle fraction for Produce and Fetch during matched tests.

**Interpretation:** high queue time with low handler idle suggests saturation; high remote time can indicate replica lag; high local time may reflect storage or CPU. Correlation is not causation—cross-check disk/network/GC.

**Acceptance:** identify dominant latency stage using actual metric series and timestamps.

## 14. Lab 09 — Network thread sizing tabletop and controlled experiment

Inspect current `num.network.threads`, connection rates, network processor idle and TLS handshake overhead. Prepare a GitOps diff for a **small, supported** adjustment, but do not apply to a production cluster. Determine whether Strimzi reconciliation requires rolling broker restarts.

```bash
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.config}{"\n"}' \
  | tee evidence-ch34/broker-config.txt
```

**Acceptance:** approved test hypothesis and expected rollback. Only execute a live change on a disposable cluster with healthy ISR and verified operator behavior.

## 15. Lab 10 — I/O request handler tuning

Evaluate `num.io.threads` against request handler idle, CPU run queue, request queue latency and storage wait. More threads can increase context switching without increasing disk bandwidth. Change one setting at a time and rerun identical offered load.

**Acceptance:** before/after p99, handler idle, CPU and ISR evidence. Revert if no measurable improvement.

## 16. Lab 11 — JVM heap experiment

Prepare two compatible heap configurations for the **disposable** KafkaNodePool, respecting container memory and Strimzi-supported JVM configuration. Record effective `-Xms/-Xmx`, GC pause, allocation, page cache and broker readiness before and after an operator-managed rolling reconciliation.

**Do not** mutate a running broker's JVM options directly or force-delete Pods. **Acceptance:** improved/unchanged metrics with no OOM or quorum/ISR loss, and tested rollback.

## 17. Lab 12 — CPU limits and throttling

Compare a resource-safe baseline with a modest approved CPU budget change in the disposable broker node pool. Review:

- `container_cpu_cfs_throttled_seconds_total` or equivalent cgroup metrics.
- Broker CPU usage, request queue and p99 latency.
- Node allocatable, noisy neighbors and scheduler placement.
- Operator reconciliation and Pod restart implications.

**Acceptance:** throttling evidence and resource headroom; no claim that removing CPU limits is universally safe.

## 18. Lab 13 — Storage IOPS, latency and PVC behavior

```bash
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch34/pvcs.txt
kubectl get storageclass \
  | tee evidence-ch34/storageclasses.txt
kubectl -n kafka-lab get kafkanodepool \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.storage}{"\n"}{end}' \
  | tee evidence-ch34/storage-config.txt
```

Correlate broker disk write/read latency, cloud IOPS/bandwidth limits, volume burst credits, disk queue depth and log growth. Do not delete or replace existing broker PVCs to test storage classes. **Acceptance:** storage bottleneck or adequate headroom supported by metrics.

## 19. Lab 14 — Page cache and sustained-load sensitivity

Compare a short warm-cache run to a longer bounded sustained test with the same rate, subject to disk and cluster abort thresholds. Inspect page cache, broker heap, disk reads, GC and retention effects. Never run `drop_caches` on a shared host or deliberately fill disks.

**Acceptance:** explain cache-related variance and avoid generalizing from short synthetic trials.

## 20. Lab 15 — Partition leader distribution and hot partitions

Describe synthetic topic partition leaders and replicas:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-broker-perf-ch34 \
  | tee evidence-ch34/partition-layout.txt
```

Correlate per-broker produce bytes, CPU and leader count. Test balanced versus intentionally skewed synthetic keys **without reassigning production partitions**. **Acceptance:** hot-leader diagnosis and partition-key remediation proposal.

## 21. Lab 16 — Replication and follower fetch pressure

Measure follower fetch latency, replica lag, ISR shrink/expand, inter-broker traffic and Produce remote time under bounded load. Review `num.replica.fetchers` only after confirming network/storage bottlenecks and supported config semantics.

**Abort immediately** if sustained under-replication, under-minISR or controller quorum instability occurs. **Acceptance:** replication headroom quantified without durability weakening.

## 22. Lab 17 — Quotas and tenant fairness

Use two synthetic producer identities/topics with approved Kafka quotas and separate metrics. Compare a throttled tenant to an unthrottled tenant, distinguishing deliberate quota throttling from resource saturation. Do not alter production user/client quotas.

**Acceptance:** observed quota behavior, per-tenant fairness and no uncontrolled cross-tenant impact.

## 23. Lab 18 — TLS/SASL broker overhead

Repeat a bounded subset on a secure listener obtained from `Kafka.status.listeners`. Use approved Secret-mounted credentials and CA bundles; preserve hostname verification and Kafka ACLs. Measure TLS handshake/connection churn, broker CPU and steady-state Produce/Fetch p99.

**Acceptance:** matched secure/plaintext trial analysis or Pending if no supported secure listener exists. Never disable encryption for production performance.

## 24. Lab 19 — GitOps canary and rollback

For an approved disposable-cluster broker tuning candidate:

1. Capture baseline Kafka/KafkaNodePool manifests and resource versions.
2. Verify target CRD schema and Strimzi release notes.
3. Prepare minimal GitOps PR changing one parameter.
4. Perform server-side dry-run where applicable; review resulting diff.
5. Confirm operator reconciliation and whether rolling restart is required.
6. Apply only after change approval and observe each broker.
7. Validate KRaft quorum, ISR, latency and CPU/disk metrics.
8. Revert via GitOps if thresholds fail; do not patch Pod templates directly.

**Acceptance:** reproducible diff, canary metrics, rollback evidence and reviewer signoff.

## 25. Lab 20 — Read-only broker performance preflight

Save `verify-ch34.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/10] Context'
kubectl config current-context

echo '[2/10] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/10] Kafka/NodePool inventory'
kubectl -n "$NS" get kafka,kafkanodepool -o wide

echo '[4/10] CRD served versions'
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'
kubectl get crd kafkanodepools.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'

echo '[5/10] Kafka listeners'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[6/10] Pod placement'
kubectl -n "$NS" get pods -o wide

echo '[7/10] PVCs and StorageClasses'
kubectl -n "$NS" get pvc -o wide
kubectl get storageclass

echo '[8/10] Broker config'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.config}{"\n"}'

echo '[9/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[10/10] Synthetic topic (optional)'
if kubectl -n "$NS" get kafkatopic sre-broker-perf-ch34 >/dev/null 2>&1; then
  kubectl -n "$NS" get kafkatopic sre-broker-perf-ch34 -o wide
else
  echo 'PENDING: synthetic benchmark topic not provisioned'
fi

echo 'PASS: read-only broker/Kubernetes inventory preflight.'
echo 'NOT PROVEN: throughput, JVM/GC performance, storage headroom, ISR under load or tuning acceptance.'
```

```bash
chmod +x verify-ch34.sh
./verify-ch34.sh | tee evidence-ch34/preflight.txt
```

**Note:** This script intentionally makes no broker configuration changes and generates no load. A PASS is a prerequisite, not a performance result.

## 26. Twelve failure scenarios

### 26.1 Produce p99 spikes with high request queue time
**Inspect:** request handler idle, CPU throttling and queued requests. **Recover:** remove bottleneck before increasing threads.

### 26.2 Network processor idle near zero
**Inspect:** connection churn, TLS handshakes, network threads and node bandwidth. **Recover:** connection reuse, capacity and measured tuning.

### 26.3 JVM GC pause correlates with producer timeouts
**Inspect:** heap occupancy, allocation, GC pause and container limits. **Recover:** approved heap/GC change with page-cache headroom.

### 26.4 Broker Pod OOMKilled after heap increase
**Inspect:** native/direct buffers, heap and cgroup memory. **Recover:** revert via Strimzi, restore quorum/ISR.

### 26.5 CPU throttling mimics disk saturation
**Inspect:** cgroup throttling and disk latency separately. **Recover:** rightsize CPU after verifying node capacity.

### 26.6 PVC write latency increases under sustained load
**Inspect:** IOPS limits, cloud burst credits, queue depth. **Recover:** reduce load and plan approved storage capacity.

### 26.7 Hot partition overloads one broker
**Inspect:** leader bytes, key skew and client partitioner. **Recover:** application key redesign or reviewed partition strategy.

### 26.8 Under-replicated partitions rise after tuning
**Inspect:** follower fetch, network, storage and restarts. **Recover:** abort test and restore replica health.

### 26.9 Quota throttling mistaken for broker failure
**Inspect:** client throttle time and configured quotas. **Recover:** correct workload expectations or approved quota.

### 26.10 TLS listener CPU rises after client connection churn
**Inspect:** handshakes, authentication and socket reuse. **Recover:** optimize clients without disabling security.

### 26.11 Strimzi reconciliation rolls brokers unexpectedly
**Inspect:** Kafka/KafkaNodePool diff and operator events. **Recover:** freeze changes, monitor rolling health and revert approved change.

### 26.12 KRaft controller quorum degrades during load
**Inspect:** controller Pod health, network/storage and broker resource contention. **Recover:** stop load immediately and follow KRaft incident runbook.

## 27. Eight production runbooks

### Runbook A — Broker request latency incident
1. Identify affected brokers and request types.
2. Break total latency into queue/local/remote/response components.
3. Check handler idle, CPU throttling, GC and storage.
4. Inspect ISR, leader balance and client retry amplification.
5. Restore last known good config or capacity.
6. Verify p99, errors and durability.

### Runbook B — JVM/GC pressure
1. Confirm heap/GC symptoms and cgroup memory.
2. Inspect allocation, direct buffers and page cache.
3. Review recent Strimzi JVM/resource changes.
4. Prepare version-compatible change and rollback.
5. Apply only through approved operator workflow.
6. Validate GC, p99 and broker readiness.

### Runbook C — Broker CPU saturation
1. Identify busiest broker and hot partitions.
2. Compare CPU usage to throttling and node allocatable.
3. Check TLS handshakes, compression and request handlers.
4. Reduce unsafe synthetic load if necessary.
5. Right-size resources or redistribute workload by approved plan.
6. Validate SLO and cluster balance.

### Runbook D — Storage latency degradation
1. Check PVC fullness, disk latency, IOPS and queue depth.
2. Correlate with log append, fetch and compaction.
3. Stop benchmark if headroom is insufficient.
4. Plan storage performance/capacity remediation.
5. Use supported Strimzi storage workflows; do not delete PVCs.
6. Verify replica catch-up and stable p99.

### Runbook E — ISR and replication pressure
1. Stop load if under-minISR or sustained under-replication appears.
2. Inspect follower fetch, inter-broker network and storage.
3. Verify KRaft quorum and broker health.
4. Restore replica connectivity and catch-up.
5. Resume only after explicit approval.
6. Record durability risk and corrective action.

### Runbook F — Broker configuration rollout
1. Review Kafka/Strimzi version compatibility and CRD.
2. Baseline broker metrics and KRaft/ISR health.
3. Approve minimal GitOps change with restart implications.
4. Monitor operator-managed reconciliation and each broker.
5. Revert on abort criteria.
6. Confirm performance improvement and no security regression.

### Runbook G — Tenant quota and noisy-neighbor incident
1. Identify impacted principals, client IDs and topics.
2. Check quota throttle metrics and per-broker utilization.
3. Separate deliberate throttling from resource contention.
4. Apply least-privilege, approved quota/capacity change.
5. Validate unaffected tenant SLOs.
6. Document fairness policy and review schedule.

### Runbook H — Broker performance game day
1. Obtain approval and record capacity baseline.
2. Run bounded producer/consumer load.
3. Correlate queue/GC/CPU/storage/ISR metrics.
4. Test one tuning hypothesis at a time.
5. Reconcile GitOps and demonstrate rollback.
6. Publish evidence and independent acceptance.

## 28. Evidence package

```text
evidence-ch34/
  approval-and-scope.md
  context.txt
  inventory.txt
  listeners.txt
  kafka-crd.txt
  nodepool-crd.txt
  nodepools.yaml
  kafka-cr.yaml
  quorum.txt
  topics-before.txt
  pod-placement.txt
  pod-top.txt
  node-top.txt
  pod-descriptions.txt
  jvm-options.txt
  nodepool-resources.txt
  topic.txt
  producer-baseline.txt
  broker-request-metrics.csv
  network-thread-hypothesis.md
  io-thread-trials.csv
  jvm-heap-trials.csv
  cpu-throttling.csv
  pvcs.txt
  storageclasses.txt
  storage-config.txt
  page-cache-trials.csv
  partition-layout.txt
  replica-health.csv
  tenant-quota-trials.csv
  tls-sasl-trials.csv
  gitops-change-review.md
  gitops-rollback.md
  preflight.txt
  broker-performance-report.md
  incident-review.md
  assessor-signoff.md
```

Record versions, configuration hashes, Pod placement, security mode, offered/achieved load, request p95/p99, CPU/GC, storage, ISR, KRaft health, errors and reviewers. Sanitized evidence only; never publish credentials, private keys, production payloads or unrestricted infrastructure secrets. All unexecuted measurements remain **Pending**.

## 29. 100-point enterprise broker tuning assessment

| Domain | Points | Gate |
|---|---:|---|
| Approval, isolation and safety gates | 10 | Critical |
| Kafka/Strimzi/KRaft baseline | 10 | Critical |
| Request queue/handler latency analysis | 15 | Critical |
| JVM heap, GC and page-cache assessment | 15 | Critical |
| Network and I/O thread experiments | 10 | Normal |
| Kubernetes CPU/memory and Pod placement | 10 | Critical |
| PVC IOPS, latency and storage analysis | 10 | Critical |
| Partition/replication/ISR health | 10 | Critical |
| Secure listener and tenant quota review | 5 | Critical |
| GitOps rollback, evidence and independent signoff | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates passed with evidence. **Automatic Fail:** unapproved production tuning, disabling TLS verification, quorum loss ignored, deliberate RF/minISR weakening, deletion of broker PVCs, fabricated performance measurements or unsafe operator reconciliation.

## 30. Cleanup, references and next chapter

Remove only chapter-owned synthetic KafkaTopics, benchmark Jobs and diagnostic Pods after approval. Retain sanitized evidence. Do not delete broker PVCs, shared topics, KafkaNodePools or operator-managed Secrets as a cleanup shortcut.

**References:** [Apache Kafka Operations](https://kafka.apache.org/documentation/#operations), [Apache Kafka Broker Configurations](https://kafka.apache.org/documentation/#brokerconfigs), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [Kubernetes Storage](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 035 — Kafka End-to-End Performance Benchmarking, Capacity Acceptance and Kubernetes SRE Capstone.

---

**Verification boundary:** GitHub publication confirms document availability only. Broker tuning changes, JVM/GC analysis, performance acceptance and independent security review remain Pending until live evidence is collected.
