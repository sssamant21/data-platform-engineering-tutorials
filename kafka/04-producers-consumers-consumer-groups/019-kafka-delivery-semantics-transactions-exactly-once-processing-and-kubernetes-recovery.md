# Chapter 019 — Kafka Delivery Semantics, Transactions, Exactly-Once Processing and Kubernetes Recovery

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 04 — Producers, Consumers and Consumer Groups  
**Platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–018 and [Kubernetes-first Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers, streaming application owners  
**Publication:** Complete · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety:** This chapter uses isolated Kafka topics and a disposable transactional producer. Do not enable unclean leader election, weaken topic durability, reset production consumer offsets, delete broker PVCs, or claim exactly-once guarantees for an external database. Transaction fencing and rollback exercises must never target a shared business application.

## 1. Learning objectives

By the end, you can:

1. Distinguish at-most-once, at-least-once and Kafka exactly-once processing.
2. Explain producer idempotence, transactional IDs, producer epochs, fencing, and atomic commit/abort.
3. Explain how `read_committed` consumers treat aborted records and the last stable offset.
4. Implement a Kubernetes-run transactional producer using Kafka's Java client.
5. Demonstrate committed and aborted transactions without broker disruption.
6. Design atomic consume-transform-produce processing using `sendOffsetsToTransaction`.
7. Explain why external database/API side effects require an outbox/inbox or deduplication design.
8. Diagnose transaction coordinator, authorization, timeout, fencing and Pod-restart failures.
9. Capture evidence and pass a 100-point reliability assessment.

## 2. Delivery guarantees and their boundaries

| Mode | Application behavior | Typical risk | Control |
|---|---|---|---|
| At-most-once | Advance progress before processing | Lost business effects after crash | Use only when loss is acceptable |
| At-least-once | Process, then commit progress | Replayed records and duplicate side effects | Stable IDs and idempotent sink |
| Kafka exactly-once processing | Transactionally write Kafka output and consumed offsets | Misconfiguration, fencing, external side effects | Idempotence, transactional producer, read_committed, atomic offset commit |

Kafka's exactly-once processing guarantee is scoped to correctly implemented **Kafka-to-Kafka** transactional workflows. It is not an automatic guarantee for external databases, email, payments, object storage or HTTP APIs.

### 2.1 Failure timeline

```text
Input topic P0 offset 42
       |
consumer poll
       |
business transformation
       |
transactional producer sends output
       |
sendOffsetsToTransaction(next offset=43, group metadata)
       |
commitTransaction()
       |
output visible to read_committed consumers
and group offset advances atomically
```

If the transaction aborts, the Kafka output records remain invisible to `read_committed` consumers, and the group offset advance is not committed.

## 3. Transactional producer internals

- `enable.idempotence=true`: broker sequence checking suppresses duplicates from supported producer retries within the producer's session.
- `transactional.id`: stable logical producer identity used to coordinate transactions and fence older producers.
- `initTransactions()`: initializes transactional state and handles recovery/fencing semantics.
- `beginTransaction()`: starts a new atomic unit of Kafka writes.
- `send()`: appends records as part of the open transaction.
- `sendOffsetsToTransaction()`: adds consumed offsets and group metadata to the same transaction for consume-transform-produce.
- `commitTransaction()`: commits the transaction.
- `abortTransaction()`: aborts the transaction when safe and applicable.

**Fencing:** two simultaneously running producers with the same `transactional.id` cannot safely own that identity. The newer producer epoch fences the older one; the old producer must stop rather than retry indefinitely. In Kubernetes, design one transactional ID per **logical task/partition owner**, not one shared ID for all Deployment replicas.

**Timeouts:** `transaction.timeout.ms` must be compatible with broker `transaction.max.timeout.ms`. Long processing, stalled Pod scheduling, or slow storage can cause aborts. `delivery.timeout.ms` is a different client property and does not replace transaction timeout design.

## 4. Consumer isolation and last stable offset

A consumer with `isolation.level=read_uncommitted` may see records from aborted transactions. A `read_committed` consumer excludes aborted transactional records and cannot read beyond the last stable offset (LSO) while an earlier transaction is open. This can appear as consumer lag even when the broker log end offset is ahead.

**Operational warning:** `read_committed` does not automatically prevent reprocessing after a consumer crash; it controls visibility of transactional writes. End-to-end guarantees require correct offset handling and processing topology.

## 5. Kubernetes/Strimzi architecture

```text
 Kubernetes Job: transactional producer
         |
     Kafka bootstrap Service
         |
    broker leaders / replicated log
         |
    transaction coordinator
         |
   __transaction_state (internal topic)
         |
   committed / aborted markers
         |
 read_committed consumer in Kafka CLI Pod
         |
 application reconciliation / observability
```

For a production consume-transform-produce service, use a reviewed long-running application with stable task identity, graceful SIGTERM handling, resource requests, Pod rollout control, and transaction fencing logic. The short-lived Job below is a controlled lab, not a complete production application.

## 6. Prerequisites and lab safety gates

Assume namespace `kafka-lab`, Strimzi Kafka cluster `sre-kafka`, Kafka CLI Pod `kafka-cli`, internal bootstrap `sre-kafka-kafka-bootstrap:9092`, and a dedicated lab cluster with three healthy brokers.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
mkdir -p evidence-ch19
```

**Compatibility gates:** confirm the installed Strimzi KafkaTopic API version (the examples use `kafka.strimzi.io/v1`), broker/client version compatibility, and transaction coordinator availability. Transactional Kafka clients need `Write` permissions for the topics and suitable permissions for the transactional ID and group in secured environments. Plaintext and unrestricted lab credentials are **not** production patterns.

## 7. Lab A — Create transactional input and output topics

Save `topics-ch19.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-txn-input-ch19
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-txn-output-ch19
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
kubectl apply --dry-run=server -f topics-ch19.yaml
kubectl apply -f topics-ch19.yaml
kubectl -n kafka-lab get kafkatopic sre-txn-input-ch19 sre-txn-output-ch19
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-txn-output-ch19 \
  | tee evidence-ch19/topic-output-before.txt
```

**Acceptance:** RF=3, ISR=3, valid leaders and topic operator reconciliation healthy.

## 8. Lab B — Seed deterministic input events

```bash
printf '%s\n' \
  'order-1:event-1901' 'order-1:event-1902' \
  'order-2:event-1903' 'order-3:event-1904' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-txn-input-ch19 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Record four unique IDs. This nontransactional seed is for later workflow design; it does not itself prove exactly-once processing.

## 9. Lab C — Build a small transactional Java producer

Use a reviewed Java/Kafka client toolchain compatible with the Kafka broker. The example uses only the standard Kafka client API. Save as `TxnDemo.java`:

```java
import java.util.Properties;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

public class TxnDemo {
  public static void main(String[] args) throws Exception {
    if (args.length != 3)
      throw new IllegalArgumentException("Usage: TxnDemo <bootstrap> <transactionalId> <commit|abort>");
    String bootstrap = args[0], txnId = args[1], action = args[2];
    if (!action.equals("commit") && !action.equals("abort"))
      throw new IllegalArgumentException("action must be commit or abort");

    Properties p = new Properties();
    p.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
    p.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
    p.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
    p.put(ProducerConfig.ACKS_CONFIG, "all");
    p.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
    p.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, txnId);
    p.put(ProducerConfig.TRANSACTION_TIMEOUT_CONFIG, "60000");

    try (KafkaProducer<String, String> producer = new KafkaProducer<>(p)) {
      producer.initTransactions();
      producer.beginTransaction();
      String eventId = action.equals("commit") ? "event-1905" : "event-1906";
      producer.send(new ProducerRecord<>("sre-txn-output-ch19",
          "order-txn", eventId)).get();
      if (action.equals("commit")) {
        producer.commitTransaction();
        System.out.println("COMMITTED " + eventId);
      } else {
        producer.abortTransaction();
        System.out.println("ABORTED " + eventId);
      }
    }
  }
}
```

**Important:** the code is intentionally small; production implementations must handle fatal producer exceptions, fencing, authorization errors, interruption, bounded retries, metrics, and safe shutdown. Never reuse a transactional ID concurrently across two running Pods.

Compile using the Kafka client JARs available in your **verified** Kafka CLI image:

```bash
kubectl -n kafka-lab cp TxnDemo.java kafka-cli:/tmp/TxnDemo.java
kubectl -n kafka-lab exec kafka-cli -- sh -c \
  'javac -cp "/opt/kafka/libs/*" /tmp/TxnDemo.java'
```

**Toolchain gate:** some Kafka CLI images ship a Java runtime but no `javac`. If so, compile in a separate reviewed JDK build image and copy the resulting class into a compatible Kafka CLI/runtime image. Do not install packages interactively into production broker Pods.

## 10. Lab D — Commit one transaction

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  java -cp "/tmp:/opt/kafka/libs/*" TxnDemo \
  sre-kafka-kafka-bootstrap:9092 sre-txn-ch19-commit commit \
  | tee evidence-ch19/transaction-commit.txt
```

**Acceptance:** output reports `COMMITTED event-1905`. This alone is not enough; confirm visibility in the next lab.

## 11. Lab E — Abort a different transaction

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  java -cp "/tmp:/opt/kafka/libs/*" TxnDemo \
  sre-kafka-kafka-bootstrap:9092 sre-txn-ch19-abort abort \
  | tee evidence-ch19/transaction-abort.txt
```

**Acceptance:** output reports `ABORTED event-1906`. No broker failure is required. Use separate IDs to avoid accidental fencing between lab runs.

## 12. Lab F — Compare read_committed and read_uncommitted

Use bounded console-consumer runs with a short timeout to avoid waiting forever for an invisible aborted record:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-txn-output-ch19 --from-beginning \
  --consumer-property isolation.level=read_committed \
  --timeout-ms 10000 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch19/read-committed.txt
```

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-txn-output-ch19 --from-beginning \
  --consumer-property isolation.level=read_uncommitted \
  --timeout-ms 10000 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch19/read-uncommitted.txt
```

**Acceptance:** `read_committed` sees `event-1905` but not `event-1906`. `read_uncommitted` may expose the aborted record. The console consumer may exit nonzero on timeout after printing available records; classify timeout separately from transaction failure. Re-run on an empty dedicated topic if prior test data contaminates evidence.

## 13. Lab G — Kubernetes Job for the transactional producer

After compiling and validating the Java class, build a reviewed image containing the class, matching Kafka client libraries and a JRE; push it to your approved registry. Do not use a mutable `latest` tag.

Save `txn-job-ch19.yaml`, replacing the image placeholder:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: txn-commit-ch19
  namespace: kafka-lab
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: txn-commit-ch19
    spec:
      restartPolicy: Never
      containers:
        - name: producer
          image: <VERIFIED_TXN_DEMO_IMAGE_DIGEST>
          command: ["java"]
          args:
            - "-cp"
            - "/app:/app/libs/*"
            - "TxnDemo"
            - "sre-kafka-kafka-bootstrap:9092"
            - "sre-txn-ch19-job-commit"
            - "commit"
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
```

**Image contract:** the compiled class must be in `/app`, Kafka client JARs in `/app/libs`, and the Java version compatible. Review ServiceAccount, NetworkPolicy, KafkaUser credentials and securityContext for your cluster. The sample plaintext listener is only for the isolated lab.

```bash
kubectl apply --dry-run=server -f txn-job-ch19.yaml
kubectl apply -f txn-job-ch19.yaml
kubectl -n kafka-lab wait --for=condition=complete job/txn-commit-ch19 --timeout=180s
kubectl -n kafka-lab logs job/txn-commit-ch19 \
  | tee evidence-ch19/job-commit.txt
```

**Acceptance:** Job completes and its committed event is visible to `read_committed`. A Job retry or duplicate execution can create another business event; the transactional producer does not deduplicate arbitrary new submissions.

## 14. Lab H — Transaction fencing tabletop

Without launching conflicting Pods, analyze:

1. Producer A owns transactional ID `processor-task-0`.
2. Producer A is paused by Kubernetes node pressure.
3. Replacement producer B initializes with the **same** transactional ID.
4. Producer A resumes and attempts to commit.
5. Kafka fences producer A; only the valid producer epoch may proceed.

**Acceptance:** describe how the application treats `ProducerFencedException` as fatal for the old instance, stops work, and avoids duplicate downstream effects. Do not intentionally create concurrent writers on a shared topic.

## 15. Lab I — Atomic consume-transform-produce design

For an actual transactional stream processor:

```java
// Pseudocode: Kafka client version and application integration required.
consumer.poll(timeout);
producer.beginTransaction();
for (record : completedInputRecords) {
    producer.send(transform(record));
}
Map<TopicPartition, OffsetAndMetadata> nextOffsets =
    highestContiguouslyProcessedOffsetPlusOneByPartition();
producer.sendOffsetsToTransaction(nextOffsets, consumer.groupMetadata());
producer.commitTransaction();
```

**Correctness gates:** `enable.auto.commit=false`, stable task ownership, read-committed downstream consumers, per-partition contiguous completed offsets, no untracked asynchronous work, and fatal fencing handling. After an abort, reset consumer positions to the last committed offsets before reprocessing; do not assume in-memory positions rewind automatically. Use application-level idempotency for external side effects.

## 16. Lab J — Automated transaction metadata preflight

Save as `verify-ch19.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka readiness'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Input/output topic CRs'
kubectl -n "$NS" get kafkatopic sre-txn-input-ch19 sre-txn-output-ch19

echo '[3/6] Metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[4/6] Output partition RF/ISR'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic sre-txn-output-ch19)"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++; if(rf!=3 || isr!=3) bad++
  }
  END {if(seen!=3 || bad){print "FAIL: partition/ISR mismatch";exit 1}
       print "PASS: three partitions, RF=3, ISR=3"}'

echo '[5/6] Kafka broker API'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[6/6] Topic config'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name sre-txn-output-ch19 --describe

echo 'PASS: metadata preflight only; transaction commit/abort must be independently tested'
```

```bash
chmod +x verify-ch19.sh
./verify-ch19.sh | tee evidence-ch19/acceptance.txt
```

**Coverage limits:** the script does not prove transactional visibility, fencing, correct offset commits, business deduplication, SLOs or production security.

## 17. Transaction correctness acceptance worksheet

| Test | Expected result | Evidence | Status |
|---|---|---|---|
| RF=3/minISR=2 on topics | Topic and Kafka metadata agree | Topic describe/config | Pending |
| Commit transaction | Event 1905 committed | Producer log | Pending |
| Abort transaction | Event 1906 aborted | Producer log | Pending |
| Read committed | 1905 visible, 1906 absent | Consumer output | Pending |
| Read uncommitted | Aborted record visibility observed where applicable | Consumer output | Pending |
| Kubernetes Job | Completed and record visible | Job/Pod + consumer | Pending |
| Fencing response | Fatal old-producer behavior documented | Tabletop | Pending |
| Atomic offsets | Correct design and failure recovery | Reviewed pseudocode | Pending |
| External effects | Explicit dedup/outbox/inbox | Architecture review | Pending |
| Security | TLS/ACL/Secrets reviewed | Independent signoff | Pending |

Do not mark a result Passed because the commands exist in GitHub.

## 18. Ten production incident scenarios

### 18.1 Transaction coordinator unavailable

**Signal:** transaction initialization/commit stalls or fails.

**Investigate:** broker health, internal transaction-state topic, coordinator leadership, ISR and network.

**Mitigate:** restore coordinator/replica health without disabling transaction durability.

### 18.2 Producer fenced during rollout

**Signal:** `ProducerFencedException` on an old Pod.

**Investigate:** duplicate transactional IDs, overlapping Deployment replicas, task ownership.

**Mitigate:** stop fenced producer; restore unique stable task identities and rollout sequencing.

### 18.3 Transaction timeout

**Signal:** open transaction expires during slow processing.

**Investigate:** transaction timeout, processing duration, broker load, Kubernetes CPU throttling.

**Mitigate:** bound work per transaction and improve throughput; avoid unbounded timeout inflation.

### 18.4 Aborted records appear in downstream analytics

**Signal:** consumer reads aborted transactional output.

**Investigate:** `isolation.level` and consumer client configuration.

**Mitigate:** use `read_committed` where business semantics require committed-only visibility.

### 18.5 Consumer offset advanced outside transaction

**Signal:** input records skipped or output duplicated after crash.

**Investigate:** auto commit enabled, incorrect `sendOffsetsToTransaction` usage, async processing.

**Mitigate:** disable auto commit for transactional workflow, atomically commit completed offsets.

### 18.6 Transactional ID authorization failure

**Signal:** transactional ID or topic authorization exception.

**Investigate:** KafkaUser ACLs, principal mapping, TLS/SASL identity.

**Mitigate:** grant minimum required transactional ID/topic/group permissions; never disable authentication.

### 18.7 Kubernetes Job restarts after commit ambiguity

**Signal:** Job retries while first transaction may already have committed.

**Investigate:** Pod/Job history, event IDs, committed output, producer epochs.

**Mitigate:** reconcile stable business IDs before resubmission; do not assume idempotence across independent business attempts.

### 18.8 Read-committed lag spikes with open transaction

**Signal:** consumer seems stalled while log end grows.

**Investigate:** LSO, open transactions, coordinator health, transaction duration.

**Mitigate:** resolve stalled transactions; distinguish LSO from LEO-based lag.

### 18.9 External database updated but Kafka transaction aborts

**Signal:** database side effect exists but output record/offset transaction aborted.

**Investigate:** operation order, outbox/inbox implementation, idempotency keys.

**Mitigate:** reconcile external effect, use transactional outbox or idempotent sink design.

### 18.10 Broker Pod failure during commit

**Signal:** commit timeout or coordinator change during Kafka broker recovery.

**Investigate:** transaction status, broker/ISR health, Pod/PVC events, producer epoch.

**Mitigate:** restore broker health, resolve ambiguous transaction state with application reconciliation, avoid unbounded retries.

## 19. Troubleshooting matrix

| Symptom | Kubernetes checks | Kafka checks | Unsafe shortcut |
|---|---|---|---|
| Transaction init fails | Pod DNS, TLS, secrets | Coordinator/ACLs | Disable auth |
| Commit times out | CPU throttling, network | Transaction coordinator/ISR | Blind replay |
| Producer fenced | Overlapping Pods | Transactional ID epochs | Retry fenced producer |
| Aborted record visible | Client config | Isolation level | Assume EOS |
| Output missing | Job logs, image version | Commit/abort status | Reset offsets blindly |
| Group progress wrong | App restarts | Transactional offset commits | Auto commit |
| Lag spikes | Pod processing time | LSO vs LEO | Scale indefinitely |
| DB duplicate effect | Sink deployment logs | Business IDs | Assume Kafka transactions cover DB |

## 20. Production runbooks

### Runbook A — Transactional producer outage

1. Identify transactional IDs, client versions, affected topics and time window.
2. Inspect producer errors, Kafka coordinator/ISR and Kubernetes Pod events.
3. Determine whether failures are retriable, abortable or fatal/fenced.
4. Stop fenced producers; restore coordinator or authorization health.
5. Reconcile committed business event IDs before resubmission.
6. Verify read-committed output and client SLO recovery.

### Runbook B — Transaction fencing incident

1. Identify duplicate task ownership and transactional IDs.
2. Capture Deployment rollout, Pod identities and producer epochs.
3. Stop old fenced instances; prevent concurrent ID reuse.
4. Restore one valid owner per logical task.
5. Validate transaction commits and offset progression.
6. Review rollout policy and static task identity design.

### Runbook C — Exactly-once processing investigation

1. Capture input partitions/offsets, output event IDs and group commits.
2. Verify transactional producer and read-committed consumer configuration.
3. Inspect `sendOffsetsToTransaction` and contiguous completed offsets.
4. Reconcile aborted/committed transactions and duplicate effects.
5. Validate replay behavior in staging.
6. Document precise guarantee boundaries and residual risks.

### Runbook D — External sink duplication

1. Identify affected database/API operations and business IDs.
2. Compare Kafka transaction state with external side-effect audit logs.
3. Stop repeated writes and implement approved deduplication.
4. Recover via outbox/inbox or compensating transaction where applicable.
5. Verify business correctness and replay behavior.
6. Update architecture and incident controls.

### Runbook E — Kubernetes recovery and operational handoff

1. Preserve Pod/Job logs, ReplicaSet history and Kafka metadata.
2. Restore stable task ownership, Secrets and network connectivity.
3. Validate producer fencing, transaction completion and graceful shutdown.
4. Confirm topic ISR and read-committed consumer progress.
5. Measure event age, commit latency, error rate and transaction aborts.
6. Obtain application-owner and security reviewer signoff.

## 21. Observability and SLOs

Monitor transaction commit/abort rate, commit latency, transaction timeout/fencing errors, producer retry/error rate, coordinator health, topic ISR, read-committed consumer event age, group lag, Pod restart/OOM, and duplicate external business effects.

Define business-specific SLOs for committed event availability and processing freshness. Distinguish Kafka log end offsets from last stable offsets; avoid interpreting every read-committed lag increase as a slow consumer.

## 22. Enterprise readiness checklist

- [ ] Transactional IDs are stable, unique per logical task and never shared concurrently.
- [ ] Kafka broker/client versions and transactional configuration verified.
- [ ] RF/min ISR and transaction-state internal topic health reviewed.
- [ ] Producer idempotence and acks configured.
- [ ] Fencing treated as fatal by old producer.
- [ ] Read-committed consumers validated.
- [ ] Consume-transform-produce commits offsets in the transaction.
- [ ] External side effects have deduplication/outbox/inbox.
- [ ] Kubernetes rollout, shutdown and Job retry semantics reviewed.
- [ ] TLS/SASL, ACLs, Secrets and NetworkPolicies approved.
- [ ] Transaction errors, latency and event age monitored.
- [ ] Live execution, security review and acceptance independently recorded.

## 23. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain at-most/at-least/exactly-once boundaries | 10 |
| Explain transactional producer internals | 10 |
| Create and verify Strimzi KafkaTopic resources | 10 |
| Produce deterministic input events | 10 |
| Compile and run Java transactional producer | 10 |
| Demonstrate commit/abort visibility | 10 |
| Design Kubernetes transactional Job and safe identity | 10 |
| Explain fencing and transactional offset commits | 10 |
| Execute metadata preflight and evidence review | 10 |
| Deliver incident runbooks, SLOs and external sink design | 10 |

**Pass:** ≥85/100 with all critical safety checks and captured execution evidence. Unexecuted labs remain Pending, not Passed.

## 24. Cleanup and next chapter

After retaining sanitized evidence and confirming all resources are disposable:

```bash
kubectl -n kafka-lab delete job txn-commit-ch19 --ignore-not-found
kubectl -n kafka-lab delete kafkatopic sre-txn-input-ch19 sre-txn-output-ch19 --ignore-not-found
```

Topic deletion permanently removes its records. Do not delete Kafka PVCs, shared groups or the Strimzi cluster.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/), [Kafka Java producer API](https://kafka.apache.org/documentation/#producerapi).

**Next:** Chapter 020 — Kafka Producer and Consumer Reliability, Kubernetes Scaling and Exactly-Once Acceptance Capstone.

---

**Verification boundary:** GitHub publication does not establish live lab execution, version-specific transaction correctness, independent security review or production readiness.
