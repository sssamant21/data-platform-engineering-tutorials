# Chapter 038 — Kafka Centralized Logging, Kubernetes Log Pipelines, Audit Events and Incident Forensics

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 08 — Monitoring, Metrics and Observability (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–037; security, KRaft, Kubernetes, monitoring and incident response foundations  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use an approved disposable Kubernetes cluster and synthetic log events. Kafka and Kubernetes logs can expose principals, broker endpoints, tokens, connection strings and payload fragments. Collect only authorized bounded time windows, redact sensitive fields, restrict forensic evidence and use approved retention. Never enable DEBUG/TRACE cluster-wide in production without change review; never disable TLS verification, alter production audit settings or restart brokers for a logging exercise.

## 1. Mission and learning objectives

Design, deploy and validate a Kubernetes-first centralized logging and incident-forensics architecture for Kafka KRaft clusters. The system must preserve timestamps, component identity and error context while preventing secret leakage, unbounded cardinality and log pipeline overload.

By the end, you can identify Kafka broker/controller/operator/client logs, route and parse Java stack traces, implement bounded collectors, secure log transport, distinguish Kubernetes API audit from Kafka application logs, reconstruct incident timelines, detect log loss and perform a reviewed forensic handoff.

## 2. Architecture

```text
Kafka broker + KRaft controller Pods
Strimzi Cluster Operator / Entity Operator
Producer and consumer application Pods
Kubernetes Events and API audit (if enabled)
               |
               v
  Container stdout/stderr + kubelet/CRI files
               |
               v
Approved DaemonSet collector
(Fluent Bit / Vector / OTel Collector)
  parse -> enrich -> redact -> filter -> buffer
               |
               | TLS + least privilege
               v
Approved central log backend
(OpenSearch / Elasticsearch / Loki / SIEM)
  retention + RBAC + audit + immutable evidence policy
               |
               v
Search / dashboards / alerts / incident timeline
               ^
               |
Prometheus metrics + Kafka CLI + GitOps change history
```

**Critical distinctions:** Kubernetes Events are not a complete audit trail; Kubernetes API audit must be enabled at the control plane and may not be accessible on managed services. Kafka authorization failures and Strimzi reconciliation logs do not replace an authoritative audit of every administrative action. Client logs do not prove Kafka record durability or downstream business completion.

## 3. Logging source and schema contract

| Source | Typical signal | Validation |
|---|---|---|
| Kafka broker | network, request, replica, storage, authorization errors | broker Pod and JMX metrics |
| KRaft controller | quorum election, metadata log and controller events | metadata-quorum CLI |
| Strimzi Cluster Operator | reconciliation, resource generation, rolling operations | Kafka CR status and events |
| Entity Operator | KafkaTopic/KafkaUser reconciliation | resource status and events |
| Producer client | retries, timeout, callback failure | acknowledged-event ledger |
| Consumer client | rebalance, commits, handler failure | consumer-group offsets |
| Kubernetes Events | scheduling, probes, eviction, mount errors | Pod status |
| Kubernetes API audit | API actor, verb, resource and response (if enabled) | control-plane audit policy |
| Central log collector | ingestion, parsing, buffering, drops | pipeline metrics and synthetic event IDs |

Minimum fields: UTC timestamp, observed timestamp, severity, cluster, namespace, Pod UID, container, component, message, source and parser version. Broker ID, partition, group and correlation IDs may be added when bounded and appropriate. **Never log credentials, private keys, SASL passwords, authorization headers or raw customer events.**

## 4. Log pipeline design principles

1. Use approved image digests and version-compatible collector configurations.
2. Read container logs through least-privilege read-only mounts; do not give collectors unrestricted Kubernetes API permissions.
3. Enrich with bounded Kubernetes metadata; avoid excessive Pod labels and high-cardinality event identifiers as index fields.
4. Handle multiline Java exceptions without discarding original records.
5. Bound buffering and backpressure so the collector cannot starve Kafka brokers.
6. Encrypt transport, authenticate the sink and scope writer permissions.
7. Track ingested, rejected, retried, dropped and delayed events.
8. Apply documented retention, privacy, legal hold and forensic access controls.
9. Maintain a source-to-sink synthetic event reconciliation test.
10. Version pipelines and parsing rules through GitOps with rollback.

## 5. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve logging scope and evidence policy

**Objective and procedure:** Record disposable cluster, change ticket, owners, data classification, retention, access boundaries, redaction rules, allowed destinations and forensic chain of custody. Do not collect production payloads or credentials.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 02 — Inspect Kafka/Strimzi/KRaft log sources

**Objective and procedure:** Inventory broker and controller Pods, Strimzi operator, Entity Operator, Kafka CLI, client Deployments, Kubernetes Events and audit-log availability. Confirm node pool roles and log format.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 03 — Capture baseline Kubernetes events

**Objective and procedure:** Run kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp and kubectl -n kafka-lab get pods -o wide. Correlate events with Kafka CR readiness and KRaft quorum CLI.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 04 — Collect broker Pod logs safely

**Objective and procedure:** Run kubectl -n kafka-lab logs <approved-broker-pod> --since=15m --timestamps --all-containers=false with a verified container name where needed. Sanitize output and avoid collecting broad historical data.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 05 — Collect KRaft controller logs

**Objective and procedure:** Identify controller-role KafkaNodePool Pods and extract bounded log windows for leader elections, metadata catch-up and quorum-related errors. Compare with metadata-quorum CLI rather than inferring quorum from a single log line.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 06 — Collect Strimzi operator reconciliation logs

**Objective and procedure:** Inspect operator namespace and deployment, capture bounded reconcile errors/events, correlate Kafka/KafkaNodePool generation and observed status, and redact sensitive CR content.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 07 — Define structured logging schema

**Objective and procedure:** Specify timestamp UTC, severity, cluster, namespace, Pod, container, component, broker ID, correlation ID, exception type and message; prohibit secrets, raw event payloads and unbounded identity labels.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 08 — Validate JSON and multiline Java stack traces

**Objective and procedure:** Use a synthetic sample with Java stack trace and structured JSON, test parsing and multiline grouping, preserve original message and timestamp, and detect truncation.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 09 — Design node-level log collection

**Objective and procedure:** Compare approved Fluent Bit, Vector or OpenTelemetry Collector DaemonSet patterns, service accounts, read-only mounts, backpressure, resource limits and node filesystem permissions; do not install an unreviewed agent.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 10 — Configure namespace and component routing

**Objective and procedure:** Create allowlisted routes for kafka-lab broker/controller/operator/client logs, separate security/audit destinations and explicit drop/redaction rules for secret-bearing fields.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 11 — Implement safe buffering and retries

**Objective and procedure:** Design bounded memory/disk buffering, retry/backoff, delivery guarantees, log-drop metrics and graceful shutdown; ensure collector cannot exhaust broker PVC or node ephemeral storage.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 12 — Validate TLS and authorization for log sink

**Objective and procedure:** Require TLS certificate validation, least-privilege sink credentials from Kubernetes Secrets, scoped index/stream permissions, NetworkPolicy and credential rotation procedure.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 13 — Build searchable forensic fields

**Objective and procedure:** Index cluster, Pod, component, severity, time and correlation ID; avoid indexing unbounded message bodies or secrets. Test exact event retrieval and ordering with synthetic records.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 14 — Correlate Kafka client and broker events

**Objective and procedure:** Use synthetic producer/client IDs and timestamps to correlate timeout, retry, broker queue/replication symptoms and Kubernetes Pod events; distinguish causation from temporal coincidence.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 15 — Correlate consumer rebalances and lag

**Objective and procedure:** Join bounded consumer application logs, group membership events, committed offsets and event-age metrics; avoid offset reset and raw message logging.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 16 — Audit administrative and security changes

**Objective and procedure:** Identify Kubernetes API audit records (when available), Strimzi CR GitOps changes, Kafka ACL/authorization errors and operator reconciliation; distinguish audit sources from ordinary application logs.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 17 — Validate retention, privacy and deletion

**Objective and procedure:** Check log retention, lifecycle, legal hold, access review, encryption at rest, immutable evidence controls where required and tested expiry in a synthetic index.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 18 — Run synthetic incident timeline reconstruction

**Objective and procedure:** Inject a client-only synthetic timeout or a test log event; collect producer/client, broker, operator and Kubernetes signals, align clocks and build a timeline without harming brokers.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 19 — Test log pipeline outage and recovery

**Objective and procedure:** Temporarily disable an approved test-only sink/route, observe buffer limits, dropped-log counters and alerting, restore delivery and reconcile expected versus received synthetic IDs.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

### Lab 20 — Execute read-only preflight and assessor signoff

**Objective and procedure:** Run verify-ch38.sh, review sample queries, access controls, redaction, timestamps and completeness, then record Pass/Fail/Pending and a GitOps rollback plan.

**Validation:** Capture approved cluster context, exact Kafka/Strimzi/Kubernetes/collector versions, source log sample, expected central destination, observed result, pipeline counters, redaction check and rollback. Use synthetic identifiers for traceability. Mark **Pending** until the lab is executed and independently reviewed.

## 6. Kubernetes read-only log inventory and forensics commands

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch38
kubectl config current-context | tee evidence-ch38/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods -o wide \
  | tee evidence-ch38/inventory.txt
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp \
  | tee evidence-ch38/events.txt
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}' \
  | tee evidence-ch38/kafka-conditions.txt
kubectl -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch38/quorum.txt

# Inspect approved Pod and container names first.
kubectl -n "$NS" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'

# Replace these placeholders only after identifying an approved Kafka Pod:
# kubectl -n "$NS" logs <broker-pod> -c <broker-container> --since=15m --timestamps
# kubectl -n "$NS" logs <broker-pod> -c <broker-container> --previous --tail=200 --timestamps
```

Do not automatically upload raw command output to public GitHub. Review and redact addresses, principals, tokens and incident data before storing evidence.

## 7. Example collector pipeline design (pseudoconfiguration)

The following is a **design sketch**, not a ready-to-deploy Fluent Bit/Vector/OpenTelemetry manifest. Field names, parser stages and sink plugins are release-specific.

```yaml
source:
  type: kubernetes_container_logs
  namespaces: [kafka-lab]
transform:
  - parse_cri_timestamp
  - group_java_multiline
  - attach_allowlisted_kubernetes_metadata
  - redact_credentials_and_payloads
  - normalize_severity_and_utc_timestamp
buffer:
  type: bounded
  overflow: alert_and_account_for_loss
sink:
  type: approved_central_log_backend
  transport: tls_with_certificate_validation
  credentials: read_only_kubernetes_secret_mount
  retention: policy_defined
```

A production implementation must pin the collector version, validate the actual schema, use appropriate Kubernetes RBAC/NetworkPolicy, set resource requests/limits, and test sink outage recovery. Redaction patterns are not sufficient by themselves: upstream applications must avoid emitting secrets.

## 8. Correlation and incident timeline example

| Time (UTC) | Source | Synthetic observation | Correlation |
|---|---|---|---|
| 12:00:00 | Producer | callback latency increases | client p99 |
| 12:00:03 | Broker | Produce request queue rises | request-stage metrics |
| 12:00:05 | Kubernetes | consumer Pod CPU throttling | cAdvisor |
| 12:00:10 | Consumer | processing backlog increases | lag and event age |
| 12:00:20 | Collector | synthetic log event arrives | ingestion delay |

These rows are **illustrative, not observed events**. Normalize clock skew, retain original event timestamps and ingestion timestamps, and distinguish correlation from proven causation.

## 9. Read-only verification script

Save as `verify-ch38.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/10] Context'
kubectl config current-context
echo '[2/10] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/10] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Kafka Pods'
kubectl -n "$NS" get pods -o wide
echo '[5/10] Recent Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[6/10] Pod/container names'
kubectl -n "$NS" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'
echo '[7/10] Kafka CR status'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[8/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo '[9/10] Log collector inventory (optional)'
kubectl get daemonsets -A -o wide
echo '[10/10] PVC inventory'
kubectl -n "$NS" get pvc -o wide
echo 'PASS: read-only Kafka logging platform inventory.'
echo 'NOT PROVEN: centralized ingestion, parser correctness, redaction, audit coverage or incident acceptance.'
```

Run `chmod +x verify-ch38.sh && ./verify-ch38.sh | tee evidence-ch38/preflight.txt`. The internal 9092 endpoint is only an isolated-lab CLI convention; production-like access must use approved TLS/SASL and ACLs.

## 10. Twelve troubleshooting scenarios

### Scenario 1 — Broker logs missing after Pod restart

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 2 — Java stack traces split into unrelated events

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 3 — Kafka client timeout not correlated with broker errors

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 4 — Collector CPU throttling causes log loss

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 5 — Collector buffer fills node ephemeral storage

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 6 — TLS authentication to log sink fails

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 7 — Sensitive SASL credentials appear in log fields

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 8 — KRaft leader election logs interpreted incorrectly

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 9 — Strimzi reconciliation logs disappear after upgrade

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 10 — Duplicate logs after collector restart

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 11 — Kubernetes audit records unavailable or incomplete

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

### Scenario 12 — Incident timeline distorted by clock skew

**Detect:** Inspect collector ingestion/dropped-event counters, source Pod logs, Kubernetes Events and central backend timestamps. **Diagnose:** Check source selection, CRI parser, multiline grouping, buffering, TLS/auth, label enrichment, clock skew, retention and role permissions. **Recover:** Apply an approved, minimal pipeline or application logging correction; preserve original forensic evidence and do not weaken security. **Verify:** Reconcile synthetic event IDs and timestamps, record loss/duplication and update the incident timeline.

## 11. Eight SRE production runbooks

### Runbook A — Broker incident log capture

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook B — KRaft controller incident forensics

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook C — Strimzi operator reconciliation investigation

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook D — Producer timeout and retry correlation

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook E — Consumer rebalance and offset investigation

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook F — Log pipeline outage and data-loss accounting

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook G — Security audit and sensitive log exposure

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

### Runbook H — Forensic evidence preservation and handoff

1. Establish incident scope, authorized collectors, time window and evidence owner.
2. Capture Kafka/KRaft status and Kubernetes Events independently of the log backend.
3. Gather bounded, timestamped and redacted broker/controller/operator/client logs.
4. Correlate with Prometheus metrics, Kafka CLI and GitOps change history.
5. Determine gaps, duplicates, clock skew, parsing failures and source credibility.
6. Remediate via approved change; preserve chain of custody and reviewer signoff.

## 12. Evidence package

```text
evidence-ch38/
  approval-and-scope.md
  context.txt
  inventory.txt
  events.txt
  kafka-conditions.txt
  quorum.txt
  source-inventory.csv
  log-schema.md
  parser-multiline-test.md
  collector-deployment-review.yaml
  routing-and-redaction.md
  buffer-and-drop-metrics.csv
  tls-and-rbac-review.md
  forensic-query-tests.md
  client-broker-correlation.md
  consumer-rebalance-timeline.md
  audit-coverage-matrix.md
  retention-privacy-review.md
  synthetic-incident-timeline.md
  pipeline-outage-recovery.md
  preflight.txt
  incident-forensic-report.md
  assessor-signoff.md
```

Every evidence item records software version, context, source, UTC time range, redaction status, expected/observed result, reviewer and retention policy. Live results must not be invented.

## 13. 100-point enterprise logging assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, authorization and data classification | 10 | Yes |
| Kafka broker, KRaft and operator log coverage | 15 | Yes |
| Kubernetes source discovery and parser correctness | 10 | Yes |
| Collector reliability, buffering and drop accounting | 15 | Yes |
| TLS, RBAC, redaction and privacy | 15 | Yes |
| Producer/consumer log correlation | 10 | Yes |
| Audit source coverage and limitations | 10 | Yes |
| Incident timeline and forensic preservation | 10 | Yes |
| Runbooks and independent reviewer signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** at least 85/100 and all critical gates passed with evidence. **Automatic Fail:** exposed secrets or raw production payloads, disabled TLS verification, unapproved production audit changes, fabricated log coverage, unaccounted log loss, broken chain of custody or missing security signoff.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic log events, temporary test routes and approved diagnostic Pods. Preserve redacted evidence according to policy. Do not delete Kafka PVCs, operator-managed Secrets, shared log indexes or control-plane audit records.

**References:** [Strimzi documentation](https://strimzi.io/documentation/), [Kafka documentation](https://kafka.apache.org/documentation/), [Kubernetes logging architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/), [Kubernetes auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/), [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/), [Fluent Bit](https://docs.fluentbit.io/manual).

**Next:** Chapter 039 — Kafka Distributed Tracing, OpenTelemetry, Client Correlation and End-to-End Streaming Observability.

---

**Verification boundary:** GitHub publication establishes document availability only. Live logging pipeline execution, audit validation, forensic drills and independent technical/security review remain Pending.
