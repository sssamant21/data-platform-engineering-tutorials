# Chapter 065 — Kafka Streams Production Observability, Performance, Failure Recovery and Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 13 — Kafka Streams and Stream Processing (5/5, final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–064, particularly 061–064  
**Status:** Published · **Live integrated labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Default broker outage, Pod eviction, transactional fencing, corrupt RocksDB, offset reset, schema incompatibility and topology migration to **tabletop**. Use approved disposable clusters and synthetic data for live fault injection. Do not delete production changelog/repartition topics, modify production application IDs or claim measured SLO/RPO/RTO without executed evidence.

## 1. Capstone mission

Integrate topology design, joins and event-time windows, RocksDB state stores, changelog recovery, exactly-once Kafka transactions, observability and incident operations into a reproducible SRE acceptance exercise. Distinguish a healthy Kubernetes Pod from a healthy stream task, a healthy stream task from correct results, and Kafka-scoped exactly-once from external business side effects.

**Learning outcomes:** establish golden input/output ledgers, instrument stateful topology and task metrics, bound recovery time, investigate Kafka transactions, rehearse safe rollback, and obtain independent reliability and security acceptance.

## 2. Production architecture

```text
Synthetic source events (event_id, key, event_time)
                    |
              Kafka input topic
                    |
     +--------------+--------------+
     | Kubernetes Streams instances|
     | topology: filter/join/window |
     | active + standby tasks       |
     | RocksDB state + changelog    |
     +--------------+--------------+
                    |
        Kafka EOS-v2 transaction
     (output + consumed offsets + state)
                    |
          read_committed consumer
                    |
         durable output event ledger
                    |
     SRE/DBRE dashboards + SLO + RCA
```

**Critical boundary:** Kafka Streams is a JVM client library. Strimzi manages Kafka, not the Streams application Deployment. Kafka EOS-v2 coordinates supported Kafka-scoped operations, **not** arbitrary external database/HTTP writes. A Kafka output acknowledgment does not prove an external sink commit.

## 3. Acceptance charter and failure budget

| Gate | Required evidence | If missing |
|---|---|---|
| Business contract | signed event correctness, freshness SLO, RPO/RTO, ownership | BLOCK |
| Kafka durability | KRaft quorum, ISR/minISR, RF, internal topic health | BLOCK |
| Topology | exact application.id, topology graph, key/partition contract | BLOCK |
| State recovery | RocksDB, changelog, standby, bounded restore time | BLOCK |
| Event-time | window/grace/late-drop reconciliation | BLOCK |
| Kafka transactions | EOS-v2 version/ACL, committed/aborted visibility | BLOCK |
| Security | TLS/SASL, least privilege, secrets, PII controls | BLOCK |
| Observability | task/thread metrics, lag, latency, event ledger | BLOCK |
| Change safety | rollback, abort, migration and incident runbooks | BLOCK |
| Independent review | SRE/platform/security/business signoff | NOT READY |

No-go: missing accepted event IDs, unreviewed internal-topic deletion, unsupported external exactly-once claims, insufficient RocksDB storage, unhealthy transaction coordinator or unsafe production fault injection.

## 4. SLIs, SLOs and error-budget policy

| SLI | Definition | Required evidence |
|---|---|---|
| End-to-end freshness | output durable UTC minus source event UTC, adjusted for clock uncertainty | event ID and timestamp ledger |
| Output correctness | expected fixture outputs versus committed output IDs/values | deterministic comparison |
| Task availability | time topology tasks can process input | thread/task state transitions |
| Processing lag | task/partition backlog and oldest accepted record age | Streams JMX + Kafka offsets |
| Recovery RTO | outage declaration to independently verified correct output | UTC incident timeline |
| Restore throughput | changelog bytes/seconds and standby catch-up | restore metrics and state size |
| Late/drop rate | late or rejected records divided by eligible records | event-time/drop ledger |
| Transaction errors | abort/fencing/timeout failures per attempted commit | client/broker metrics |

Use business-approved thresholds based on baseline. A universal lag number is not meaningful. Record metric names with the pinned Kafka Streams release because JMX sensor names and availability can vary.

## 5. Versioned monitoring and instrumentation

- **Kafka broker/KRaft:** quorum, broker availability, ISR/minISR, under-replicated partitions, transaction coordinator and disk.
- **Kafka Streams client:** `kafka-streams` thread, task, processor and state-store JMX groups; processing/commit rates, `records-lag-max`, rebalance and restore state where exposed.
- **JVM/Pod:** CPU throttling, heap/GC, RSS/native memory, restarts, OOM, disk bytes/inodes and eviction events.
- **RocksDB:** state size, cache, compaction, write stalls, native memory and changelog restore progress.
- **Application integrity:** accepted input IDs, intentionally filtered IDs, join/window matches, committed output IDs and external sink durable IDs.
- **Security:** TLS handshake errors, ACL denials, transactional ID authorization and redacted poison-pill handling.

Metrics are proxies, not a substitute for business event reconciliation. Distinguish **no input** from **blocked processing** using an approved synthetic heartbeat or fixture.

## 6. Kubernetes-first preflight

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc,svc -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
kubectl -n kafka-lab get deploy -l app=sre-ch65-streams -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
```

Validate Strimzi release-specific CRDs and actual listener TLS/SASL settings. If the example Deployment is missing, mark **NOT DEPLOYED**, not a pass.

## 7. Deterministic golden event fixture

```json
{"event_id":"sre65-001","key":"customer-a","event_time":"2026-10-20T12:00:01Z","amount":10}
{"event_id":"sre65-002","key":"customer-a","event_time":"2026-10-20T12:00:02Z","amount":12}
{"event_id":"sre65-003","key":"customer-b","event_time":"2026-10-20T12:00:03Z","amount":20}
{"event_id":"sre65-004","key":"customer-a","event_time":"2026-10-20T11:59:59Z","amount":5}
```

For a five-minute tumbling count keyed by customer, all four fixture events fall into the same UTC window and expected final counts are `customer-a=3`, `customer-b=1`, **provided** the event timestamp extractor reads `event_time`, the records are accepted before grace closure, and no deduplication/filter changes the contract. Kafka record timestamps may differ from payload event timestamps; configure the extractor explicitly. Add duplicate IDs, unmatched joins, late events and tombstones as separate fixtures. Record all intended drops.

## 8. Twenty integrated Kubernetes-first labs

### Lab 01 — Charter and business SLO

**Procedure:** Agree business freshness, correctness, availability, recovery objectives, fault approval and RACI.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 02 — Version and cluster inventory

**Procedure:** Capture Strimzi, Kafka, KRaft, Streams, JDK, Kubernetes, client image and configuration.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 03 — Topology and key contract

**Procedure:** Inspect Topology.describe, application.id, keys, partition alignment and internal topics.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 04 — Baseline golden event ledger

**Procedure:** Prepare synthetic source IDs, expected join/window outputs, tombstones and dedup contract.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 05 — Kafka KRaft durability baseline

**Procedure:** Review quorum, RF, minISR, under-replicated partitions, transactional coordinator and ACL.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 06 — Streams thread/task health

**Procedure:** Record RUNNING/REBALANCING/ERROR, active/standby tasks and rebalance timeline.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 07 — Consumer lag and freshness

**Procedure:** Correlate records-lag-max, input timestamp, output acknowledgment and clock skew.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 08 — Processing latency and throughput

**Procedure:** Measure process/commit/poll rates and per-partition skew under bounded synthetic load.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 09 — RocksDB memory and I/O

**Procedure:** Inspect state bytes, off-heap memory, cache, compaction stalls and storage headroom.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 10 — Changelog restore capacity

**Procedure:** Estimate restore bytes, throughput, task placement, standby freshness and recovery time.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 11 — Event-time/window correctness

**Procedure:** Test on-time, out-of-order, grace, late drop, hopping overlap and suppression design.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 12 — KStream/KTable join reconciliation

**Procedure:** Validate co-partitioning, temporal table semantics and expected match ledger.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 13 — Exactly-once transaction boundary

**Procedure:** Inspect EOS-v2, read_committed, aborted records, fencing and external sink exclusions.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 14 — TLS/SASL and least privilege

**Procedure:** Review KafkaUser topic/group/transactional ACLs, Secret mounts and NetworkPolicy.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 15 — Kubernetes availability controls

**Procedure:** Review probes, PDB, topology spread, graceful shutdown and storage eviction risk.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 16 — Pod-loss tabletop

**Procedure:** Assess task reassignment, standby promotion, state restoration and event reconciliation.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 17 — Broker/ISR outage tabletop

**Procedure:** Assess transactional writes, task progress, backpressure and no-go thresholds.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 18 — Poison-pill and schema drift tabletop

**Procedure:** Assess deserialization handlers, DLQ/redaction, serde compatibility and replay.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 19 — Topology upgrade and rollback tabletop

**Procedure:** Review state-store names, app identity, internal topic compatibility and dual-run options.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

### Lab 20 — Independent acceptance and RCA

**Procedure:** Score critical gates, record observed versus tabletop evidence, risk owners and signoffs.

**Evidence and pass criteria:** Record exact Strimzi/Kafka/Streams/JDK versions, Kubernetes context, UTC start/end, command or approved tabletop design, expected and observed event IDs, thread/task and RocksDB/changelog metrics, transaction visibility, security, rollback/abort and assessor. Mark **Pending** until executed. No fault-injection result is assumed.

## 9. Read-only Kubernetes inventory script

Save as `verify-ch65.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] KRaft and NodePools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/9] Storage'; kubectl -n "$NS" get pvc -o wide
echo '[5/9] Services'; kubectl -n "$NS" get svc -o wide
echo '[6/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[7/9] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo '[8/9] Streams app'
if kubectl -n "$NS" get deploy -l app=sre-ch65-streams -o name | grep -q .; then
  kubectl -n "$NS" get deploy,pods -l app=sre-ch65-streams -o wide
else
  echo 'NOT DEPLOYED: sre-ch65-streams'
fi
echo '[9/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: Kubernetes inventory only.'
echo 'NOT PROVEN: event correctness, state recovery, Kafka EOS, SLO or independent review.'
```

Run `chmod +x verify-ch65.sh && ./verify-ch65.sh | tee evidence-ch65/preflight.txt`. Success is **inventory only**, not capstone certification.

## 10. Twelve failure scenarios

### Scenario 1 — Lag climbs but broker metrics look healthy

**Diagnosis:** Investigate skew, task stalls, RocksDB compaction and downstream producer backpressure. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 2 — Streams Pods Ready but no output

**Diagnosis:** Inspect thread/task state, topic input, join conditions, ACL and transactional visibility. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 3 — Restore exceeds RTO

**Diagnosis:** Inspect changelog size, restore rate, disk, standby placement and scheduling. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 4 — RocksDB disk pressure

**Diagnosis:** Inspect state dir, compaction, ephemeral eviction and key cardinality. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 5 — Rebalance storm after rollout

**Diagnosis:** Inspect Pod churn, SIGTERM grace, group assignments and PDB. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 6 — Join results unexpectedly absent

**Diagnosis:** Inspect keys, co-partitioning, table update order and event-time windows. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 7 — Late records silently dropped

**Diagnosis:** Inspect timestamp extractor, grace, window close and dropped-record accounting. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 8 — Output duplicated after failure

**Diagnosis:** Inspect at-least-once/EOS, replay, producer fencing and external sink idempotency. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 9 — Transaction coordinator disruption

**Diagnosis:** Inspect internal topic ISR, broker health, transaction timeouts and read_committed lag. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 10 — Serde change breaks state restore

**Diagnosis:** Inspect changelog schema, store names, topology upgrade and rollback. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 11 — Poison-pill handler silently skips

**Diagnosis:** Inspect exception policy, DLQ, PII redaction and event-ID gap. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

### Scenario 12 — Metrics appear green but business ledger differs

**Diagnosis:** Hold incident until source/output reconciliation and owner signoff. Correlate UTC timeline, Kafka ISR, Streams thread/task state, lag, RocksDB/changelog, transaction visibility and expected vs actual event IDs. **Response:** Freeze unsafe mutations, preserve logs, protect durability, execute owner-approved rollback and reconcile business state. **Exit:** Measured recovery or explicitly labeled tabletop result, remediation owner and reviewer.

## 11. Eight production runbooks

### Runbook A — SLO breach triage

**Trigger/response:** Identify freshness vs correctness vs availability; assign IC and preserve evidence. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook B — Streams lag and throughput regression

**Trigger/response:** Inspect task skew, poll/commit/process metrics, CPU, GC, broker throttling and rollback. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook C — State-store and restore recovery

**Trigger/response:** Check RocksDB storage, changelog ISR, standby state and recovery RTO. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook D — Rebalance and Pod/node loss

**Trigger/response:** Review Kafka group, Kubernetes rollout, task reassignment, graceful termination and event ledger. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook E — Exactly-once and transactional incident

**Trigger/response:** Check EOS-v2, coordinator, fencing, read_committed, output IDs and external side effects. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook F — Join/window correctness incident

**Trigger/response:** Review keys, co-partitioning, timestamps, grace, suppression and expected fixtures. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook G — Security/serialization/poison-pill incident

**Trigger/response:** Review TLS/SASL, ACL, serde, exception handlers, DLQ redaction and replay. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

### Runbook H — Capstone acceptance, rollback and RCA

**Trigger/response:** Reconcile accepted IDs, verify observed RPO/RTO, sign critical gates and track remediation. **Abort/no-go:** unknown data loss, unsafe state reset, internal topic deletion, missing ACL/TLS, unapproved production fault injection or unverified business output. **Exit:** Correct committed output, bounded freshness/restore, RCA, security review and independent signoff.

## 12. Independent evidence package

```text
evidence-ch65/
  capstone-charter-raci-slo-rpo-rto.md
  version-kraft-strimzi-streams-jdk-matrix.md
  preflight.txt
  topology-applicationid-keys.md
  golden-input-fixture.jsonl
  expected-join-window-results.csv
  actual-committed-output.csv
  filtered-late-dropped-ids.csv
  transaction-visibility-eos-boundary.md
  kraft-isr-internal-topics.md
  thread-task-rebalance-metrics.md
  lag-freshness-clock-skew.md
  cpu-gc-throughput-baseline.md
  rocksdb-native-memory-io-disk.md
  changelog-standby-restore-rto.md
  tls-acl-networkpolicy-security.md
  kubernetes-pdb-shutdown-spread.md
  pod-loss-tabletop.md
  broker-isr-outage-tabletop.md
  poison-pill-schema-drift-tabletop.md
  topology-upgrade-rollback-tabletop.md
  incident-timeline-rca.md
  independent-sre-platform-security-signoff.md
  business-readiness-signoff.md
  scorecard.md
```

Each artifact requires timestamp, exact versions, expected/observed outcome, **Live** versus **Tabletop**, sanitized evidence, owner, rollback and reviewer. Do not mark missing artifacts as passed.

## 13. 100-point enterprise Kafka Streams capstone

| Domain | Points | Critical |
|---|---:|---|
| Charter, RACI, business correctness/SLO | 10 | Yes |
| Kafka KRaft, Streams topology and task durability | 15 | Yes |
| Lag, latency, throughput and observability | 15 | Yes |
| RocksDB, changelog, standby and restore RTO | 15 | Yes |
| Join/window correctness and event ledger | 15 | Yes |
| Kafka EOS-v2, transaction and external sink boundary | 10 | Yes |
| Kubernetes security, capacity and safe rollout | 10 | Yes |
| Incident drills, rollback, RCA and independent signoff | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 **and** every critical gate has representative live evidence plus independent approval. **Automatic fail:** fabricated test evidence, missing event-ID reconciliation, unreviewed state reset, deleted internal topics, credential leak, unsupported external exactly-once claim, unsafe production fault injection or absent signoff.

**Current readiness:** **Pending / Not Ready** until approved live tests and independent review are complete. Publication and tabletop design do not prove production readiness.

## 14. Cleanup and transition

Remove only chapter-owned synthetic workloads and topics after approval and evidence retention. Never delete Streams internal changelog/repartition topics or state stores until the application is retired through a reviewed procedure.

**References:** [Apache Kafka Streams](https://kafka.apache.org/documentation/streams/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/), [RocksDB](https://github.com/facebook/rocksdb/wiki).

**Part 13 — Kafka Streams and Stream Processing is fully published (061–065).**

**Next:** Chapter 066 — Advanced Kafka on Kubernetes: Strimzi Operator Architecture, KRaft and GitOps Foundations, beginning Part 14 — Advanced Kubernetes, Strimzi and GitOps.

---

**Verification boundary:** Chapter published; integrated live reliability drills, measured RTO/RPO, event reconciliation and independent security acceptance remain Pending.
