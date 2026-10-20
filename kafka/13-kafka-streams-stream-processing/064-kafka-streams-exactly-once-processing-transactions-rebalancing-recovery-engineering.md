# Chapter 064 — Kafka Streams Exactly-Once Processing, Transactions, Rebalancing and Recovery Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 13 — Kafka Streams and Stream Processing (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–063, especially 061–063  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety boundary:** All transaction-fencing, Pod crash, broker failure, offset reset and state rebuild drills are **tabletop by default**. Only use synthetic events in an approved disposable Kubernetes/Strimzi cluster for live testing. Do not delete production internal topics, reuse a production `application.id`, modify Kafka transactional ACLs without review, disable TLS or claim exactly-once behavior for external databases/HTTP calls.

## 1. Mission and learning objectives

Operate Kafka Streams' transactional processing model as an SRE. Distinguish idempotent Kafka producers, Kafka transactions, consumer isolation and Kafka Streams' `exactly_once_v2` processing guarantee. Explain task migration, rebalance, fencing, aborted records, local state recovery and end-to-end event integrity under failure.

At completion, learners can identify the Kafka transaction boundary, audit Kafka transactional authorization, distinguish committed from aborted records, plan a Kubernetes rolling restart, and independently verify recovery without inventing RPO/RTO evidence.

## 2. End-to-end architecture

```text
Kafka input topic / source partitions
           |
    Streams active task
           |
  state store + changelog ---------+
           |                       |
  transactional Kafka producer     |
           |                       |
  Kafka output topic               |
           +--> input offsets -----+
                   |
          Kafka transaction coordinator
          (__transaction_state)
                   |
     read_committed Kafka consumer
                   |
     external sink (NOT in Kafka txn)
                   |
       idempotent event-ID ledger
```

Kafka Streams coordinates consumed offsets, Kafka output and relevant state/changelog writes transactionally where supported. A transaction commit does not atomically commit an external database, HTTP endpoint, object store or third-party service.

## 3. Delivery semantics: compare precisely

| Mode | What it protects | What it does not prove |
|---|---|---|
| At-most-once | avoids replay after early offset advancement | may lose records after crash |
| At-least-once | retries after uncertain failures | duplicate outputs/business effects possible |
| Idempotent Kafka producer | broker deduplication of retried batches within supported producer/session semantics | cross-system exactly-once or arbitrary application duplicates |
| Kafka transactions | atomic visibility of Kafka writes and offsets under correct consumer isolation | external side effects |
| Kafka Streams `exactly_once_v2` | supported Kafka-scoped read-process-write and state updates | source/business event uniqueness and external sink atomicity |

Do not equate a green Pod, zero consumer lag or a successful producer callback with business-level exactly-once processing.

## 4. Producer fencing, epochs and transactional identity

A transactional producer uses a `transactional.id` and broker-maintained producer identity/epoch to fence stale producers. During failover or task reassignment, a stale instance must not continue committing transactions after ownership moves. Producer fencing is a correctness mechanism, not a symptom to bypass by granting broader permissions or disabling transactions.

Kafka Streams manages internal transactional producer identities; avoid manually assigning a fixed `transactional.id` to multiple application instances. Audit transactional ID ACLs using the approved Strimzi KafkaUser configuration and exact client release.

## 5. Consumer visibility: read_committed

A consumer with `isolation.level=read_committed` reads committed transactional data and nontransactional records, withholding aborted transactional output. Consumers using `read_uncommitted` may see records from aborted transactions. Open transactions can hold back the last stable offset (LSO), making read-committed consumers appear delayed even when the broker has more appended records.

Downstream consumer isolation must be part of the EOS acceptance test; the Streams application configuration alone is insufficient.

## 6. Exactly-once-v2 configuration sketch

The following is a **Java configuration excerpt**, not a complete runnable application. Validate supported config names and the broker/client compatibility matrix.

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "sre-ch64-eos-v1");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");
props.put(StreamsConfig.STATE_DIR_CONFIG, "/var/lib/kafka-streams/state");
props.put(StreamsConfig.NUM_STANDBY_REPLICAS_CONFIG, 1);
props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());
// Production: use approved TLS/SASL Secrets, least-privilege ACLs and monitored timeouts.
// Kafka Streams owns internal transaction lifecycle and task-scoped producers.
```

The `commit.interval.ms` setting affects how often Streams commits processing progress and may trade latency/transaction overhead. Kafka broker `transaction.max.timeout.ms` limits allowable client transaction timeouts. Avoid raising timeouts as the first response to blocked processing.

## 7. Kafka durability prerequisites

- KRaft controller quorum must be healthy; Kafka brokers must meet ISR/minISR for transactional writes.
- Internal `__transaction_state` and `__consumer_offsets` topics must be healthy and configured with durable replication suitable for the cluster size.
- Streams changelog and repartition topics need correct RF, ACL, retention and sufficient broker storage.
- The application principal needs the approved topic, group and transactional ID permissions.
- Kafka TLS/SASL and Kubernetes NetworkPolicy must allow only intended traffic.
- Broker failures and coordinator migration can temporarily disrupt transaction commits; recovery must be observed rather than assumed.

## 8. Kubernetes deployment review

```yaml
# Reference Deployment fragment; requires approved image, Secrets and listener.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-ch64-streams
  namespace: kafka-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: sre-ch64-streams}
  template:
    metadata:
      labels: {app: sre-ch64-streams}
    spec:
      terminationGracePeriodSeconds: 120
      containers:
        - name: streams
          image: registry.example.invalid/sre/ch64@sha256:REPLACE_WITH_APPROVED_DIGEST
          resources:
            requests: {cpu: "500m", memory: "1Gi", ephemeral-storage: "2Gi"}
            limits: {cpu: "2", memory: "2Gi", ephemeral-storage: "6Gi"}
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities: {drop: ["ALL"]}
```

This is **not deployable as-is**: supply Kafka client credentials, listener, non-root writable state directory, health probes aware of restore/rebalance, PodDisruptionBudget, topology spread and version-pinned image. A graceful shutdown must allow `KafkaStreams.close()` to finish within Kubernetes termination grace; abrupt SIGKILL can cause task migration and replay.

## 9. Read-only Strimzi/Kubernetes preflight

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,svc,pvc -o wide
kubectl -n kafka-lab get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get deploy sre-ch64-streams -o wide
```

A missing example Deployment means **NOT DEPLOYED**. Never infer that Kafka transactions are functioning from Kubernetes inventory alone.

## 10. Twenty Kubernetes-first EOS and recovery labs

### Lab 01 — Approve EOS and failure-safety charter

**Procedure:** Define business event integrity, Kafka-only transaction boundary, owner, SLO, RPO/RTO and abort criteria.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 02 — Inventory Kafka KRaft and Strimzi

**Procedure:** Record Kafka/Strimzi versions, quorum, RF, minISR, KafkaUser ACLs and transaction coordinator health.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 03 — Inventory Streams deployment and image

**Procedure:** Record Java/Streams version, image digest, application.id, topology, store names and replicas.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 04 — Review producer idempotence and transaction semantics

**Procedure:** Distinguish producer sequence deduplication from Streams transactionally coordinated processing.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 05 — Review exactly_once_v2 compatibility

**Procedure:** Confirm pinned Kafka Streams and broker versions support EOS-v2 and transactional authorization.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 06 — Review transactional ACLs

**Procedure:** Inspect Write/Read/Describe and TransactionalId authorization for approved application principals.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 07 — Inspect Kafka internal topic durability

**Procedure:** Review __transaction_state, __consumer_offsets and Streams changelog/repartition RF/minISR.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 08 — Compare at-least-once with EOS-v2

**Procedure:** Use synthetic input IDs and expected outputs to build a failure/replay matrix.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 09 — Inspect transaction commit cadence

**Procedure:** Assess commit.interval.ms, producer buffering, latency, open transactions and recovery.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 10 — Review read_committed consumers

**Procedure:** Confirm downstream consumer isolation and visibility of aborted/uncommitted records.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 11 — Review task assignment and rebalance

**Procedure:** Map source partitions, active tasks, standby tasks, cooperative movement and migration.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 12 — Review graceful Kubernetes shutdown

**Procedure:** Check terminationGracePeriodSeconds, SIGTERM, streams.close and drain timing.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 13 — Review PodDisruptionBudget and topology spread

**Procedure:** Evaluate rollout maxUnavailable, PDB, node failure domains and capacity for standby tasks.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 14 — Model worker crash before transaction commit

**Procedure:** Predict aborted Kafka output, input offset visibility, retry and state-store rollback/recovery.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 15 — Model crash after transaction commit

**Procedure:** Predict committed output, consumed offsets and duplicate business event handling.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 16 — Model broker/controller outage

**Procedure:** Check transaction coordinator availability, ISR/minISR, timeout and Streams recovery.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 17 — Model transaction fencing

**Procedure:** Analyze producer epoch/transactional identity, stale instance fencing and safe single ownership.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 18 — Model rebalance during state restore

**Procedure:** Assess changelog restore, task revocation, standby catch-up and output integrity.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 19 — Model external sink side effect

**Procedure:** Show why Kafka EOS does not atomically commit arbitrary database/HTTP side effects.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

### Lab 20 — Complete EOS acceptance and rollback

**Procedure:** Reconcile source IDs, committed Kafka outputs, aborted records, sink IDs and signed security review.

**Expected evidence:** Record Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected and observed Kafka committed/aborted output IDs, input offsets, transaction and task states, changelog integrity, security, rollback/abort and independent reviewer. Mark **Pending** until executed. Broker outages, task fencing and forced crashes are **Tabletop** unless approved in disposable infrastructure.

## 11. Read-only verification script

Save as `verify-ch64.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Kafka KRaft'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/9] Storage'; kubectl -n "$NS" get pvc -o wide
echo '[5/9] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo '[6/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[7/9] Streams Deployment'
if kubectl -n "$NS" get deploy sre-ch64-streams >/dev/null 2>&1; then
  kubectl -n "$NS" get deploy sre-ch64-streams -o wide
  kubectl -n "$NS" get pods -l app=sre-ch64-streams -o wide
else
  echo 'NOT DEPLOYED: sre-ch64-streams'
fi
echo '[8/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/9] CRD schema'; kubectl explain kafka.spec
echo 'PASS: read-only Kubernetes inventory.'
echo 'NOT PROVEN: transaction atomicity, read_committed, fencing, EOS, state recovery or security review.'
```

Run `chmod +x verify-ch64.sh && ./verify-ch64.sh | tee evidence-ch64/preflight.txt`. A successful inventory is **not** an EOS acceptance result.

## 12. Twelve transaction/rebalance failure scenarios

### Scenario 1 — ProducerFencedException

**Diagnosis:** Inspect competing transactional identity, stale instances and rollout overlap. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 2 — Transaction timeout exceeded

**Diagnosis:** Inspect processing stall, commit interval, broker limits and long-running callbacks. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 3 — InvalidProducerEpochException

**Diagnosis:** Inspect producer epoch/fencing, coordinator transitions and client compatibility. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 4 — NotEnoughReplicasException

**Diagnosis:** Inspect ISR/minISR, broker failures, transactional writes and recovery. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 5 — Authorization failure for transactional ID

**Diagnosis:** Inspect KafkaUser ACL, TransactionalId resource and identity mapping. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 6 — read_uncommitted consumer sees aborted data

**Diagnosis:** Review downstream isolation.level and output reconciliation. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 7 — Repeated rebalance during rolling deployment

**Diagnosis:** Inspect Pod termination, cooperative assignment, probes and PDB. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 8 — State store recovery repeats processing

**Diagnosis:** Review changelog, input offsets, EOS transaction status and idempotent business keys. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 9 — Long open transaction delays visibility

**Diagnosis:** Review commit interval, processing latency, LSO and read_committed lag. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 10 — Transaction coordinator unavailable

**Diagnosis:** Inspect __transaction_state partitions, ISR, broker and controller health. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 11 — External database contains duplicate side effects

**Diagnosis:** Review outbox/idempotent sink and Kafka-only EOS boundary. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

### Scenario 12 — Consumer lag zero but output missing

**Diagnosis:** Review aborted transactions, output topic, state-store semantics and event ledger. Correlate transaction coordinator and broker health, Kafka ISR, Streams task/producer state, consumer isolation, Pod lifecycle, changelog, input/output event IDs and external sink effects. **Response:** Preserve evidence, freeze unsafe offset/state mutations, recover Kafka durability, follow approved rollout/rollback and independently reconcile committed IDs. **Evidence:** UTC timeline, expected/observed transaction matrix, security and reviewer.

## 13. Eight production runbooks

### Runbook A — EOS transaction failure

**Trigger and response:** Inspect producer fencing, transaction coordinator, ACL, timeout and abort/retry safety. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook B — Broker quorum and transaction durability

**Trigger and response:** Inspect KRaft, __transaction_state, __consumer_offsets, RF/ISR and minISR. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook C — Streams rebalance storm

**Trigger and response:** Review group state, Pod churn, graceful shutdown, task assignment and PDB. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook D — Stateful crash recovery

**Trigger and response:** Verify changelog, RocksDB restoration, committed offsets and event-ID reconciliation. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook E — Consumer visibility mismatch

**Trigger and response:** Inspect read_committed isolation, last stable offset and aborted transaction effects. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook F — Transactional identity/security incident

**Trigger and response:** Audit KafkaUser, TransactionalId ACL, stale instances, TLS/SASL and fencing. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook G — External sink duplicate investigation

**Trigger and response:** Reconcile Kafka output vs external durable IDs, enforce idempotency and compensate safely. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

### Runbook H — EOS acceptance and change rollback

**Trigger and response:** Measure transaction SLO, lag, RTO, security, rollback and independent signoff. **Safety:** Never bypass fencing, disable Kafka transactions to mask loss, delete internal topics, reset production offsets, expose secrets or assume external sinks are transactionally covered. **Exit:** Healthy broker/transaction coordinator, correct committed visibility, stable task assignment, bounded lag, reconciled business event IDs, RCA and independent approval.

## 14. Failure/visibility acceptance matrix

| Fault boundary | Expected Kafka-scoped outcome under EOS-v2 | Must verify |
|---|---|---|
| Crash before transaction commit | uncommitted Kafka output not visible to read_committed consumers | aborted/hidden IDs and offset retry |
| Crash after commit | committed output and input offsets persist | no Kafka-scoped duplicate from replay |
| Stale producer after task reassignment | stale producer fenced | producer epoch/error and new owner |
| Consumer read_uncommitted | may observe aborted records | isolation-level comparison |
| Long open transaction | read_committed visibility may lag LSO | transaction duration and lag |
| Broker ISR below minISR | writes may fail rather than silently weaken durability | ISR and producer errors |
| External sink commit then crash | side effect may duplicate on replay | sink idempotency ledger |
| Rebalance during restore | task migration and changelog catch-up | restore RTO and state reconciliation |

The matrix describes intended semantics, not measured results. Build a synthetic ID ledger and record the actual outcome of each approved live test.

## 15. SLI/SLO and alert design

| Signal | Why it matters | Alert concept |
|---|---|---|
| Transaction abort/failure rate | transactional processing disruption | sustained increase |
| Transaction coordinator availability | commit and fencing reliability | coordinator failures |
| Read-committed lag/LSO | committed output visibility | sustained freshness breach |
| Streams task rebalance duration | availability and processing pause | RTO risk |
| Changelog restore bytes/time | state recovery capacity | predicted restore > budget |
| Kafka ISR/minISR | transactional durability | under-replication |
| Pod termination duration | graceful close and task handoff | termination budget exhausted |
| Input vs committed output IDs | Kafka-scoped correctness | missing or unexpected IDs |
| External sink durable ID ledger | business correctness | duplicates/missing effects |

Derive thresholds from observed workload and business SLO; do not invent universal values.

## 16. Evidence package

```text
evidence-ch64/
  approved-eos-charter-raci.md
  kafka-strimzi-streams-jdk-version-matrix.md
  preflight.txt
  transaction-coordinator-kraft-isr.md
  immutable-image-topology-identity.md
  idempotence-vs-transaction-contract.md
  eos-v2-client-broker-compatibility.md
  transactional-id-acl-review.md
  internal-topic-durability.md
  at-least-once-vs-eos-fixture.csv
  commit-interval-timeout-budget.md
  read-committed-lso-matrix.csv
  task-assignment-rebalance.md
  kubernetes-graceful-shutdown.md
  pdb-topology-spread.md
  crash-before-commit-tabletop.md
  crash-after-commit-tabletop.md
  broker-coordinator-outage-tabletop.md
  producer-fencing-tabletop.md
  rebalance-restore-tabletop.md
  external-sink-idempotency.md
  accepted-input-event-ledger.csv
  committed-kafka-output-ledger.csv
  durable-external-sink-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

All evidence requires exact versions, UTC timestamps, expected/observed result, **Live** vs **Tabletop**, redaction, owner, abort/rollback and independent reviewer.

## 17. 100-point EOS reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Kafka transaction semantics and EOS boundary | 20 | Yes |
| Kafka KRaft coordinator, ISR and internal topic durability | 15 | Yes |
| Transactional ACLs, TLS/SASL and Kubernetes security | 15 | Yes |
| Producer fencing, epochs and read_committed | 15 | Yes |
| Task rebalance, graceful shutdown and state restore | 15 | Yes |
| Event-ID integrity and external sink idempotency | 10 | Yes |
| SLO, runbooks and rollback | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated EOS testing, unsupported external exactly-once claims, unreviewed offset reset, deletion of production internal topics, bypassed fencing, leaked credentials or absent independent review.

## 18. Cleanup, references and next chapter

Remove only chapter-owned synthetic app resources after approval and evidence retention. Preserve internal topics and state until intentionally retired using a reviewed Streams reset/migration plan.

**References:** [Apache Kafka Streams](https://kafka.apache.org/documentation/streams/), [Apache Kafka Transactions](https://kafka.apache.org/documentation/#semantics), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/).

**Next:** Chapter 065 — Kafka Streams Production Observability, Performance, Failure Recovery and Reliability Acceptance Capstone.

---

**Verification boundary:** Publication proves document availability only. Live transactional fault injection, read_committed visibility, fencing, recovery RTO and independent technical/security review remain Pending.
