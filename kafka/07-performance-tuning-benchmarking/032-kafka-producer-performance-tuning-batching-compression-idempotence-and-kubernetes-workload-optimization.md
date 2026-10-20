# Chapter 032 — Kafka Producer Performance Tuning, Batching, Compression, Idempotence and Kubernetes Workload Optimization

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 07 — Performance Tuning and Benchmarking (2/5)  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 016–020, 026–031; Kubernetes lab foundation; secure Kafka client access  
**Audience:** Kafka SRE, application SRE, performance engineer, platform engineer and DBRE  
**Publication:** Published · **Live lab execution:** Pending · **Technical/security review:** Pending

> **Safety:** Run load experiments only in an approved, isolated cluster using synthetic topics and bounded workloads. Never disable TLS hostname verification, lower durability settings or change production producer configurations without an explicit reliability decision. Performance numbers are **not** claimed until tests are executed. Kubernetes is the primary lab environment; Docker is not required.

## 1. Learning outcomes

By completing this chapter, you will be able to:

1. Trace the producer path from application buffer to leader acknowledgment and follower replication.
2. Explain `batch.size`, `linger.ms`, `buffer.memory`, `max.block.ms`, `max.in.flight.requests.per.connection`, `delivery.timeout.ms`, retries and `request.timeout.ms`.
3. Compare `none`, `lz4`, `snappy`, `gzip` and `zstd` compression against realistic payload entropy.
4. Explain idempotent delivery, ordering, transactions and exactly-once processing boundaries.
5. Build reproducible Kubernetes Job-based producer tests with controlled CPU/memory budgets.
6. Identify client-side CPU throttling, JVM GC, broker request queues, storage and replication bottlenecks.
7. Separate offered throughput from acknowledged throughput and p50/p95/p99 latency.
8. Tune for throughput without silently sacrificing durability or causing resource exhaustion.
9. Execute controlled failure tests, incident runbooks and rollback.
10. Publish a reproducible, independently reviewed performance evidence package.

## 2. Architecture: producer hot path

```text
Application Pod / producer thread
  |
  +-- serialize key/value, choose partition
  +-- compress batches (when configured)
  +-- RecordAccumulator + buffer.memory
  +-- linger.ms / batch.size / sender thread
  |
  v
Kubernetes DNS + Service + advertised broker endpoint
  | TCP, TLS/SASL, CNI, conn reuse
  v
Partition leader broker
  +-- append log to page cache / PVC-backed log
  +-- replicate to in-sync followers
  +-- respond according to acks
  |
  v
Producer callback / success or exception
  |
  +-- retries, backoff, delivery timeout
  +-- application SLI, metrics and tracing
```

The producer's acknowledged throughput depends on the full path, not just `batch.size`. Producer CPU, compression, network, broker request handling, ISR and storage can each dominate at different loads.

## 3. Key producer settings and semantics

| Setting | Purpose | Common failure mode |
|---|---|---|
| `acks=all` | Wait for leader's configured replication acknowledgment conditions | Latency rises with slow ISR |
| `enable.idempotence=true` | Deduplicate retries per producer session/partition sequence | Invalid combinations with acks/retries/in-flight |
| `linger.ms` | Wait briefly to accumulate records into batches | Added low-load latency |
| `batch.size` | Upper target for a partition batch; not a guaranteed filled batch | Excess memory with many active partitions |
| `buffer.memory` | Approximate buffer budget for unsent records | Producer blocks/exhausts memory |
| `compression.type` | Compress record batches | CPU or payload entropy dominates |
| `max.in.flight.requests.per.connection` | Cap concurrent unacknowledged requests per connection | Ordering/throughput trade-offs |
| `retries` | Retry transient errors | Unbounded retry duration assumptions |
| `delivery.timeout.ms` | Upper bound for reporting delivery outcome under normal operation | Delivery failures under sustained saturation |
| `request.timeout.ms` | Wait for broker request response | Spurious retries if too low |
| `max.block.ms` | Bound metadata/buffer waiting for send/partitionsFor | App threads stall |
| `max.request.size` | Max request payload size | Oversized record errors |

**Version warning:** Kafka producer defaults evolve; for example default linger behavior differs across Kafka client releases. Always record the actual client version and explicitly set experimental values. Validate configuration constraints in the installed client rather than copying defaults from another release.

## 4. Reliability invariants

- **At-least-once:** retries can produce duplicates unless idempotence or application-level deduplication applies.
- **Idempotent producer:** protects against duplicate log entries from retrying the same producer session's writes; it does **not** provide exactly-once business processing across arbitrary external systems.
- **Transactions:** coordinate atomic visibility across Kafka topic partitions and, with appropriate consumer semantics, support Kafka-to-Kafka exactly-once workflows; external side effects still need their own transactional/outbox/idempotency design.
- **Ordering:** partition-local, not globally ordered across a topic. Producer retries and concurrency configuration matter.
- **Durability:** `acks=all` and topic `min.insync.replicas` work together; replication factor alone is not an acknowledgment guarantee.
- **Timeouts:** a client timeout can leave the outcome unknown; blindly replaying an event with a new producer or key can create duplicates.

For a durability-oriented baseline, use `acks=all`, `enable.idempotence=true`, RF3 and minISR2 in the disposable cluster.

## 5. Test matrix and guardrails

| Test | Message size | Target records/s | Linger | Batch | Compression | Acks |
|---|---:|---:|---:|---:|---|---|
| Baseline | 1 KiB | 1,000 | 0 ms | 16 KiB | none | all |
| Batch A | 1 KiB | 1,000 | 5 ms | 16 KiB | none | all |
| Batch B | 1 KiB | 1,000 | 5 ms | 64 KiB | none | all |
| Compression A | 1 KiB | 1,000 | 5 ms | 64 KiB | lz4 | all |
| Compression B | 1 KiB | 1,000 | 5 ms | 64 KiB | zstd | all |
| Rate A | 1 KiB | 500 | 5 ms | 64 KiB | lz4 | all |
| Rate B | 1 KiB | 2,000 | 5 ms | 64 KiB | lz4 | all |

These are **illustrative limits**, not performance predictions. Keep trials short, cap total records, repeat at least three times where feasible, and abort on Kafka NotReady, ISR loss, KRaft instability, high disk utilization, client OOM or unapproved tenant impact.

## 6. Lab 01 — Confirm isolated Kubernetes context

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch32
kubectl config current-context | tee evidence-ch32/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch32/platform.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch32/listeners.txt
```

**Acceptance:** approved cluster, healthy Kafka, sufficient PVC headroom, named test owner and abort criteria.

## 7. Lab 02 — Capture version and producer defaults

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh --version \
  | tee evidence-ch32/client-version.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-producer-perf-test.sh --help \
  > evidence-ch32/perf-help.txt 2>&1 || true
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch32/kafka-cr.yaml
```

Review the client library documentation matching the installed binary, including idempotence constraints and producer performance CLI flags. Sanitize internal topology from public evidence. **Acceptance:** exact version, config assumptions and tool compatibility recorded.

## 8. Lab 03 — Provision dedicated synthetic topic

Save `kafkatopic-producer-ch32.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-producer-perf-ch32
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
kubectl apply --dry-run=server -f kafkatopic-producer-ch32.yaml
# Approved disposable cluster only:
kubectl apply -f kafkatopic-producer-ch32.yaml
kubectl -n kafka-lab get kafkatopic sre-producer-perf-ch32 -o wide \
  | tee evidence-ch32/topic.txt
```

**Acceptance:** topic Ready, RF3/minISR2, six partitions distributed across eligible brokers.

## 9. Lab 04 — Prepare bounded Kubernetes benchmark Job

Use a dedicated non-root Pod with a pinned approved Kafka client image, dedicated ServiceAccount, restricted Secret mounts, CPU/memory requests and limits, and no broad Kubernetes API access. Example template:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: producer-perf-ch32
  namespace: kafka-lab
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  activeDeadlineSeconds: 300
  template:
    spec:
      restartPolicy: Never
      serviceAccountName: approved-kafka-benchmark
      containers:
        - name: producer
          image: <APPROVED_KAFKA_IMAGE_DIGEST>
          command: ["/bin/sh", "-ec"]
          args:
            - |
              exec /opt/kafka/bin/kafka-producer-perf-test.sh \
                --topic sre-producer-perf-ch32 \
                --num-records 100000 \
                --record-size 1024 \
                --throughput 1000 \
                --producer-props \
                  bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
                  acks=all \
                  enable.idempotence=true \
                  linger.ms=0 \
                  batch.size=16384 \
                  compression.type=none
          resources:
            requests:
              cpu: "500m"
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
```

The image placeholder and ServiceAccount **must** be replaced before use. This initial example uses the isolated plaintext foundation; for production-like testing, switch to a secure listener and use `--producer.config` with a protected mounted file rather than secrets in `--producer-props`. Benchmark output can contain internal topology; sanitize before sharing.

**Acceptance:** Job has bounded lifetime, immutable image, approved identity and resource isolation.

## 10. Lab 05 — Establish producer baseline

From the approved `kafka-cli` Pod in the disposable cluster:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-producer-perf-test.sh \
    --topic sre-producer-perf-ch32 \
    --num-records 100000 \
    --record-size 1024 \
    --throughput 1000 \
    --producer-props \
      bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
      acks=all \
      enable.idempotence=true \
      linger.ms=0 \
      batch.size=16384 \
      compression.type=none \
  | tee evidence-ch32/baseline.txt
```

Record achieved records/s, MiB/s, average and reported p50/p95/p99 latency, total duration and failures. Some Kafka CLI versions report only selected percentiles; do not invent missing p99 values. **Acceptance:** successful bounded baseline and no broker/ISR alerts.

## 11. Lab 06 — Tune linger.ms

Repeat the exact baseline with `linger.ms=5` and `linger.ms=20`; keep message count, target throughput, batch size, compression, topic and producer Pod placement constant. At low rates, extra linger may add latency without filling batches; at high rates, it can reduce request overhead.

**Acceptance:** side-by-side throughput, latency percentiles and producer batch-size observations. Record whether observed batches actually grew.

## 12. Lab 07 — Tune batch.size

Compare 16 KiB, 64 KiB and 128 KiB with `linger.ms=5`. A producer accumulates batches per active partition; a larger `batch.size` can increase memory pressure when many partitions are active.

**Acceptance:** achieved throughput, memory use, batch-size-average and p99 latency with the same offered load.

## 13. Lab 08 — Compression codec comparison

Compare `none`, `lz4`, `snappy`, `gzip` and `zstd` where supported. Measure producer CPU, broker CPU, network bytes, compressed batch size, throughput and p99 latency. Compression depends strongly on payload entropy and format; random synthetic data may not compress like JSON/Avro/Protobuf application events.

**Acceptance:** realistic compressibility noted, supported codecs verified and no conclusion drawn from CPU-free assumptions.

## 14. Lab 09 — Message size and key distribution

Repeat with 256 B, 1 KiB and 16 KiB synthetic messages. Compare uniform key distribution with skewed keys using an approved custom producer workload. The built-in perf tool does not necessarily reproduce application partition-key distributions.

**Acceptance:** identify hot partitions, broker imbalance, records/s versus MiB/s and request-size limits.

## 15. Lab 10 — Idempotence and retries

Baseline:

```properties
acks=all
enable.idempotence=true
retries=2147483647
max.in.flight.requests.per.connection=5
delivery.timeout.ms=120000
request.timeout.ms=30000
```

These values are **illustrative** and must be checked against the installed client version and application SLO. Idempotence has configuration constraints; the client can reject incompatible settings. A very high retry count does not imply infinite retry time because `delivery.timeout.ms` still bounds delivery outcome.

Use a client-side simulated transient failure only in an isolated test harness; do not kill production brokers. **Acceptance:** retries and final outcomes classified, no unsupported exactly-once claim.

## 16. Lab 11 — Ordering and max.in.flight.requests

Test a keyed sequence of synthetic events on one partition with idempotence enabled. Vary `max.in.flight.requests.per.connection` within supported idempotent-producer constraints. Record sequence gaps, duplicates and out-of-order observations after controlled client-side retries.

**Acceptance:** partition-local ordering demonstrated under the tested configuration; avoid extrapolating to cross-partition global ordering.

## 17. Lab 12 — Buffer memory and backpressure

Observe producer `bufferpool-wait-time`, available buffer bytes, blocked sends and `max.block.ms` under a bounded rate sweep. Client memory includes serialization, compression, JVM overhead and in-flight requests beyond the nominal buffer budget.

**Acceptance:** application backpressure policy, bounded timeout behavior and no Pod OOM. Do not intentionally exhaust broker storage.

## 18. Lab 13 — Producer concurrency and partitions

Compare one producer Pod, two Pods and four Pods. Keep **aggregate offered throughput** constant for efficiency comparison; then perform a separate scaling sweep. Ensure partition/key distribution permits concurrency and account for Kubernetes node placement.

**Acceptance:** client CPU and network saturation separated from broker partition-leader constraints.

## 19. Lab 14 — Kubernetes CPU limits and throttling

```bash
kubectl -n kafka-lab top pods \
  | tee evidence-ch32/pod-top.txt
kubectl top nodes | tee evidence-ch32/node-top.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch32/pod-placement.txt
```

If Metrics Server is absent, use approved Prometheus/cAdvisor metrics. Compare benchmark Pod CPU requests/limits and observed CFS throttling; never infer low throttling from `kubectl top` alone.

**Acceptance:** actual CPU throttling evidence, client GC/heap context and resource-sizing recommendation.

## 20. Lab 15 — Broker replication and storage correlation

Collect Kafka request queue latency, produce request latency, under-replicated partitions, ISR events, broker network and storage IOPS/latency. Check PVC and node capacity:

```bash
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch32/pvcs.txt
kubectl -n kafka-lab get pods -l strimzi.io/cluster=sre-kafka -o wide \
  | tee evidence-ch32/broker-placement.txt
```

**Acceptance:** evidence-backed distinction between client-side and broker-side bottlenecks. Stop load if ISR shrinks or Kafka becomes NotReady.

## 21. Lab 16 — Secure-listener producer performance

Run a matched subset through an approved `SASL_SSL` or mTLS listener. Obtain the actual endpoint from `Kafka.status.listeners`. Mount client credentials and CA in read-only volumes; generate `client.properties` with restrictive permissions. Never log passwords or tokens.

```bash
# Example inside an approved client Pod with protected config:
# /opt/kafka/bin/kafka-producer-perf-test.sh \
#   --topic sre-producer-perf-ch32 \
#   --num-records 100000 --record-size 1024 --throughput 1000 \
#   --producer.config /etc/kafka/client.properties
```

Validate the installed tool supports the specified configuration flag; some releases require supplying security properties differently. **Acceptance:** same load, security enabled, certificate verification intact, measured delta.

## 22. Lab 17 — Producer delivery timeout and retry policy

Design a bounded test where a disposable client experiences an unreachable bootstrap endpoint or simulated network failure. Distinguish:

- `max.block.ms`: synchronous blocking while waiting for metadata/buffer.
- `request.timeout.ms`: broker request wait.
- `delivery.timeout.ms`: overall delivery result bound, subject to Kafka client semantics.
- `retry.backoff.ms`: delay between retries.

Do not use a failure to production broker networking as a shortcut. **Acceptance:** application retry/backoff budget aligns with end-user SLO and unknown-outcome handling.

## 23. Lab 18 — Application-level producer instrumentation

Instrument a synthetic Java producer (or equivalent Kafka client) to capture:

```text
send_attempts_total
send_success_total
send_failures_total
producer_callback_latency_ms
producer_enqueue_block_ms
producer_record_size_bytes
producer_inflight_requests
producer_retry_count
producer_buffer_wait_ms
```

These are **suggested application-level metric names**, not guaranteed built-in Kafka JMX names. Correlate with actual producer-client JMX metrics exposed by the installed library, Kubernetes Pod metrics and broker telemetry. Do not log payloads, credentials or raw headers containing sensitive data.

**Acceptance:** p95/p99 callback latency, error classification and queueing visible in a dashboard.

## 24. Lab 19 — Repeatability and configuration selection

Repeat at least three trials per candidate where practical. Preserve per-run raw outputs and avoid averaging percentiles as though they were a pooled distribution. Select the configuration based on **all** of throughput, tail latency, CPU, network, durability, operational complexity and SLO.

Use a comparison sheet:

| Candidate | Achieved MiB/s | p95 ms | p99 ms | Errors | Client CPU | Broker ISR | Decision |
|---|---:|---:|---:|---:|---:|---|---|
| Baseline | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Batch tuned | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Compression tuned | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Secure listener | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

**Acceptance:** evidence-based selection, no fabricated measurements.

## 25. Lab 20 — Read-only preflight automation

Save `verify-ch32.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/9] Kubernetes context'
kubectl config current-context

echo '[2/9] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/9] Kafka and node pools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide

echo '[4/9] Kafka listeners'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[5/9] Benchmark topic status (optional)'
if kubectl -n "$NS" get kafkatopic sre-producer-perf-ch32 >/dev/null 2>&1; then
  kubectl -n "$NS" get kafkatopic sre-producer-perf-ch32 -o wide
else
  echo 'PENDING: benchmark topic not provisioned'
fi

echo '[6/9] Client tooling'
kubectl -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-producer-perf-test.sh" --help >/dev/null 2>&1 || true

echo '[7/9] PVC inventory'
kubectl -n "$NS" get pvc -o wide

echo '[8/9] Broker/client Pod placement'
kubectl -n "$NS" get pods -o wide

echo '[9/9] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: read-only platform and producer-tooling preflight.'
echo 'NOT PROVEN: benchmark throughput, latency, ordering, idempotence, or secure listener performance.'
```

```bash
chmod +x verify-ch32.sh
./verify-ch32.sh | tee evidence-ch32/preflight.txt
```

The producer `--help` invocation is intentionally non-blocking because some versions return nonzero for help; inspect the captured output and tool availability separately. A successful preflight is **not** a producer performance test.

## 26. Twelve troubleshooting scenarios

### 26.1 Throughput plateaus with low broker CPU
**Inspect:** producer Pod throttling, client network, partitions and `buffer.memory`. **Recover:** rightsize client and repeat matched trial.

### 26.2 p99 spikes after increasing linger
**Inspect:** batch fill, low-rate traffic and request queue. **Recover:** reduce linger if latency SLO dominates.

### 26.3 Large batch size causes memory pressure
**Inspect:** active partitions, buffer use, heap and GC. **Recover:** reduce batch size or bound active partition concurrency.

### 26.4 Compression saves network but saturates CPU
**Inspect:** codec, payload entropy, client CPU. **Recover:** compare lz4/zstd or adjust resource requests.

### 26.5 `OutOfOrderSequenceException`
**Inspect:** producer identity/sequence state and unsupported retry behavior. **Recover:** follow client-specific fatal error guidance; recreate producer when required.

### 26.6 `TimeoutException` under burst
**Inspect:** `delivery.timeout.ms`, metadata, buffer waits, broker latency. **Recover:** reduce overload and align timeouts to SLO.

### 26.7 `NotEnoughReplicasException`
**Inspect:** ISR and minISR. **Recover:** restore replica health; do not lower minISR reflexively.

### 26.8 Producer sends duplicate business events
**Inspect:** application retry/outbox semantics, new producer sessions and consumer deduplication. **Recover:** enforce event identity and idempotent business processing.

### 26.9 Ordering breaks across partitions
**Inspect:** keying and partition changes. **Recover:** correct partition-key design; no global ordering assumption.

### 26.10 Secure-listener throughput lower than plaintext
**Inspect:** TLS CPU, connection churn, authentication latency and placement. **Recover:** optimize client connection reuse without disabling security.

### 26.11 Benchmark appears faster after broker cache warms
**Inspect:** trial order, page cache, storage metrics and warm-up. **Recover:** balanced repeated trials and documented cache state.

### 26.12 Producer load degrades KRaft/ISR
**Inspect:** broker/controller contention, storage and network. **Recover:** abort load, restore quorum/ISR and document incident.

## 27. Eight production runbooks

### Runbook A — Producer latency regression
1. Identify client cohort and p95/p99 regression window.
2. Compare configuration and workload changes.
3. Inspect client buffering, retries and broker request latency.
4. Check ISR, storage and network.
5. Roll back the smallest approved change.
6. Verify delivery success and durability.

### Runbook B — Producer throughput saturation
1. Compare offered versus acknowledged records/s.
2. Check client CPU, network and Pod throttling.
3. Inspect broker CPU, partitions, disk and quotas.
4. Form one bottleneck hypothesis.
5. Reproduce in disposable Kubernetes benchmark.
6. Implement measured change with rollback.

### Runbook C — Retry storm and timeout incident
1. Quantify error rate and retry amplification.
2. Inspect `delivery.timeout.ms` and broker availability.
3. Rate-limit/reduce offered load safely.
4. Restore broker/ISR health before tuning retries.
5. Verify duplicate-handling policy.
6. Record retry budget and corrective action.

### Runbook D — Compression-related CPU incident
1. Identify changed codec or payload mix.
2. Compare CPU and network bytes.
3. Check client and broker throttling.
4. Revert to last approved codec if SLO violated.
5. Retest representative payloads.
6. Document CPU/bandwidth trade-off.

### Runbook E — Idempotence/ordering incident
1. Identify affected topic, partition and event keys.
2. Review producer configs and exception types.
3. Determine whether failures are retriable or fatal.
4. Restore a supported idempotent configuration.
5. Validate partition-local order and deduplication.
6. Audit downstream business effects.

### Runbook F — Buffer exhaustion/backpressure
1. Confirm `buffer.memory` waits and `max.block.ms` exceptions.
2. Reduce input rate or apply bounded upstream backpressure.
3. Check broker and network health.
4. Right-size client resources and batch settings.
5. Re-run controlled load test.
6. Update capacity alert thresholds.

### Runbook G — Secure producer connection degradation
1. Separate DNS, TCP, TLS, SASL and Kafka authorization errors.
2. Validate advertised endpoints and cert chain.
3. Inspect handshake churn and authentication load.
4. Restore secure client configuration without bypasses.
5. Confirm producer callbacks and p99 recovery.
6. Preserve security-safe evidence.

### Runbook H — Producer tuning change rollout
1. Approve candidate and performance baseline.
2. Canary small client cohort with immutable config.
3. Compare throughput, p99, errors, ISR and CPU.
4. Halt/roll back on predefined thresholds.
5. Expand cohorts only after measured acceptance.
6. Publish results, owner and next review date.

## 28. Evidence package

```text
evidence-ch32/
  approval-and-scope.md
  context.txt
  platform.txt
  listeners.txt
  client-version.txt
  perf-help.txt
  kafka-cr.yaml
  topic.txt
  benchmark-job.yaml
  baseline.txt
  linger-trials.csv
  batch-trials.csv
  compression-trials.csv
  message-size-key-distribution.csv
  idempotence-retry-test.md
  ordering-test.md
  buffer-backpressure.md
  concurrency-trials.csv
  pod-top.txt
  node-top.txt
  pod-placement.txt
  pvcs.txt
  broker-placement.txt
  broker-metrics.md
  secure-listener-trials.csv
  timeout-tests.md
  application-metrics.md
  comparison-report.md
  preflight.txt
  incident-review.md
  assessor-signoff.md
```

Every trial must include version, configuration hash, topic/partition count, client placement, offered and achieved load, success/error counts, p50/p95/p99 if available, resource metrics, ISR state, duration, timestamp and reviewer. Mark missing evidence **Pending**, never Pass.

## 29. 100-point assessment

| Domain | Points | Gate |
|---|---:|---|
| Approved workload design and safety controls | 10 | Critical |
| Kubernetes/Strimzi baseline and client isolation | 10 | Critical |
| Producer baseline throughput and tail latency | 15 | Critical |
| Batching/linger tuning evidence | 10 | Normal |
| Compression and message-size experiments | 10 | Normal |
| Idempotence, retry and ordering correctness | 15 | Critical |
| Buffer memory, backpressure and concurrency | 10 | Normal |
| Broker/ISR/storage and Kubernetes resource correlation | 10 | Critical |
| Secure-listener validation and no security regression | 5 | Critical |
| Runbooks, repeatability and independent signoff | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates demonstrated. Automatic **Fail** for unapproved production load, disabled TLS verification, undocumented durability weakening, ignored ISR/quorum degradation, fabricated measurements or unsafe credential handling.

## 30. Cleanup, references and next chapter

After approval, delete only the chapter-owned synthetic KafkaTopic, benchmark Job and client Pods. Preserve sanitized evidence and honor retention requirements. Never delete broker PVCs or shared topics to reclaim benchmark storage.

**References:** [Apache Kafka Producer Configs](https://kafka.apache.org/documentation/#producerconfigs), [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/), [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

**Next:** Chapter 033 — Kafka Consumer Performance Tuning, Fetch Optimization, Group Parallelism and Kubernetes Scaling.

---

**Verification boundary:** GitHub publication proves availability of this chapter only. Producer benchmark results, idempotence behavior, secure-listener measurements and independent review remain Pending until live evidence is collected.
