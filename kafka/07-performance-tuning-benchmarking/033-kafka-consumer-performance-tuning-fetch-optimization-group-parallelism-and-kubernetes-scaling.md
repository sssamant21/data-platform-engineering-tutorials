# Chapter 033 — Kafka Consumer Performance Tuning, Fetch Optimization, Group Parallelism and Kubernetes Scaling

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 07 — Performance Tuning and Benchmarking (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 016–020, 026–032; Kafka consumer groups, offsets, security, observability and Kubernetes workloads  
**Audience:** Kafka SREs, application SREs, DBREs, platform engineers and performance engineers  
**Publication:** Published · **Live lab execution:** Pending · **Technical/security review:** Pending

> **Safety:** Run all benchmarks against synthetic topics in an approved disposable cluster. Never reset a production consumer group's offsets, delete production topics, disable TLS hostname verification, or scale shared consumers to test a theory. Kafka CLI examples using port 9092 apply only to the isolated plaintext lab; repeat acceptance tests on a supported TLS/SASL listener. A published chapter is not a validated runbook.

## 1. Objectives and acceptance

This chapter develops a reproducible method for measuring and improving Kafka consumer throughput, fetch efficiency, group parallelism, offset-commit safety, rebalances and Kubernetes scaling.

You will:

1. Distinguish broker log end offset, consumer position, committed offset and application-processed offset.
2. Explain fetch request behavior and `fetch.min.bytes`, `fetch.max.wait.ms`, `fetch.max.bytes`, `max.partition.fetch.bytes`.
3. Tune `max.poll.records`, `max.poll.interval.ms`, `session.timeout.ms` and `heartbeat.interval.ms` without losing group stability.
4. Compare eager/cooperative assignment where supported and understand static membership trade-offs.
5. Measure consumers-per-partition scaling and identify idle consumer capacity.
6. Distinguish fetch throughput from actual business-processing throughput.
7. Diagnose consumer lag, event age, rebalances, CPU throttling and backpressure.
8. Apply bounded Kubernetes Deployment/HPA/KEDA-style scaling with guardrails.
9. Validate at-least-once delivery and failure recovery without unapproved offset resets.
10. Produce repeatable benchmark evidence, production runbooks and a 100-point assessment.

## 2. Architecture: the consumer hot path

```text
Strimzi/KRaft Kafka cluster
  |
  +-- Partition leaders and follower ISR
  +-- Broker fetch request queue / page cache / PVC
  |
  v
Kubernetes Service + advertised broker endpoints
  | TCP / TLS / SASL / ACL
  v
Consumer Pod (Deployment)
  +-- fetch.min.bytes / fetch.max.wait.ms
  +-- fetch.max.bytes / max.partition.fetch.bytes
  +-- decompression / deserialization
  +-- poll loop / max.poll.records
  +-- application handler / downstream DB or API
  +-- offset commit / error handling
  |
  v
Consumer group coordinator
  +-- heartbeats / membership / assignments
  +-- rebalance protocol / committed offsets
  |
  v
Metrics: records/s, event age, lag, rebalance rate,
        fetch latency, processing p99, retries, errors
```

The true end-to-end throughput is constrained by the slowest stage: broker fetch, client CPU/network, processing dependencies, concurrency, commits or partition count. Fetching records quickly is not proof that they have been processed successfully.

## 3. Key metrics and formulas

| Metric | Meaning | Caution |
|---|---|---|
| Fetch throughput (records/s) | Records returned by broker to consumer | Excludes business processing |
| Processed throughput (records/s) | Records successfully handled by application | Requires application instrumentation |
| Consumer lag (records) | Broker end offset minus committed/observed offset | Lag alone is not delay in seconds |
| Event age (seconds) | Now minus event creation/ingest time | Clock skew and timestamp type matter |
| Processing latency p99 | Time spent handling a record | Distinct from fetch latency |
| Fetch request latency | Broker/client fetch completion time | Influenced by batching/wait |
| Rebalance frequency | Group membership/assignment changes per period | Can create pauses and duplicates |
| Commit latency/errors | Offset commit completion and failures | Determines replay window |
| Catch-up time | Backlog divided by net drain rate | Undefined if drain rate ≤ 0 |
| Assignment efficiency | Active assigned consumers / total group consumers | Depends on partitions and protocol |

**Example:** ingress 10,000 records/s and processing 12,000 records/s gives net drain 2,000 records/s; a backlog of 600,000 records needs ~300 seconds in steady state, ignoring variability. If ingress matches processing, backlog does not drain.

## 4. Consumer configuration semantics

| Setting | Role | Risk if misused |
|---|---|---|
| `fetch.min.bytes` | Minimum data broker tries to return per fetch | Higher value can add low-volume latency |
| `fetch.max.wait.ms` | Broker wait ceiling for minimum fetch data | Larger value can increase latency |
| `fetch.max.bytes` | Approximate maximum data per fetch response | Not a strict cap for first oversized batch |
| `max.partition.fetch.bytes` | Approximate max bytes per partition in fetch | First batch may exceed limit to allow progress |
| `max.poll.records` | Max records returned per poll | Does not change underlying fetch batching |
| `max.poll.interval.ms` | Max interval between calls to poll for group-managed consumers | Slow processing can trigger membership loss |
| `session.timeout.ms` | Failure detection timeout under applicable group protocol | Protocol/version constraints apply |
| `heartbeat.interval.ms` | Heartbeat frequency under classic protocol | Not necessarily client-controlled in newer protocol |
| `enable.auto.commit` | Periodic background offset commits | May commit before business processing finishes |
| `auto.offset.reset` | Behavior when no valid committed offset exists | Not a substitute for incident offset recovery |
| `partition.assignment.strategy` | Classic group partition assignment behavior | Version/protocol compatibility matters |
| `group.instance.id` | Static member identity | Duplicate IDs or stuck members delay recovery |
| `isolation.level` | Read committed vs uncommitted transactional visibility | May alter visible records and lag semantics |

**Kafka protocol warning:** Newer Kafka clients support a newer consumer group protocol with broker-managed heartbeat/session settings. Confirm `group.protocol`, Kafka version and coordinator settings before tuning classic-protocol properties. Do not assume every property is honored by every client version.

## 5. Benchmark design and safety thresholds

Use dedicated synthetic topic `sre-consumer-perf-ch33`, RF3/minISR2, six partitions, a bounded producer load and fresh test consumer groups. Set a retention window that provides enough replay time. Fix:

- Broker/Strimzi/Kubernetes versions and topology.
- Topic partitions, replication, message size and compression.
- Producer ingress rate and synthetic payload entropy.
- Consumer image digest, security listener, CPU/memory limits and node placement.
- Fetch configuration, processing delay and commit mode.
- Test duration, warm-up, trial count and data start offsets.

**Stop conditions:** Kafka NotReady, KRaft quorum degradation, unexpected ISR shrink, sustained broker disk pressure, consumer OOM, uncontrolled retry storm, cross-tenant authorization failure or exceeded benchmark duration.

## 6. Lab 01 — Validate Kubernetes and Kafka baseline

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch33
kubectl config current-context | tee evidence-ch33/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch33/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch33/listeners.txt
```

**Acceptance:** disposable cluster approval, stable Kafka and sufficient CPU, network and PVC headroom.

## 7. Lab 02 — Capture client and group protocol versions

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh --version \
  | tee evidence-ch33/kafka-version.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-perf-test.sh --help \
  > evidence-ch33/consumer-help.txt 2>&1 || true
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch33/kafka-cr.yaml
```

Record consumer client version, supported `group.protocol`, assignor, heartbeat behavior and CLI options. Sanitize internal addresses from public evidence. **Acceptance:** exact compatibility matrix; unsupported options are marked Not Applicable.

## 8. Lab 03 — Provision synthetic six-partition topic

Save `kafkatopic-consumer-ch33.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-consumer-perf-ch33
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
kubectl apply --dry-run=server -f kafkatopic-consumer-ch33.yaml
# Only after isolated-cluster approval:
kubectl apply -f kafkatopic-consumer-ch33.yaml
kubectl -n kafka-lab get kafkatopic sre-consumer-perf-ch33 -o wide \
  | tee evidence-ch33/topic.txt
```

**Acceptance:** topic Ready with six partitions and RF3/minISR2.

## 9. Lab 04 — Seed bounded synthetic records

Run a bounded producer from the approved `kafka-cli` Pod:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic sre-consumer-perf-ch33 \
  --num-records 60000 \
  --record-size 1024 \
  --throughput 1000 \
  --producer-props \
    bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
    acks=all \
    enable.idempotence=true \
  | tee evidence-ch33/seed-producer.txt
```

Record successful sends and partition distribution; do not assume 60,000 records were delivered if the tool exited unsuccessfully. **Acceptance:** known synthetic backlog and healthy ISR.

## 10. Lab 05 — Baseline consumer fetch throughput

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-perf-test.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-consumer-perf-ch33 \
  --messages 10000 \
  --group sre-consumer-ch33-baseline \
  --timeout 30000 \
  | tee evidence-ch33/fetch-baseline.txt
```

The Kafka consumer performance tool flags vary across versions; validate `--help`. A fresh group should start at the intended position; confirm actual start offsets rather than assuming tool defaults. This measures fetch/consume speed, not database writes or external side effects.

**Acceptance:** achieved records/s, MB/s, elapsed time and group offset state recorded.

## 11. Lab 06 — Fetch minimum and wait experiment

Run matched tests with `fetch.min.bytes` at 1, 16 KiB and 64 KiB; vary `fetch.max.wait.ms` separately at 100, 500 and 1,000 ms. Use the installed CLI's supported `--consumer.config` or equivalent mechanism to supply a properties file.

**Hypothesis:** larger fetch minimums can improve request efficiency under high load but delay delivery under sparse traffic.

**Acceptance:** broker fetch request rate, bytes/fetch, consumer latency and throughput captured.

## 12. Lab 07 — Fetch response sizing

Compare `fetch.max.bytes` and `max.partition.fetch.bytes` using bounded 1 KiB and 16 KiB records. These are approximate fetch bounds; the first record batch can exceed them so the consumer can make progress.

**Acceptance:** consumer memory, network and fetch throughput correlated with actual batch sizes; no assertion that limits are hard memory caps.

## 13. Lab 08 — max.poll.records and application processing

Create an approved synthetic consumer that sleeps for a bounded processing time (for example 5 ms/record), and compare `max.poll.records=100`, 500 and 1,000. Do **not** use the consumer perf tool to claim application handler latency.

At 5 ms/record, 1,000 serial records can consume ~5 seconds before the next poll, excluding other work. Verify processing duration remains within `max.poll.interval.ms` or use a properly designed processing/poll architecture.

**Acceptance:** p95/p99 processing time, poll interval, throughput and group stability observed.

## 14. Lab 09 — Commit strategy and at-least-once behavior

Compare auto-commit with explicit commit-after-success in an isolated synthetic consumer. Show the failure window:

```text
poll records -> process -> commit -> next poll
                    |
           crash before commit
                    |
          replay after restart
```

Auto-commit may advance offsets before downstream processing is durable. Manual commits after processing provide at-least-once semantics but allow replay. A commit is not proof that an external DB transaction succeeded.

**Acceptance:** deliberate client crash/restart in disposable Pod demonstrates replay handling with idempotent sink keys; no production offsets modified.

## 15. Lab 10 — Consumer count versus partition count

For six partitions, compare consumer groups of 1, 3, 6 and 8 members. Use **separate groups** per trial to avoid offset interference and ensure enough records remain for each trial. Under ordinary exclusive partition assignment, no more than six group members can be actively assigned partitions simultaneously.

**Acceptance:** partition assignments, active/idle consumers, records/s and CPU measured. Do not promise linear scaling.

## 16. Lab 11 — Rebalance and cooperative assignment

Inspect the supported assignors and consumer group protocol. Where available, compare eager versus cooperative assignment using approved synthetic consumer Pods; measure rebalance duration, revoked partitions, duplicates and processing pauses. Cooperative assignment requires compatible member configurations.

**Acceptance:** observed assignment transitions and recovery time; no claim that a rebalance is zero-disruption.

## 17. Lab 12 — Static membership and rolling restart

Use unique stable `group.instance.id` values for an isolated synthetic group. Roll a single consumer Pod, measuring reassignment and recovery. Static membership can reduce unnecessary rebalances, but stale/duplicate instance IDs can delay recovery or fence a member.

**Acceptance:** verified membership behavior, restart latency and documented recovery timeout.

## 18. Lab 13 — Consumer lag and event-age monitoring

From the approved CLI Pod:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-consumer-ch33-baseline \
  | tee evidence-ch33/group-lag.txt
```

Lag is a count of records, not elapsed time. Capture application event-age histograms, end-to-end processing time and committed offsets separately. **Acceptance:** lag, event age and catch-up rate tracked with correct definitions.

## 19. Lab 14 — Kubernetes Deployment resources and placement

Use a dedicated non-root synthetic consumer Deployment with immutable image digest, dedicated ServiceAccount, resource requests/limits, read-only Secret mounts and termination grace period sufficient for safe processing/commit. Example **template**, not runnable until image and client command are supplied:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: consumer-ch33
  namespace: kafka-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: consumer-ch33
  template:
    metadata:
      labels:
        app: consumer-ch33
    spec:
      serviceAccountName: approved-kafka-consumer
      terminationGracePeriodSeconds: 60
      containers:
        - name: consumer
          image: <PINNED_APPROVED_CONSUMER_IMAGE>
          command: ["/app/consumer"]
          resources:
            requests:
              cpu: "500m"
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
```

**Acceptance:** versioned Deployment, readiness/termination behavior and per-Pod CPU/memory evidence.

## 20. Lab 15 — Horizontal scaling and HPA limitations

Kubernetes HPA CPU utilization alone may not reflect Kafka backlog, downstream capacity or partition ceilings. Test bounded replica changes (1→3→6) in the disposable Deployment and observe assignment, lag and rebalances. If using KEDA Kafka scaler, verify installed KEDA version, authentication, lag interpretation, min/max replicas and scale-to-zero behavior; KEDA is optional and **not assumed installed**.

**Acceptance:** maximum effective replicas no greater than useful partition parallelism unless other processing stages justify extra Pods; no oscillation or rebalance storm.

## 21. Lab 16 — Backpressure and slow downstream simulation

Use a synthetic handler with controlled 10–50 ms processing delays or an approved local mock service. Measure backlog growth and catch-up after removing delay. Avoid writing synthetic data to production databases or APIs.

**Acceptance:** controlled backpressure, bounded retry/dead-letter behavior and explicit drain-rate calculation.

## 22. Lab 17 — CPU throttling, GC and memory pressure

```bash
kubectl -n kafka-lab top pods \
  | tee evidence-ch33/pod-top.txt
kubectl top nodes | tee evidence-ch33/node-top.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch33/pod-placement.txt
```

If Metrics Server is unavailable, use approved Prometheus/cAdvisor telemetry. Inspect JVM GC, decompression CPU, CFS throttling, heap/off-heap buffers, Pod restarts and OOM events. Never infer no throttling from `kubectl top` alone.

**Acceptance:** bottleneck analysis with real resource metrics.

## 23. Lab 18 — Secure listener and ACL performance

Repeat a bounded fetch trial through an approved `SASL_SSL` or mTLS listener discovered from `Kafka.status.listeners`. Mount credentials and CA via restricted Secrets; preserve hostname verification. Ensure consumer principal has topic Read/Describe and group Read permissions as applicable.

**Acceptance:** secure client authentication, Kafka authorization, fetch throughput and resource overhead measured. Mark Pending if secure listener unavailable.

## 24. Lab 19 — Failure recovery and offset integrity

Use an isolated synthetic consumer Pod and simulate a **client-only** termination during processing. Observe rebalance, replay, commit behavior, application deduplication and time to resume. Do not terminate Kafka broker Pods or alter shared group offsets.

**Acceptance:** documented at-least-once behavior, no unaccounted synthetic events, bounded recovery and idempotent sink semantics.

## 25. Lab 20 — Read-only consumer preflight script

Save `verify-ch33.sh`:

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

echo '[4/9] Listener status'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[5/9] Topic readiness (optional)'
if kubectl -n "$NS" get kafkatopic sre-consumer-perf-ch33 >/dev/null 2>&1; then
  kubectl -n "$NS" get kafkatopic sre-consumer-perf-ch33 -o wide
else
  echo 'PENDING: benchmark topic not provisioned'
fi

echo '[6/9] Consumer CLI availability'
kubectl -n "$NS" exec kafka-cli -- \
  sh -c 'test -x /opt/kafka/bin/kafka-consumer-perf-test.sh && test -x /opt/kafka/bin/kafka-consumer-groups.sh'

echo '[7/9] PVC inventory'
kubectl -n "$NS" get pvc -o wide

echo '[8/9] Consumer and broker Pod placement'
kubectl -n "$NS" get pods -o wide

echo '[9/9] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: read-only Kafka consumer platform preflight.'
echo 'NOT PROVEN: consumer throughput, commit safety, scaling or recovery.'
```

```bash
chmod +x verify-ch33.sh
./verify-ch33.sh | tee evidence-ch33/preflight.txt
```

The CLI Pod must contain `sh` and Kafka tools. This script does not produce, consume, scale or reset offsets.

## 26. Twelve troubleshooting scenarios

### 26.1 Consumer lag rises with stable ingress
**Check:** processing rate, downstream latency, active assignments, fetch throttling. **Recover:** relieve bottleneck; do not reset offsets.

### 26.2 Low fetch throughput with high broker capacity
**Check:** fetch minimum/wait, max partition fetch, client CPU/network. **Recover:** controlled matched tuning.

### 26.3 High latency under low traffic
**Check:** `fetch.min.bytes`, `fetch.max.wait.ms` and batching. **Recover:** reduce excessive fetch wait.

### 26.4 Consumer repeatedly leaves group
**Check:** `max.poll.interval.ms`, slow handlers, heartbeats and protocol. **Recover:** bound processing, tune supported timeout.

### 26.5 Rebalance storm after HPA scale
**Check:** scaling oscillation, readiness, assignment and KEDA settings. **Recover:** stabilize replica bounds and cooldown.

### 26.6 Extra consumer Pods remain idle
**Check:** partition count versus members. **Recover:** cap useful parallelism or redesign partitioning.

### 26.7 Duplicates after consumer restart
**Check:** commit-after-process window and sink idempotency. **Recover:** deterministic event IDs and replay-safe writes.

### 26.8 Missing business events after auto-commit
**Check:** offsets committed before durable processing. **Recover:** incident review and approved replay strategy.

### 26.9 CPU throttling causes false Kafka bottleneck
**Check:** Pod CFS throttling, decompression CPU and GC. **Recover:** client resource rightsizing.

### 26.10 Oversized record batch exceeds expected fetch bound
**Check:** first batch exception to fetch size limits and producer message sizes. **Recover:** align message limits and memory headroom.

### 26.11 SASL succeeds but group authorization fails
**Check:** principal, group Read ACL and topic Read/Describe. **Recover:** least-privilege KafkaUser ACL correction.

### 26.12 Static member fenced or recovery delayed
**Check:** duplicate `group.instance.id`, session timeout and old Pod termination. **Recover:** correct identity and wait/recover safely.

## 27. Eight production runbooks

### Runbook A — Consumer lag incident
1. Confirm lag, event age and ingress trend.
2. Inspect active consumers and partition assignments.
3. Check handler/downstream latency and fetch metrics.
4. Stabilize group membership before scaling.
5. Restore net drain rate and monitor catch-up.
6. Document root cause and replay impact.

### Runbook B — Rebalance storm
1. Identify group protocol, assignment strategy and member churn.
2. Check Kubernetes rollouts, probes and HPA/KEDA changes.
3. Confirm poll intervals and heartbeat/session settings.
4. Pause unsafe scaling and stabilize replicas.
5. Verify assignment, commits and p99 processing latency.
6. Adjust rollout/cooldown strategy.

### Runbook C — Consumer fetch saturation
1. Measure fetch requests, bytes/fetch and response latency.
2. Check broker queues, network, page cache and storage.
3. Separate consumer CPU/decompression bottleneck.
4. Test one fetch setting in disposable environment.
5. Compare throughput and event age.
6. Roll out with SLO gates and rollback.

### Runbook D — Offset commit/replay incident
1. Freeze unapproved offset mutations.
2. Record committed offsets and partition log boundaries.
3. Identify processed-but-uncommitted and committed-but-unprocessed windows.
4. Use application deduplication or approved replay process.
5. Validate downstream data correctness.
6. Document recovery and change controls.

### Runbook E — Slow downstream processing
1. Identify affected dependency and handler latency.
2. Apply bounded backpressure/retry.
3. Prevent unbounded memory or DLQ growth.
4. Restore downstream capacity.
5. Measure net drain rate and catch-up.
6. Update dependency SLO and alerting.

### Runbook F — Kubernetes consumer scaling
1. Check partitions, current assignments and capacity.
2. Verify ServiceAccount, Secrets, TLS and resource requests.
3. Scale in bounded steps within useful partition ceiling.
4. Watch rebalances, lag, event age and Pod health.
5. Roll back on oscillation or error increase.
6. Record steady-state capacity.

### Runbook G — Secure consumer failure
1. Distinguish DNS, TCP, TLS, SASL and ACL errors.
2. Validate advertised endpoints and certificate SAN.
3. Confirm principal/topic/group authorization.
4. Restore approved secure config without bypass.
5. Verify commits, lag and consumer processing.
6. Preserve sanitized evidence.

### Runbook H — Consumer performance game day
1. Approve synthetic workload and abort criteria.
2. Capture Kafka/Strimzi/Kubernetes baseline.
3. Run fetch, parallelism and processing sweeps.
4. Simulate isolated client termination.
5. Verify replay correctness and recovery SLO.
6. Publish evidence and independent review.

## 28. Evidence package

```text
evidence-ch33/
  approval-and-scope.md
  context.txt
  inventory.txt
  listeners.txt
  kafka-version.txt
  consumer-help.txt
  kafka-cr.yaml
  topic.txt
  seed-producer.txt
  fetch-baseline.txt
  fetch-min-wait.csv
  fetch-size.csv
  poll-processing.csv
  commit-safety.md
  parallelism.csv
  rebalance.md
  static-membership.md
  group-lag.txt
  event-age.csv
  consumer-deployment.yaml
  scaling.csv
  downstream-backpressure.md
  pod-top.txt
  node-top.txt
  pod-placement.txt
  secure-listener.csv
  recovery.md
  preflight.txt
  performance-report.md
  incident-review.md
  assessor-signoff.md
```

For each test, record version/config hash, start offsets, topic partitions, consumer group, security mode, Pod placement, offered/processed records, latency percentiles, lag, event age, rebalances, resource metrics, errors and review status. Never include passwords, tokens, private keys or real customer payloads.

## 29. 100-point assessment

| Domain | Points | Gate |
|---|---:|---|
| Approved design, isolation and abort criteria | 10 | Critical |
| Kafka/Kubernetes baseline and topic readiness | 10 | Critical |
| Consumer fetch throughput and latency baseline | 15 | Critical |
| Fetch minimum, wait and response-size tuning | 10 | Normal |
| Poll/processing and offset commit correctness | 15 | Critical |
| Group parallelism, assignment and rebalances | 10 | Critical |
| Kubernetes HPA/KEDA scaling and backpressure | 10 | Normal |
| Resource, broker and downstream correlation | 10 | Critical |
| Secure-listener and ACL validation | 5 | Critical |
| Recovery evidence, runbooks and signoff | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. Automatic **Fail** for unapproved production offset resets, disabling TLS verification, ignoring Kafka quorum/ISR degradation, fabricated benchmark results, or a demonstrated unrecovered data-loss path.

## 30. Cleanup, references and handoff

Remove only the chapter-owned synthetic KafkaTopic, test consumer Deployment and approved benchmark Pods after evidence collection. Do not delete broker PVCs or unrelated consumer groups/topics. Preserve sanitized records and incident evidence under retention policy.

**References:** [Apache Kafka Consumer Configs](https://kafka.apache.org/documentation/#consumerconfigs), [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Kubernetes Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).

**Next:** Chapter 034 — Kafka Broker Performance Tuning, JVM, Network, Storage and Kubernetes Resource Optimization.

---

**Verification boundary:** GitHub publication establishes document availability only. Consumer benchmark results, offset integrity, secure-listener tests and independent technical/security review remain Pending until live evidence is collected.
