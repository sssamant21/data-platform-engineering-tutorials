# Chapter 094 — Kafka Producer, Consumer, Kafka Connect and Streaming Pipeline Chaos Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 19 — Chaos Engineering and Resilience Validation (4/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS; Kafka Connect, CDC and downstream sink examples  
**Prerequisites:** Chapters 001–093; Kafka delivery semantics, consumer groups, Connect/CDC, schema evolution, streaming state and chaos safety  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter designs synthetic-only, isolated-cluster experiments. Never crash production producers/consumers, restart production Connect workers, interrupt source CDC logs, poison real topics or disrupt healthcare data feeds without approved incident command, change window, rollback and explicit data owner approval. Use no PHI/PII. Fault injection is tabletop until independently approved.

## 1. Mission and learning outcomes

Validate Kafka **end-to-end streaming correctness** under producer failures, ambiguous acknowledgements, consumer rebalances, Kafka Connect worker/task crashes, CDC outages, schema incompatibility, DLQ behavior, sink backpressure and stateful streaming recovery.

Readers will distinguish broker durability from business delivery, build a unique synthetic event ledger, design bounded fault hypotheses, measure freshness and recovery, and independently verify **no unexplained loss, duplication or unauthorized side effects**.

## 2. Streaming failure-domain architecture

```text
Synthetic source / database CDC
               |
        producer / connector
               |
       Kafka topic partitions
               |
       consumer group / stream
               |
   +-----------+-----------+
   |                       |
Kafka Connect sink       DLQ / quarantine
   |                       |
Snowflake / search /     restricted evidence
operational sink
   |
processed-ID ledger + downstream correctness
   |
SLO metrics + alert + incident command
   |
bounded isolated fault -> stop -> reconcile
```

A Kafka broker may preserve acknowledged records while a sink duplicates, loses or delays business effects. Exactly-once guarantees depend on the specific producer, transaction, Kafka Streams/Connect and sink implementation; **do not assume universal end-to-end exactly-once processing**.

## 3. Failure hypotheses and steady-state SLIs

| Dimension | Evidence |
|---|---|
| Producer correctness | unique IDs successfully acknowledged, error and retry records |
| Kafka durability | partition ISR/minISR, offsets, leader stability |
| Consumer correctness | committed offsets, replay, deduplication and processing ledger |
| Connect health | connector/task state, source/sink offsets, DLQ count and retry budget |
| CDC continuity | source log window, capture lag, snapshot boundary |
| Schema safety | compatible schema contract, converter and field constraints |
| Downstream truth | sink IDs, upsert keys, materialized counts and duplicate effects |
| Freshness | event-to-sink latency, lag, recovery time and SLO |

Define workload-specific acceptance thresholds before fault injection. A lag of zero does not prove that sink records were committed.

## 4. Producer chaos engineering

A producer may time out after the broker accepted a batch, making the result **ambiguous**. Idempotent producer configuration reduces duplicates for supported retry cases, but does not make arbitrary application re-submissions or downstream side effects exactly once.

Model Pod crash before/after acknowledgement, client DNS outage, retry storms, max in-flight requests, batching, delivery timeout, transaction boundaries and graceful shutdown. Use unique synthetic event IDs to reconcile outcomes.

## 5. Consumer and rebalance chaos

Consumer restart, heartbeat failure and group reassignment can replay records when offsets are committed before or after side effects. Validate idempotent sink writes, transactional processing where supported, poison-record handling, pause/resume behavior and lag drain.

Kafka ordering is per partition, not across all partitions. Test late/out-of-order events and business-key partitioning assumptions.

## 6. Kafka Connect and CDC chaos

A worker failure triggers connector/task reassignment depending on deployment mode and health. Source and sink connectors differ in offset management and delivery guarantees; validate each connector implementation rather than relying on generic promises.

CDC source downtime can exceed database WAL/oplog/binlog retention and require controlled resnapshot. Track connector lag, source log capacity, schema changes, DLQ, converter failures and downstream idempotency.

## 7. Streaming state and downstream sinks

Kafka Streams and other stateful processors may rebuild local state from changelog topics, replay events and reprocess windows. Check changelog retention, checkpoint/state-store restore, event-time watermarks and external side effects.

For Snowflake/search/analytics sinks, reconcile unique synthetic keys and update semantics, not just row counts. Avoid testing with real patient EMPI or DOB.

## 8. DLQ, schema and privacy controls

Use restricted DLQs with bounded retention, encryption, ownership and explicit recovery procedures. A DLQ may contain full original payloads; **never log or export regulated data as incident evidence**.

A schema compatibility pass does not ensure all consumers are operationally compatible or prevent new sensitive fields. Include coordinated rollout, contract tests and classification review.

## 9. Guarded chaos controls

Every fault requires an approved isolated namespace, exact workload UID, single bounded target, fault TTL, rollback, event ledger and on-call observer. Abort on unexplained acknowledged-event loss, critical downstream error, Kafka ISR/minISR or KRaft risk, unbounded sink retry, privacy exposure or missing telemetry.

Do not automatically replay a failed connector if it may duplicate irreversible downstream side effects; coordinate with data owners.

## 10. Read-only Kubernetes/Strimzi preflight

```bash
kubectl config current-context
kubectl get kafka,kafkaconnect,kafkaconnector -A
kubectl get deployments,statefulsets -A
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.metadata.creationTimestamp
kubectl get networkpolicy -A
```

KafkaConnector CRs may not exist in every deployment and their reconciliation depends on Strimzi configuration. Do not print Secret values or payloads.

## 11. Twenty streaming pipeline chaos labs

### Lab 01 — Approve isolated pipeline game day

**Procedure:** Identify synthetic dataset, owner, scope, approver, stop conditions and rollback.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Map end-to-end event path

**Procedure:** Document producer, Kafka topic, consumer, Connect/CDC, DLQ, sink and state stores.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Establish correctness ledger

**Procedure:** Assign unique synthetic event IDs and expected sink materialization.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Baseline producer delivery

**Procedure:** Measure acks, retries, P99, throughput, error codes and idempotence.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Baseline consumer freshness

**Procedure:** Measure lag, commit cadence, rebalance, processing delay and downstream freshness.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Validate connector configuration

**Procedure:** Inventory source/sink tasks, converter, schema, error tolerance and DLQ.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Design producer Pod crash

**Procedure:** Model in-flight batches, unknown outcomes, idempotence and safe replay.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Design producer network timeout

**Procedure:** Model ambiguous ack, retries, ordering and duplicate prevention.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Design consumer restart/rebalance

**Procedure:** Evaluate partition assignment, offset commits and idempotent processing.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Design poison-message isolation

**Procedure:** Use synthetic malformed record, quarantine and DLQ ownership.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Design Connect worker crash

**Procedure:** Model task reassignment, source offsets, sink writes and restart convergence.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Design connector task failure

**Procedure:** Evaluate retry policy, error handling, DLQ and no silent skips.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Design CDC source outage

**Procedure:** Model connector lag, source log retention and restart without gap.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Design schema incompatibility

**Procedure:** Evaluate producer rejection, schema evolution and consumer recovery.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Design sink outage/backpressure

**Procedure:** Measure Connect buffering, retries, consumer lag and downstream recovery.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Design stateful stream restart

**Procedure:** Evaluate checkpoint/changelog restore, window state and replay semantics.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Design duplicate/out-of-order events

**Procedure:** Validate key-based ordering scope, dedupe, late-event windows and business rules.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Design DLQ privacy controls

**Procedure:** Review retention, ACL, encryption and no PHI in test payload/logs.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Measure full pipeline recovery

**Procedure:** Compare acknowledged IDs to sink IDs, duplicates, omissions and freshness.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Independent pipeline acceptance

**Procedure:** Review faults, correctness ledger, data safety, SLO and signoff.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/Connect/client versions, source-to-sink lineage, synthetic IDs, hypothesis, baseline SLO, fault scope/duration, expected/observed, producer acknowledgements, sink reconciliation, duplicates/omissions, lag/freshness, abort/rollback, **Tabletop** vs **Live**, owner and independent reviewer. **Status: Pending** until executed.

## 12. Offline end-to-end correctness validator

Save as `validate_pipeline_ledger.py`. Inputs are **synthetic JSON arrays** of acknowledged producer IDs and materialized sink IDs. This is not a live Kafka or connector test.

```python
#!/usr/bin/env python3
import argparse
import collections
import json

p = argparse.ArgumentParser()
p.add_argument("ledger", help="JSON with acknowledged_ids and sink_ids")
args = p.parse_args()
with open(args.ledger, encoding="utf-8") as f:
    d = json.load(f)
if not isinstance(d, dict):
    p.error("expected object")
for key in ("acknowledged_ids", "sink_ids"):
    if not isinstance(d.get(key), list) or any(
        not isinstance(v, str) or not v for v in d[key]
    ):
        p.error(key + " must be an array of nonempty synthetic ID strings")
acked = collections.Counter(d["acknowledged_ids"])
sink = collections.Counter(d["sink_ids"])
missing = sorted(set(acked) - set(sink))
unexpected = sorted(set(sink) - set(acked))
duplicates = {k: v for k, v in sink.items() if v > 1}
duplicate_ack_ids = {k: v for k, v in acked.items() if v > 1}
passed = bool(acked) and not missing and not unexpected and not duplicates and not duplicate_ack_ids
print(json.dumps({
    "acknowledged_unique": len(acked), "sink_unique": len(sink),
    "missing_in_sink": missing, "unexpected_in_sink": unexpected,
    "duplicate_sink_ids": duplicates, "duplicate_acknowledged_ids": duplicate_ack_ids,
    "pass": passed
}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Caveats:** This checks one-to-one ID materialization only. Upserts, tombstones, aggregations, intentional fan-out, multi-output streaming and exactly-once business semantics require a domain-specific oracle. It cannot detect a sink that falsely reports its ledger or confirm transaction durability. Run after lag drains and capture source/sink consistency boundaries.

## 13. Twelve pipeline chaos failure scenarios

### Scenario 01 — Producer timeout hides ambiguous acknowledgement

**Diagnosis:** Reconcile event IDs before retry and inspect idempotence/acks. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 02 — Producer Pod crash loses buffered messages

**Diagnosis:** Differentiate acknowledged from unacknowledged records and inspect flush policy. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 03 — Consumer rebalance repeats side effects

**Diagnosis:** Check offset commit ordering, sink idempotency and transactional boundary. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 04 — Consumer lag never drains after recovery

**Diagnosis:** Assess partition skew, downstream throughput and backpressure. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 05 — Connect worker failure stalls tasks

**Diagnosis:** Inspect rebalance, task status, plugin dependencies and connector logs. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 06 — Connector silently skips bad records

**Diagnosis:** Audit error tolerance, DLQ routing and reconciliation. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 07 — CDC source log expires during outage

**Diagnosis:** Review source retention and resnapshot/recovery plan. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 08 — Schema change breaks deserialization

**Diagnosis:** Check registry compatibility, converter and rollout coordination. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 09 — Sink outage causes uncontrolled retry storm

**Diagnosis:** Bound retries, backoff and sink protection while preserving offsets. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 10 — Stateful stream replay changes output

**Diagnosis:** Review event-time, windows, state stores and deterministic processing. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 11 — DLQ exposes sensitive payload

**Diagnosis:** Contain access, sanitize evidence and notify privacy response. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

### Scenario 12 — All metrics green but sink misses events

**Diagnosis:** Fail acceptance until independent end-to-end reconciliation passes. Correlate producer ack/retry logs, Kafka partition offsets, consumer commits/rebalances, Connect task/CDC lag, DLQ, schema registry, sink state and synthetic ID ledger. **Response:** Stop bounded fault, preserve data correctness, protect source log retention, contain sensitive payload exposure and coordinate replay. **Exit:** Reconciled IDs and business effects, stable Kafka/Connect, recovered freshness, RCA and independent review.

## 14. Eight production pipeline recovery runbooks

### Runbook A — Pipeline chaos preflight

**Trigger/actions:** Confirm isolated Kafka, synthetic event ledger, dependencies, SLO and approvals. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook B — Producer crash and retry recovery

**Trigger/actions:** Validate acknowledged IDs, idempotence, ordering and restored throughput. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook C — Consumer rebalance and offset recovery

**Trigger/actions:** Check group assignment, commits, lag and duplicate side effects. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook D — Kafka Connect task/worker failure

**Trigger/actions:** Inspect status, DLQ, retries, source/sink offsets and recovery. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook E — CDC source outage

**Trigger/actions:** Protect source log window, monitor connector lag and resnapshot approval. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook F — Schema incompatibility incident

**Trigger/actions:** Quarantine invalid events, restore compatible contracts and reconcile. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook G — Sink backpressure and streaming state

**Trigger/actions:** Protect downstream system, checkpoint/replay and catch-up safely. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

### Runbook H — Pipeline acceptance and RCA

**Trigger/actions:** Reconcile producer-to-sink IDs, SLO recovery, incident timeline and signoff. **No-go:** real PHI, production fault without approval, unexplained acknowledged-ID loss, irreversible duplicate side effects, source log expiry risk, uncontrolled DLQ or no rollback. **Exit:** Fault removed, producer/consumer/Connect healthy, end-to-end synthetic correctness verified, SLO recovered and evidence reviewed.

## 15. Evidence package

```text
evidence-ch094/
  01-game-day-approval.md
  02-pipeline-lineage.md
  03-correctness-ledger.json
  04-producer-baseline.md
  05-consumer-baseline.md
  06-connect-config-review.md
  07-producer-crash.md
  08-producer-timeout.md
  09-consumer-rebalance.md
  10-poison-message.md
  11-connect-worker-failure.md
  12-connector-task-failure.md
  13-cdc-source-outage.md
  14-schema-incompatibility.md
  15-sink-backpressure.md
  16-stateful-recovery.md
  17-duplicate-ordering.md
  18-dlq-privacy.md
  19-pipeline-reconciliation.md
  20-independent-acceptance.md
  scorecard.md
```

Every artifact includes UTC time, environment/version, **Tabletop** vs **Live**, synthetic data, fault target/duration, expected/observed, producer acknowledgements, sink ledger, retries/duplicates, lag/freshness, abort/rollback and independent reviewer.

## 16. 100-point pipeline resilience acceptance

| Domain | Points | Critical |
|---|---:|---|
| Experiment safety, lineage and baseline | 15 | Yes |
| Producer acknowledgement and retry correctness | 20 | Yes |
| Consumer offsets, rebalance and duplicate handling | 20 | Yes |
| Kafka Connect/CDC, schema and DLQ resilience | 20 | Yes |
| Sink reconciliation, freshness and recovery | 15 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** unapproved production fault, unexplained acknowledged-ID loss, unhandled duplicate side effects, unsafe source-log expiry, sensitive data leak, absent rollback or fabricated live evidence.

**Current status:** **Pending**. No live producer, consumer, connector or streaming failure injection is claimed.

## 17. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Kafka Connect](https://kafka.apache.org/documentation/#connect), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/).

**Next:** Chapter 095 — Kafka Enterprise Chaos Engineering, Resilience Game Day and Reliability Acceptance Capstone.

---

**Verification boundary:** Publication confirms document availability only. Live fault injection, source-to-sink event reconciliation, SLO measurements and independent technical/security review remain Pending.
