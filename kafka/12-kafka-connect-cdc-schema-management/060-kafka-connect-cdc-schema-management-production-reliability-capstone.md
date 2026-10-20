# Chapter 060 — Kafka Connect, CDC and Schema Management Production Reliability Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 12 — Kafka Connect, CDC and Schema Management (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Primary CDC example:** PostgreSQL + Debezium + Kafka Connect + Schema Registry + idempotent sink  
**Prerequisites:** Chapters 001–059, especially 056–059  
**Status:** Published · **Live integrated drills:** Pending · **Independent DBRE/SRE/security review:** Pending

> **Safety boundary:** Default all database outage, WAL saturation, worker disruption, registry outage, CDC failover, schema-breaking deployment, resnapshot and offset-reset exercises to **tabletop**. Only run bounded synthetic tests in explicitly approved disposable infrastructure. Never stop production databases, drop replication slots, delete Kafka Connect internal topics, bypass TLS/ACL, disable schema compatibility or assume zero data loss from healthy Pods. Publication is not proof of production readiness.

## 1. Mission

Integrate Kafka Connect architecture (056), source/sink reliability (057), Debezium CDC and database safety (058), and schema governance (059) into one independent enterprise reliability capstone. Prove a transaction can travel from a database commit through Kafka to a durable downstream sink while preserving schema meaning, idempotency, security and operational recovery.

## 2. Required outcomes

- Document a complete, independently reviewable source-to-sink architecture and business contract.
- Validate Strimzi/KRaft health, Connect workers/tasks and internal topic durability.
- Establish PostgreSQL WAL/slot/publication/snapshot retention controls and safe DBRE ownership.
- Validate schema registry implementation, subject governance, Avro/Protobuf/JSON Schema compatibility and converter correctness.
- Demonstrate or plan end-to-end unique-event reconciliation, including updates, deletes and tombstones.
- Measure source commit → Kafka acceptance → durable sink freshness with explicit time uncertainty.
- Rehearse worker failure, DB outage, WAL pressure, registry failure, poison pills, breaking schema and CDC failover decisions.
- Produce UTC evidence, runbooks, RCA, risk register and independent acceptance score.

## 3. Integrated architecture

```text
PostgreSQL OLTP primary
  transaction commit + WAL LSN
             |
    publication + logical slot
             |
  Debezium SourceConnector task  -- snapshot/stream offsets
             |
      Kafka Connect workers
      (config/offset/status)
             |
      converters / SMTs <------ Schema Registry
             |                 (subjects/IDs/compatibility)
     Kafka KRaft topic
    (RF, ISR, ACL, retention)
             |
      SinkConnector tasks
             |
  idempotent sink commit
             |
  accepted ID / durable ID ledger
             |
  DBRE + Kafka SRE + security alerts, SLO and incident command
```

**Failure boundaries:** Kubernetes Pod readiness does not prove task health; RUNNING tasks do not prove CDC freshness; schema compatibility does not prove business semantics; Kafka producer acknowledgments do not prove sink durability; an asynchronous pipeline cannot claim zero RPO without evidence.

## 4. Non-negotiable acceptance gates

| Gate | Required evidence | Decision when missing |
|---|---|---|
| Business contract | signed freshness SLO, loss tolerance, RPO/RTO, owner | BLOCK |
| Database safety | WAL headroom, slot retention budget, approved snapshot plan | BLOCK |
| Kafka durability | KRaft quorum, RF/ISR/minISR, acks contract | BLOCK |
| Connect | worker group, internal topics, task status, offsets | BLOCK |
| Source CDC | publication/slot, LSN progression, source identity | BLOCK |
| Schema registry | TLS/auth, subject owner, compatibility CI, backup | BLOCK |
| Sink correctness | idempotent key, deletes, tombstones, durable ID ledger | BLOCK |
| Security | DB/Kafka/registry TLS, least privilege, PII redaction | BLOCK |
| Recovery | failover/resnapshot/rollback and single-writer authority | BLOCK |
| Independent review | DBRE, SRE, security and business approval | NOT READY |

**No-go:** Unknown WAL pressure, unreviewed slot deletion, incompatible schema, missing sink ledger, exposed credentials, unsupported exactly-once claims or unapproved production fault injection.

## 5. RPO, RTO, CDC freshness and evidence semantics

Define:
- **Source acceptance:** committed DB transaction with stable transaction/event ID and source LSN/GTID (engine-specific).
- **Kafka acceptance:** successful broker acknowledgment and captured topic-partition-offset/event ID.
- **Sink durability:** independently queried durable record/event ID or approved committed sink transaction.
- **Freshness:** sink durable commit UTC minus source commit UTC, with clock-skew bounds.
- **Observed missing set:** accepted source IDs minus sink durable IDs at a documented cutoff.
- **RTO:** verified end-to-end service restoration UTC minus declared outage start UTC.

A healthy schema registry or zero Kafka lag is not a substitute for unique-event reconciliation. Snapshot rows and streaming updates require key/version-aware accounting; simply counting records may double-count updates. Label all tabletop numbers **Hypothetical**, never **Measured**.

## 6. Kubernetes and PostgreSQL read-only preflight

```bash
# Approved disposable context; read-only Kubernetes inventory.
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkaconnect,pods,svc,pvc,networkpolicy -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl api-resources | grep -Ei 'kafkaconnect|kafkaconnector'
kubectl explain kafkaconnect.spec
kubectl -n kafka-lab get kafkaconnector -o wide
```

```sql
-- Run separately with an authorized PostgreSQL account.
SHOW server_version;
SHOW wal_level;
SHOW max_replication_slots;
SHOW max_wal_senders;
SHOW max_slot_wal_keep_size;
SELECT slot_name, plugin, slot_type, active, restart_lsn, confirmed_flush_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_wal_bytes
FROM pg_replication_slots WHERE slot_type = 'logical';
SELECT pubname, puballtables FROM pg_publication;
```

Interpret slot lag on the appropriate primary, check null LSNs, version/permission constraints and compare to actual `pg_wal` filesystem capacity. The LSN delta is an estimate of WAL retained from the slot restart point, not a direct disk-usage measurement.

## 7. Synthetic integrated data fixture

```json
{"event_id":"sre060-001","order_id":"o-001","version":1,"operation":"insert","amount":10}
{"event_id":"sre060-002","order_id":"o-001","version":2,"operation":"update","amount":12}
{"event_id":"sre060-003","order_id":"o-002","version":1,"operation":"insert","amount":20}
{"event_id":"sre060-004","order_id":"o-002","version":2,"operation":"delete"}
```

This is a design fixture, **not** an actual Debezium envelope. For delete semantics, capture both the change event and any compaction tombstone behavior according to connector configuration. The sink's expected final state is `o-001=12` and `o-002` absent. Also preserve an immutable processing ledger for all four accepted synthetic events.

## 8. Twenty integrated Kubernetes-first capstone labs

### Lab 01 — Approve integrated capstone charter

**Procedure:** Assign DBRE, Kafka SRE, platform, application, security, incident commander and assessor; set business RPO/RTO, freshness and abort conditions.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 02 — Inventory Kubernetes platform and versions

**Procedure:** Record exact Strimzi, Kafka, KRaft, Connect, Debezium, PostgreSQL and registry versions, CRD schemas and immutable images.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 03 — Validate broker/controller safety

**Procedure:** Record KRaft quorum, ISR/minISR, RF, PVC/CSI, storage and failure-domain assumptions.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 04 — Validate Connect worker group

**Procedure:** Inspect worker replicas, internal config/offset/status topics, Kafka ACLs, Service isolation and task assignment.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 05 — Validate Debezium source database

**Procedure:** Read PostgreSQL wal_level, slot/publication metadata, permissions, snapshot policy, replication lag and WAL disk headroom.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 06 — Validate registry and subject governance

**Procedure:** Record implementation, TLS/auth, subject strategy, Avro/Protobuf/JSON Schema policies, backup and owner.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 07 — Validate sink idempotency and deletes

**Procedure:** Define primary key, upsert/delete, tombstones, transaction boundaries, duplicates and replay contract.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 08 — Create synthetic event acceptance fixture

**Procedure:** Design unique IDs, source transaction/LSN, Kafka callback, sink durable commit, schema version and UTC timestamps.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 09 — Baseline end-to-end freshness

**Procedure:** Calculate source commit to Kafka acceptance and durable sink latency; identify unknown clock/skew and lag gaps.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 10 — Review initial snapshot load budget

**Procedure:** Define DB CPU/IO/locks, snapshot boundary, table allowlist, rate limits and rollback.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 11 — Review streaming and slot retention budget

**Procedure:** Correlate confirmed_flush_lsn, restart_lsn, WAL bytes, Connect task state and disk alerting.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 12 — Validate schema evolution matrix

**Procedure:** Evaluate Avro writer/reader, Protobuf field tags and JSON Schema required/additionalProperties with CI gates.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 13 — Validate converter and SMT correctness

**Procedure:** Review Debezium envelope, key, schema ID, SMT chain, PII masking and tombstone semantics.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 14 — Model Connect worker failure tabletop

**Procedure:** Analyze task rebalance, source cursor continuity, sink duplicates, offsets and end-to-end freshness.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 15 — Model database outage tabletop

**Procedure:** Analyze WAL/binlog retention, connector restart, source failover and no-loss claims.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 16 — Model registry outage tabletop

**Procedure:** Assess serializer cache, new registration failure, registry DR, schema ID mapping and client behavior.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 17 — Model poison pill and DLQ tabletop

**Procedure:** Review converter errors, DLQ authorization, sensitive-data redaction, replay and data integrity.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 18 — Model breaking schema rollback tabletop

**Procedure:** Enforce compatibility CI, halt rollout, restore producer/consumer contract and reconcile events.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 19 — Model CDC failover and resnapshot tabletop

**Procedure:** Require DBRE approval, slot/timeline/GTID verification, offset backup and bounded reconciliation.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

### Lab 20 — Complete independent acceptance and RCA

**Procedure:** Score 100-point rubric, assess RPO/RTO as observed or Unknown, collect signed DBRE/SRE/security decisions and corrective actions.

**Expected evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/Connect/Debezium/DB/registry versions, UTC commands, expected/observed outputs, WAL/slot budget, schema compatibility, event-ID reconciliation, security, abort/rollback and independent assessor. Mark **Pending** until executed. Failure injections and state-changing exercises are **Tabletop** unless independently authorized in a disposable lab.

## 9. Read-only capstone verification script

Save as `verify-ch60.sh`. This does not inspect DB slots or prove CDC correctness; run Section 6 SQL independently.

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka/Connect'; kubectl -n "$NS" get kafka,kafkanodepool,kafkaconnect -o wide
echo '[3/10] KafkaConnector CRD'
if kubectl api-resources -o name | grep -q '^kafkaconnectors.kafka.strimzi.io$'; then
  kubectl -n "$NS" get kafkaconnector -o wide
else
  echo 'UNKNOWN: KafkaConnector CRD not discovered'
fi
echo '[4/10] Pods'; kubectl -n "$NS" get pods -o wide
echo '[5/10] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[6/10] NetworkPolicies'; kubectl -n "$NS" get networkpolicy
echo '[7/10] PVC'; kubectl -n "$NS" get pvc -o wide
echo '[8/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/10] CRD schema'; kubectl explain kafkaconnect.spec
echo '[10/10] Registry Service inventory (best effort)'
kubectl -n "$NS" get svc -o name | grep -Ei 'schema|registry' || echo 'UNKNOWN: registry service not discovered by name'
echo 'PASS: read-only Kubernetes inventory completed.'
echo 'NOT PROVEN: DB WAL/slot safety, CDC events, schema compatibility, sink durability, failover or independent review.'
```

Run `chmod +x verify-ch60.sh && ./verify-ch60.sh | tee evidence-ch60/preflight.txt`. A failed prerequisite means **BLOCKED**; do not infer a capstone pass from this script.

## 10. Twelve integrated incident scenarios

### Scenario 1 — CDC task RUNNING but no new events

**Triage:** Check source commits, heartbeat, slot LSN, publication filters and freshness. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 2 — PostgreSQL WAL fills disk during Connect outage

**Triage:** Check retained WAL, slot restart_lsn, disk pressure and emergency DBRE escalation. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 3 — Snapshot overloads OLTP primary

**Triage:** Inspect locks, CPU/IO, transaction age and stop/rollback. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 4 — Connector offset topic unavailable

**Triage:** Inspect Kafka ISR, ACL, internal topic durability and worker errors. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 5 — Source cursor lost after failover

**Triage:** Validate slot/timeline/GTID, connector offsets and recovery boundaries. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 6 — Registry rejects schema evolution

**Triage:** Review compatibility mode, Avro defaults, Protobuf tags and JSON required fields. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 7 — Registry DR restores different schema IDs

**Triage:** Validate serializer wire format, subject mapping and ID preservation. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 8 — Connect converter strips tombstones

**Triage:** Check delete event semantics, compaction and sink state. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 9 — DLQ hides record loss

**Triage:** Inspect DLQ counts, age, replay, ACLs and accepted-ID ledger. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 10 — Sink commits before Kafka offset

**Triage:** Check at-least-once replay, idempotency and transaction boundary. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 11 — Credentials rotate and CDC stops

**Triage:** Check DB TLS, Kafka SASL/ACL, registry auth and secret rollout. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

### Scenario 12 — Dashboards green but durable sink missing IDs

**Triage:** Hold incident open until independent event reconciliation. Correlate DB transaction/LSN, WAL/slot pressure, Connect task/offset, Kafka quorum/ISR, registry schema/version, DLQ and durable sink IDs. **Response:** Protect database and data integrity, freeze unsafe changes, quantify missing IDs, escalate to DBRE/SRE/security and apply approved rollback. **Acceptance:** UTC incident timeline, redacted evidence, measured versus hypothetical RPO/RTO, corrective-action owner.

## 11. Eight production runbooks

### Runbook A — Integrated CDC incident declaration

**Trigger and first response:** Assign IC/DBRE/SRE, freeze unsafe changes, assess business freshness and RPO/RTO. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook B — PostgreSQL WAL/slot emergency

**Trigger and first response:** Check slot restart_lsn, pg_wal disk, task state and DBRE-approved retention response. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook C — Connect worker/task recovery

**Trigger and first response:** Check Kafka quorum/ISR, worker group, internal topics, REST status and plugin. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook D — Snapshot and resnapshot approval

**Trigger and first response:** Bound DB load, identify offset/LSN boundary, verify backup and reconciliation. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook E — Schema compatibility and registry incident

**Trigger and first response:** Check subjects, versions, schema IDs, TLS, compatibility CI, converter and rollback. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook F — DLQ, poison pill and sink integrity

**Trigger and first response:** Contain sensitive payloads, investigate errors, replay safely and deduplicate. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook G — CDC failover and single-writer recovery

**Trigger and first response:** Verify DB promotion, slot continuity, connector offset, Kafka/sink event IDs and owner authority. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

### Runbook H — Independent reliability acceptance and RCA

**Trigger and first response:** Score gates, validate actual vs tabletop evidence, RPO/RTO, security, remediation and signoff. **Safety gates:** No production slot deletion, offset reset, unapproved resnapshot, compatibility bypass, dual writer, unreviewed plugin image or secret exposure. **Exit:** Safe DB storage headroom, healthy Kafka/Connect/registry, end-to-end unique-event reconciliation, freshness SLO restored, independent approval and RCA.

## 12. Incident timeline and recovery decision workflow

```text
ALERT / DECLARE
     |
FREEZE unsafe DB / Connect / registry mutations
     |
ASSESS DB WAL/slot + Kafka quorum/ISR + Connect task/offset + registry
     |
RECONCILE source committed IDs -> Kafka accepted IDs -> sink durable IDs
     |
+----+-----------------------+
| unsafe/unknown            | evidence complete
v                           v
BLOCK / ESCALATE        APPROVE recovery plan
                            |
                       REHEARSE rollback
                            |
                    RESTORE + VERIFY SLO
                            |
                     INDEPENDENT SIGNOFF
```

A resumed connector does not close the incident if WAL pressure, DLQ backlog, schema mismatch or missing sink IDs persist.

## 13. Evidence package

```text
evidence-ch60/
  integrated-charter-raci-slo-rpo-rto.md
  exact-version-matrix.md
  preflight.txt
  kraft-isr-pvc-failure-domains.md
  connect-workers-internal-topics.md
  postgres-wal-slot-publication.md
  registry-subject-compatibility-security.md
  sink-idempotence-delete-contract.md
  synthetic-event-fixture.jsonl
  accepted-source-events.csv
  kafka-accepted-events.csv
  durable-sink-events.csv
  freshness-and-rpo-rto-worksheet.md
  snapshot-load-budget.md
  streaming-slot-retention-budget.md
  avro-protobuf-json-compatibility-matrix.csv
  converters-smt-pii-tombstones.md
  connect-worker-failure-tabletop.md
  db-outage-wal-tabletop.md
  registry-outage-tabletop.md
  poison-pill-dlq-tabletop.md
  breaking-schema-rollback-tabletop.md
  cdc-failover-resnapshot-tabletop.md
  incident-utc-timeline.md
  rca-and-corrective-actions.md
  independent-dbre-sre-security-review.md
  business-readiness-signoff.md
  readiness-scorecard.md
```

Every artifact must record source/version, UTC timestamp, expected/observed result, **Live** vs **Tabletop**, redaction, owner, rollback/abort and independent reviewer. Do not claim the integrated capstone was executed merely because the evidence template exists.

## 14. 100-point enterprise CDC/schema reliability capstone

| Domain | Points | Critical |
|---|---:|---|
| Business charter, RACI, SLO/RPO/RTO and safety | 10 | Yes |
| Kafka KRaft, Strimzi, Connect workers/internal topics | 15 | Yes |
| PostgreSQL WAL/slots, snapshot and DBRE capacity | 20 | Yes |
| Debezium offsets, failover and replay integrity | 10 | Yes |
| Registry HA/security and compatibility CI | 10 | Yes |
| Converter/SMT, CDC deletes, PII and sink idempotency | 10 | Yes |
| Source → Kafka → durable sink ledger and freshness | 15 | Yes |
| Incident scenarios, runbooks and RCA | 5 | Yes |
| Independent DBRE/SRE/security/business signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate evidenced with representative live tests. **Automatic Fail:** fabricated execution, unapproved slot deletion, missing WAL capacity, unreviewed resnapshot, incompatible schema, PII leak, unsupported exactly-once guarantee, missing sink reconciliation or absent independent signoff.

**Readiness status:** **Pending / Not Ready** until integrated live drills, DBRE safety checks, schema compatibility tests, recovery evidence and independent review pass. A tabletop demonstrates preparation, not production RPO/RTO compliance.

## 15. Cleanup, references and curriculum transition

Remove only chapter-owned synthetic connectors, topics, registry subjects, test DB objects and alerts through approved GitOps/DBRE procedures after evidence retention. Never delete production slots, publications, Connect internal topics, offsets, schema histories, PVCs or Secrets.

**References:** [Apache Kafka Connect](https://kafka.apache.org/documentation/#connect), [Debezium Documentation](https://debezium.io/documentation/), [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html), [Apache Avro](https://avro.apache.org/docs/current/specification/), [Protocol Buffers](https://protobuf.dev/), [JSON Schema](https://json-schema.org/), [Strimzi Documentation](https://strimzi.io/documentation/).

**Part 12 — Kafka Connect, CDC and Schema Management is fully published (Chapters 056–060).**

**Next:** Chapter 061 — Kafka Streams Architecture, Processing Topologies and Stateful Stream Processing, beginning Part 13 — Kafka Streams and Stream Processing.

---

**Verification boundary:** Publication establishes document availability only. Live integrated CDC/registry/Connect drills, RPO/RTO, end-to-end sink durability and independent DBRE/SRE/security acceptance remain Pending.
