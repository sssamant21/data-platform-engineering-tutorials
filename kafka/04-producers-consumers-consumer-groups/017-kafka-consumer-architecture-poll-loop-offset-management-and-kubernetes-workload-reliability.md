# Chapter 017 — Kafka Consumer Architecture, Poll Loop, Offset Management and Kubernetes Workload Reliability

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 04 — Producers, Consumers and Consumer Groups  
**Platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–016; [Kubernetes-first Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers and application reliability engineers  
**Publication:** Complete · **Live lab execution:** Pending · **Security review:** Pending

> **Safety:** Consumer offset resets, topic retention changes, and group manipulation can replay or skip business events. All write operations here use a disposable topic and dedicated consumer group. Never reset offsets for active production consumers; pause workloads, obtain application-owner approval, preserve original offsets and understand the replay/deduplication impact.

## 1. Learning objectives

After this chapter, you can:

1. Trace a Kafka consumer from metadata discovery through partition fetch, poll, processing and offset commit.
2. Explain the distinction between log offset, consumer position, committed offset, log start offset and consumer lag.
3. Compare auto commit and manual commit, and the risks of committing before or after processing.
4. Understand `max.poll.interval.ms`, `session.timeout.ms`, `heartbeat.interval.ms`, `max.poll.records`, and `fetch.max.wait.ms`.
5. Deploy a Kubernetes consumer Job, inspect its lifecycle and reason about restart-driven replay.
6. Diagnose consumer group membership, partition assignment, lag and stalled processing.
7. Practice read-only offset inspection and a **separate opt-in** safe offset reset on a disposable group.
8. Establish consumer reliability SLIs, alerts, runbooks and evidence-based acceptance.

## 2. Consumer architecture

```text
     Kafka broker partition leaders
            |       |       |
          Fetch responses / batches
                    |
         Consumer client in K8s Pod
                    |
           poll() / deserialize
                    |
       application processing + side effects
                    |
       offset commit (group coordinator)
                    |
          __consumer_offsets topic
                    |
      Kubernetes Deployment / HPA / PDB
```

The broker stores records; the consumer stores its **progress** by committing offsets to Kafka's internal group-offset storage. The committed offset is normally the **next offset** to read, not the last processed record's offset. Kubernetes Pod readiness does not prove that business processing is succeeding.

### 2.1 Offset vocabulary

| Term | Definition | Incident implication |
|---|---|---|
| Log start offset | Earliest currently available offset | Data before this is no longer replayable from the topic |
| Log end offset (LEO) | Next offset after the log tail | Useful lag reference |
| Consumer position | Next offset the consumer will fetch | Can advance before processing completes |
| Committed offset | Next offset stored for group recovery | Determines replay after restart |
| Consumer lag | Log end minus committed or current position, depending on tool | Not the same as end-to-end event age |
| Consumer group | Consumers cooperating on partition assignments | Enables horizontal processing |

**Important:** consumer lag metrics can differ by collector and whether they use committed offset or consumer position. Define the exact metric semantics in alerts.

## 3. Poll loop and processing contracts

```text
poll records -> process records -> commit next offsets -> poll again
```

### 3.1 Auto commit

`enable.auto.commit=true` periodically commits consumer positions. It is convenient for demonstrations but can commit beyond application work still in flight. A crash after a commit but before processing completes can result in skipped business effects.

### 3.2 Manual commit

With `enable.auto.commit=false`, the application controls commits. A typical at-least-once pattern is:

1. Poll a batch.
2. Process and durably record each event's business effect.
3. Commit the next offsets for fully processed records.
4. On failure before commit, allow replay and deduplicate side effects by stable event ID.

This can cause duplicate processing but avoids falsely advancing progress before work completes. Multi-partition and asynchronous processing require per-partition commit tracking; do not commit an offset that skips unfinished earlier records.

### 3.3 Exactly-once scope

Kafka transactions can atomically coordinate Kafka output records and consumer offsets for supported consume-transform-produce flows. They do **not** automatically make external database writes, HTTP calls or email notifications exactly once. Those require idempotent sinks, outbox/inbox, transactional integration or reconciliation.

## 4. Consumer configuration and failure behavior

| Property | Purpose | SRE risk |
|---|---|---|
| `group.id` | Consumer progress/assignment namespace | Sharing group ID accidentally causes interference |
| `auto.offset.reset` | Behavior if no valid committed offset exists | `latest` can skip historical data |
| `enable.auto.commit` | Periodic offset commits | Processing/commit mismatch |
| `max.poll.interval.ms` | Maximum gap between polls for active membership | Long processing can trigger rebalances |
| `session.timeout.ms` | Coordinator detects failed members | Too low causes churn; bounds vary |
| `heartbeat.interval.ms` | Classic group protocol heartbeat cadence | Must align with group protocol and session timeout |
| `max.poll.records` | Records returned per poll | Large batches can exceed processing budget |
| `fetch.min.bytes` | Minimum desired fetch payload | Throughput vs latency |
| `fetch.max.wait.ms` | Broker fetch wait upper bound | Latency vs batching |
| `isolation.level` | Read committed versus uncommitted transactional records | Transactional visibility |
| `partition.assignment.strategy` | Supported partition assignment algorithm | Rebalance behavior |
| `group.protocol` | Classic or consumer group protocol in supported clients | Heartbeat/configuration behavior differs |

**Compatibility:** supported Kafka versions differ in consumer group protocol, heartbeat configuration, assignment strategy and tooling. Inspect your actual client and broker version before tuning; do not assume all listed settings apply unchanged to the newer consumer protocol.

## 5. Lab prerequisites

Use the [shared Kubernetes lab](../kubernetes/README.md): namespace `kafka-lab`, Strimzi cluster `sre-kafka`, a version-matched `kafka-cli` Pod, and internal lab-only bootstrap `sre-kafka-kafka-bootstrap:9092`. The production equivalent must use TLS, authorized KafkaUsers and appropriate NetworkPolicies.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch17
```

Stop if Kafka, controller quorum or PVC health is degraded. Confirm your installed Strimzi KafkaTopic CRD supports `kafka.strimzi.io/v1`, or substitute the supported API version.

## 6. Lab A — Create a dedicated topic and consumer group

Save `topic-ch17.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-consumer-ch17
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

```bash
kubectl apply --dry-run=server -f topic-ch17.yaml
kubectl apply -f topic-ch17.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-consumer-ch17 \
  | tee evidence-ch17/topic-before.txt
```

**Acceptance:** three partitions, RF=3, ISR=3. Use group ID `sre-consumer-ch17-g1` only for this chapter.

## 7. Lab B — Produce deterministic test events

```bash
printf '%s\n' \
  'acct-1:event-1701' \
  'acct-1:event-1702' \
  'acct-2:event-1703' \
  'acct-2:event-1704' \
  'acct-3:event-1705' \
  'acct-3:event-1706' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-consumer-ch17 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

**Acceptance:** six unique IDs published. Save the expected ID set before running consumers.

## 8. Lab C — Consume with an isolated group

The console consumer can commit offsets for a group, but its exact commit behavior is client/version dependent; this lab does **not** prove application-level manual commit semantics.

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-consumer-ch17 \
  --group sre-consumer-ch17-g1 \
  --from-beginning --max-messages 6 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch17/consumer-records.txt
```

**Acceptance:** all six IDs observed; same-key events remain ordered within their partition. If records were previously consumed by this group, `--from-beginning` does not override an existing committed offset. Use a new dedicated group for a clean baseline.

## 9. Lab D — Inspect consumer group offsets

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-consumer-ch17-g1 \
  | tee evidence-ch17/group-offsets.txt
```

Record `CURRENT-OFFSET`, `LOG-END-OFFSET`, `LAG`, group state and members. Some short-lived consumers may leave a group with no active members; offset commits may be delayed or absent depending on how the console consumer exited. Do not claim zero lag without inspecting actual results.

## 10. Lab E — Observe group membership and partition assignment

Run the console consumer interactively in one terminal, then inspect from another:

```bash
kubectl -n kafka-lab exec -it kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-consumer-ch17 \
  --group sre-consumer-ch17-members \
  --consumer-property auto.offset.reset=earliest
```

In a second terminal:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-consumer-ch17-members --members --verbose
```

Open a second consumer with the **same** group ID, then inspect assignments again. The three partitions are divided among active members; a fourth consumer can be idle when the group has only three partitions. Exit the test consumers after evidence capture.

## 11. Lab F — Kubernetes Job consumer execution

A continuously running production consumer normally uses a Deployment (with carefully managed shutdown) or another workload controller. This lab uses a bounded Job to demonstrate lifecycle and restart semantics.

Inspect the CLI image:

```bash
kubectl -n kafka-lab get pod kafka-cli -o jsonpath='{.spec.containers[0].image}{"\n"}'
```

Create `consumer-job-ch17.yaml`, replacing `<MATCHING_KAFKA_CLI_IMAGE>` with the verified, compatible image:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: consumer-ch17
  namespace: kafka-lab
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: consumer-ch17
    spec:
      restartPolicy: Never
      containers:
        - name: consumer
          image: <MATCHING_KAFKA_CLI_IMAGE>
          command: ["/bin/sh", "-ec"]
          args:
            - |
              /opt/kafka/bin/kafka-console-consumer.sh \
                --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
                --topic sre-consumer-ch17 \
                --group sre-consumer-ch17-job \
                --from-beginning --max-messages 6 \
                --property print.key=true \
                --property print.partition=true \
                --property print.offset=true
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

```bash
kubectl apply --dry-run=server -f consumer-job-ch17.yaml
kubectl apply -f consumer-job-ch17.yaml
kubectl -n kafka-lab wait --for=condition=complete job/consumer-ch17 --timeout=180s
kubectl -n kafka-lab logs job/consumer-ch17 \
  | tee evidence-ch17/job-consumer.txt
kubectl -n kafka-lab get jobs,pods -l app=consumer-ch17 -o wide
```

**Acceptance:** Job Completed and six records logged. If the Job fails or times out, investigate scheduling, image, group offset state, topic availability and data retention; do not automatically mark Passed.

## 12. Lab G — Manual commit semantics tabletop

**No external database mutation.** For records at offsets 10, 11, 12, evaluate:

| Failure point | Commit state | Recovery effect |
|---|---|---|
| Before processing offset 10 | Last committed next offset=10 | Replay from 10 |
| After processing 10 but before commit | Last committed next offset=10 | 10 may replay; dedup needed |
| After processing 10, commit next offset=11 | Next offset=11 | Resume at 11 |
| Commit next offset=13 before processing 12 | Next offset=13 | 12 may be skipped after crash |
| External side effect succeeds, commit fails | Old committed offset | Side effect may repeat |

Write pseudocode for per-partition tracking of fully processed offsets and explain why asynchronous processing must not commit beyond unfinished records.

## 13. Lab H — Opt-in offset reset on a disposable group

**Dangerous operation:** offsets may be moved backward (replay) or forward (skip). This is **not** a production runbook shortcut. Only use `sre-consumer-ch17-g1` after all its consumers are stopped, and preserve a before snapshot.

Preview the reset:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --group sre-consumer-ch17-g1 \
  --topic sre-consumer-ch17 \
  --reset-offsets --to-earliest \
  | tee evidence-ch17/reset-preview.txt
```

**Do not execute until the owner confirms:** group is Empty, target topic is disposable, previewed offsets are correct, and duplicate replay is acceptable.

Execute only after approval:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --group sre-consumer-ch17-g1 \
  --topic sre-consumer-ch17 \
  --reset-offsets --to-earliest --execute
```

Then inspect group offsets and consume with the same group to demonstrate replay. If the group has no committed offsets or Kafka version rejects the reset, record the result and use a fresh group for the remaining labs rather than forcing a production-like change.

## 14. Lab I — Retention and replay boundary review

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-consumer-ch17 \
  --describe | tee evidence-ch17/retention-config.txt
```

Review topic `retention.ms`, log start offsets and consumer group lag. A lagging consumer can fall behind the retention window and permanently lose the ability to replay expired records. Increasing retention after deletion does not restore old data. Design alerts on **time lag / event age**, not only record count.

## 15. Lab J — Consumer operational acceptance script

Save as `verify-ch17.sh`. This script is read-only and does not reset offsets.

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
TOPIC=sre-consumer-ch17
GROUP=sre-consumer-ch17-g1
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka readiness'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/6] Topic metadata'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

echo '[4/6] Topic RF/ISR'
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++
    if(rf!=3 || isr!=3) bad++
  }
  END {
    if(seen!=3 || bad){print "FAIL: partitions="seen" unhealthy="bad; exit 1}
    print "PASS: three partitions, RF=3, ISR=3"
  }'

echo '[5/6] Consumer group offsets (may be absent until first commit)'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-consumer-groups.sh" \
  --bootstrap-server "$BS" --describe --group "$GROUP" || \
  echo 'PENDING: group has no committed offsets or is unavailable'

echo '[6/6] Metadata connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo 'PASS: Kafka topic metadata only; consumer processing and offset correctness require separate evidence'
```

```bash
chmod +x verify-ch17.sh
./verify-ch17.sh | tee evidence-ch17/acceptance.txt
```

**Coverage limits:** the script checks topic metadata and connectivity; it does not prove manual commits, business processing, zero lag, exactly-once effects, or consumer group availability. The group describe step explicitly permits a Pending state.

## 16. Eight production incident scenarios

### Incident 1 — Consumer lag grows after deployment

**Signals:** committed offset stalls, event age increases, consumer Pod Ready.

**Investigate:** group assignments, processing latency, downstream dependency, CPU throttling, partition skew.

**Mitigate:** restore processing capacity, tune batch size, scale within partition limits, preserve ordering and idempotency.

### Incident 2 — Rebalance storm

**Signals:** repeated group membership changes, throughput collapses.

**Investigate:** Pod restarts, HPA churn, long processing exceeding max poll interval, heartbeat/session configuration.

**Mitigate:** stabilize membership, bound processing, use compatible cooperative/static membership strategies where supported.

### Incident 3 — Duplicate business effects after crash

**Signals:** repeated event IDs in downstream database or API.

**Investigate:** processing success followed by offset commit failure, restart timeline, manual/auto commit configuration.

**Mitigate:** implement idempotent sink/inbox and commit only after durable processing.

### Incident 4 — Missing events due to premature commits

**Signals:** committed offsets advanced beyond unprocessed events.

**Investigate:** asynchronous processing, batch commits, auto commit, exception handling.

**Mitigate:** stop affected consumer, reconcile business IDs and replay from approved earlier offsets if retained.

### Incident 5 — Consumer falls behind retention

**Signals:** `OffsetOutOfRange`, log start offset exceeds committed offset.

**Investigate:** retention policy, outage duration, consumer lag/event age, replay backups.

**Mitigate:** recover from upstream or backup; a blind offset reset can skip missing business events.

### Incident 6 — Consumer cannot join group

**Signals:** coordinator errors, authentication failures, group stuck preparing rebalance.

**Investigate:** bootstrap/listeners, ACLs, coordinator broker, group protocol compatibility.

**Mitigate:** restore coordinator/network/auth access; do not disable security.

### Incident 7 — Hot partition and idle consumers

**Signals:** one partition lags while extra consumers are idle.

**Investigate:** key skew, partition count, assignment, processing costs.

**Mitigate:** redesign key distribution or partitioning through an approved migration; scaling consumers above partition count is insufficient.

### Incident 8 — Kubernetes termination interrupts processing

**Signals:** Pod receives SIGTERM, work abandoned, offsets uncertain.

**Investigate:** terminationGracePeriodSeconds, preStop behavior, readiness, drain/rebalance timing.

**Mitigate:** stop polling, finish or safely abandon in-flight work, commit only completed offsets, close consumer and verify replay.

## 17. Troubleshooting matrix

| Symptom | Kubernetes first checks | Kafka first checks | Unsafe shortcut |
|---|---|---|---|
| Consumer Pod Pending | Scheduling, image, quota | None | Privileged Pod |
| Group not found | Pod logs, group ID | Offset commits/group describe | Invent offsets |
| Lag growing | CPU/memory, downstream | Partition lag/assignments | Scale blindly |
| Rebalance storm | Pod churn, HPA | Membership and timeouts | Disable monitoring |
| Missing events | Restart history | Committed vs log start offsets | Reset to latest |
| Duplicate effects | Pod termination | Commit timing, event IDs | Assume Kafka deduplicates sink |
| Auth error | Secret/NetworkPolicy | ACLs, group authorization | Disable TLS/SASL |
| OffsetOutOfRange | Outage/retention history | Log start vs committed | Blind reset |

## 18. Production runbooks

### Runbook A — Consumer lag incident

1. Identify affected topic, group, partitions, committed offsets and event age.
2. Inspect consumer Pod readiness, CPU/memory, restarts and downstream dependencies.
3. Compare per-partition lag to assignment and key distribution.
4. Restore processing or safely scale within partition constraints.
5. Verify business event age, throughput and committed progress.
6. Preserve incident timeline and alert tuning actions.

### Runbook B — Offset recovery

1. Stop group members and obtain application-owner approval.
2. Capture current offsets, log start/end offsets, retention and event IDs.
3. Define replay/skip scope and downstream deduplication plan.
4. Preview offset changes with Kafka CLI.
5. Execute only the approved reset and restart consumers.
6. Reconcile replayed events and document irreversible gaps.

### Runbook C — Rebalance instability

1. Capture group state, membership, assignments and rebalance frequency.
2. Correlate with Kubernetes Pod rollout/HPA, processing time and poll interval.
3. Restore stable membership and bounded processing.
4. Review cooperative/static membership only if supported by client/protocol.
5. Verify reduced rebalance frequency and restored SLOs.
6. Update deployment and runbook standards.

### Runbook D — Duplicate processing

1. Collect duplicate business IDs and downstream side effects.
2. Compare processing logs with committed offsets and crash/restart history.
3. Determine whether commits happened before or after durable processing.
4. Apply idempotent sink/outbox/inbox protections.
5. Replay carefully in staging and reconcile results.
6. Record root cause and control effectiveness.

### Runbook E — Kubernetes graceful shutdown

1. Configure termination grace period to cover bounded processing.
2. On SIGTERM, stop accepting new work and polling where appropriate.
3. Complete or abandon in-flight work with explicit offset tracking.
4. Commit only fully processed offsets, then close consumer cleanly.
5. Allow coordinator reassignment and verify group recovery.
6. Alert on termination timeouts and repeated restarts.

## 19. SLO and observability design

Track consumer group committed lag, event age, poll frequency, records consumed/sec, processing latency, commit latency/errors, rebalance rate, assignment churn, Pod restarts, CPU throttling, downstream failures and replay/duplicate event rate.

**Example SLO design (not measured):** a specified percentage of events processed within a business-defined delay, no unexplained missing business events, bounded recovery time after Pod restart, and controlled replay duplicates through idempotent sinks. Derive numeric thresholds from the actual service and error budget.

## 20. Enterprise readiness checklist

- [ ] Consumer client and group protocol versions documented.
- [ ] Topic partitions and group parallelism designed.
- [ ] Offset commit contract matches business processing guarantees.
- [ ] Auto versus manual commit trade-offs reviewed.
- [ ] Retry, backoff and idempotent downstream processing defined.
- [ ] Poll interval and processing duration monitored.
- [ ] Kubernetes Deployment termination behavior validated.
- [ ] TLS/SASL, Kafka ACLs and Secrets least privilege reviewed.
- [ ] Consumer group lag and event age alerts enabled.
- [ ] Retention versus outage/replay window approved.
- [ ] Offset reset procedure restricted to authorized operators.
- [ ] Live execution and independent security review tracked separately.

## 21. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain consumer architecture and poll loop | 10 |
| Distinguish position, committed offset, LEO and lag | 10 |
| Explain auto/manual commit failure windows | 10 |
| Create KafkaTopic and produce deterministic records | 10 |
| Consume with a dedicated group and inspect offsets | 10 |
| Observe group membership and partition assignments | 10 |
| Deploy bounded Kubernetes consumer Job | 10 |
| Preview safe offset reset and explain replay risk | 10 |
| Run automated metadata acceptance and explain gaps | 10 |
| Deliver incident response, SLOs and runbooks | 10 |

**Pass:** ≥85/100 with no safety violations and independently captured evidence. Do not award points for unexecuted labs.

## 22. Cleanup and next chapter

After capturing evidence and confirming the resources are disposable:

```bash
kubectl -n kafka-lab delete job consumer-ch17 --ignore-not-found
kubectl -n kafka-lab delete kafkatopic sre-consumer-ch17 --ignore-not-found
```

Topic deletion can permanently remove data. Do not delete the Kafka cluster, broker PVCs, or unrelated consumer groups.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/), [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/).

**Next:** Chapter 018 — Kafka Consumer Groups, Rebalancing Protocols and Kubernetes Horizontal Scaling.

---

**Verification boundary:** Published content is not executed content. Kubernetes labs, version-specific consumer protocol validation, security review and production acceptance remain Pending.
