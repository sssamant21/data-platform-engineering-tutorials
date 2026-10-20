# Chapter 063 — Kafka Streams State Stores, RocksDB, Changelog Topics and Fault-Tolerant Recovery

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 13 — Kafka Streams and Stream Processing (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–062, especially 061–062  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use disposable topics, synthetic data and a dedicated Streams application ID. Never delete production changelog/repartition topics, remove RocksDB state, reset offsets, alter retention or perform Pod/node fault injection without an approved recovery plan. Stateful correctness depends on the Kafka changelog, application topology, task assignments and source-topic retention. No live recovery or RPO/RTO result is claimed in this document.

## 1. Mission and learning objectives

Engineer reliable local state for Kafka Streams applications running on Kubernetes. Understand persistent RocksDB state stores, changelog topic replication and compaction, state restoration, standby tasks, resource pressure, task rebalances and safe topology evolution.

By the end, the reader can distinguish state availability from state correctness, estimate cold-start recovery time, explain when standby replicas reduce recovery time, and produce an independently reviewable recovery plan.

## 2. Architecture and state lifecycle

```text
Kafka input topic (partition/key)
            |
      Streams active task
            |
      aggregate / KTable
            |
  RocksDB local state directory ----> Kafka changelog topic
            |                               |
      checkpoint/cache                       |
            |                               v
     local restart reuse              restore/replay
            |                               |
            +--------- task migration ------+
                          |
                 standby task (optional)
                          |
                  Kubernetes Pod/node
```

Kafka Streams runs inside ordinary JVM Pods. State stores are local; Kafka changelog topics provide the durable log needed to reconstruct state, subject to configured replication, compaction and retention. A warm local restart may reuse checkpointed state; a cold start must rebuild from Kafka records. A standby task maintains a replica of store data to reduce failover restore work but is not a substitute for Kafka durability or recovery testing.

## 3. Store types and semantics

| Store | Typical use | Failure/capacity concern |
|---|---|---|
| Persistent key-value | `KTable`, per-key aggregates | RocksDB size, compaction, restore |
| Persistent window | tumbling/hopping counts | retention, grace, cardinality |
| Persistent session | activity/session aggregates | merging and retention |
| In-memory key-value | small transient state | memory pressure, restore on restart |
| Global store | replicated reference table | full dataset per instance |
| Timestamped/versioned stores | temporal semantics where supported | API/version constraints and disk |

Not every Streams DSL operation uses the same physical store type or changelog configuration. Validate `Topology.describe()`, metrics and actual internal topics for the pinned client release.

## 4. Changelog and repartition topics

**Changelog topic:** records state mutations so tasks can reconstruct materialized stores after loss. Log compaction is commonly used for key-value stores; window/session store cleanup can differ. Review actual cleanup policies and retention requirements rather than assuming all changelogs behave identically.

**Repartition topic:** redistributes records after key-changing operations to preserve correct downstream grouping/join partitioning. Repartition topics add network, disk and broker throughput cost.

**Critical safety:** Internal topics derive names from `application.id`, topology and store/operator names. Unreviewed changes to these identifiers can orphan state or break compatibility. Never manually delete internal topics to “fix” an application without a controlled state reset/migration procedure.

## 5. RocksDB operational mechanics

RocksDB uses a log-structured merge-tree design with mutable memory tables, immutable SST files, block cache and background compaction. For Kubernetes capacity, monitor:

- State directory size, available bytes and inode pressure.
- Read/write IOPS, write amplification and compaction stalls.
- JVM heap, RocksDB native/off-heap memory, cache and container limits.
- Task/partition key skew and state cardinality.
- Changelog production rate, compaction, replication and restore throughput.
- Pod eviction signals and `ephemeral-storage` usage.

A Streams container with a 1 GiB memory limit may still OOM despite low JVM heap because RocksDB and native allocations consume container memory. Set explicit capacity and benchmark against the actual workload.

## 6. Recovery and RTO calculation

For planning:

```text
cold_restore_seconds ≈ changelog_bytes_to_replay / effective_restore_bytes_per_second
                     + startup_and_task_assignment_seconds
                     + validation_seconds
```

This is an approximation, not a guaranteed bound. Account for broker throttling, Kafka compaction, disk write amplification, task parallelism, serialization, remote network and Pod scheduling. Record measured recovery using UTC start/finish timestamps and independently reconciled output state.

| Mode | Potential benefit | Risk |
|---|---|---|
| Warm restart on same storage | reuse valid local state | node/volume loss may invalidate |
| Standby promotion | pre-restored state reduces catch-up | standby may lag and requires resources |
| Cold changelog restore | reconstruct from Kafka durability | long RTO for large stores |
| Source-topic replay/rebuild | possible when inputs retained and semantics permit | may be impossible after retention; side effects must be idempotent |

## 7. Kafka Streams configuration review sketch

The following Java configuration is a **review template**, not a complete deployable application:

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "sre-ch63-state-v1");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");
props.put(StreamsConfig.STATE_DIR_CONFIG, "/var/lib/kafka-streams/state");
props.put(StreamsConfig.NUM_STANDBY_REPLICAS_CONFIG, 1);
props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());
// Add approved Kafka client TLS/SASL, transactional ACLs and monitored timeouts.
// Confirm supported config names/values against the pinned Kafka Streams release.
```

`exactly_once_v2` coordinates Kafka transactional writes and consumed offsets for supported Streams operations; it does not guarantee exactly-once effects in an external database or HTTP service. Standby replicas require enough task placement capacity and add disk/network cost.

## 8. Kubernetes workload storage design

```yaml
# Illustrative Pod template fragment, not a complete Deployment.
spec:
  securityContext:
    runAsNonRoot: true
    fsGroup: 10001
  containers:
    - name: streams
      image: registry.example.invalid/sre/ch63@sha256:REPLACE_WITH_PINNED_DIGEST
      resources:
        requests:
          cpu: "500m"
          memory: "1Gi"
          ephemeral-storage: "2Gi"
        limits:
          cpu: "2"
          memory: "2Gi"
          ephemeral-storage: "6Gi"
      volumeMounts:
        - name: streams-state
          mountPath: /var/lib/kafka-streams/state
  volumes:
    - name: streams-state
      emptyDir:
        sizeLimit: 6Gi
```

An `emptyDir` is discarded when the Pod is removed, so the application must restore from changelog. A PVC can reduce some cold restores if mounted back to the appropriate instance, but it introduces attachment, ownership, scheduling and lifecycle complexity. The actual choice requires a measured RTO and storage review. Production Pods additionally need TLS/SASL Secret mounts, Kafka ACLs, readiness/startup probes aligned with restore, PDB, topology spread and a non-root writable state directory.

## 9. Kubernetes-first read-only preflight

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc,storageclass -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get deploy sre-ch63-streams -o wide
```

If the example Deployment does not exist, record **NOT DEPLOYED**; do not interpret that as a recovery pass. Verify the installed Strimzi CRD schema and listener authentication before creating workloads.

## 10. Twenty Kubernetes-first state-store labs

### Lab 01 — Approve stateful processing charter

**Procedure:** Document business state correctness, event ID integrity, RPO/RTO, state retention, recovery owners and abort thresholds.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 02 — Inventory Strimzi and KRaft

**Procedure:** Capture Kafka/KafkaNodePool versions, controller/broker health, ISR, storage and Kubernetes fault domains.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 03 — Inventory Streams application versions

**Procedure:** Record Kafka Streams/JDK versions, immutable image digest, application.id, topology and state store names.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 04 — Describe materialized key-value state

**Procedure:** Map KTable aggregation to persistent RocksDB store, state.dir and changelog topic.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 05 — Review window/session store retention

**Procedure:** Verify event-time window size, grace, store retention, segment layout and cleanup.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 06 — Review changelog durability

**Procedure:** Inspect internal changelog topic replication factor, minISR, compaction, retention and ACL.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 07 — Review repartition topic safety

**Procedure:** Map key-changing operators to internal repartition topics and task assignment.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 08 — Inspect state directory storage

**Procedure:** Review Pod writable paths, ephemeral-storage requests/limits, PVC options and ownership.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 09 — Assess RocksDB write amplification

**Procedure:** Estimate memtable, SST, compaction, block cache, disk I/O and headroom.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 10 — Review standby replica placement

**Procedure:** Inspect num.standby.replicas, available partitions/instances and failure-domain distribution.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 11 — Review warm restart

**Procedure:** Model retained local state reuse, checkpoint validity, changelog catch-up and restore time.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 12 — Review cold restart

**Procedure:** Estimate changelog bytes, restore throughput, new Pod placement and recovery RTO.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 13 — Review task rebalance

**Procedure:** Map active task migration, standby promotion, consumer group movement and state transfer.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 14 — Review Kafka transaction boundaries

**Procedure:** Compare at-least-once and exactly_once_v2 for state, changelog, outputs and offsets.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 15 — Review changelog retention anomaly

**Procedure:** Assess compaction/cleanup, missing offsets, source-topic retention and rebuild feasibility.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 16 — Model RocksDB corruption

**Procedure:** Plan isolate/quarantine, preserve evidence, approved rebuild and replay reconciliation.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 17 — Model disk-full state store

**Procedure:** Estimate volume exhaustion, compaction stalls, Kafka lag and safe scaling.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 18 — Model Pod/node loss

**Procedure:** Review Kubernetes eviction, Stateful vs Deployment placement, topology spread and PDB.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 19 — Review state schema migration

**Procedure:** Assess serde evolution, state store rename, application.id, dual-run and rollback.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

### Lab 20 — Complete fault-tolerant acceptance

**Procedure:** Reconcile input/output IDs and materialized counts, restore RTO, disk headroom, independent review.

**Expected evidence:** Capture Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, state store/changelog identity, restore bytes/time, key counts and input/output event IDs, security, rollback/abort and independent reviewer. Mark **Pending** until executed. State corruption, Pod loss, disk-full and internal topic deletion are **Tabletop** without approved disposable fault-injection infrastructure.

## 11. Read-only verification script

Save as `verify-ch63.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Kafka KRaft'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/9] PVC'; kubectl -n "$NS" get pvc -o wide
echo '[5/9] StorageClass'; kubectl get storageclass
echo '[6/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[7/9] Streams app'
if kubectl -n "$NS" get deploy sre-ch63-streams >/dev/null 2>&1; then
  kubectl -n "$NS" get deploy sre-ch63-streams -o wide
  kubectl -n "$NS" get pods -l app=sre-ch63-streams -o wide
else
  echo 'NOT DEPLOYED: sre-ch63-streams'
fi
echo '[8/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/9] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo 'PASS: read-only Kubernetes inventory.'
echo 'NOT PROVEN: RocksDB health, changelog durability, restore RTO, event integrity or security review.'
```

Run `chmod +x verify-ch63.sh && ./verify-ch63.sh | tee evidence-ch63/preflight.txt`. This is an inventory gate, not a live state restore test.

## 12. Twelve stateful processing failure scenarios

### Scenario 1 — State restore never completes

**Diagnosis:** Check changelog partition/offset, restore throughput, network, RocksDB and Kafka ISR. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 2 — RocksDB reports corruption

**Diagnosis:** Preserve disk/log evidence, inspect filesystem, isolate workload and plan controlled rebuild. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 3 — Pod OOMKilled during compaction

**Diagnosis:** Review heap, off-heap/native RocksDB cache, container memory and limits. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 4 — Ephemeral storage eviction

**Diagnosis:** Inspect node ephemeral capacity, state.dir, eviction signals and storage requests. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 5 — Changelog topic under-replicated

**Diagnosis:** Inspect ISR, RF, minISR, broker disk and state durability. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 6 — Standby replica not assigned

**Diagnosis:** Check num.standby.replicas, instances, tasks and assignment constraints. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 7 — State store shows stale counts

**Diagnosis:** Inspect processing lag, task ownership, changelog progress and event ledger. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 8 — Internal topic missing after manual deletion

**Diagnosis:** Escalate; review backup, rebuild feasibility and data retention before any reset. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 9 — State schema upgrade fails

**Diagnosis:** Inspect store name, serializer, changelog schema and rollback compatibility. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 10 — Task rebalances continuously

**Diagnosis:** Inspect Pod churn, session timeout, liveness, restore and broker connectivity. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 11 — Disk pressure increases latency

**Diagnosis:** Inspect compaction, write stalls, IOPS, cache and partition skew. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

### Scenario 12 — Exactly-once enabled but external sink duplicates

**Diagnosis:** Review Kafka transaction scope, external idempotency and side-effect ledger. Correlate Kubernetes events, Kafka ISR, changelog offsets, Streams thread/task state, RocksDB metrics, disk and memory, source/output event ledger. **Response:** Preserve evidence, freeze destructive operations, protect Kafka durability and choose owner-approved recovery. **Acceptance:** UTC timeline, measured versus tabletop RTO, corrected state counts, rollback and independent review.

## 13. Eight production runbooks

### Runbook A — RocksDB state restore SLO breach

**Trigger and response:** Check active tasks, changelog offsets, restore bytes, storage and safe capacity increase. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook B — State-store disk or memory pressure

**Trigger and response:** Check compaction, cache, heap/off-heap, ephemeral/PVC capacity and abort thresholds. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook C — Changelog availability incident

**Trigger and response:** Check Kafka KRaft, RF/ISR, ACL, compaction, retention and recovery options. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook D — Pod loss and standby promotion

**Trigger and response:** Review task migration, standby readiness, checkpoint state and freshness. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook E — State corruption containment

**Trigger and response:** Preserve logs, freeze destructive changes, identify affected stores and plan controlled rebuild. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook F — State schema/topology migration

**Trigger and response:** Validate serde compatibility, application.id, store names, dual-run and rollback. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook G — Event-integrity and duplicate investigation

**Trigger and response:** Reconcile input IDs, state updates, changelog, output IDs and external side effects. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

### Runbook H — Independent recovery acceptance

**Trigger and response:** Measure observed restore RTO, event integrity, disk headroom, security and signed RCA. **Safety:** No production state directory wipe, internal topic deletion, application.id/offset reset, unreviewed topology migration or ACL bypass. **Exit:** Healthy active tasks and changelog, bounded restore, reconciled materialized state/output IDs, recovered SLO, RCA and independent approval.

## 14. Capacity, SLI and SLO matrix

| Signal | Interpretation | Operational response |
|---|---|---|
| RocksDB state bytes | local materialized state footprint | forecast disk and restore time |
| Changelog backlog/restore bytes | replay work after task migration | compare to RTO |
| Compaction write stall | storage bottleneck | review IOPS and amplification |
| Container RSS/native memory | JVM + RocksDB memory pressure | rightsize and cap caches |
| Pod ephemeral usage | eviction risk | increase headroom or redesign storage |
| Standby task lag | warm recovery readiness | verify assignment and restore |
| Streams records-lag-max | processing freshness proxy | correlate end-to-end latency |
| Accepted input vs materialized state | correctness, duplicates and loss | reconcile by key/version |
| Recovery RTO | outage-to-verified-correctness duration | independent SLO evidence |

Do not choose universal numeric alert thresholds. Derive thresholds from measured baseline, volume size, business RTO and recovery capacity.

## 15. Evidence package

```text
evidence-ch63/
  approved-stateful-charter.md
  kafka-strimzi-streams-jdk-version-matrix.md
  preflight.txt
  kraft-isr-storage-baseline.md
  topology-store-changelog-map.md
  window-session-retention.md
  changelog-rf-minisr-acl.md
  repartition-topic-review.md
  state-dir-storage-permissions.md
  rocksdb-memory-io-compaction.md
  standby-task-placement.md
  warm-restart-tabletop.md
  cold-restore-rto-estimate.md
  task-rebalance-tabletop.md
  kafka-eos-boundary.md
  changelog-retention-risk.md
  rocksdb-corruption-tabletop.md
  disk-pressure-tabletop.md
  pod-node-loss-tabletop.md
  state-schema-migration-plan.md
  accepted-input-event-ledger.csv
  materialized-state-reconciliation.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

Every artifact requires exact version, UTC timestamp, expected/observed result, **Live** vs **Tabletop**, redaction, owner, rollback/abort and independent reviewer.

## 16. 100-point fault-tolerant state assessment

| Domain | Points | Critical |
|---|---:|---|
| State architecture and topology mapping | 10 | Yes |
| RocksDB store lifecycle and capacity | 20 | Yes |
| Changelog/repartition topic durability | 15 | Yes |
| Kubernetes storage, placement and security | 15 | Yes |
| Standby task, rebalance and restore RTO | 15 | Yes |
| Processing guarantee and event integrity | 10 | Yes |
| Incident runbooks and state migration | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated restore testing, missing state/event reconciliation, unreviewed internal topic deletion, unsupported external exactly-once claims, unsafe state reset, leaked secrets or absent independent review.

## 17. Cleanup, references and next chapter

Retire only chapter-owned synthetic application resources after owner approval and evidence retention. Keep changelog/repartition topics and local state until the application is intentionally retired under a reviewed migration/cleanup procedure.

**References:** [Apache Kafka Streams](https://kafka.apache.org/documentation/streams/), [Kafka Streams Developer Guide](https://docs.confluent.io/platform/current/streams/developer-guide/overview.html), [RocksDB Wiki](https://github.com/facebook/rocksdb/wiki), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/).

**Next:** Chapter 064 — Kafka Streams Exactly-Once Processing, Transactions, Rebalancing and Recovery Engineering.

---

**Verification boundary:** Publication proves document availability only. Live RocksDB state restore, changelog durability, Pod-loss recovery, measured RTO and independent technical/security review remain Pending.
