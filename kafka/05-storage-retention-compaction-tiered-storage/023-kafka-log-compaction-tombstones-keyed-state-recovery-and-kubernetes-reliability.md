# Chapter 023 — Kafka Log Compaction, Tombstones, Keyed State Recovery and Kubernetes Reliability

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 05 — Storage, Retention, Compaction and Tiered Storage (3/5)  
**Platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 011–022, particularly Chapters 017, 021 and 022  
**Audience:** Kafka SREs, DBREs, platform engineers, CDC and streaming application owners  
**Status:** Published · Live labs pending · Security review pending

> **Safety:** Compaction changes the records available for replay and tombstones can delete logical state. Run every exercise on the disposable `sre-compaction-ch23` topic only. Do not change production cleanup policies, delete keys, reset offsets, modify broker segment files or delete broker PVCs. Preserve an upstream authoritative snapshot for critical state stores.

## 1. Outcomes

By the end, you can:

1. Explain compacted partition logs, record keys, offsets and retained state.
2. Distinguish `cleanup.policy=compact` from `delete` and `compact,delete`.
3. Explain tombstones, `delete.retention.ms`, cleaner eligibility and snapshot bootstrap windows.
4. Design deterministic keyed-state reconstruction from a compacted topic.
5. Monitor cleaner throughput, backlog, segment eligibility and disk pressure.
6. Use Kubernetes/Strimzi KafkaTopic CRs to apply compaction configuration safely.
7. Diagnose unexpected key loss, replay gaps, unbounded growth and application ordering defects.
8. Implement acceptance evidence, SRE runbooks and operational governance.

## 2. Reference architecture

```text
CDC / event producer with stable business keys
                   |
             KafkaTopic CR
         cleanup.policy=compact
                   |
          partition append-only log
             /           \
     active segment    closed segments
                            |
                    background log cleaner
                            |
              older superseded key values
                  eligible for removal
                            |
             latest value / tombstone state
                            |
             state bootstrap consumer
                            |
       Kubernetes consumer Deployment / PVC
                            |
           materialized state + checkpoint
```

Kafka compaction is asynchronous. The log cleaner reclaims superseded records in eligible segments; it does **not** rewrite history synchronously on every key update. Compacted topics still have offsets and ordering within each partition, and offsets may have gaps after cleaning.

## 3. Compaction semantics and guarantees

For a compacted topic, Kafka retains the latest value for a given **non-null record key**, subject to cleaner progress and deletion semantics. Earlier versions may remain until cleaning occurs. A consumer reading a compacted log reconstructs the most recent state by applying records in offset order for each key.

**Important boundaries:**

- Compaction is not a uniqueness constraint on producer writes.
- Kafka records require non-null keys for meaningful compaction; null-key records are invalid for compacted topics.
- A key must consistently map to the same partition to preserve its update order. Changing partition counts or partitioner behavior can break this assumption.
- Kafka does not guarantee a fixed time at which superseded records disappear.
- Compaction is not a backup or a permanent historical audit log.
- Log cleaning may create offset gaps. Consumers must not assume contiguous offsets.

### 3.1 Example keyed state

| Offset | Key | Value | Logical state after processing |
|---:|---|---|---|
| 0 | customer-1 | tier=bronze | customer-1=bronze |
| 1 | customer-2 | tier=silver | customer-2=silver |
| 2 | customer-1 | tier=gold | customer-1=gold |
| 3 | customer-2 | tombstone (null) | customer-2 removed |
| 4 | customer-3 | tier=basic | customer-3=basic |

After sufficient compaction, superseded values may disappear. The final state is customer-1=gold, customer-3=basic, and customer-2 absent. **A text payload containing the word "null" is not a tombstone**; tombstones have an actual null Kafka record value.

## 4. Tombstones and deletion retention

A tombstone is a record with a non-null key and a **null value**. It tells state reconstruction consumers to remove the key. The tombstone is retained for a limited period to allow readers that began scanning the log to observe the deletion. `delete.retention.ms` controls the minimum time tombstone markers remain eligible for cleaner retention, with precise visibility dependent on cleaning cycles and segment eligibility.

A new bootstrap reader that starts too late may miss a removed key's tombstone, especially if it merges into a preexisting stale local state. Correct recovery generally rebuilds from an empty state store, replays from a consistent beginning/snapshot, and validates against an authoritative source.

**Never use tombstone expiration as a legal-erasure SLA.** Backups, downstream copies, remote storage and other data systems require separate treatment.

## 5. Cleaner mechanics and configuration

| Setting | Effect | Risk |
|---|---|---|
| `cleanup.policy=compact` | Enables log compaction | Historical versions may be removed |
| `min.cleanable.dirty.ratio` | Influences when dirty segments qualify | High values may delay cleanup |
| `min.compaction.lag.ms` | Minimum time before eligible records can be compacted | Higher storage demand |
| `max.compaction.lag.ms` | Upper bound influencing cleaner eligibility, not a strict completion SLA | Cleaner contention may still delay work |
| `delete.retention.ms` | Tombstone retention for snapshot readers | Too short for slow bootstrap |
| `segment.bytes` / `segment.ms` | Controls rolling of active segments | Tiny values cause file-count overhead |
| `retention.ms` with `compact,delete` | Time deletion plus compaction | May remove state history required for rebuild |

Cleaner performance depends on broker configuration, I/O bandwidth, cleaner threads, partition layout and workload. Do not promise a hard compaction completion time from topic config alone.

## 6. Lab safety and preflight

Lab assumptions: namespace `kafka-lab`, cluster `sre-kafka`, CLI Pod `kafka-cli`, bootstrap `sre-kafka-kafka-bootstrap:9092`. KafkaTopic examples use `kafka.strimzi.io/v1` only if the installed CRD serves it.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl get crd kafkatopics.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'
mkdir -p evidence-ch23
```

**Stop** if the namespace contains business data, KRaft quorum is unhealthy, any broker ISR is degraded, or the test topic name is already owned by another team.

## 7. Lab A — Create the compacted topic

Save `topic-ch23.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-compaction-ch23
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: compact
    min.cleanable.dirty.ratio: 0.1
    min.compaction.lag.ms: 0
    delete.retention.ms: 86400000
    segment.bytes: 1048576
    segment.ms: 60000
```

Small segments and low cleaner threshold are **lab-only** settings. Production values require storage/IO benchmarking and state-bootstrap SLA review.

```bash
kubectl apply --dry-run=server -f topic-ch23.yaml
kubectl apply -f topic-ch23.yaml
kubectl -n kafka-lab get kafkatopic sre-compaction-ch23 -o yaml \
  | tee evidence-ch23/topic-cr.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-compaction-ch23 \
  | tee evidence-ch23/partition-health.txt
```

**Acceptance:** three partitions, RF3, full ISR and operator reconciliation.

## 8. Lab B — Verify effective cleanup settings

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-compaction-ch23 --describe \
  | tee evidence-ch23/effective-config.txt
```

Confirm `cleanup.policy=compact`, `delete.retention.ms=86400000`, segment settings and `min.cleanable.dirty.ratio=0.1`. Note that broker defaults and version-specific validation can affect accepted settings.

## 9. Lab C — Write deterministic keyed updates

```bash
printf '%s\n' \
  'customer-1:tier=bronze' \
  'customer-2:tier=silver' \
  'customer-1:tier=gold' \
  'customer-3:tier=basic' \
  'customer-2:tier=platinum' \
  'customer-1:tier=diamond' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-compaction-ch23 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Read with a fresh consumer group:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-compaction-ch23 \
  --group sre-compaction-ch23-read \
  --from-beginning --max-messages 6 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch23/initial-records.txt
```

**Acceptance:** all six records are visible **before cleaner removes older versions**. Since compaction is asynchronous, the exact count may vary if cleaning runs quickly; treat the six-record read as a time-sensitive observation, not an invariant.

## 10. Lab D — Produce a real null-value tombstone

Kafka console producer behavior for null values depends on Kafka version and console producer properties. For reliable tombstone creation, use a small Kafka Java producer with `ProducerRecord<String,String>(topic, key, null)`.

Save `TombstoneProducer.java`:

```java
import java.util.Properties;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

public final class TombstoneProducer {
  public static void main(String[] args) throws Exception {
    if (args.length != 3) {
      throw new IllegalArgumentException("usage: bootstrap topic key");
    }
    Properties p = new Properties();
    p.put("bootstrap.servers", args[0]);
    p.put("key.serializer", StringSerializer.class.getName());
    p.put("value.serializer", StringSerializer.class.getName());
    p.put("acks", "all");
    p.put("enable.idempotence", "true");
    try (KafkaProducer<String,String> producer = new KafkaProducer<>(p)) {
      producer.send(new ProducerRecord<>(args[1], args[2], null)).get();
      producer.flush();
    }
  }
}
```

Build this in an approved Java/Kafka client environment using the **exact Kafka client dependency version** and deploy the resulting artifact to an isolated Kubernetes Job with an approved image digest and matching bootstrap/authentication configuration. Do not assume `kafka-cli` has `javac` or that a raw `java` invocation includes Kafka client libraries.

**Acceptance:** an actual null-value record for `customer-2` is produced, verified using a client that distinguishes null from the literal string `"null"`. If no approved build/runtime exists, mark this lab Pending; do not claim a tombstone was generated.

## 11. Lab E — Validate logical state reconstruction

Build a state map by reading the topic from earliest available offsets:

```text
for each Kafka record, ordered within its partition:
  assert key is non-null
  if record.value == null:
      state.remove(record.key)
  else:
      state[record.key] = record.value
```

**Expected state after Lab D succeeds:**

```text
customer-1 = tier=diamond
customer-2 = absent
customer-3 = tier=basic
```

Use a real Kafka consumer that processes **all partitions** and waits until it reaches a captured end-offset snapshot, not a fixed `--max-messages` count. After compaction, the number of physical records is not predictable. A state store must track progress independently for each partition.

**Acceptance:** exact final map and input offsets recorded, no stale customer-2 value.

## 12. Lab F — Observe compaction eligibility and segment rolling

Wait beyond the lab segment roll interval, then produce another keyed update:

```bash
sleep 70
printf '%s\n' 'customer-3:tier=premium' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-compaction-ch23 \
  --producer-property acks=all \
  --property parse.key=true --property key.separator=:
```

Observe broker log-cleaner metrics, segment counts, cleaner backlog and log-start/end offsets using the installed monitoring stack. If permitted, inspect broker files **read-only** in the verified broker data mount; never modify them.

**Acceptance:** document cleaner progress and whether older superseded versions disappeared. **No fixed wait time guarantees compaction**, so mark this observational test Pending when evidence is insufficient.

## 13. Lab G — Snapshot/bootstrap reliability tabletop

Design a consumer Deployment that:

1. Uses a **new, empty** local state store on full bootstrap.
2. Captures per-partition end offsets for a consistent stopping condition.
3. Applies every available keyed update in partition offset order.
4. Deletes keys on actual null values.
5. Persists checkpoints atomically with state, or uses an appropriate Kafka Streams state-store/changelog mechanism.
6. Reconciles against an upstream authoritative snapshot.
7. Exposes bootstrap progress and state divergence metrics.

**Acceptance:** explain why a compacted log can reconstruct latest state but cannot reproduce a complete historical audit trail or necessarily reconstruct data that was deleted under combined retention.

## 14. Lab H — Kubernetes consumer Deployment reliability design

A production-like state consumer should have:

- A reviewed image digest and explicit Kafka client dependencies.
- A persistent or reconstructible state store and documented recovery time.
- Stable key serialization/partitioner behavior.
- Graceful SIGTERM, bounded poll loop, offset/checkpoint consistency.
- Readiness that only becomes true after bootstrap/recovery is complete.
- Resource requests/limits and storage capacity for state.
- Kafka authentication/TLS and least-privilege ACLs.
- Metrics for bootstrap time, state size, last processed offsets and key divergence.

**Do not deploy a placeholder image.** If a verified image is not available, assess the manifest and mark runtime execution Pending.

## 15. Lab I — Compaction and disk-capacity forecasting

For a topic with 50 million distinct keys, an average compacted record footprint of 300 bytes and RF3:

```text
logical latest-value footprint ≈ 50,000,000 × 300 B ≈ 15 GB
replicated latest-value footprint ≈ 45 GB
```

This is a **lower-bound conceptual estimate**. Actual disk includes multiple versions awaiting cleaning, segment/index overhead, tombstones, cleaner headroom, key skew, broker placement and replication recovery capacity.

Calculate:

- Unique key cardinality and update frequency.
- Latest-value footprint and historical dirty-data rate.
- Cleaner I/O bandwidth and maximum acceptable backlog.
- Tombstone generation rate and bootstrap duration.
- RF, per-broker distribution and PVC headroom.
- Recovery time for rebuilding state from compacted log.

## 16. Lab J — Tombstone retention and bootstrap race tabletop

Scenario: a bootstrap consumer needs 30 hours to read the full topic, but `delete.retention.ms` is 24 hours. A key was deleted shortly before bootstrap began.

**Risk:** the consumer may fail to observe the tombstone before cleaner removes it, especially when merging into a stale local state store. The correct mitigation is a tested bootstrap protocol, adequate deletion retention, and reconciliation—not blindly assuming compaction provides an indefinite deletion history.

**Acceptance:** document a safe bootstrap window, a fresh-state rebuild policy and a reconciliation procedure.

## 17. Lab K — Read-only Kafka/Kubernetes observability collection

```bash
kubectl -n kafka-lab get kafka,kafkanodepool,pvc -o wide \
  > evidence-ch23/kubernetes-storage.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch23/kubernetes-events.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-compaction-ch23-read \
  > evidence-ch23/group-offsets.txt || true
```

Collect actual JMX/Prometheus cleaner metrics (names depend on Kafka version and exporter configuration), broker disk utilization, log size, segment count, partition ISR and consumer bootstrap age. Never invent monitoring data or infer filesystem free space from PVC requested capacity.

## 18. Lab L — Automated metadata acceptance

Save `verify-ch23.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
BS=sre-kafka-kafka-bootstrap:9092
TOPIC=sre-compaction-ch23
BIN=/opt/kafka/bin

echo '[1/5] Kafka Ready'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/5] KafkaTopic exists'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/5] Partition health'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++; if(rf!=3 || isr!=3) bad++
  }
  END {if(seen!=3 || bad){print "FAIL partition/RF/ISR";exit 1}
       print "PASS: 3 partitions RF3 ISR3"}'

echo '[4/5] Effective compaction configuration'
config="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name "$TOPIC" --describe)"
printf '%s\n' "$config"
for expected in 'cleanup.policy=compact' 'delete.retention.ms=86400000' \
                'min.cleanable.dirty.ratio=0.1'; do
  if ! grep -Fq "$expected" <<<"$config"; then
    echo "FAIL: missing $expected" >&2
    exit 1
  fi
done

echo '[5/5] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: metadata/config only; tombstone creation, cleaner progress and state reconstruction require independent evidence'
```

```bash
chmod +x verify-ch23.sh
./verify-ch23.sh | tee evidence-ch23/metadata-acceptance.txt
```

**Limits:** the script does not prove real tombstones, compaction completion, reconstructed state, disk performance, security or recovery SLOs.

## 19. Ten production failure scenarios

### 19.1 Null keys in a compacted topic

**Signal:** producer error or invalid compaction semantics.

**Diagnose:** key serializer, producer payload schema and topic cleanup policy.

**Recover:** enforce stable non-null keys and reject invalid events before publish.

### 19.2 Tombstone encoded as string

**Signal:** deleted customer remains with value `"null"`.

**Diagnose:** actual serialized bytes and record nullability.

**Recover:** emit genuine null-value tombstone and reconcile downstream state.

### 19.3 Cleaner backlog grows

**Signal:** disk usage and dirty ratio rise despite compaction enabled.

**Diagnose:** cleaner metrics, I/O saturation, segment eligibility, broker CPU.

**Recover:** restore cleaner capacity and storage headroom; do not delete files manually.

### 19.4 Tombstone removed before bootstrap completes

**Signal:** stale deleted key reappears after recovery.

**Diagnose:** bootstrap duration, delete retention, state-store initialization.

**Recover:** rebuild from empty state, increase tested retention window, reconcile upstream.

### 19.5 Partition count changes break key ordering

**Signal:** updates for one key appear across multiple partitions.

**Diagnose:** partition count history, partitioner/serializer changes.

**Recover:** approved repartitioning/migration with deterministic key routing.

### 19.6 Consumer assumes contiguous offsets

**Signal:** false corruption alerts on offset gaps.

**Diagnose:** compacted log offsets and consumer logic.

**Recover:** advance by actual consumed offsets; gaps are expected.

### 19.7 Mixed compact/delete policy truncates state

**Signal:** state bootstrap missing keys.

**Diagnose:** `cleanup.policy`, retention limits, segment eligibility.

**Recover:** restore from authoritative snapshot/upstream, redesign policy.

### 19.8 Broker disk pressure during cleaning

**Signal:** write latency, replica lag, cleaner backlog.

**Diagnose:** PVC headroom, IOPS, segment churn, ISR.

**Recover:** approved storage/throughput remediation without reducing durability.

### 19.9 State store corrupted on Pod restart

**Signal:** consumer fails bootstrap or serves stale state.

**Diagnose:** checkpoint consistency, PVC state, shutdown sequence.

**Recover:** recreate disposable local state from compacted log and verify upstream reconciliation.

### 19.10 KafkaTopic policy drift

**Signal:** effective broker config differs from GitOps desired state.

**Diagnose:** Strimzi reconciliation, direct CLI changes, operator logs.

**Recover:** restore approved source of truth and audit controls.

## 20. Troubleshooting matrix

| Symptom | Kafka evidence | Kubernetes evidence | Unsafe action |
|---|---|---|---|
| Key not removed | Null-value bytes, cleaner lag | Producer logs | Send literal "null" |
| Disk growth | Dirty ratio, segment count | PVC free space | Delete .log files |
| Missing state after rebuild | Tombstone horizon, policy | Consumer checkpoint | Assume compaction is backup |
| Duplicate versions remain | Cleaner progress | Broker I/O saturation | Force broker restart |
| Ordering wrong | Partition assignment | App version/rollout | Add partitions blindly |
| Consumer offset gaps | Compacted log offsets | Consumer exception | Treat as corruption |
| Cleaner stalled | JMX/logs | Broker CPU/PVC latency | Disable replication |
| State Pod not ready | Bootstrap lag | Pod logs/PVC | Bypass readiness |

## 21. Six production runbooks

### Runbook A — Compaction backlog and disk pressure

1. Confirm topic owner, cleanup policy, broker disk and ISR.
2. Capture cleaner backlog, segment eligibility, write latency and PVC free space.
3. Identify hot partitions, excessive updates and cleaner contention.
4. Restore capacity/throughput through approved changes.
5. Verify cleaner progress, ISR and application freshness.
6. Document capacity forecast and alert tuning.

### Runbook B — Tombstone and logical deletion incident

1. Confirm actual null-value tombstone was produced for the intended key.
2. Trace key serializer and partition placement.
3. Verify consumer processing and state-store deletion semantics.
4. Assess tombstone retention and bootstrap age.
5. Reconcile against authoritative source; repair affected state.
6. Record prevention controls and deletion audit evidence.

### Runbook C — Stateful consumer rebuild

1. Identify state store and checkpoint ownership.
2. Capture committed offsets and upstream authoritative snapshot.
3. Stop serving stale state; preserve incident evidence.
4. Rebuild in isolation from earliest retained offsets or approved snapshot.
5. Validate key counts, checksums and deletion reconciliation.
6. Promote recovered consumer after owner signoff.

### Runbook D — Key-partition migration

1. Freeze unreviewed partition count/partitioner changes.
2. Document old/new key routing and ordering requirements.
3. Design a new topic with stable partition mapping and migration window.
4. Dual-write/replay only under an approved correctness protocol.
5. Reconcile final state and switch consumers safely.
6. Retire old topic only after retention and recovery approval.

### Runbook E — Compaction policy change

1. Review business need, history retention and CDC semantics.
2. Capture topic config, replay requirements, consumer bootstrap duration.
3. Evaluate `compact` versus `compact,delete` consequences.
4. Apply via GitOps/Strimzi with approvals.
5. Monitor cleaner backlog, disk and state reconstruction.
6. Retain audit trail and rollback limitations.

### Runbook F — Compaction reliability game day

1. Confirm disposable topic, change approval and rollback owner.
2. Establish baseline keys, offsets, broker/cleaner metrics.
3. Run controlled update and tombstone scenarios.
4. Observe segment/cleaner behavior without broker file edits.
5. Rebuild and reconcile state after application Pod restart.
6. Publish evidence, scores, unresolved risks and next actions.

## 22. Evidence manifest and acceptance

```text
evidence-ch23/
  context-and-change-approval.md
  topic-cr.yaml
  partition-health.txt
  effective-config.txt
  initial-records.txt
  tombstone-producer-build-and-run.txt
  tombstone-verification.txt
  state-reconstruction.json
  segment-cleaner-observation.md
  storage-capacity-forecast.md
  bootstrap-recovery-tabletop.md
  kubernetes-storage.txt
  metadata-acceptance.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

For each lab record expected/actual results, command, timestamp, environment version, evidence path and reviewer. A missing tombstone build or cleaner observation must remain **Pending**, not Passed.

## 23. Assessment — 100 points

| Domain | Points | Critical |
|---|---:|---|
| Compaction semantics and key/offset ordering | 10 | Yes |
| Tombstone and delete-retention correctness | 10 | Yes |
| Strimzi topic provisioning and RF/ISR health | 10 | Yes |
| Effective topic configuration | 10 | Yes |
| Keyed updates and event reconciliation | 10 | No |
| Real null-value tombstone execution | 10 | Yes |
| Deterministic state reconstruction | 10 | Yes |
| Cleaner/storage monitoring and capacity forecast | 10 | No |
| Automated preflight and recovery design | 10 | No |
| Runbooks, incident handling and independent review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate evidenced. Lab publication is not execution, and a tabletop is not a tested state-recovery run.

## 24. Cleanup and next chapter

After preserving evidence and confirming the topic is disposable:

```bash
kubectl -n kafka-lab delete kafkatopic sre-compaction-ch23 --ignore-not-found
```

Topic deletion permanently removes its records. Do not delete Kafka broker/controller PVCs, KafkaNodePools or the Strimzi cluster.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 024 — Kafka Tiered Storage, Remote Log Lifecycle, Object Storage Security and Kubernetes Disaster Recovery.

---

**Verification boundary:** Publishing this chapter verifies document availability, not actual tombstone creation, cleaner completion, state recovery, security approval or production acceptance.
