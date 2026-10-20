# Chapter 031 — Kafka Performance Fundamentals, Throughput, Latency and Kubernetes Benchmarking

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 07 — Performance Tuning and Benchmarking (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft Kafka  
**Prerequisites:** Chapters 001–030, especially partition leadership, replication, storage, security and observability  
**Audience:** Kafka SREs, performance engineers, DBREs, platform engineers and application owners  
**Publication:** Published · **Live lab execution:** Pending · **Independent review:** Pending

> **Safety:** All load tests run against an approved disposable cluster and dedicated synthetic topics. Never benchmark a production cluster without an explicit change window, capacity reservation, abort thresholds and owner approval. Benchmark clients consume CPU, network and memory; uncontrolled tests can cause ISR loss, disk exhaustion, tenant impact and unexpected cloud costs. The tutorial's internal plaintext bootstrap on 9092 is an isolated lab baseline only. Production-like performance results must be repeated using approved TLS/SASL listeners.

## 1. Objectives and measurable outcomes

After this chapter, you can:

1. Define throughput, latency, percentile, offered load, achieved load and saturation.
2. Explain Kafka's producer → broker → disk/replication → consumer critical path.
3. Design a reproducible Kubernetes-first benchmark without conflating client and broker bottlenecks.
4. Use Kafka producer and consumer performance tools from isolated Kubernetes Pods.
5. Control message size, partition count, compression, batching, acknowledgments and concurrency.
6. Correlate throughput and latency with CPU, network, disk, page cache, ISR and consumer lag.
7. Separate warm-up, steady state and cool-down; avoid misleading aggregate averages.
8. Quantify replication, TLS/SASL and storage trade-offs.
9. Detect saturation, protect cluster health and stop tests safely.
10. Produce an evidence-backed performance baseline and 100-point assessment.

**Key outcome:** a versioned performance report with achieved MB/s, records/s, p50/p95/p99 latency, error rate, consumer catch-up, resource utilization and an explicit bottleneck hypothesis.

## 2. Kafka performance model

```text
Synthetic producer Pods
   | serialize / compress / batch
   v
Kubernetes DNS + Service + advertised broker endpoints
   | TCP + TLS/SASL (when configured)
   v
Partition leader broker
   | request processing / page cache / local log append
   +--> follower replication / ISR / acks=all
   |
   v
Kafka log segments on PVC / storage backend
   |
   v
Consumer Pods
   | fetch / decompress / deserialize / process
   v
Observed throughput, lag and end-to-end latency

Supporting paths: KRaft metadata quorum, network/CNI, node CPU,
memory, disk IOPS, storage latency, Kubernetes scheduling and quotas.
```

**Throughput** is data or records processed per unit time; **latency** is elapsed time per request or record. Higher throughput does not guarantee lower p99 latency. At saturation, queuing, retries and tail latency can increase sharply.

## 3. Definitions and formulas

| Metric | Formula / interpretation | Caveat |
|---|---|---|
| Producer throughput (records/s) | Successful records / elapsed seconds | Exclude failed records |
| Producer throughput (MiB/s) | Successful payload bytes / 1,048,576 / elapsed seconds | Distinguish payload from wire bytes |
| Request latency | Client send → acknowledgment | Depends on acks and retries |
| End-to-end latency | Event creation → consumer processing | Requires synchronized clocks and trace IDs |
| p95 / p99 latency | 95th / 99th percentile of observations | Do not infer from mean |
| Consumer throughput | Successfully processed records / time | Processing workload matters |
| Consumer lag | Latest log offset − committed/processed offset | Interpretation depends on client and metrics |
| Utilization | Resource demand / available capacity | CPU, network, IOPS, quotas |
| Error rate | Failed operations / total attempts | Count timeouts/retries explicitly |
| Replication factor | Number of partition replicas | Not equivalent to available ISR |

**Units:** label MB versus MiB and MB/s versus Mbit/s. The Kafka performance CLI may report throughput in MB/sec with tool-specific conventions; record the exact version and units rather than silently converting.

## 4. Benchmark experimental design

A credible experiment varies **one primary factor at a time**, unless explicitly testing interactions. Fix:

- Kafka/Strimzi/Kubernetes versions and configuration hashes.
- Number of brokers, controller roles, nodes, zones and storage classes.
- RF, minISR, partitions and topic retention.
- Producer count, threads, key distribution, message size and compression.
- Producer `acks`, idempotence, retries, batching and linger.
- Consumer group size, fetch settings and application processing cost.
- Security listener and protocol.
- Benchmark Pod CPU/memory requests/limits, node placement and network topology.
- Warm-up duration, measured duration, repetition count and test order.

Run at least three comparable trials for each scenario where practical; report medians and variance, not only the best result. **Do not compare** TLS-enabled production workloads to a plaintext lab test as though they were equivalent.

## 5. Baseline topology and capacity gates

Recommended disposable starting point: three Kafka brokers, separate KRaft controllers where supported, three partitions per synthetic topic, RF3/minISR2, persistent volumes and a dedicated benchmark client workload. A single-node kind cluster is useful for functional testing, **not representative throughput**.

Check:

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch31
kubectl config current-context | tee evidence-ch31/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch31/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl get nodes -o wide | tee evidence-ch31/nodes.txt
kubectl -n "$NS" get resourcequota,limitrange \
  | tee evidence-ch31/quotas.txt
```

**Stop** if cluster is shared, disks are nearly full, Kafka is not Ready, ISR is degraded, node capacity is insufficient, or test approval is missing.

## 6. Lab 01 — Inventory Kafka and Strimzi versions

```bash
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch31/kafka-cr.yaml
kubectl -n kafka-lab get kafkanodepool -o wide \
  | tee evidence-ch31/nodepools.txt
kubectl -n kafka-lab get svc -l strimzi.io/cluster=sre-kafka -o wide \
  | tee evidence-ch31/services.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch31/pods.txt
```

Sanitize CR metadata and internal addresses before public publication. Capture Kafka binary version from an approved CLI Pod:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh --version \
  | tee evidence-ch31/kafka-client-version.txt
```

**Acceptance:** exact topology, client version and resource requests documented.

## 7. Lab 02 — Baseline broker health and replication

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch31/quorum.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 --list \
  | tee evidence-ch31/topics-before.txt
```

Collect real broker under-replicated partition and ISR metrics from the deployed monitoring stack. Kafka Ready alone does not guarantee zero under-replicated partitions. **Acceptance:** healthy quorum and replication baseline with no pre-existing alert violations.

## 8. Lab 03 — Provision a synthetic performance topic

Save `kafkatopic-perf-ch31.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-perf-ch31
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 3600000
```

```bash
kubectl apply --dry-run=server -f kafkatopic-perf-ch31.yaml
# After approval:
kubectl apply -f kafkatopic-perf-ch31.yaml
kubectl -n kafka-lab get kafkatopic sre-perf-ch31 -o wide \
  | tee evidence-ch31/topic-ready.txt
```

**Acceptance:** KafkaTopic reconciled and ready, no production topics involved. RF3 requires at least three eligible brokers.

## 9. Lab 04 — Validate benchmark Pod isolation

Use the existing `kafka-cli` Pod only if it has approved capacity and appropriate client tooling. Prefer a **dedicated benchmark Pod or Kubernetes Job** using an immutable image digest, non-root security context, restricted ServiceAccount, resource requests/limits and approved node placement. An illustrative Job template:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kafka-perf-ch31
  namespace: kafka-lab
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      serviceAccountName: approved-kafka-benchmark
      containers:
        - name: benchmark
          image: <PINNED_APPROVED_KAFKA_IMAGE>
          command: ["/bin/sh", "-ec"]
          args:
            - |
              echo "Replace with an approved bounded Kafka benchmark command"
          resources:
            requests:
              cpu: "500m"
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
```

This template is **not directly runnable** until the approved image, ServiceAccount and command are supplied. Validate the image includes Kafka CLI tools and that it is compatible with cluster security requirements.

**Acceptance:** benchmark clients isolated from brokers, no uncontrolled resource contention.

## 10. Lab 05 — Producer throughput baseline

Use Kafka's bundled producer performance tool from an approved benchmark Pod:

```bash
/opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic sre-perf-ch31 \
  --num-records 100000 \
  --record-size 1024 \
  --throughput 2000 \
  --producer-props \
    bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
    acks=all \
    enable.idempotence=true \
    compression.type=none \
    linger.ms=0 \
    batch.size=16384
```

**Safety:** the `--throughput` value is a target cap in records/s, not guaranteed achieved rate. Adjust cap, record count and payload size downward for small clusters. Kafka tool flags can change across releases; check `--help` on the installed binary.

Record output throughput, average latency, p50/p95/p99 where reported, errors and elapsed time. The baseline uses isolated plaintext only; repeat with secure `SASL_SSL` and a protected `--producer.config` file for production-like claims.

## 11. Lab 06 — Controlled throughput sweep

Use three bounded producer rates, for example 500, 1,000 and 2,000 records/s at 1 KiB, keeping all other variables fixed. Ensure record count and test duration are comparable. Record:

| Trial | Target records/s | Achieved records/s | MiB/s | p95 | p99 | Errors | Broker CPU |
|---|---:|---:|---:|---:|---:|---:|---:|
| Low | 500 | Pending | Pending | Pending | Pending | Pending | Pending |
| Medium | 1,000 | Pending | Pending | Pending | Pending | Pending | Pending |
| High | 2,000 | Pending | Pending | Pending | Pending | Pending | Pending |

**Acceptance:** identify where achieved throughput no longer follows offered load, without triggering cluster health abort thresholds.

## 12. Lab 07 — Message-size sensitivity

Repeat with fixed total payload budget where possible and vary message sizes, for example 256 B, 1 KiB and 16 KiB. Compare records/s **and** MiB/s; small messages can be CPU/request dominated, larger messages network/storage dominated. Respect Kafka `max.message.bytes`, client `max.request.size` and batch configuration.

**Acceptance:** separate per-record overhead from payload bandwidth, with explicit unit conversions.

## 13. Lab 08 — Producer acknowledgments and durability trade-offs

Compare **only in the disposable lab**:

- `acks=all`, `min.insync.replicas=2`, RF3: durability-oriented baseline.
- `acks=1`: lower acknowledgment requirements but different data-loss risk.
- Optional `acks=0`: fire-and-forget behavior; not a valid durability or success-count comparison.

Do not call `acks=0` "successful delivery" because the producer does not receive broker acknowledgments. Do not recommend weakening `acks` to resolve a production SLO without an explicit reliability decision.

**Acceptance:** quantified latency/throughput difference and a written durability impact statement.

## 14. Lab 09 — Batching and linger experiment

Vary one setting at a time:

| Setting | Baseline | Experiment | Hypothesis |
|---|---:|---:|---|
| `linger.ms` | 0 | 5 / 20 | More batching, potentially higher low-load latency |
| `batch.size` | 16 KiB | 64 / 128 KiB | More efficient batch use under load |
| `compression.type` | none | lz4 / zstd | Lower network bytes at CPU cost |

Kafka versions may support adaptive linger defaults and additional compression behavior; explicitly set values and record versions. Compression results depend on payload entropy. The standard producer performance tool uses generated data; to test realistic compressibility, use a synthetic workload with controlled entropy and documented generation.

**Acceptance:** throughput, latency, CPU and wire-byte observations for each configuration.

## 15. Lab 10 — Partition-count scaling

Create **separate disposable topics** with 3, 6 and 12 partitions and RF3/minISR2. Keep broker count and producer load fixed; use enough producer keys/concurrency to distribute traffic. Do not repeatedly change partition count on a topic with keyed records if key-to-partition stability matters.

**Acceptance:** identify throughput scaling, broker/leader distribution and the point of diminishing returns. More partitions increase metadata, open files, replication and operational overhead.

## 16. Lab 11 — Producer concurrency and client bottlenecks

Compare one producer process versus multiple independent benchmark Pods. Keep **aggregate offered load** constant when comparing efficiency, then increase load only in a separate scaling experiment.

Observe client CPU throttling, GC, connection count, node placement and network utilization. A client-side CPU limit can create a false Kafka bottleneck.

**Acceptance:** evidence that client resources were not the limiting factor—or a documented client bottleneck.

## 17. Lab 12 — Consumer throughput and catch-up

Use Kafka's consumer performance tool, checking version-specific flags:

```bash
/opt/kafka/bin/kafka-consumer-perf-test.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-perf-ch31 \
  --messages 10000 \
  --group sre-perf-consumer-ch31 \
  --timeout 30000
```

Consumer perf CLI flags and group behavior vary by Kafka version; verify `--help`. Produce sufficient synthetic records first and use a **fresh consumer group** per trial to avoid offset reuse. This measures fetch/consume throughput, **not full application processing**. For secure listeners supply the appropriate consumer configuration using supported flags.

**Acceptance:** consumer records/s, MB/s, elapsed time, lag and processing limitations recorded.

## 18. Lab 13 — Consumer parallelism and partitions

Test 1, 3 and 6 consumers against a three-partition topic. Within a single consumer group, at most three consumers can own partitions at once in the standard group assignment model; extra consumers can be idle. Rebalances and assignment strategies affect measurements.

**Acceptance:** observed active assignments, throughput and rebalance cost; no claim of linear scaling beyond partitions.

## 19. Lab 14 — Kubernetes CPU throttling and memory pressure

```bash
kubectl -n kafka-lab top pods \
  | tee evidence-ch31/pod-top.txt
kubectl top nodes | tee evidence-ch31/node-top.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch31/pod-placement.txt
```

Metrics Server may not be installed; absence is a monitoring gap, not proof of low usage. Use Prometheus/cAdvisor or cloud metrics to inspect CPU throttling, memory RSS, GC pauses, network retransmissions and Pod restarts. Do not intentionally OOM broker Pods.

**Acceptance:** resource saturation analysis for clients and brokers, with actual observed metrics.

## 20. Lab 15 — Storage latency and PVC behavior

Inventory PVCs and StorageClasses:

```bash
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch31/pvcs.txt
kubectl get storageclass \
  | tee evidence-ch31/storageclasses.txt
```

Collect storage latency, IOPS, queue depth, throughput and volume burst/credit metrics from the provider. Broker page cache can hide disk limitations in short tests; sustained tests and cache effects must be documented. Never drop Linux caches or fill production PVCs to force a result.

**Acceptance:** correlation between broker write/read behavior and underlying storage capability.

## 21. Lab 16 — Replication, ISR and inter-broker network

Track under-replicated partitions, ISR shrink/expand, leader changes, replication fetch latency and inter-broker traffic during increasing load. Keep `acks=all` and minISR2 for the durability-oriented baseline.

**Abort** on sustained under-replication, KRaft quorum degradation or unexpected broker restarts. **Acceptance:** replication headroom measured without destructive fault injection.

## 22. Lab 17 — TLS/SASL performance overhead

Repeat a subset of benchmarks on an approved TLS/SASL listener using a secure client config stored in a restricted mounted Secret or ephemeral file. Compare only otherwise equivalent topology, offered load and client resource allocations.

Separate handshake/connection setup costs from steady-state throughput and include certificate/identity validation. Do not disable hostname verification to improve results.

**Acceptance:** measured secure-listener overhead or Pending if no secure listener is available.

## 23. Lab 18 — Kubernetes placement and noisy-neighbor review

Inspect broker and benchmark Pod node placement, topology spread, anti-affinity, node pool CPU/network limits and storage attachment zones. Design a controlled placement comparison **without moving live broker PVCs or restarting brokers**. Test client placement in the disposable cluster and record network topology.

**Acceptance:** evidence-backed hypothesis for cross-zone latency, node contention or benchmark-client placement bias.

## 24. Lab 19 — Repeatability and statistical reporting

Run each approved scenario at least three times with fixed parameters, randomized or balanced order when practical, and recorded warm-up. Compute median throughput, p95/p99 latency per trial and variation across trials.

**Important:** averaging p99 values from multiple runs does not yield a globally correct p99; retain distributions or report per-run p99 with a stated aggregation rule. Do not silently discard failed or slow runs.

**Acceptance:** reproducible result table, variance, confidence limits and known biases.

## 25. Lab 20 — Read-only performance preflight script

Save `verify-ch31.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/8] Kubernetes context'
kubectl config current-context

echo '[2/8] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/8] Kafka/KafkaNodePool inventory'
kubectl -n "$NS" get kafka,kafkanodepool -o wide

echo '[4/8] Broker and client Pod placement'
kubectl -n "$NS" get pods -o wide

echo '[5/8] PVC and StorageClass inventory'
kubectl -n "$NS" get pvc -o wide
kubectl get storageclass

echo '[6/8] Services and listener status'
kubectl -n "$NS" get svc -l "strimzi.io/cluster=$CLUSTER"
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[7/8] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[8/8] Benchmark binary availability'
kubectl -n "$NS" exec kafka-cli -- \
  sh -c 'test -x /opt/kafka/bin/kafka-producer-perf-test.sh && test -x /opt/kafka/bin/kafka-consumer-perf-test.sh'

echo 'PASS: read-only platform and tooling preflight.'
echo 'NOT PROVEN: load performance, ISR stability under load, TLS overhead or benchmark repeatability.'
```

```bash
chmod +x verify-ch31.sh
./verify-ch31.sh | tee evidence-ch31/preflight.txt
```

The `sh` check assumes the CLI Pod includes a shell; adapt if the image is distroless. This script does not generate load or establish performance acceptance.

## 26. Automated benchmark harness design

For repeatable test execution, parameterize the following **without storing secrets in CLI flags**:

```text
KAFKA_BOOTSTRAP=<secure listener from Kafka status>
TOPIC=sre-perf-ch31
NUM_RECORDS=100000
RECORD_SIZE=1024
TARGET_RECORDS_PER_SEC=2000
ACKS=all
COMPRESSION=none
LINGER_MS=0
BATCH_SIZE=16384
TRIAL_ID=ch31-001
CLIENT_CONFIG=/etc/kafka/client.properties
```

The harness should validate all inputs, reject non-allowlisted cluster contexts, record exact command and tool versions, enforce bounded timeouts, capture exit codes, stop on SLO abort thresholds, and produce machine-readable trial results. Kafka perf tool output is not guaranteed to be stable JSON; parse conservatively or preserve raw output and transform with version-specific parsers.

**Do not** claim automated abort-on-ISR behavior unless the harness actually polls a trusted monitoring endpoint and terminates tests.

## 27. Twelve troubleshooting scenarios

### 27.1 High p99 latency with normal average
**Check:** queueing, GC, network retransmits, storage latency and retries. **Action:** identify tail source before tuning batch/linger.

### 27.2 Offered load rises but achieved throughput plateaus
**Check:** client CPU, broker CPU, disk throughput, quotas, network bandwidth. **Action:** find saturated resource and rerun controlled trial.

### 27.3 Producer performance tool reports high throughput but application is slow
**Check:** serialization, payload compressibility, transactions, security, application processing. **Action:** reproduce realistic workload.

### 27.4 `acks=all` latency spikes
**Check:** ISR, follower fetch latency, inter-broker network and storage. **Action:** restore replication health; do not weaken durability reflexively.

### 27.5 Consumer lag grows while producer throughput is steady
**Check:** group assignments, fetch limits, processing bottleneck, rebalances. **Action:** scale within partition limits or optimize processing.

### 27.6 CPU throttling in benchmark Pod
**Check:** Pod limits and CFS throttling metrics. **Action:** allocate dedicated client capacity; rerun before blaming brokers.

### 27.7 Broker GC pauses during test
**Check:** heap, allocation, page cache, memory pressure. **Action:** correlate JVM and host metrics; avoid arbitrary heap changes.

### 27.8 Disk write latency climbs under sustained load
**Check:** PVC IOPS, cloud burst credits, queue depth and log flush behavior. **Action:** assess storage tier and capacity.

### 27.9 Compression improves network but hurts throughput
**Check:** CPU saturation and payload entropy. **Action:** compare codecs at equivalent offered load.

### 27.10 Increasing partitions reduces efficiency
**Check:** metadata overhead, file descriptors, leader balance and client concurrency. **Action:** select measured partition count.

### 27.11 TLS/SASL trial unexpectedly faster than plaintext
**Check:** test order, warm-up, client placement, load and caching. **Action:** rerun matched controlled experiments.

### 27.12 Performance run destabilizes KRaft/ISR
**Check:** broker/controller resource contention and network/storage saturation. **Action:** stop load immediately, restore cluster health and file incident evidence.

## 28. Eight SRE runbooks

### Runbook A — Benchmark preflight and approval
1. Confirm disposable context and owner approval.
2. Verify Kafka Ready, quorum, ISR, PVC headroom and metrics.
3. Reserve client CPU/network capacity and document security mode.
4. Establish abort thresholds and rollback.
5. Execute low-rate smoke trial first.
6. Capture baseline evidence and proceed only if healthy.

### Runbook B — Producer latency regression
1. Identify affected producer cohort and p95/p99.
2. Correlate client retries, batching, acks and broker metrics.
3. Check ISR, storage and network health.
4. Compare last known good configuration.
5. Apply one approved change at a time.
6. Verify tail latency and durability after rollback/tuning.

### Runbook C — Throughput saturation
1. Confirm offered versus achieved throughput.
2. Separate client and broker utilization.
3. Inspect CPU, disk, network, quotas and partition leadership.
4. Change one factor in disposable test.
5. Re-run controlled trials with same workload.
6. Document bottleneck and capacity recommendation.

### Runbook D — Consumer lag during peak load
1. Verify producer ingress and lag trend.
2. Inspect consumer group membership and assignments.
3. Check fetch and application processing bottlenecks.
4. Scale consumers only within effective partition parallelism.
5. Validate backlog drain and event-age SLO.
6. Record steady-state capacity and recovery headroom.

### Runbook E — Storage performance degradation
1. Identify affected brokers/PVCs.
2. Check IOPS, latency, queue depth and cloud storage limits.
3. Inspect Kafka retention, compaction and page-cache behavior.
4. Stop synthetic load if thresholds exceeded.
5. Plan storage/capacity changes through approved Strimzi workflows.
6. Verify recovery without deleting broker data.

### Runbook F — Replication/ISR pressure
1. Stop benchmark load on ISR/under-replication alerts.
2. Check broker readiness, follower fetch and inter-broker links.
3. Verify KRaft quorum and leader stability.
4. Restore replication headroom.
5. Re-run only after explicit SRE approval.
6. Preserve timeline and prevent recurrence.

### Runbook G — Secure-listener performance regression
1. Compare matched TLS/SASL and plaintext trials.
2. Inspect handshake rates, client connection churn and authentication errors.
3. Check certificate/identity configuration without disabling verification.
4. Evaluate connection pooling and client CPU.
5. Rerun controlled secure tests.
6. Report overhead and security trade-offs accurately.

### Runbook H — Performance game day and acceptance
1. Agree workload, targets and safety thresholds.
2. Capture baseline metrics and client configuration.
3. Run rate, message-size and concurrency sweeps.
4. Classify bottlenecks and stop on abort criteria.
5. Validate consumer catch-up and Kafka health.
6. Publish results, open issues and independent signoff.

## 29. Performance evidence package

```text
evidence-ch31/
  approval-and-scope.md
  context.txt
  inventory.txt
  nodes.txt
  quotas.txt
  kafka-cr.yaml
  nodepools.txt
  services.txt
  pods.txt
  kafka-client-version.txt
  quorum.txt
  topics-before.txt
  topic-ready.txt
  benchmark-client-spec.yaml
  producer-baseline.txt
  throughput-sweep.csv
  message-size-trials.csv
  acks-comparison.md
  batching-compression.csv
  partition-scaling.csv
  producer-concurrency.csv
  consumer-throughput.txt
  consumer-parallelism.md
  pod-top.txt
  node-top.txt
  pod-placement.txt
  pvcs.txt
  storageclasses.txt
  replication-health.md
  tls-sasl-comparison.md
  placement-review.md
  repeated-trials.csv
  preflight.txt
  benchmark-report.md
  incident-review.md
  assessor-signoff.md
```

Each trial needs timestamp, duration, environment fingerprint, command/config hash, offered and achieved rate, successful records, latency percentiles, errors, broker/client resource observations, Kafka health and reviewer. Mark unexecuted sections **Pending**, not Pass.

## 30. 100-point assessment

| Domain | Points | Acceptance |
|---|---:|---|
| Approved experimental design and safety gates | 10 | Critical |
| Kafka/Strimzi/Kubernetes topology baseline | 10 | Critical |
| Producer throughput and p95/p99 baseline | 15 | Critical |
| Rate and message-size sensitivity | 10 | Normal |
| Acks, batching and compression analysis | 10 | Normal |
| Partition and concurrency scaling | 10 | Normal |
| Consumer throughput and lag recovery | 10 | Critical |
| CPU, network, disk and replication correlation | 15 | Critical |
| Repeatability, evidence and statistical integrity | 5 | Critical |
| Runbooks, rollback and independent review | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. Automatic **Fail** for unapproved production load, unbounded benchmark, material Kafka health degradation ignored, fabricated results or misrepresented security configuration. This chapter is published but no live performance scores have been earned.

## 31. Cleanup, handoff and references

After approval, delete only owned synthetic KafkaTopics, benchmark Jobs and client Pods; preserve sanitized evidence and respect any data retention/incident hold. Do not delete broker PVCs, Strimzi operator resources or unrelated topics. Benchmark topics may contain substantial synthetic data; account for storage retention and cleanup timing.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Apache Kafka Operations](https://kafka.apache.org/documentation/#operations), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [Kubernetes Metrics Pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/).

**Next:** Chapter 032 — Kafka Producer Performance Tuning, Batching, Compression, Idempotence and Kubernetes Workload Optimization.

---

**Verification boundary:** GitHub publication confirms document availability, not successful benchmark execution, production representativeness or independent operational approval.
