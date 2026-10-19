# Chapter 016 — Kafka Producer Architecture, Acknowledgments, Retries and Idempotence on Kubernetes

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 04 — Producers, Consumers and Consumer Groups  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–015; [Kubernetes-first lab foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers, application reliability engineers  
**Publication:** Complete · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety:** Run all labs against an isolated Kafka cluster and disposable topic. Never reduce `min.insync.replicas`, enable unclean leader election, delete PVCs, or disrupt a production broker to make a producer succeed. Kafka console-producer exit status and idempotence settings alone do not prove end-to-end exactly-once delivery.

## 1. Learning objectives

By the end of this chapter, you can:

1. Explain producer metadata discovery, key serialization, partition selection, batching, compression, and broker acknowledgments.
2. Distinguish `acks=0`, `acks=1`, and `acks=all` with RF=3/minISR=2.
3. Explain producer retries, `delivery.timeout.ms`, `request.timeout.ms`, and delivery ambiguity.
4. Configure Kafka producer idempotence and understand its scope and ordering requirements.
5. Design safe retry, backoff, and application-level deduplication for Kubernetes workloads.
6. Deploy a Kubernetes Job that exercises a producer and inspect Pod/Job failure evidence.
7. Capture broker metadata, produced records, partition offsets, and client errors.
8. Establish producer SLIs/SLOs and incident runbooks for availability and durability.

## 2. Producer data path and failure domains

```text
 Kubernetes Deployment / Job / application Pod
                    |
            serializer + partitioner
                    |
       producer record accumulator/batches
                    |
         metadata cache + network client
                    |
         Kafka bootstrap Service (discovery)
                    |
       partition leader broker (Strimzi Pod)
                    |
              append to local log
                    |
          follower replica fetch / ISR
                    |
         producer acknowledgment response
                    |
      application retry / reconciliation logic
```

The bootstrap Service is for discovering broker metadata; the producer ultimately connects to advertised broker listeners. Kubernetes DNS, Service configuration, network policies, TLS certificates, Kafka authorization, broker Pod placement, PVC latency, and client retry behavior can all affect success.

**Important:** a Kubernetes Job restart or Deployment reschedule can create a new producer session. Kafka producer idempotence is scoped to supported producer protocol semantics, **not** a global guarantee that a business event will never be submitted twice across application restarts.

## 3. Producer architecture internals

### 3.1 Serialization and partitioning

A producer serializes keys and values to bytes, selects a partition, batches records per partition, and sends Produce requests to the current partition leader. With a stable key serializer, partitioner and partition count, the same key normally maps to the same partition; increasing partitions can change key routing and break ordering assumptions across the change.

### 3.2 Batching and compression

| Setting | Reliability/performance role | Operational trade-off |
|---|---|---|
| `batch.size` | Upper target batch buffer per partition | Larger batches may improve throughput but increase memory usage |
| `linger.ms` | Wait briefly to accumulate batch | More batching versus added latency |
| `compression.type` | Reduce network/disk bytes | CPU cost and codec compatibility |
| `buffer.memory` | Producer buffering budget | Buffer exhaustion under broker slowness |
| `max.block.ms` | Bounds blocking for metadata/buffer availability | Application backpressure and errors |
| `delivery.timeout.ms` | Upper bound on reporting send completion/failure | Must account for linger/retries/request timeout |
| `request.timeout.ms` | Bounds an individual request wait | Too low can amplify retries |
| `retry.backoff.ms` | Wait between retry attempts | Retry storm versus recovery speed |

**Configuration rule:** choose these from measured workload behavior. The Java client, CLI and non-Java clients can have different defaults and configuration surfaces; verify the installed client version.

### 3.3 Acknowledgment semantics

| `acks` | Broker acknowledgment behavior | Durability concern |
|---|---|---|
| `0` | Producer does not wait for broker acknowledgment | Application cannot confirm broker acceptance |
| `1` | Leader acknowledges after its local append | Acknowledged data can be lost on leader failure before replication |
| `all` / `-1` | Leader waits for the required ISR acknowledgment conditions | Stronger durability; writes can fail when ISR falls below min ISR |

For critical workloads, RF=3, `min.insync.replicas=2`, `acks=all`, and idempotence are a common starting point. These are **not** an end-to-end exactly-once guarantee and do not replace cross-zone placement, application deduplication, or DR planning.

### 3.4 Idempotent producer protocol

With supported Kafka clients, `enable.idempotence=true` uses producer IDs, epochs and per-partition sequence numbers so broker retries do not append duplicate records for the same producer session. Compatible settings generally include `acks=all`, retries enabled, and `max.in.flight.requests.per.connection` no greater than five. A client should reject conflicting configurations rather than silently weakening guarantees.

Idempotence does **not** prevent:

- An application creating the same business event twice.
- A new producer instance replaying an event after a restart.
- Duplicate effects in a database or downstream API.
- An event being reprocessed by a consumer after an offset commit failure.
- Cross-topic atomicity without a properly configured transactional producer and consumer workflow.

## 4. Lab environment and readiness

Use the shared [Kubernetes-first Kafka lab](../kubernetes/README.md). This chapter assumes namespace `kafka-lab`, cluster `sre-kafka`, Kafka bootstrap `sre-kafka-kafka-bootstrap:9092`, and a `kafka-cli` Pod with Kafka CLI tools at `/opt/kafka/bin`. The internal plaintext listener is **lab-only**. Production workloads require approved TLS/authentication and least-privilege ACLs.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch16
```

Stop if Kafka Ready is false, controller quorum is degraded, broker Pods/PVCs are unhealthy, or the namespace is not a disposable lab. Verify the installed Strimzi KafkaTopic CRD supports `kafka.strimzi.io/v1`; substitute the supported version if needed.

## 5. Lab A — Create a durable producer topic

Save `topic-ch16.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-producer-ch16
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

```bash
kubectl apply --dry-run=server -f topic-ch16.yaml
kubectl apply -f topic-ch16.yaml
kubectl -n kafka-lab get kafkatopic sre-producer-ch16 -o yaml \
  > evidence-ch16/topic-cr.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-producer-ch16 \
  | tee evidence-ch16/topic-before.txt
```

**Acceptance:** six partitions, RF=3, full ISR=3, all leaders valid, and effective min ISR=2. Confirm topic state in Kafka metadata, not merely the Kubernetes CR.

## 6. Lab B — Baseline `acks=all` and keyed ordering

```bash
printf '%s\n' \
  'customer-101:event-1601' \
  'customer-101:event-1602' \
  'customer-101:event-1603' \
  'customer-202:event-1604' \
  'customer-202:event-1605' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-producer-ch16 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true \
  --property key.separator=:
```

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-producer-ch16 --from-beginning --max-messages 5 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch16/baseline-records.txt
```

**Acceptance:** five unique event IDs, `customer-101` records in increasing offset order on one partition, and `customer-202` likewise. Do not infer global ordering across partitions.

## 7. Lab C — Compare acknowledgment policies safely

**Read-only design exercise:** document the expected outcomes for `acks=0`, `acks=1`, and `acks=all` under:

1. All three ISR members healthy.
2. One broker unavailable, ISR=2.
3. Two broker replicas unavailable, ISR=1.
4. Leader failure before a follower fetch.
5. Network timeout after the broker commits the record.

Do **not** inject a two-broker failure. The point is to demonstrate why `acks=all` plus min ISR enforces a safer failure mode and why a client timeout does not prove that a record was absent.

**Acceptance:** a written matrix that distinguishes producer-visible success, possible Kafka commit, and application delivery ambiguity.

## 8. Lab D — Idempotence configuration validation

Inspect the Kafka CLI help and version:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh --help
```

Run a second producer with explicitly compatible properties:

```bash
printf 'customer-303:event-1606\n' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-producer-ch16 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --producer-property max.in.flight.requests.per.connection=5 \
  --producer-property delivery.timeout.ms=30000 \
  --property parse.key=true --property key.separator=:
```

**Acceptance:** `event-1606` is readable. This proves the producer can run with idempotence enabled; it does **not** prove duplicate suppression under retries. A dedicated client fault test is needed for that claim.

## 9. Lab E — Batching and compression comparison

Run a controlled small-batch producer:

```bash
printf '%s\n' \
  'perf-1:batch-1' 'perf-2:batch-2' 'perf-3:batch-3' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-producer-ch16 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --producer-property linger.ms=10 \
  --producer-property batch.size=32768 \
  --producer-property compression.type=lz4 \
  --property parse.key=true --property key.separator=:
```

Compare against the baseline's configuration, noting that nine tiny records are **not** enough to benchmark throughput or compression ratio. For a meaningful performance test, use a dedicated load generator and measure records/s, bytes/s, p95/p99 latency, producer buffer wait, CPU, and broker network/disk utilization. Never claim improvement without measured results.

## 10. Lab F — Kubernetes Job producer execution

A production producer is normally a Deployment or application service; this lab uses a short-lived **Job** to demonstrate Pod scheduling, Job retries and duplicate-business-event risk.

First identify the actual CLI container image and security context:

```bash
kubectl -n kafka-lab get pod kafka-cli -o jsonpath='{.spec.containers[0].image}{"\n"}'
kubectl -n kafka-lab get pod kafka-cli -o yaml \
  > evidence-ch16/cli-pod-spec.yaml
```

Create `producer-job-ch16.yaml` and replace `<MATCHING_KAFKA_CLI_IMAGE>` with the verified image (prefer an immutable digest). Confirm the image has `/bin/sh` and Kafka scripts at `/opt/kafka/bin`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: producer-ch16
  namespace: kafka-lab
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: producer-ch16
    spec:
      restartPolicy: Never
      containers:
        - name: producer
          image: <MATCHING_KAFKA_CLI_IMAGE>
          command: ["/bin/sh", "-ec"]
          args:
            - |
              printf 'job-16:event-1607\n' |
                /opt/kafka/bin/kafka-console-producer.sh \
                  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
                  --topic sre-producer-ch16 \
                  --producer-property acks=all \
                  --producer-property enable.idempotence=true \
                  --property parse.key=true \
                  --property key.separator=:
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

```bash
kubectl apply --dry-run=server -f producer-job-ch16.yaml
kubectl apply -f producer-job-ch16.yaml
kubectl -n kafka-lab wait --for=condition=complete job/producer-ch16 --timeout=180s
kubectl -n kafka-lab logs job/producer-ch16 \
  | tee evidence-ch16/job-producer-logs.txt
kubectl -n kafka-lab get job,pod -l app=producer-ch16 -o wide
```

**Acceptance:** Job completes, `event-1607` is readable from Kafka, and Job/Pod events are captured. If the Job is restarted or recreated after an ambiguous outcome, the same event can be produced twice even with Kafka idempotence. Use a stable business event ID and downstream deduplication.

## 11. Lab G — Delivery ambiguity tabletop

**No broker fault injection.** Model these outcomes:

| Producer observation | Possible broker state | Safe next action |
|---|---|---|
| Success acknowledgment | Record accepted under configured policy | Track event ID and downstream delivery |
| Timeout | Record may or may not be committed | Reconcile event ID before application retry |
| `NOT_ENOUGH_REPLICAS` | ISR below write policy | Restore replicas; preserve min ISR |
| Authorization failure | Principal lacks Write permission | Fix ACL/principal, not broker security |
| Metadata timeout | DNS/network/listener/broker discovery issue | Diagnose connectivity and advertised listeners |
| Job restarted | New producer session may repeat event | Business-level idempotency |

**Acceptance:** incident worksheet contains at least one ambiguity case and a non-destructive reconciliation plan.

## 12. Lab H — Kubernetes producer connectivity troubleshooting

Collect:

```bash
kubectl -n kafka-lab get svc,endpointslices -o wide \
  | tee evidence-ch16/services-endpoints.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch16/pods-connectivity.txt
kubectl -n kafka-lab describe job producer-ch16 \
  | tee evidence-ch16/job-describe.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  | tail -50 | tee evidence-ch16/events.txt
```

Inspect DNS, bootstrap listener, broker advertised endpoints, NetworkPolicies, TLS/SASL credentials, Kubernetes ServiceAccount permissions, and Kafka ACLs. Avoid logging client Secrets or private keys.

## 13. Lab I — Validate producer ordering and record accounting

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-producer-ch16 --from-beginning --max-messages 10 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch16/all-records.txt
```

The expected IDs are `event-1601` through `event-1607` plus `batch-1`, `batch-2`, and `batch-3` (ten total) **if every preceding producer command succeeded exactly once**. Inspect actual output and investigate missing/duplicate IDs. Use offsets and keys to validate within-partition order, not global arrival order.

## 14. Lab J — Producer reliability acceptance script

Save as `verify-ch16.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
TOPIC=sre-producer-ch16
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka Ready'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/6] Kafka metadata'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

echo '[4/6] Replica and ISR health'
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++
    if(rf!=3 || isr!=3) bad++
  }
  END {
    if(seen!=6 || bad){print "FAIL: partitions="seen" degraded="bad; exit 1}
    print "PASS: six partitions, RF=3, ISR=3"
  }'

echo '[5/6] Kafka broker API'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[6/6] Topic effective config'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name "$TOPIC" --describe

echo 'PASS: metadata acceptance only; producer event reconciliation is separate'
```

```bash
chmod +x verify-ch16.sh
./verify-ch16.sh | tee evidence-ch16/acceptance.txt
```

**Coverage limits:** this script checks cluster/topic metadata, not producer p99, actual event count, application deduplication, cross-AZ resilience, security controls, or exactly-once processing. Those require separate checks and evidence.

## 15. Eight production incident scenarios

### Incident 1 — Producer `NOT_ENOUGH_REPLICAS`

**Signal:** writes requiring `acks=all` fail as ISR falls below min ISR.

**Investigate:** topic ISR, broker Pod/PVC health, replica fetch lag, controller quorum.

**Mitigate:** restore replica health. Do not lower min ISR to conceal the incident.

### Incident 2 — Duplicate business events after Job retry

**Signal:** same business event ID appears twice after Pod or Job restart.

**Investigate:** Job restart/backoff, producer session changes, ambiguous acknowledgment, application retry.

**Mitigate:** deduplicate using stable business IDs; idempotent producer alone does not span independent sessions.

### Incident 3 — Producer metadata timeout

**Signal:** client can reach bootstrap Service but cannot reach advertised broker listeners.

**Investigate:** Kubernetes DNS, Services, listener addresses, NetworkPolicies, TLS/SASL config.

**Mitigate:** correct advertised listener and network access, preserve authentication.

### Incident 4 — Producer buffer exhaustion

**Signal:** `max.block.ms` exceeded, buffer allocation wait rises, application stalls.

**Investigate:** broker latency, batch settings, network pressure, producer metrics and Pod memory.

**Mitigate:** restore throughput or apply backpressure; do not increase buffer.memory without memory capacity review.

### Incident 5 — Unexpected key ordering

**Signal:** same key records appear in different partitions or out of intended sequence.

**Investigate:** partition count changes, serializer/partitioner, producer concurrency and retry settings.

**Mitigate:** stabilize key routing and producer configuration; use versioned-topic migration when partition-count changes alter ordering.

### Incident 6 — Compression-related latency regression

**Signal:** producer CPU increases and p99 worsens after codec change.

**Investigate:** client CPU limits, codec choice, batch size, broker decompression behavior.

**Mitigate:** benchmark alternative codec/batch settings and revert reviewed config if needed.

### Incident 7 — Authentication or authorization failure

**Signal:** `TopicAuthorizationException`, SSL handshake error, SASL failure.

**Investigate:** KafkaUser, Secrets, certificates, principal ACLs and NetworkPolicies.

**Mitigate:** rotate/fix scoped credentials and permissions; never disable authentication to make the lab pass.

### Incident 8 — Producer timeout after leader election

**Signal:** delivery times out during broker recovery, but record may already be committed.

**Investigate:** leader epochs, topic offsets, producer error logs, unique event IDs and downstream effects.

**Mitigate:** reconcile actual records and deduplicate before retrying; classify ambiguous results separately.

## 16. Troubleshooting matrix

| Symptom | Kubernetes evidence | Kafka/client evidence | Unsafe response |
|---|---|---|---|
| Producer Pod Pending | Scheduler events, quota, image pull | None yet | Grant broad privileges |
| Producer Job fails | Pod logs, exit code, DNS | Broker errors | Blind retry without event ID |
| Write rejected | Broker Pod/PVC health | ISR, min ISR, acks | Lower min ISR |
| Connection fails | Service, endpoints, NetworkPolicy | Metadata/listener/TLS | Disable TLS |
| High p99 | CPU throttling, node pressure | Batching, broker request latency | Arbitrary timeouts |
| Duplicate events | Job restarts | Producer sessions, event IDs | Assume idempotence solves all |
| Out-of-order | Pod rollout, app version | Key/partitioner/offsets | Add partitions blindly |
| Timeout ambiguity | Pod/client logs | Kafka offsets and event IDs | Retry indefinitely |

## 17. Production runbooks

### Runbook A — Producer write outage

1. Declare scope and capture producer errors, affected topics, client versions and business SLIs.
2. Inspect Kafka partition leaders, ISR and min ISR, plus KRaft quorum.
3. Map broker IDs to Kubernetes Pods, nodes, PVCs and network conditions.
4. Restore broker or connectivity health without weakening durability.
5. Verify bounded retries, write success and consumer-visible event IDs.
6. Record incident timeline and customer impact.

### Runbook B — Duplicate event investigation

1. Identify stable business event IDs and duplicate frequency.
2. Correlate producer session IDs, Job/Pod restarts, retries and timeouts.
3. Inspect Kafka partitions/offsets and downstream writes.
4. Apply application-level deduplication or transactional processing where appropriate.
5. Validate correction in staging and monitor recurrence.
6. Document exactly-once scope and residual limitations.

### Runbook C — Producer performance regression

1. Capture baseline throughput, p95/p99, error rate and broker capacity.
2. Inspect batch.size, linger.ms, compression, buffer.memory and client CPU.
3. Compare network/disk and broker request metrics.
4. Change one variable in a controlled staging benchmark.
5. Roll back if SLOs regress or resource limits are exceeded.
6. Save benchmark and approval evidence.

### Runbook D — Kubernetes producer connectivity

1. Confirm namespace, Service, endpoints and DNS.
2. Inspect advertised broker listeners and network path from producer Pod.
3. Validate TLS/SASL secrets, KafkaUser principal and topic ACLs.
4. Review NetworkPolicies and cluster egress controls.
5. Run a least-privilege authenticated smoke test.
6. Preserve sanitized logs and restore intended security posture.

### Runbook E — Ambiguous acknowledgment recovery

1. Stop unbounded application retries.
2. Capture client request IDs, timestamps, business event IDs and error type.
3. Search Kafka for committed records and inspect downstream state.
4. Reconcile duplicates/missing events before resubmission.
5. Resume with bounded retry, backoff and idempotency controls.
6. Obtain business owner acceptance for unresolved uncertainty.

## 18. SLO and observability requirements

Track producer send rate, error rate, retry rate, record queue time, buffer wait time, request latency, p99 end-to-end acknowledgment latency, bytes/sec, compression ratio, per-partition skew, broker under-min-ISR and offline partitions, Kubernetes Pod restart/OOM rate, and business event deduplication rate.

Example **SLO design**, not a measured claim:

- Successful acknowledged critical events / attempted eligible critical events over a rolling window.
- p99 producer acknowledgment latency for a representative workload.
- Maximum time from event creation to Kafka acknowledgment.
- Number of unexplained duplicate business events after deduplication.
- Error-budget burn for producer-side delivery failures.

Define targets from business requirements and observed baselines; do not copy arbitrary numerical thresholds into production alerts.

## 19. Enterprise readiness checklist

- [ ] Producer client version and configuration compatibility recorded.
- [ ] Kafka topic RF/min ISR/retention approved.
- [ ] Producer `acks=all` and idempotence configured for critical streams.
- [ ] Key serialization, partitioner and ordering contracts documented.
- [ ] Retry, delivery timeout, backoff and max in-flight reviewed.
- [ ] Business event IDs and application deduplication designed.
- [ ] Kubernetes Pod resources, Job restart semantics and network access reviewed.
- [ ] TLS/SASL, Kafka ACLs and Secrets handling verified for production.
- [ ] Topic ISR and broker health confirmed before load testing.
- [ ] Producer p99, errors, retries and business SLIs monitored.
- [ ] Ambiguous delivery recovery runbook rehearsed.
- [ ] Automated acceptance and unique event reconciliation evidence retained.
- [ ] Independent security and live execution reviews tracked.

## 20. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain producer data path, metadata and partition routing | 10 |
| Compare acks and ISR durability behavior | 10 |
| Configure idempotence with compatible retry settings | 10 |
| Create and verify Kubernetes-managed KafkaTopic | 10 |
| Produce keyed events and validate ordering/offsets | 10 |
| Explain batching, compression and backpressure | 10 |
| Deploy and verify Kubernetes producer Job | 10 |
| Reconcile event IDs and delivery ambiguity | 10 |
| Execute automated topic health acceptance | 10 |
| Produce incident analysis, runbooks and SLO design | 10 |

**Pass:** ≥85/100 with all critical safety controls and captured execution evidence. Written lab instructions do not count as execution.

## 21. Cleanup and next chapter

Only after saving evidence and confirming the resources are disposable:

```bash
kubectl -n kafka-lab delete job producer-ch16 --ignore-not-found
kubectl -n kafka-lab delete kafkatopic sre-producer-ch16 --ignore-not-found
```

Topic deletion can permanently remove records. Do not delete Kafka PVCs or the shared lab cluster.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/), [Kubernetes networking](https://kubernetes.io/docs/concepts/services-networking/).

**Next:** Chapter 017 — Kafka Consumer Architecture, Poll Loop, Offset Management and Kubernetes Workload Reliability.

---

**Verification boundary:** GitHub publication is not live execution. Kubernetes Job, producer semantics, version-specific CRD/API compatibility, security review and production readiness remain Pending.
