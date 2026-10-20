# Chapter 035 — Kafka End-to-End Performance Benchmarking, Capacity Acceptance and Kubernetes SRE Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 07 — Performance Tuning and Benchmarking (5/5, final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–034, especially 031–034, Kafka security, observability and SRE change control  
**Audience:** Kafka SRE, platform engineer, DBRE, performance engineer, technical assessor and incident commander  
**Publication:** Published · **Live capstone execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This capstone is a *reference acceptance plan*, not proof that a real cluster meets performance targets. Execute only in an approved disposable Kubernetes cluster with synthetic data, bounded workloads, healthy KRaft quorum, verified ISR and an abort owner. Never weaken TLS/SASL, replication factor, minISR or access controls to obtain better benchmark scores. Do not reset shared consumer offsets, delete broker PVCs, stress production dependencies or assume a kind/minikube result represents EKS/AKS/GKE capacity.

## 1. Capstone mission

Design, execute, diagnose and defend a production-style Kafka performance acceptance test across producers, brokers, consumers, Kubernetes infrastructure and failure recovery. The capstone integrates the baseline methods of Chapter 031, producer tuning of Chapter 032, consumer tuning of Chapter 033 and broker tuning of Chapter 034.

**End state:** a reviewer can reproduce the experiment from manifests, client versions, configuration hashes and evidence; distinguish offered from achieved throughput; verify p95/p99 latency, lag and recovery; confirm durability/security invariants; and approve or reject capacity based on explicit gates.

## 2. Learning outcomes

You will be able to:

1. Translate business event volume, size, peaks and latency SLOs into Kafka workload assumptions.
2. Estimate aggregate and per-broker ingress, replication, storage and network requirements.
3. Design a multi-phase benchmark with controlled warm-up, steady state, burst, soak and recovery.
4. Measure producer acknowledgment, broker request, consumer fetch and end-to-end processing latency separately.
5. Determine sustainable throughput rather than peak transient throughput.
6. Evaluate partition, leader and consumer group parallelism under a realistic key distribution.
7. Assess JVM, page cache, CPU throttling, storage IOPS, network, TLS/SASL and quotas.
8. Validate at-least-once delivery, idempotence, offsets and replay safety during client failures.
9. Execute a reviewed, operator-managed GitOps tuning change and rollback.
10. Deliver a 100-point enterprise reliability and capacity acceptance package.

## 3. Reference architecture

```text
Kubernetes namespace: kafka-lab
  |
  +-- Approved synthetic producer Job(s)
  |     +-- acks=all / idempotence / bounded rate
  |     +-- TLS/SASL for secure acceptance
  |     +-- client metrics and callbacks
  |
  +-- Strimzi Kafka KRaft cluster: sre-kafka
  |     +-- controller quorum health
  |     +-- KafkaNodePool broker Pods
  |     +-- RF3 / minISR2 topic
  |     +-- PVC log storage + page cache
  |     +-- JMX exporter / Prometheus
  |
  +-- Synthetic consumer Deployment(s)
  |     +-- group membership / commits
  |     +-- bounded handler delay
  |     +-- idempotent test sink / event ledger
  |
  +-- Observability stack
  |     +-- producer p95/p99 / success/errors
  |     +-- broker queues / CPU / GC / ISR
  |     +-- consumer lag / event age / commits
  |     +-- Kubernetes CPU / memory / PVC / network
  |
  +-- Evidence archive and independent assessor
```

## 4. Workload and capacity model

Let:

- `R` = incoming records/second.
- `S` = average serialized record size in bytes.
- `F` = replication factor.
- `H` = retained hours.
- `C` = observed compression ratio (compressed bytes / uncompressed bytes).
- `B` = number of brokers.
- `P` = topic partitions.
- `G` = actively assigned consumer group members.

Approximate logical ingress bytes/s: `R × S`. Approximate compressed log ingress: `R × S × C`. A first-order **cluster-wide** replicated storage write estimate is `R × S × C × F`, excluding indexes, overhead, compaction and retries. Approximate retained replicated payload bytes: `R × S × C × F × H × 3600`, before headroom and storage-engine effects. Per-broker average is the cluster total divided by `B` only when leaders/replicas and traffic are balanced.

**Example (illustrative, not measured):** 5,000 records/s × 1,024 B = 5.12 MB/s logical ingress. With `C=0.6`, RF3, 24-hour retention, replicated payload estimate is ~796 GB cluster-wide (decimal), before indexes, overhead, compaction, segment behavior and reserve capacity. Actual requirements depend on compression and payload distribution.

**Capacity caution:** replication and fetch traffic, recovery, leader imbalance, storage throughput limits and disk headroom require additional modeling. Do not use the simple storage formula as a production sizing guarantee.

## 5. Explicit SLO and acceptance gates

The following are **sample lab targets** to be approved before execution, not results:

| Gate | Example threshold | Evidence |
|---|---|---|
| Offered workload | 1,000 records/s at 1 KiB | Generator config and counters |
| Acknowledged throughput | ≥95% of offered rate at steady state | Producer callbacks and broker bytes |
| Producer p99 acknowledgment latency | ≤250 ms | Client histogram |
| End-to-end processing p99 | ≤2 seconds | Event ledger and sink timestamps |
| Consumer lag | Stable or draining during steady state | Group offset trend |
| Burst recovery | Backlog drains within 10 minutes | Lag and processed-rate graph |
| Producer delivery errors | 0 unexplained failures | Callback/error counters |
| Data integrity | No missing accepted event IDs | Event ledger reconciliation |
| Broker health | No sustained under-minISR/ISR shrink | ReplicaManager metrics |
| KRaft health | Quorum remains healthy | Quorum status and controller metrics |
| Kubernetes health | No OOMKilled or sustained unacceptable throttling | Pod/node metrics |
| Security | TLS/SASL/ACL validation succeeds | Redacted client/security checks |
| Change rollback | Reviewed reversal demonstrably restores baseline | GitOps commit and health evidence |

A reviewer must adjust thresholds to the actual cluster and business SLO before testing. Failure of a critical safety gate invalidates the run even if throughput appears high.

## 6. Test phases and fixed variables

| Phase | Duration (example) | Workload | Purpose |
|---|---:|---|---|
| P0 Preflight | 15 min | None | Verify environment and approvals |
| P1 Warm-up | 5 min | 25% target | Stabilize caches and client connections |
| P2 Baseline | 10 min | 100% target | Measure steady-state throughput/latency |
| P3 Burst | 5 min | 150% target | Identify backpressure and lag growth |
| P4 Recovery | ≤10 min | 50% target | Demonstrate backlog drain |
| P5 Soak | 30 min | 75% target | Identify GC/storage drift |
| P6 Client failure | 10 min | 75% target | Verify replay and recovery |
| P7 Security/rollback | As approved | Matched load | Validate secure mode and revert |

These are examples only; cluster and storage headroom must support the chosen load. Repeat comparable trials at least three times where practical. Record per-trial warm-up, duration, configuration, key distribution and security mode. Do not average p99 values as if they form a pooled histogram.

## 7. Lab 01 — Capstone approval and change freeze

Create `evidence-ch35/approval-and-scope.md` with:

- Cluster context, namespace, owner, change ID and assessment date.
- Kafka, Strimzi, Kubernetes, client, storage and security versions.
- Permitted synthetic topics, service accounts, clients and network destinations.
- CPU, memory, disk, network, message-count and duration limits.
- Abort triggers, escalation contact, rollback and evidence retention.
- Named independent assessor and explicit production exclusions.

**Acceptance:** approved and signed scope before any write/load operation.

## 8. Lab 02 — Read-only platform inventory

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch35
kubectl config current-context | tee evidence-ch35/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch35/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch35/listeners.txt
kubectl -n "$NS" get kafka "$CLUSTER" -o yaml \
  > evidence-ch35/kafka-cr.yaml
```

**Acceptance:** correct disposable context, cluster Ready, approved resources, available metrics and capacity.

## 9. Lab 03 — Validate KRaft, ISR and storage headroom

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch35/quorum-before.txt
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch35/pvcs-before.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch35/pod-placement.txt
```

Confirm quorum voters, replica health, disk utilization and PVC latency using approved telemetry. `kubectl get pvc` alone does not show filesystem utilization. **Acceptance:** no degraded KRaft/ISR state.

## 10. Lab 04 — Provision synthetic benchmark topic

Save `kafkatopic-capstone-ch35.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-capstone-perf-ch35
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 7200000
```

```bash
kubectl apply --dry-run=server -f kafkatopic-capstone-ch35.yaml
# Approved disposable cluster only:
kubectl apply -f kafkatopic-capstone-ch35.yaml
kubectl -n kafka-lab get kafkatopic sre-capstone-perf-ch35 -o wide \
  | tee evidence-ch35/topic.txt
```

**Acceptance:** KafkaTopic Ready, RF3/minISR2, six partitions and bounded retention.

## 11. Lab 05 — Producer baseline

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-producer-perf-test.sh \
  --topic sre-capstone-perf-ch35 \
  --num-records 100000 \
  --record-size 1024 \
  --throughput 1000 \
  --producer-props \
    bootstrap.servers=sre-kafka-kafka-bootstrap:9092 \
    acks=all \
    enable.idempotence=true \
    linger.ms=5 \
    batch.size=65536 \
    compression.type=lz4 \
  | tee evidence-ch35/producer-baseline.txt
```

**Acceptance:** achieved rate, successful acknowledgments, errors and reported latency captured. The CLI producer performance tool does not establish application-level end-to-end delivery.

## 12. Lab 06 — Consumer baseline

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-perf-test.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-perf-ch35 \
  --messages 10000 \
  --group sre-capstone-ch35-baseline \
  --timeout 30000 \
  | tee evidence-ch35/consumer-baseline.txt
```

Confirm supported CLI flags with `--help` and verify the fresh group starts at intended offsets. **Acceptance:** fetch throughput measured, separate from business processing and durable sink acknowledgment.

## 13. Lab 07 — Application event ledger and data integrity

Implement an approved synthetic event format:

```json
{
  "event_id": "synthetic-unique-id",
  "sequence": 1,
  "partition_key": "tenant-test-001",
  "created_at_utc": "synthetic-timestamp",
  "payload_bytes": 1024
}
```

Use an idempotent test sink that records `event_id`, processing outcome and durable commit timestamp. A real workload generator must create distinct event IDs and timestamps; the JSON above is a schema example, not a runnable generator.

**Acceptance:** reconcile accepted producer event IDs with processed event IDs; classify duplicates and missing records. Do not equate broker offsets with business completion.

## 14. Lab 08 — Producer tuning candidate matrix

Run matched trials changing only one dimension at a time:

| Candidate | Linger | Batch | Codec | Acks | Idempotence |
|---|---:|---:|---|---|---|
| Baseline | 5 ms | 64 KiB | lz4 | all | true |
| Low latency | 0 ms | 16 KiB | lz4 | all | true |
| Batch efficiency | 10 ms | 128 KiB | lz4 | all | true |
| Compression | 5 ms | 64 KiB | zstd | all | true |

Record actual client version, payload entropy, CPU, network and p99. **Acceptance:** no durability compromise and justified candidate selection.

## 15. Lab 09 — Consumer fetch and poll matrix

Compare approved `fetch.min.bytes`, `fetch.max.wait.ms`, `max.partition.fetch.bytes`, `max.poll.records` and commit-after-processing settings. Use separate synthetic groups and identical start-offset policy.

**Acceptance:** fetched records/s, processed records/s, p99 handler latency, commits, group stability and event age measured independently.

## 16. Lab 10 — Partition and consumer parallelism

For six partitions, compare consumer group sizes 1, 3, 6 and 8 with constant **aggregate** offered throughput. Confirm assigned partitions and idle members; extra consumers do not create more exclusive partition assignments.

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-capstone-ch35-baseline \
  | tee evidence-ch35/group-assignments.txt
```

**Acceptance:** observed scaling efficiency, rebalances and saturation point.

## 17. Lab 11 — Broker request and JVM baseline

Capture Produce/Fetch request queue, local/remote/response latency, handler idle, network processor idle, JVM heap/GC and direct buffers. Match timestamps with producer and consumer trial windows.

**Acceptance:** evidence identifies the dominant request stage and avoids speculative JVM tuning.

## 18. Lab 12 — Kubernetes CPU, memory and placement

```bash
kubectl -n kafka-lab top pods \
  | tee evidence-ch35/pod-top.txt
kubectl top nodes | tee evidence-ch35/node-top.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch35/placement.txt
```

Use cAdvisor/Prometheus for throttling, OOM and resource saturation; Metrics Server is optional and does not report all required signals. **Acceptance:** client and broker resource constraints separated.

## 19. Lab 13 — PVC storage and retention under load

Collect PVC utilization, disk write/read latency, IOPS, throughput, burst credits where applicable, page cache and log segment growth. Do not alter retention or delete PVCs to pass a test. **Acceptance:** sustained-load storage headroom quantified, not inferred from provisioned volume size.

## 20. Lab 14 — Steady-state and burst phases

Run bounded P2/P3 workload through approved producer Jobs with `activeDeadlineSeconds`, immutable image digests and resource limits. Monitor producer errors, p99, consumer lag, KRaft and ISR continuously.

**Acceptance:** stable baseline and controlled burst response. Abort on health threshold breach rather than waiting for benchmark completion.

## 21. Lab 15 — Backlog recovery and catch-up time

During P4 reduce offered load and measure **net drain rate** = processed records/s minus new records/s. Estimate catch-up time as backlog / positive net drain rate. Compare estimate to actual lag/event-age curves.

**Acceptance:** backlog returns to approved threshold within declared recovery window; no unbounded retries or downstream overload.

## 22. Lab 16 — Thirty-minute soak and variance analysis

Run an approved 30-minute bounded soak with periodic samples of p99, CPU throttling, JVM GC, PVC latency, log growth, ISR and consumer event age. Stop on unsafe drift. Repeatability requires consistent offered load, partitions, security mode and placement.

**Acceptance:** no hidden resource leak or progressive degradation. If monitoring is unavailable, mark **Blocked**, not Pass.

## 23. Lab 17 — Client-only failure injection

In a disposable synthetic consumer group, terminate **one approved client Pod** during processing. Observe group rebalance, offset commits, replay, event-ID deduplication and recovery. Do not kill Kafka brokers/controllers or modify shared consumer groups.

**Acceptance:** at-least-once processing behavior documented; replay is safe and recovery within agreed SLO.

## 24. Lab 18 — Secure listener and least-privilege acceptance

Repeat a matched test using an approved TLS/SASL listener. Discover actual endpoints from `Kafka.status.listeners`; mount credentials via Kubernetes Secrets with read-only volumes and least-privilege ServiceAccounts. Validate topic/group ACLs. Never log passwords, tokens or private keys.

**Acceptance:** authentication, authorization, hostname verification and matched performance metrics. If no secure listener is available, security gate remains **Pending**.

## 25. Lab 19 — GitOps tuning and rollback

1. Review Kafka/Strimzi/Kubernetes compatibility and served CRD schema.
2. Capture Kafka and KafkaNodePool baseline.
3. Propose **one** broker/NodePool tuning change with expected impact and rollback.
4. Run server-side dry-run and peer review.
5. Apply only in disposable cluster after approval.
6. Observe Strimzi reconciliation, KRaft, ISR and SLOs.
7. Revert via GitOps and verify original state.
8. Attach diff, metrics, operator events and reviewer decision.

**Acceptance:** demonstrable, safe rollback with no silent operator drift.

## 26. Lab 20 — Read-only capstone preflight automation

Save `verify-ch35.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/10] Context'
kubectl config current-context

echo '[2/10] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/10] Strimzi CRDs'
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io kafkatopics.kafka.strimzi.io

echo '[4/10] Cluster and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide

echo '[5/10] Listeners'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[6/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[7/10] Pods'
kubectl -n "$NS" get pods -o wide

echo '[8/10] PVC inventory'
kubectl -n "$NS" get pvc -o wide

echo '[9/10] Benchmark topic (optional)'
if kubectl -n "$NS" get kafkatopic sre-capstone-perf-ch35 >/dev/null 2>&1; then
  kubectl -n "$NS" get kafkatopic sre-capstone-perf-ch35 -o wide
else
  echo 'PENDING: capstone topic not provisioned'
fi

echo '[10/10] CLI availability'
kubectl -n "$NS" exec kafka-cli -- \
  sh -c 'test -x /opt/kafka/bin/kafka-producer-perf-test.sh && test -x /opt/kafka/bin/kafka-consumer-perf-test.sh'

echo 'PASS: read-only Kafka performance capstone preflight.'
echo 'NOT PROVEN: workload SLO, data integrity, recovery, security or capacity acceptance.'
```

```bash
chmod +x verify-ch35.sh
./verify-ch35.sh | tee evidence-ch35/preflight.txt
```

This script is read-only; it does not execute performance phases or imply acceptance.

## 27. Twelve troubleshooting scenarios

### 27.1 Producer meets target but consumer falls behind
**Inspect:** processing throughput, commits, downstream dependencies and partitions. **Recover:** relieve slow stage and verify catch-up.

### 27.2 Producer p99 rises during burst
**Inspect:** client buffer, broker request queue, remote replication and CPU. **Recover:** reduce offered load or approved capacity/tuning.

### 27.3 Throughput plateaus despite adding producers
**Inspect:** broker leaders, network, disk and quotas. **Recover:** address saturated stage, not blindly add clients.

### 27.4 Consumer replicas exceed partitions
**Inspect:** assignments and idle Pods. **Recover:** bound replicas and reconsider partition strategy.

### 27.5 JVM GC pauses distort benchmark
**Inspect:** heap, allocation, CPU throttling and page cache. **Recover:** isolate bottleneck and rerun matched test.

### 27.6 PVC latency spikes during soak
**Inspect:** storage credits, IOPS, compaction and node contention. **Recover:** abort unsafe load and plan capacity.

### 27.7 Under-replicated partitions increase
**Inspect:** follower lag, network and storage. **Recover:** stop load, restore ISR and invalidate run.

### 27.8 KRaft quorum instability
**Inspect:** controller health and resource contention. **Recover:** abort immediately and follow controller incident plan.

### 27.9 Duplicate events after consumer restart
**Inspect:** commit-after-processing and event-ID sink semantics. **Recover:** idempotent replay and ledger reconciliation.

### 27.10 TLS/SASL test has higher CPU
**Inspect:** handshake churn, auth plugin, connection reuse and client placement. **Recover:** optimize without bypassing security.

### 27.11 GitOps tuning causes unexpected rolling restart
**Inspect:** operator events, CRD and desired-state diff. **Recover:** stop further changes and revert reviewed diff.

### 27.12 Benchmark results vary between trials
**Inspect:** warm-up, cache, payload entropy, scheduling, storage credits and background load. **Recover:** control variables and report confidence/variance.

## 28. Eight production runbooks

### Runbook A — Performance acceptance kickoff
1. Confirm approval, owner and change window.
2. Record Kafka/Strimzi/Kubernetes versions.
3. Verify synthetic workload and isolation.
4. Define SLO thresholds and abort criteria.
5. Validate observability and evidence collection.
6. Begin only after independent preflight signoff.

### Runbook B — Producer throughput and latency failure
1. Compare offered versus acknowledged load.
2. Inspect producer CPU/buffering and retries.
3. Correlate broker queue/replication latency.
4. Identify the first saturated stage.
5. Apply approved candidate or rollback.
6. Rerun identical trial and document result.

### Runbook C — Consumer lag and backlog failure
1. Confirm ingress, processed rate and lag trend.
2. Inspect partitions, group assignments and rebalances.
3. Check handler/downstream latency and commits.
4. Stabilize scaling and apply backpressure.
5. Verify positive net drain rate.
6. Confirm recovery SLO and replay integrity.

### Runbook D — Broker resource saturation
1. Identify broker hot spots and leaders.
2. Check CPU throttling, GC and network processors.
3. Inspect PVC IOPS/latency and page cache.
4. Stop unsafe load on ISR/quorum risk.
5. Prepare one reviewed resource/tuning change.
6. Validate health and p99 after reconciliation.

### Runbook E — Data integrity and replay incident
1. Preserve accepted event IDs and committed offsets.
2. Freeze unapproved offset mutations.
3. Reconcile accepted versus durably processed IDs.
4. Identify duplicates, missing events and unknown outcomes.
5. Apply idempotent replay through approved procedure.
6. Document recovery and business impact.

### Runbook F — Security/performance regression
1. Separate TLS, SASL, ACL and network errors.
2. Confirm certificate validation and identity.
3. Inspect handshake CPU and connection reuse.
4. Restore secure configuration, not plaintext bypass.
5. Re-run matched secure trial.
6. Record reviewer approval.

### Runbook G — Tuning rollback
1. Stop load if abort criteria are breached.
2. Freeze unrelated Kafka CR changes.
3. Revert the minimal GitOps diff.
4. Observe Strimzi-managed rollout and KRaft/ISR.
5. Verify original throughput, latency and health.
6. Attach rollback evidence and incident note.

### Runbook H — Final assessor signoff
1. Review approval and workload reproducibility.
2. Validate each critical SLO and safety gate.
3. Review raw logs, metrics and event ledger.
4. Confirm failures and exclusions are disclosed.
5. Score the 100-point rubric.
6. Approve, conditionally approve or reject with actions.

## 29. Evidence package and artifact contract

```text
evidence-ch35/
  approval-and-scope.md
  context.txt
  inventory.txt
  listeners.txt
  kafka-cr.yaml
  quorum-before.txt
  pvcs-before.txt
  pod-placement.txt
  topic.txt
  producer-baseline.txt
  consumer-baseline.txt
  event-ledger-schema.json
  accepted-event-ids.csv
  processed-event-ids.csv
  producer-matrix.csv
  consumer-matrix.csv
  group-assignments.txt
  broker-request-metrics.csv
  jvm-gc-metrics.csv
  pod-top.txt
  node-top.txt
  placement.txt
  storage-soak.csv
  burst-recovery.csv
  soak-metrics.csv
  client-failure.md
  security-acceptance.md
  gitops-diff.patch
  gitops-rollback.md
  preflight.txt
  final-capacity-report.md
  incident-review.md
  assessor-signoff.md
```

Every trial must include timestamp, software/image versions, config hash, topic and group, partition count, payload size/entropy, producer/consumer Pod placement, security mode, offered and achieved load, p50/p95/p99 where available, lag, event age, CPU/GC, PVC latency, ISR/quorum, errors and reviewer. Sanitize addresses, credentials, private keys and customer data. Missing results are **Pending**, never Pass.

## 30. 100-point enterprise capstone assessment

| Domain | Points | Gate |
|---|---:|---|
| Approval, scope, isolation and abort plan | 10 | Critical |
| KRaft/Strimzi/Kubernetes preflight and safety | 10 | Critical |
| Capacity model and workload reproducibility | 10 | Critical |
| Producer throughput and p99 acceptance | 10 | Critical |
| Consumer processing, lag and catch-up | 10 | Critical |
| Broker JVM, request queue and storage evidence | 10 | Critical |
| Kubernetes CPU/memory, placement and scaling | 10 | Normal |
| Client failure recovery and event integrity | 15 | Critical |
| TLS/SASL/ACL and durability invariants | 10 | Critical |
| GitOps rollback, reporting and independent review | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 **and every critical gate passed** with live evidence. **Conditional:** ≥85/100 but noncritical evidence gaps, with explicit remediation and deadline. **Fail:** any critical gate failure, unauthorized load, disabled TLS verification, unapproved offset reset, lost KRaft quorum, ignored under-minISR, unsafe PVC deletion or fabricated benchmark result.

**Publication status is not an assessment result.** All live execution, SLO acceptance and independent review gates remain Pending at publication.

## 31. Final capacity decision template

```text
Cluster/context:
Kafka / Strimzi / Kubernetes versions:
Workload / payload / key distribution:
Offered load:
Acknowledged producer load:
Producer p95 / p99:
Processed consumer load:
End-to-end p95 / p99:
Peak lag and recovery time:
KRaft quorum / ISR health:
Broker CPU / GC / storage headroom:
Security mode and ACL results:
Client failure / event reconciliation:
GitOps change / rollback:
Pass / Conditional / Fail:
Assessor:
Date and evidence link:
```

## 32. Cleanup, references and next part

After approval, delete **only** chapter-owned synthetic KafkaTopic, benchmark Jobs and consumer Deployments; preserve sanitized evidence. Do not delete broker PVCs, operator-managed Secrets, production groups or unrelated topics.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Apache Kafka Operations](https://kafka.apache.org/documentation/#operations), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/).

**Part 07 — Performance Tuning and Benchmarking is complete (Chapters 031–035).**

**Next:** Chapter 036 — Kafka Observability Architecture, JMX Exporter, Prometheus, Grafana and Kubernetes Monitoring Foundations, beginning Part 08 — Monitoring, Metrics and Observability.

---

**Verification boundary:** This Markdown document and its GitHub commit establish publication only. The capstone has **not** been run, its performance targets have **not** been verified and independent technical/security review is still **Pending**.
