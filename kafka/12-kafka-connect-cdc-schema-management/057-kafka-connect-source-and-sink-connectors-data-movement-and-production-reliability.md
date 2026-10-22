# Chapter 057 — Kafka Connect Source and Sink Connectors, Data Movement and Production Reliability

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 12 — Kafka Connect, CDC and Schema Management (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–056, especially 026–030, 036–056  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use only disposable Kafka/Connect environments, synthetic records and approved connector plugins. Source/sink configuration changes, offset resets, external system writes, topic deletion and REST mutations require explicit isolated change approval. Do not publish secrets, expose Connect REST, weaken TLS/SASL/ACLs or promise exactly-once external side effects without connector-specific proof.

## 1. Mission

Engineer a reliable Kafka Connect data path from a source system through a source connector, Kafka topic and sink connector to a durable downstream store. Operate Strimzi-managed distributed workers on Kubernetes, reason about source versus sink offsets, and prove end-to-end delivery with unique event IDs, replay controls, error handling, DLQs and SLOs.

## 2. Learning objectives

- Distinguish source connector polling/CDC, source offsets and Kafka producer acknowledgment from sink consumer offsets and external sink commits.
- Review connector task parallelism, `tasks.max`, topic partitions and bottleneck behavior.
- Design converters and Single Message Transforms (SMTs) without breaking keys, ordering, schemas or sensitive-data policy.
- Apply least-privilege identities to Kafka, source and sink systems; isolate Connect REST and plugin supply chain.
- Handle retryable errors, poison pills, dead-letter queues, backpressure, ambiguous writes and replay.
- Measure source-to-Kafka, Kafka-to-sink and end-to-end freshness; reconcile accepted event IDs against durable sink IDs.
- Produce Kubernetes-first operational evidence and independent acceptance.

## 3. Source-to-sink architecture

```text
External source / CDC cursor
           |
   SourceConnector tasks -- source offset storage
           |
    converter + SMT chain
           |
  Kafka topic (RF / ISR / retention / ACL)
           |
   SinkConnector tasks -- Kafka consumer offsets
           |
    converter + SMT chain
           |
 Durable sink (idempotent key / commit)
           |
  event-ID ledger / SLO / DLQ / RCA
```

Kafka Connect workers are shared distributed runtimes. A source connector may emit duplicate records if it retries after an ambiguous acknowledgment; a sink may write a record successfully but fail before committing the Kafka consumer offset. Exactly-once behavior of Kafka transactions does not automatically extend to external databases or APIs.

## 4. Offset and delivery semantics

| Stage | Progress marker | Reliability hazard |
|---|---|---|
| External source | source cursor, LSN, timestamp or API token | source cursor advances without Kafka durability |
| Source connector | framework source offset state | replay or skip if connector semantics are wrong |
| Kafka | topic-partition offset and producer callback | retries, ISR/minISR, retention |
| Sink connector | Kafka consumer group offsets | commits before/after external effects |
| External sink | durable primary key / transaction commit | duplicate writes, partial batches, timeout ambiguity |
| End-to-end | unique accepted IDs vs durable sink IDs | hidden loss despite healthy task status |

**Acceptance rule:** A healthy KafkaConnector CR, RUNNING task or zero consumer lag alone does not prove durable end-to-end delivery. Require an independent source event ledger and sink reconciliation.

## 5. Connector configuration review matrix

| Area | Source connector | Sink connector |
|---|---|---|
| Input | API, database, log, filesystem | Kafka topics |
| Output | Kafka topics | database, object store, search, API |
| State | source offsets/cursors | consumer group offsets |
| Key design | stable business key, deterministic ID | idempotent upsert or dedup |
| Error handling | poll retry, backoff, source DLQ policy | record retry, DLQ, bounded replay |
| Parallelism | source partitions / tasks | Kafka partitions / tasks |
| Security | source credential + Kafka produce ACL | Kafka consume ACL + sink credential |
| Evidence | accepted Kafka event IDs | durable sink event IDs |

Do not assume the connector's `tasks.max` is the number of tasks actually created. Review connector implementation and source system limits.

## 6. Kubernetes/Strimzi prerequisites and commands

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkaconnect,pods,svc -o wide
kubectl api-resources | grep -Ei 'kafkaconnect|kafkaconnector'
kubectl explain kafkaconnect.spec
kubectl -n kafka-lab get kafkaconnector -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
```

Check installed Strimzi CRD and Kafka Connect version before interpreting these fields. `KafkaConnector` management may require release-specific annotations and conflicts with manual REST mutation if both are used. REST administrative APIs must be isolated and authenticated via approved gateway/policy.

## 7. Synthetic data integrity fixture

Use a bounded test set with deterministic keys and explicit expected sink state:

```jsonl
{"event_id":"sre057-001","customer_id":"c-001","sequence":1,"event_type":"upsert","value":10}
{"event_id":"sre057-002","customer_id":"c-001","sequence":2,"event_type":"upsert","value":11}
{"event_id":"sre057-003","customer_id":"c-002","sequence":1,"event_type":"upsert","value":20}
```

The JSON Lines above is **illustrative input**, not a deployable connector configuration. Persist the source acceptance record with event ID, partition, offset and UTC timestamp after Kafka producer callback success. In the sink, use a durable uniqueness constraint on `event_id` (or approved business key/version semantics) and record the committed event IDs. For upsert semantics, define expected final state separately from total processed events.

## 8. Safe connector management model

Prefer GitOps-managed KafkaConnector CRs when supported by the installed Strimzi release, or an explicitly approved REST management workflow—not both competing over the same connector. Connector `config` can contain credentials; use Secret references or an approved external secret mechanism supported by the connector and worker runtime.

**Read-only REST inspection** from an approved local test gateway:

```bash
# Example only; do not expose an unauthenticated public Connect REST endpoint.
curl -fsS http://127.0.0.1:8083/
curl -fsS http://127.0.0.1:8083/connectors
curl -fsS http://127.0.0.1:8083/connectors/sre057-source/status
curl -fsS http://127.0.0.1:8083/connectors/sre057-sink/status
curl -fsS http://127.0.0.1:8083/connector-plugins
```

Avoid `GET /connectors/{name}/config` in shared evidence because configuration responses can expose secrets. Production REST access needs network isolation, authorization and audit logging.

## 9. Twenty Kubernetes-first labs

### Lab 01 — Approve source-to-sink contract

**Objective and procedure:** Record source and sink owners, data classification, throughput, lag SLO, delivery guarantee, retention and rollback.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 02 — Inspect Kubernetes Kafka and Connect CRDs

**Objective and procedure:** Capture context, Strimzi/Kafka versions, KafkaConnect/KafkaConnector CRD schema, NodePools, Pods and security boundaries.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 03 — Verify broker and worker readiness

**Objective and procedure:** Inspect KRaft quorum, broker ISR, Connect worker replicas, internal topics, Services and REST isolation.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 04 — Inventory source connector capabilities

**Objective and procedure:** Document supported connector class, source partitioning, polling/CDC behavior, schema handling and source offset semantics.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 05 — Inventory sink connector capabilities

**Objective and procedure:** Document sink write mode, key semantics, idempotence, batching, retries, transactions and failure handling.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 06 — Validate plugin provenance

**Objective and procedure:** Review immutable image digest, plugin dependencies, connector compatibility, SBOM, signatures and CVEs.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 07 — Define synthetic input fixture

**Objective and procedure:** Create approved small deterministic event set with unique IDs, expected order, null/tombstone cases and schema versions.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 08 — Design source connector configuration

**Objective and procedure:** Plan least-privilege external credentials, topic allowlist, transforms, converters and offset storage.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 09 — Design sink connector configuration

**Objective and procedure:** Plan topic selection, sink identity, DLQ, error tolerance, idempotent upsert and offset commit boundaries.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 10 — Validate Kafka topic durability

**Objective and procedure:** Inspect synthetic topic RF, minISR, retention, partitions, compaction and Kafka ACLs.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 11 — Review converter and serialization paths

**Objective and procedure:** Compare String/JSON/Avro/Protobuf converter choices, schemas.enable, null values and registry dependencies.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 12 — Review SMT safety

**Objective and procedure:** Test planned transforms on synthetic records; identify key mutation, field masking and schema compatibility risks.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 13 — Inspect connector and task status

**Objective and procedure:** Read KafkaConnector status and secured Connect REST task state; correlate worker logs and Pod readiness.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 14 — Measure source-to-Kafka freshness

**Objective and procedure:** Track source event time, successful Kafka acceptance, event IDs, duplicates and missing IDs.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 15 — Measure Kafka-to-sink freshness

**Objective and procedure:** Track Kafka offset/event ID to durable sink commit, sink error rate, retries and backlog.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 16 — Analyze task scaling

**Objective and procedure:** Compare tasks.max, connector-created task count, source partitions, topic partitions and sink capacity.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 17 — Model poison-pill and DLQ behavior

**Objective and procedure:** Review invalid record, converter failure, DLQ routing, privacy, alerting and controlled replay.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 18 — Model source outage and backfill

**Objective and procedure:** Plan retry/backoff, source retention, source offsets, backfill rate and duplicate-safe replay.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 19 — Model sink outage and recovery

**Objective and procedure:** Assess consumer lag, retry policy, at-least-once duplicates, idempotent sink and rollback.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

### Lab 20 — Complete data integrity acceptance

**Objective and procedure:** Reconcile accepted synthetic IDs with durable sink IDs, verify SLO, security and independent 100-point review.

**Expected evidence:** Exact Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC query/command, expected versus observed output, connector/task status, source/sink unique-event ledger, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. External writes, offset mutation and failure injections remain **Tabletop** unless approved in a disposable lab.

## 10. Read-only verification script

Save as `verify-ch57.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka/Connect CRs'; kubectl -n "$NS" get kafka,kafkanodepool,kafkaconnect -o wide
echo '[3/10] KafkaConnector CRD'
if kubectl api-resources -o name | grep -q '^kafkaconnectors.kafka.strimzi.io$'; then
  kubectl -n "$NS" get kafkaconnector -o wide
else
  echo 'UNKNOWN/NOT CONFIGURED: KafkaConnector CRD absent'
fi
echo '[4/10] Pods'; kubectl -n "$NS" get pods -o wide
echo '[5/10] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[6/10] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[7/10] KafkaUser inventory'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo '[8/10] CRD schema'; kubectl explain kafkaconnect.spec
echo '[9/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[10/10] Storage'; kubectl -n "$NS" get pvc -o wide
echo 'PASS: read-only Connect source/sink inventory.'
echo 'NOT PROVEN: connector data movement, DLQ, replay, sink durability or independent review.'
```

Run `chmod +x verify-ch57.sh && ./verify-ch57.sh | tee evidence-ch57/preflight.txt`. If prerequisites are absent, record **BLOCKED**, not a pass. This script cannot prove application data integrity.

## 11. Twelve failure scenarios

### Scenario 1 — Source API returns 429 or 503

**Diagnosis:** Check rate limits, backoff, poll loop, task health and source offset progression. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 2 — Source connector duplicates after restart

**Diagnosis:** Inspect source offset commits, external cursor and deduplication keys. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 3 — Sink times out after write succeeds

**Diagnosis:** Review ambiguous acknowledgment, at-least-once replay and idempotent upsert. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 4 — Poison-pill serialization blocks task

**Diagnosis:** Inspect converter, schema, error tolerance and DLQ handling. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 5 — SMT silently removes business key

**Diagnosis:** Review transform chain, key schema and sink deduplication impact. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 6 — Connector reports RUNNING while source stale

**Diagnosis:** Compare source event heartbeat, Kafka timestamps and source freshness SLO. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 7 — Kafka topic partition increase causes ordering change

**Diagnosis:** Review key partitioning, per-key ordering and downstream assumptions. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 8 — DLQ grows while pipeline looks healthy

**Diagnosis:** Alert on DLQ age/count, validate privacy and replay policy. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 9 — Sink capacity saturation causes consumer lag

**Diagnosis:** Review batching, backpressure, connection pools, retries and quotas. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 10 — Schema evolution breaks sink mapping

**Diagnosis:** Inspect converter, schema registry compatibility and rollback. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 11 — Plugin upgrade changes record semantics

**Diagnosis:** Compare golden fixture output, image digest, version and replay. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

### Scenario 12 — Secret rotation breaks external connection

**Diagnosis:** Inspect credential references, TLS, network policy and safe rollout. Correlate Kubernetes Pods, Connect worker/task status, Kafka topic/offset, converter/SMT logs, DLQ, source API and durable sink ledger. **Decision:** Freeze unsafe changes, preserve source and Kafka offsets, fix the reviewed root cause and replay only through approved deduplication. **Evidence:** UTC timeline, redacted logs, expected/observed unique IDs and reviewer.

## 12. Eight production runbooks

### Runbook A — Source connector outage

**Trigger and first response:** Inspect source endpoint, auth, task status, offsets, rate limits and recovery freshness. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook B — Sink connector outage

**Trigger and first response:** Inspect destination health, task retries, lag, durable write IDs and idempotent recovery. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook C — Connector/task FAILED

**Trigger and first response:** Review REST/CR conditions, Pod logs, plugin, converter, ACL and dependency. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook D — Poison-pill, converter and DLQ incident

**Trigger and first response:** Quarantine sensitive records, capture schema errors, bound replay and correct source/sink. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook E — Offset integrity and controlled replay

**Trigger and first response:** Reconcile source cursor, Kafka offsets, sink IDs and duplicates; require approval for resets. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook F — Task scaling and throughput regression

**Trigger and first response:** Analyze partitioning, tasks.max, worker resources, sink bottlenecks and SLO. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook G — Plugin/schema/SMT rollback

**Trigger and first response:** Validate immutable image, golden fixture, schema compatibility, GitOps rollback and integrity. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

### Runbook H — Production data-movement acceptance

**Trigger and first response:** Prove end-to-end unique-event reconciliation, freshness, security, observability and signoff. **Safety:** Never reset production offsets, delete Connect internal topics, weaken ACL/TLS, expose credentials or blindly increase tasks.max. **Exit:** Restored task and external dependency health, accepted-to-durable unique-event reconciliation, SLO recovery, documented RCA and corrective-action owner.

## 13. Evidence package

```text
evidence-ch57/
  source-sink-service-contract.md
  context-version-matrix.md
  preflight.txt
  kafka-connect-crd-worker-readiness.md
  source-connector-capabilities.md
  sink-connector-capabilities.md
  plugin-provenance-sbom.md
  synthetic-input-fixture.jsonl
  source-connector-gitops-review.md
  sink-connector-gitops-review.md
  kafka-topic-rf-isr-acl.md
  converters-and-schema-review.md
  smt-key-data-privacy-review.md
  connector-task-status.md
  source-to-kafka-freshness.csv
  kafka-to-sink-freshness.csv
  tasks-scaling-capacity.md
  poison-pill-dlq-tabletop.md
  source-outage-backfill-tabletop.md
  sink-outage-replay-tabletop.md
  accepted-processed-event-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

Each artifact must include source, exact version, UTC timestamp, expected/observed result, redaction, owner, abort/rollback and reviewer. A tabletop cannot substitute for live data-movement evidence.

## 14. 100-point source/sink reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Source/sink contract, data classification and safety | 10 | Yes |
| Kubernetes/Strimzi Connect worker and connector readiness | 10 | Yes |
| Source connector offsets and Kafka durability | 15 | Yes |
| Sink connector offsets and durable idempotency | 15 | Yes |
| Converter, SMT, schema and plugin safety | 10 | Yes |
| Retries, poison pills, DLQ and replay | 15 | Yes |
| End-to-end SLO, freshness and unique-event ledger | 15 | Yes |
| Runbooks, rollback and troubleshooting | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. **Automatic Fail:** fabricated connector execution, missing durable sink ledger, unreviewed offset reset, secret exposure, unsupported exactly-once claims, DLQ data leak, missing replay/deduplication or absent independent review.

## 15. Cleanup, references and next chapter

Remove only chapter-owned synthetic connectors, test topics and alerts through approved GitOps after evidence retention. Preserve offset and DLQ state until reconciliation is complete. Never delete production Connect internal topics, consumer offsets, PVCs or Secrets.

**References:** [Apache Kafka Connect Documentation](https://kafka.apache.org/documentation/#connect), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

**Next:** Chapter 058 — Change Data Capture with Kafka Connect, Debezium and Database Reliability Engineering.

---

**Verification boundary:** Publication proves document availability only. Live source/sink data movement, offset recovery, DLQ, SLO, event integrity and independent technical/security review remain Pending.
