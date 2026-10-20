# Chapter 058 — Change Data Capture with Kafka Connect, Debezium and Database Reliability Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 12 — Kafka Connect, CDC and Schema Management (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Primary DBRE example:** PostgreSQL logical decoding and Debezium PostgreSQL connector  
**Secondary comparison:** MySQL binlog and Debezium MySQL connector  
**Prerequisites:** Chapters 001–057, especially 026–030, 036–057  
**Status:** Published · **Live labs:** Pending · **Independent DBRE/security review:** Pending

> **Safety:** Use a disposable PostgreSQL database and isolated Strimzi Kafka Connect cluster. Replication slots can retain WAL and fill disks; do not create/drop production slots, change `wal_level`, alter publications, restart primary DBs, reset offsets, resnapshot large tables or weaken database/Kafka TLS/ACLs without approved DBRE change management. Never export production rows, secrets, PII or raw CDC payloads to GitHub.

## 1. Mission

Build a production-minded CDC pipeline that streams committed database changes through Debezium and Kafka Connect into Kafka topics and an idempotent downstream sink. Learn how source database transaction logs, replication slots, snapshots, connector offsets, Kafka durability and downstream schema contracts interact. Prioritize database health and data integrity over connector uptime alone.

## 2. Learning objectives

- Explain CDC vs polling, snapshot vs streaming, Debezium change event envelopes, transactions, deletes and tombstones.
- Map PostgreSQL WAL, logical replication slots, publications and connector offset state; compare MySQL binlog/GTID.
- Choose snapshot modes, table allowlists, PK/partitioning and schema evolution policies.
- Detect WAL/binlog retention risk and avoid disk exhaustion during connector outages.
- Validate source commit to Kafka to sink freshness and unique-event reconciliation.
- Review DB failover, replication-slot continuity, snapshot recovery, secure credentials and PII governance.
- Complete Kubernetes-first DBRE operational evidence and independent acceptance.

## 3. Architecture

```text
PostgreSQL primary
  table transaction / commit LSN
       |
  WAL logical decoding -> publication -> replication slot
       |
  Debezium PostgreSQL SourceConnector task
       |
  Kafka Connect offsets + (connector-specific) schema state
       |
  Kafka KRaft topics (key, envelope, tombstone)
       |
  sink connector -> idempotent upsert / delete
       |
  durable sink + accepted-event reconciliation
       |
  DBRE alerts: WAL retained, slot lag, snapshot load, CDC freshness
```

**PostgreSQL replication slot:** A slot retains WAL needed by a consumer, subject to server configuration and slot invalidation rules. A stalled connector can therefore increase disk usage even while Kafka and Connect Pods appear healthy. Always monitor `pg_wal` usage and slot state with an owner-approved retention budget.

## 4. PostgreSQL CDC prerequisites

| Layer | Design requirement | DBRE concern |
|---|---|---|
| Database | `wal_level=logical` and sufficient WAL senders/slots | configuration change/restart may be required |
| Publication | approved table allowlist | least privilege, DDL ownership |
| Slot | unique connector-owned logical slot | WAL retention and lifecycle |
| Identity | scoped replication/table access, TLS | audit and credential rotation |
| Snapshot | supported mode and bounded table set | lock/IO/CPU/transaction impact |
| Connect | compatible Debezium plugin image and worker | task failure, offset storage |
| Kafka | secured topics, RF/minISR, ACLs | durable change log |
| Sink | deterministic key, idempotent upsert/delete | duplicate/replay safety |
| Monitoring | slot lag, WAL bytes, freshness, errors | disk-full and data-loss prevention |

PostgreSQL replication slot failover and synchronization capabilities depend on PostgreSQL version and HA implementation. Do **not** assume a promoted replica has a usable logical slot without explicit validation.

## 5. PostgreSQL read-only DBRE checks

Run only with an authorized database account. These queries reveal operational metadata, not row contents.

```sql
SHOW server_version;
SHOW wal_level;
SHOW max_replication_slots;
SHOW max_wal_senders;
SHOW max_slot_wal_keep_size;

SELECT slot_name, plugin, slot_type, database, active,
       restart_lsn, confirmed_flush_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_wal_bytes
FROM pg_replication_slots
WHERE slot_type = 'logical';

SELECT pubname, puballtables
FROM pg_publication;

SELECT application_name, state, sent_lsn, write_lsn, flush_lsn,
       replay_lsn
FROM pg_stat_replication;
```

The `retained_wal_bytes` estimate is meaningful on the current primary with a non-null `restart_lsn`; it is not the exact filesystem `pg_wal` size or proof of safe retention. Slot state visibility, WAL function availability and permissions depend on PostgreSQL version/role. Collect actual filesystem capacity and alert thresholds separately.

## 6. Kubernetes/Strimzi read-only inventory

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkaconnect,pods,svc,pvc -o wide
kubectl api-resources | grep -Ei 'kafkaconnect|kafkaconnector'
kubectl explain kafkaconnect.spec
kubectl -n kafka-lab get kafkaconnector -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
```

The Debezium connector must be included in a reviewed, immutable Connect image compatible with the Kafka Connect and database versions. Check the installed Strimzi CRD and supported KafkaConnector reconciliation model. Avoid unapproved Connect REST changes and protect its administrative API.

## 7. Debezium PostgreSQL configuration review sketch

The following is **illustrative policy/configuration**, not a deployable KafkaConnector CR. Connector property names and snapshot modes must be validated against the installed Debezium version.

```yaml
connectorClass: io.debezium.connector.postgresql.PostgresConnector
databaseHostname: approved-postgres-service
databasePort: 5432
databaseDbname: sre_cdc_lab
databaseUser: dedicated-cdc-principal
databasePassword: secret-reference-required
topicPrefix: sre057-postgres
pluginName: pgoutput
slotName: sre058_lab_slot
publicationName: sre058_lab_publication
tableIncludeList:
  - public.orders
snapshotMode: approved-version-specific-mode
schemaChangePolicy: reviewed
tombstonePolicy: reviewed
security:
  postgresTls: required
  kafkaTlsSasl: required
  kafkaAcls: least-privilege
  piiMasking: required
  secretRedaction: required
```

For example, modern Debezium PostgreSQL connectors use configuration properties such as `topic.prefix`, `slot.name`, `publication.name`, `plugin.name`, `table.include.list` and `snapshot.mode`; verify exact release syntax and semantics. Publication creation should be explicit and DBRE-approved rather than granting a connector broad DDL privileges.

## 8. Change-event envelope and delete semantics

Illustrative Debezium-like record:

```json
{
  "before": {"id": 42, "status": "new"},
  "after": {"id": 42, "status": "paid"},
  "op": "u",
  "source": {"db": "sre_cdc_lab", "schema": "public", "table": "orders"},
  "ts_ms": 1792526400000
}
```

This example is schematic; actual envelopes vary by connector/version and converter. Operation codes commonly represent create, update, delete and snapshot-read events. A delete may be followed by a tombstone for log-compacted topics. Sink connectors must implement deletion semantics deliberately; dropping tombstones can leave stale sink records.

## 9. Snapshot and streaming continuity

```text
Approve scope and snapshot mode
        |
Capture snapshot boundary / connector offsets
        |
Read allowed tables with controlled load
        |
Transition to WAL/binlog streaming
        |
Monitor source LSN / Kafka event IDs / sink IDs
        |
Reconcile snapshot + stream with PK/version semantics
```

Snapshot and streaming overlap/restart behavior is connector-specific. Do not use a blanket assumption that every snapshot is lock-free or exactly-once. Long-running snapshots can add I/O and transaction pressure. A large table requires DBRE capacity and maintenance-window review.

## 10. Twenty Kubernetes-first CDC and DBRE labs

### Lab 01 — Approve database CDC scope

**Objective and procedure:** Record DB owner, data classification, allowed tables, retention, RPO, Kafka topics, connector principal, snapshot window and abort gates.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 02 — Inventory Kafka and Connect platform

**Objective and procedure:** Inspect Strimzi Kafka/KafkaConnect CRDs, worker Pods, KRaft quorum, internal topics, NetworkPolicies and secure listeners.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 03 — Choose supported Debezium connector

**Objective and procedure:** Check plugin, Kafka Connect, database engine and Debezium version compatibility and immutable image provenance.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 04 — Inventory PostgreSQL logical decoding prerequisites

**Objective and procedure:** Read wal_level, max_replication_slots, max_wal_senders, publication privileges, slot inventory and WAL disk headroom.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 05 — Inventory MySQL binlog prerequisites

**Objective and procedure:** Review row-based binlog format, GTID/server identity, retention, permissions and failover semantics.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 06 — Design least-privilege DB identity

**Objective and procedure:** Review publication/table privileges, replication permissions, TLS trust, secret references and access audit.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 07 — Design snapshot strategy

**Objective and procedure:** Compare initial snapshot, schema-only/no-data modes where supported, incremental snapshot and DB load/locking impact.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 08 — Design source table allowlist

**Objective and procedure:** Review capture table selection, schema inclusion, masking, PII controls and topic routing.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 09 — Review PostgreSQL publication and slot ownership

**Objective and procedure:** Document dedicated publication/slot names, connector lifecycle and retention impact; do not drop shared slots.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 10 — Review schema history and connector offsets

**Objective and procedure:** Identify DB-specific schema history topic, Kafka Connect offset topic and backup/restore policy.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 11 — Design CDC event envelope

**Objective and procedure:** Document before/after/op/source/transaction/timestamp fields and tombstone/delete semantics.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 12 — Design primary key and ordering

**Objective and procedure:** Review source PK, Kafka record key, per-key ordering, partition changes and sink upsert strategy.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 13 — Inspect connector and task status

**Objective and procedure:** Review KafkaConnector CR, Connect REST task health, DB connection, source offset progress and error logs.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 14 — Measure WAL/binlog retention pressure

**Objective and procedure:** Correlate connector lag, retained WAL/binlog bytes, slot confirmed_flush_lsn and disk capacity.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 15 — Measure end-to-end CDC freshness

**Objective and procedure:** Track source commit UTC/LSN, Kafka accepted event ID, downstream sink commit and time uncertainty.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 16 — Model DB schema change

**Objective and procedure:** Assess additive vs breaking DDL, schema registry compatibility, converter and downstream consumer behavior.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 17 — Model connector pause and resume

**Objective and procedure:** Rehearse WAL growth, connector restart, snapshot state and offset continuity without stopping production CDC.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 18 — Model PostgreSQL failover and timeline changes

**Objective and procedure:** Review slot continuity and promotion compatibility for exact DB/version/HA design; do not assume automatic slot failover.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 19 — Model snapshot/backfill reconciliation

**Objective and procedure:** Reconcile snapshot rows and streaming changes with primary keys, duplicate handling and cutoff boundaries.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

### Lab 20 — Complete DBRE CDC acceptance

**Objective and procedure:** Run read-only preflight, evidence package, capacity gates, 100-point rubric, independent DBRE/security review and signoff.

**Expected evidence:** PostgreSQL/Strimzi/Kafka/Debezium version matrix, authorized context, UTC command/query, expected/observed result, WAL/slot headroom, connector offset, source commit and sink event-ID ledger, security impact, rollback/abort, DBRE owner and independent reviewer. Mark **Pending** until executed. Database mutation, slot operations, failover and resnapshot exercises remain **Tabletop** without approved disposable infrastructure.

## 11. Read-only CDC preflight script

Save as `verify-ch58.sh`. It checks Kubernetes inventory only; DBRE SQL checks in Section 5 must be run separately with an approved database account.

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
  echo 'UNKNOWN/NOT CONFIGURED: KafkaConnector CRD absent'
fi
echo '[4/10] Pods'; kubectl -n "$NS" get pods -o wide
echo '[5/10] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[6/10] NetworkPolicies'; kubectl -n "$NS" get networkpolicy
echo '[7/10] KafkaConnect schema'; kubectl explain kafkaconnect.spec
echo '[8/10] PVCs'; kubectl -n "$NS" get pvc -o wide
echo '[9/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[10/10] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo 'PASS: read-only Kubernetes CDC inventory.'
echo 'NOT PROVEN: database slot safety, WAL retention, CDC data movement, snapshot recovery or independent review.'
```

Run `chmod +x verify-ch58.sh && ./verify-ch58.sh | tee evidence-ch58/preflight.txt`. A Kubernetes inventory pass cannot certify WAL safety. If PostgreSQL metrics are unavailable, report **UNKNOWN/BLOCKED** and escalate before CDC deployment.

## 12. Twelve CDC failure scenarios

### Scenario 1 — PostgreSQL replication slot retains excessive WAL

**Diagnosis:** Correlate restart_lsn, confirmed_flush_lsn, pg_wal disk, task progress and retention thresholds. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 2 — Connector resumes from unavailable WAL position

**Diagnosis:** Review offset, slot, retention and approved re-snapshot strategy. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 3 — Initial snapshot saturates primary database

**Diagnosis:** Inspect DB CPU/IO, locks, query pressure and throttling or replica-based options. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 4 — Connector task RUNNING but CDC events stale

**Diagnosis:** Check source transactions, heartbeat, LSN progress, publication, slot and event-age SLO. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 5 — Table missing from publication or include list

**Diagnosis:** Review publication and connector table filters without broadening permissions blindly. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 6 — Primary key update causes sink duplicate or delete mismatch

**Diagnosis:** Inspect before/after keys, tombstones, routing and idempotent sink. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 7 — DDL change breaks converter or sink

**Diagnosis:** Review schema history, compatibility and downstream mapping. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 8 — MySQL binlog purged before connector catch-up

**Diagnosis:** Inspect binlog retention, GTID/position and approved snapshot recovery. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 9 — Database failover invalidates CDC continuity

**Diagnosis:** Check endpoint routing, timeline/GTID, replication slot behavior and connector offsets. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 10 — Credential rotation breaks replication

**Diagnosis:** Review DB role, TLS, Secret references, connector task logs and safe rotation. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 11 — Snapshot and streaming events double-count

**Diagnosis:** Reconcile PK/transaction boundary, snapshot markers and sink deduplication. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

### Scenario 12 — PII exposed in CDC topic or DLQ

**Diagnosis:** Contain access, audit ACLs, redaction policy, retention and security incident process. Correlate database WAL/binlog, replication slot, connector offsets, task status, Kafka topic, schema history and durable sink ledger. **Response:** Protect database availability, freeze unsafe slot/offset operations, quantify missing/duplicate events and use approved recovery. **Evidence:** UTC timeline, redacted logs, DBRE capacity measurements, rollback and independent review.

## 13. Eight production DBRE/SRE runbooks

### Runbook A — PostgreSQL WAL and replication slot pressure

**Trigger and first response:** Check pg_replication_slots, pg_stat_replication, pg_wal size, disk, lag and owner-approved retention actions. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook B — CDC connector task FAILED

**Trigger and first response:** Inspect Connect REST/CR, DB connectivity, publication/slot, credentials, Kafka ACLs and plugin. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook C — Initial snapshot resource incident

**Trigger and first response:** Assess locks, IOPS, CPU, transaction age, snapshot mode and safe stop/rollback. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook D — CDC offset and snapshot recovery

**Trigger and first response:** Preserve source cursor, Kafka Connect offset topic, schema history, backup and reconciliation. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook E — Schema change and converter incident

**Trigger and first response:** Inspect DDL, schema history, compatibility, converter, tombstones and sink contract. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook F — Database failover and CDC continuity

**Trigger and first response:** Validate DB primary, slot/timeline or GTID continuity, Kafka offsets and approved recovery. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook G — CDC freshness and data-loss investigation

**Trigger and first response:** Correlate DB commit ID, Kafka accepted ID, durable sink ID, lag and missing events. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

### Runbook H — CDC security and DBRE operational acceptance

**Trigger and first response:** Verify least privilege, TLS, PII/ACL, WAL retention, alerts, incident RCA and independent signoff. **Safety:** Never drop active production replication slots, disable logical decoding, delete Connect offset/history topics, run unapproved resnapshots, leak PII or weaken DB/Kafka TLS. **Exit:** Database capacity safe, connector offsets consistent, Kafka and sink event IDs reconciled, freshness SLO recovered, RCA and action owner assigned.

## 14. Evidence package

```text
evidence-ch58/
  approved-dbre-cdc-charter.md
  postgres-kafka-strimzi-debezium-version-matrix.md
  preflight.txt
  connect-worker-broker-readiness.md
  debezium-plugin-sbom-compatibility.md
  postgres-wal-logical-decoding-checks.md
  mysql-binlog-gtid-comparison.md
  database-cdc-identity-tls.md
  snapshot-strategy-and-load-budget.md
  source-table-allowlist-pii.md
  publication-slot-ownership.md
  connector-offset-history-policy.md
  cdc-envelope-tombstones.md
  pk-partition-ordering.md
  connector-task-health.md
  wal-slot-lag-capacity.csv
  source-kafka-sink-freshness.csv
  schema-change-tabletop.md
  connector-pause-resume-tabletop.md
  db-failover-timeline-tabletop.md
  snapshot-backfill-reconciliation.md
  accepted-processed-event-ledger.csv
  independent-dbre-security-review.md
  readiness-scorecard.md
```

Each artifact requires exact source/version, UTC time, expected/observed result, redaction, database owner, rollback/abort and independent assessor. A tabletop is not live CDC or failover evidence.

## 15. 100-point CDC DBRE acceptance

| Domain | Points | Critical |
|---|---:|---|
| DBRE charter, source contract and PII scope | 10 | Yes |
| PostgreSQL WAL/slot and MySQL binlog safety | 20 | Yes |
| Snapshot, publication and source table controls | 10 | Yes |
| Debezium/Connect plugin and offset continuity | 15 | Yes |
| Kafka topic durability and schema/tombstone integrity | 10 | Yes |
| Database failover and recovery planning | 10 | Yes |
| End-to-end freshness, lag and event reconciliation | 15 | Yes |
| Runbooks, monitoring and capacity alarms | 5 | Yes |
| Independent DBRE/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** fabricated CDC execution, unapproved slot deletion, missing WAL capacity monitoring, unreviewed production resnapshot, PII leak, unsupported exactly-once claims, missing durable sink reconciliation or absent independent review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic connectors, topics and test DB objects with explicit DBRE approval after offset/event reconciliation. Never drop production replication slots, publications, Kafka Connect internal topics, offsets, PVCs or Secrets. Preserve sanitized WAL and CDC evidence for RCA.

**References:** [Debezium Documentation](https://debezium.io/documentation/), [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html), [PostgreSQL Replication Slots](https://www.postgresql.org/docs/current/warm-standby.html#STREAMING-REPLICATION-SLOTS), [Apache Kafka Connect](https://kafka.apache.org/documentation/#connect), [Strimzi Documentation](https://strimzi.io/documentation/).

**Next:** Chapter 059 — Kafka Schema Registry, Avro, Protobuf, JSON Schema and Compatibility Engineering.

---

**Verification boundary:** Publication establishes document availability only. Live Debezium CDC, WAL/slot safety, snapshot/backfill, database failover, event integrity and independent DBRE/security acceptance remain Pending.
