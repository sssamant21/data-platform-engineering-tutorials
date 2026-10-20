# Chapter 048 — Kafka Producer, Consumer, Consumer Group and End-to-End Data Delivery Troubleshooting

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 10 — Troubleshooting and Incident Response (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–047, especially 016–020, 026–030, 036–047  
**Status:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use a disposable approved Kubernetes namespace, synthetic KafkaTopic, dedicated consumer group and idempotent test sink. Do not reset production offsets, change production topic retention, disable TLS/SASL/ACLs, weaken producer acks/minISR, kill Kafka brokers/controllers or use destructive failure injection. Record no credentials or sensitive payloads in Git. Publication is not live verification.

## 1. Mission and learning objectives

Troubleshoot Kafka end-to-end delivery from producer callback to durable downstream processing. Diagnose producer metadata, timeout, retry, idempotence, transactions and authorization failures; consumer group rebalances, offset commits, lag, freshness and poison-pill errors; and discrepancies between Kafka health and application-visible reliability. Validate recovery using unique synthetic event IDs rather than relying on lag alone.

## 2. End-to-end failure-domain model

```text
Application producer
  serialization / partition key / idempotence / transactions
          |
     Kafka client metadata, TLS/SASL, ACL, quota
          |
      Kafka broker leader + ISR / minISR
          |
     durable append + producer callback/offset
          |
    consumer group coordinator + assignments
          |
     poll / deserialize / process / retry / DLQ
          |
     durable sink transaction / unique-event ledger
          |
        end-to-end freshness and SLO
```

**Important distinctions:** A successful producer callback with `acks=all` confirms Kafka acknowledgment under configured durability conditions, not that a downstream sink processed the record. Consumer offset lag is not equivalent to event age. Kafka exactly-once semantics have defined boundaries; they do not automatically make arbitrary external sinks exactly-once.

## 3. Producer troubleshooting decision matrix

| Symptom | Common causes | Evidence | Safe response |
|---|---|---|---|
| TimeoutException | request/delivery timeout, throttling, network, ISR | callback, broker queue, quota, ISR | isolate bottleneck |
| AuthenticationException | TLS/SASL identity, trust, expiry | redacted client/broker auth logs | correct approved identity |
| AuthorizationException | topic/group/transactional ACL | principal, operation, denied resource | least-privilege ACL review |
| RecordTooLargeException | producer/broker/topic limits | record/batch size, compression | adjust payload strategy |
| OutOfOrderSequenceException | idempotent sequence state | client fatal/retriable classification | supported producer recovery |
| ProducerFencedException | duplicate transactional.id / epoch | producer instances and transaction logs | ensure unique ownership |
| Unexpected duplicates | retries, uncertain callback, sink design | unique ID ledger, idempotence | reconcile and deduplicate |

**Producer controls to record:** `acks`, `enable.idempotence`, `retries`, `delivery.timeout.ms`, `request.timeout.ms`, `max.in.flight.requests.per.connection`, `linger.ms`, `batch.size`, compression, quotas and TLS/SASL settings. Confirm version-specific defaults; do not copy arbitrary tuning values into production.

## 4. Consumer troubleshooting decision matrix

| Symptom | Common causes | Evidence | Safe response |
|---|---|---|---|
| Frequent rebalances | Pod churn, poll timeout, heartbeat, group membership | client logs, group describe | address processing/rollout |
| High offset lag | slow processing, partition skew, downstream saturation | group offsets, partition rates | isolate bottleneck |
| Low lag but stale events | source timestamps, clock skew, sink delay | event-age and sink ledger | trace end-to-end |
| CommitFailedException | rebalance/generation, long poll processing | commit logs, assignments | review poll/commit design |
| Duplicate processing | at-least-once retry, commit-after-sink | unique IDs, sink commits | idempotent sink |
| Poison-pill | schema/deserializer incompatibility | redacted error, schema version | bounded retry/DLQ policy |
| read_committed lag | open transactions / last stable offset | transaction state, LSO | investigate transaction lifecycle |

## 5. Kubernetes-first read-only CLI toolkit

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkatopic,pods,pvc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp

# Metadata quorum health (lab-only internal bootstrap).
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status

# Topic metadata and ISR.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-delivery-synthetic

# Consumer group offset/lag inventory.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-delivery-synthetic-group

# Bounded synthetic client logs (replace with actual Pod).
kubectl -n kafka-lab logs SYNTHETIC_CLIENT_POD --since=15m --timestamps --tail=300
```

These sample names and plaintext 9092 bootstrap apply to isolated labs only. For production-like clients use approved TLS/SASL `--command-config` where supported, scoped Kafka ACLs and reviewed Strimzi listeners. Do not dump KafkaUser Secrets or client credentials.

## 6. Delivery ledger and SLO contract

For each synthetic event, record `event_id`, source timestamp, producer callback success/failure, topic/partition/offset if acknowledged, consumer receipt time, durable sink commit time, deduplicated processing outcome and trace ID. Never include personal data or secrets.

```text
producer_ack_ratio = successful eligible callbacks / eligible callbacks
end_to_end_success = unique IDs durably processed by deadline / eligible accepted unique IDs
freshness = durable_sink_commit_utc - source_event_utc
duplicate_rate = duplicate sink attempts / unique accepted IDs
```

Keep producer callback attempts and unique business events as separate units of account. Missing telemetry or missing ledger entries must be treated as Unknown/Failed according to the approved contract, not silently excluded.

## 7. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve synthetic data-delivery troubleshooting scope

**Objective and procedure:** Identify approved namespace, topic, isolated group, synthetic producer and sink, owners, TLS/ACLs, change freeze, abort gates and redaction.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 02 — Capture Kafka and Kubernetes baseline

**Objective and procedure:** Inspect Kafka CR/NodePools, KRaft quorum, broker Pods/PVCs, KafkaTopic partitions/ISR, services and client Deployment versions.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 03 — Define accepted-to-processed ledger

**Objective and procedure:** Assign unique synthetic event IDs, record producer callback acknowledgment, partition/offset, consumer receipt, sink commit and event age.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 04 — Validate producer delivery guarantees

**Objective and procedure:** Review acks=all, retries, idempotence, max.in.flight, delivery timeout and partitioning; identify guarantees and non-guarantees.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 05 — Diagnose bootstrap and metadata errors

**Objective and procedure:** Check bootstrap DNS, Service endpoints, advertised listener reachability, broker metadata and version-compatible client configuration.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 06 — Diagnose TLS, SASL and ACL errors

**Objective and procedure:** Check truststore, SAN/hostname, certificate expiry, SASL mechanism, principal and topic/group ACLs without exporting Secrets.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 07 — Diagnose producer request timeouts

**Objective and procedure:** Correlate request timeout, delivery timeout, retry/backoff, quota throttle, broker request queue and network latency.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 08 — Diagnose producer record-too-large errors

**Objective and procedure:** Compare record batch/message limits, compression, application payload, topic and broker limits; use bounded synthetic payloads.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 09 — Diagnose idempotent producer sequence errors

**Objective and procedure:** Examine producer ID/epoch, out-of-order sequence, retriable versus fatal exceptions and safe producer recreation.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 10 — Diagnose partition key and ordering anomalies

**Objective and procedure:** Validate stable key serialization, partitioner behavior, partition-count changes and ordering scope per partition.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 11 — Inspect consumer group assignment

**Objective and procedure:** Use kafka-consumer-groups.sh --describe and client logs to inspect members, assignment, partition count and coordinator stability.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 12 — Diagnose rebalance storms

**Objective and procedure:** Correlate group joins/leaves, heartbeat/session timeout, max.poll.interval.ms, static membership and Kubernetes rolling changes.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 13 — Diagnose consumer poll/processing stalls

**Objective and procedure:** Measure poll duration, downstream sink latency, CPU/GC, backpressure, event age and offset commit strategy.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 14 — Diagnose offset commit failures

**Objective and procedure:** Review auto/manual commit, sync/async errors, group generation and duplicate processing; never reset shared group offsets.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 15 — Distinguish lag from end-to-end freshness

**Objective and procedure:** Compare committed offset lag, latest broker offsets, source event timestamps, clock skew, sink commit time and SLO.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 16 — Diagnose poison-pill and deserialization errors

**Objective and procedure:** Use isolated synthetic malformed payloads, error-handling policy, DLQ semantics and privacy-safe evidence.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 17 — Validate transactions and read_committed behavior

**Objective and procedure:** Review transactional producer fencing, transaction timeouts, aborted records, last stable offset and consumer isolation level.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 18 — Simulate bounded producer callback failure

**Objective and procedure:** Inject test-only client errors, capture retries and callback SLI, restore without affecting Kafka quorum/ISR and reconcile accepted IDs.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 19 — Simulate isolated consumer processing delay

**Objective and procedure:** Pause only synthetic consumer Deployment, capture group lag and event age, resume, verify unique sink commits and duplicate handling.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

### Lab 20 — Complete end-to-end recovery assessment

**Objective and procedure:** Run read-only verification, build UTC incident timeline, reconcile event ledger, validate SLO, security and 100-point rubric.

**Evidence and acceptance:** Capture Kafka/Strimzi/Kubernetes/client versions, UTC timestamps, source command/query, synthetic unique-event IDs, expected/observed callback or group behavior, Kafka quorum/ISR, security check, rollback and assessor. Mark **Pending** until actually executed. No production offsets or Kafka state may be altered by these labs.

## 8. Safe synthetic producer/consumer drills

**Producer drill:** Run a bounded synthetic producer with unique IDs against a dedicated KafkaTopic. Introduce a test-only client error (for example an invalid lab-only topic ACL principal) and capture the exact error classification. Restore approved credentials; do not disable security. Reconcile acknowledged IDs to partition/offset and sink ledger.

**Consumer drill:** Briefly pause only the isolated synthetic consumer Deployment, observe committed-offset lag and event age, then resume. Verify unique durable sink processing, duplicates and recovery time. Confirm Kafka quorum/ISR did not change.

**Poison-pill drill:** Use a deliberately invalid *synthetic* record in a dedicated topic and an application handler with bounded retries. Verify DLQ access controls, privacy, partition progress and error budget. Do not inject into shared topics.

**Abort:** Stop immediately if a non-lab namespace, production receiver, Kafka quorum/ISR, credential or unrelated workload is affected.

## 9. Automated read-only verification script

Save as `verify-ch48.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-delivery-synthetic
GROUP=sre-delivery-synthetic-group
echo '[1/11] Context'; kubectl config current-context
echo '[2/11] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/11] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/11] Pods and PVCs'
kubectl -n "$NS" get pods,pvc -o wide
echo '[5/11] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" -o wide
echo '[6/11] Topic metadata/ISR'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo '[7/11] Consumer group'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-consumer-groups.sh" --bootstrap-server "$BS" --describe --group "$GROUP"
echo '[8/11] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[9/11] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[10/11] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[11/11] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only producer/consumer Kafka inventory.'
echo 'NOT PROVEN: delivery guarantees, callback success, unique-event ledger, live drills or security acceptance.'
```

Run `chmod +x verify-ch48.sh && ./verify-ch48.sh | tee evidence-ch48/preflight.txt`. Missing synthetic topic/group is an environment prerequisite failure, not proof of Kafka unavailability.

## 10. Twelve troubleshooting scenarios

### Scenario 1 — Producer TimeoutException despite healthy brokers

**Diagnose:** Correlate delivery.timeout.ms, request latency, quotas, ISR and network before increasing timeouts. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 2 — AuthenticationException after certificate rotation

**Diagnose:** Check SAN/trust chain, expiry, SASL principal and Secret rollout without bypassing TLS. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 3 — RecordTooLargeException on one payload

**Diagnose:** Compare producer, broker/topic and batch size limits; avoid unbounded global increases. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 4 — OutOfOrderSequenceException or fenced producer

**Diagnose:** Check producer identity, transactions, concurrent instances and fatal error handling. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 5 — Producer duplicate deliveries after retry

**Diagnose:** Reconcile unique event IDs, idempotence, callback outcomes and downstream deduplication. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 6 — Consumer group rebalances every few minutes

**Diagnose:** Review poll duration, heartbeat/session, Pod restarts and assignment strategy. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 7 — Consumer lag flat but processing stale

**Diagnose:** Compare source event time, processing ledger, downstream sink and paused partitions. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 8 — Offset commit fails after rebalance

**Diagnose:** Review group generation, commit exceptions and safe reprocessing without resetting production offsets. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 9 — Poison-pill blocks one partition

**Diagnose:** Identify deserialization error, retry/DLQ policy and quarantine with schema/privacy controls. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 10 — read_committed consumer appears behind

**Diagnose:** Inspect open transactions, last stable offset and transaction coordinator. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 11 — Consumer duplicates after restart

**Diagnose:** Reconcile sink idempotency and commit ordering, separate at-least-once from exactly-once claims. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

### Scenario 12 — Kafka Ready while accepted events missing downstream

**Diagnose:** Trace producer acknowledgment to partition/offset, consumer and durable sink ledger; declare end-to-end incident. Correlate redacted client logs, Kafka topic/ISR, consumer group state, Kubernetes Pods, client SLO and unique-event ledger. **Mitigate:** Use only approved synthetic client changes and preserve TLS/ACL, acks/minISR and group offsets. **Verify:** Confirm callbacks, unique durable processing, freshness and alerts before closure.

## 11. Eight production SRE runbooks

### Runbook A — Producer callback and timeout failures

**Trigger and triage:** Check acks/retries/delivery timeout, quota, broker ISR and metadata; correlate synthetic ledger before tuning. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook B — TLS/SASL/ACL and bootstrap connectivity

**Trigger and triage:** Validate listener DNS, advertised endpoints, certificates, SASL identity and topic/group permissions without disabling controls. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook C — Idempotent and transactional producer errors

**Trigger and triage:** Inspect sequence/epoch, fencing, transactional IDs and abort/commit states; use supported client recovery. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook D — Consumer rebalance and coordinator instability

**Trigger and triage:** Inspect membership, Pod churn, heartbeat/poll intervals, group assignments and coordinator logs. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook E — Consumer lag, freshness and sink backlog

**Trigger and triage:** Correlate committed offsets, event age, processing rate, downstream latency and unique durable processing. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook F — Offset commit and duplicate processing

**Trigger and triage:** Inspect commit mode, failures, group generation, retry and idempotent sink; avoid shared offset resets. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook G — Poison-pill, schema and DLQ incident

**Trigger and triage:** Inspect deserialization, schema compatibility, bounded retry, DLQ permissions and data redaction. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

### Runbook H — End-to-end recovery and data-integrity acceptance

**Trigger and triage:** Reconcile acknowledged unique IDs, consumed offsets, durable sink commits, freshness, alerts and incident closure. **Evidence:** Kafka/Strimzi/Kubernetes versions, UTC incident timeline, source logs/metrics, quorum/ISR, affected event IDs and customer-facing SLO. **Recovery:** Approved mitigation with rollback, ledger reconciliation, security verification and postmortem owner.

## 12. Evidence package

```text
evidence-ch48/
  approval-and-scope.md
  context-version-matrix.md
  preflight.txt
  kafka-kraft-isr-baseline.md
  accepted-processed-ledger.csv
  producer-acks-retries-idempotence.md
  bootstrap-metadata-dns.md
  tls-sasl-acl-diagnosis.md
  producer-timeouts-quotas.md
  record-size-limits.md
  producer-sequence-transaction-errors.md
  partition-key-ordering.md
  consumer-group-assignments.md
  rebalance-analysis.md
  poll-processing-latency.md
  offset-commit-errors.md
  lag-vs-freshness.md
  poison-pill-dlq.md
  read-committed-transactions.md
  synthetic-producer-drill.md
  synthetic-consumer-drill.md
  incident-timeline.md
  security-review.md
  independent-signoff.md
```

Each artifact must record actual software version, UTC time, exact query/command, expected and observed result, source, owner, redaction, rollback and independent reviewer. Pending exercises must not be reported as passed.

## 13. 100-point data-delivery troubleshooting assessment

| Domain | Points | Critical |
|---|---:|---|
| Approval, safety and environment | 10 | Yes |
| Kafka/KRaft/ISR and Kubernetes baseline | 10 | Yes |
| Producer acks, retries, idempotence and errors | 15 | Yes |
| TLS/SASL/ACL, bootstrap and networking | 10 | Yes |
| Consumer group, rebalances and offset commits | 15 | Yes |
| Lag, freshness and unique-event reconciliation | 15 | Yes |
| Transactions, poison-pill and DLQ | 10 | Yes |
| Synthetic incident drills and recovery | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** fabricated execution, unapproved offset reset, weakened durability, security bypass, unexplained missing unique events, production disruption or absent independent review.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic client Deployments, test topic, test group and test alerts through approved GitOps, after confirming ownership and evidence retention. Never delete production topics, offsets, PVCs, monitoring data or operator-managed Secrets.

**References:** [Apache Kafka Producer Configs](https://kafka.apache.org/documentation/#producerconfigs), [Apache Kafka Consumer Configs](https://kafka.apache.org/documentation/#consumerconfigs), [Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Debugging](https://kubernetes.io/docs/tasks/debug/).

**Next:** Chapter 049 — Kafka Networking, TLS, SASL, ACL and Kubernetes Connectivity Incident Troubleshooting.

---

**Verification boundary:** GitHub publication confirms document availability only. Live producer/consumer drills, data-integrity verification, security review and independent technical acceptance remain Pending.
