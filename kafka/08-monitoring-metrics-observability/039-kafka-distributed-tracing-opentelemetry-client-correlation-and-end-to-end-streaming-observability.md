# Chapter 039 — Kafka Distributed Tracing, OpenTelemetry, Client Correlation and End-to-End Streaming Observability

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 08 — Monitoring, Metrics and Observability (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 016–020, 026–038, especially metrics and centralized logging  
**Status:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** All exercises use approved synthetic workloads in a disposable Kubernetes cluster. Trace headers and span attributes may contain sensitive data. Never record Kafka payloads, raw record keys, credentials, customer identifiers or authorization headers in traces. Keep OTLP receivers private, enforce TLS/authorization and bound sampling and buffering. Publication is not evidence of live trace correctness.

## 1. Mission and learning objectives

Instrument a Kafka event-driven application end to end using OpenTelemetry across producer, broker boundary, consumer and downstream processing. Build a Kubernetes-hosted OTLP pipeline, propagate W3C context through Kafka headers, correlate spans with logs and Prometheus metrics, analyze event age and asynchronous processing, and validate tracing during retries, rebalances and outages.

Understand that Kafka brokers do **not** automatically join application traces. The producer must inject trace context into record headers and the consumer must extract it; instrumentation libraries and semantic conventions are version-sensitive. A broker append timestamp is not the same as a producer callback timestamp or a business processing completion timestamp.

## 2. Reference architecture

```text
HTTP/API ingress (traceparent)
   |
   v
Producer application Pod
  span: publish + Kafka headers (traceparent/tracestate)
   |
   v
Strimzi Kafka KRaft brokers
  KafkaTopic + partitions + replication
  broker metrics/logs (no automatic app trace context)
   |
   v
Consumer application Pods
  extract headers -> process span / links
  commit after durable processing
   |
   v
Downstream API / database / idempotent synthetic sink
   |
   +---- OTLP SDK exporters --> OTel Collector --> trace backend
   +---- structured logs (trace_id/span_id) --> log backend
   +---- metrics --> Prometheus --> Grafana
                                  |
                                  v
                         SLOs and incident forensics
```

## 3. Trace and messaging semantics

| Concept | Required behavior | Failure to avoid |
|---|---|---|
| Context propagation | Inject/extract W3C traceparent/tracestate in Kafka headers | assuming broker creates spans |
| Asynchronous processing | Use parent/links appropriate to fan-out/batch | misleading single parent |
| Delivery retries | Correlate attempts to accepted event ID | double-counting business events |
| Consumer replay | New processing attempts can share event lineage | assuming exactly-once side effects |
| Timestamps | UTC wall clock + monotonic local duration | negative dwell due to skew |
| Sampling | Parent-based or reviewed tail sampling | treating sampled traces as full population |
| Attributes | Bounded service/topic/operation labels | leaking PII and high cardinality |
| Reliability | Collector outages must not block critical app path | unbounded queue or backpressure |

Use the installed OpenTelemetry messaging semantic convention version consistently; attribute names can change across SDK/instrumentation releases. Do not treat example names as universal.

## 4. Kubernetes tracing design principles

- Deploy collector components with pinned images, resource requests/limits, ServiceAccount, network isolation and reviewed ConfigMaps.
- Separate client instrumentation from broker JMX monitoring; correlate with timestamps and bounded attributes.
- Preserve trace context across serialization and producer retries without modifying Kafka record payload semantics.
- Never use unbounded event IDs as metric labels. Trace IDs are appropriate for trace/log correlation under retention and privacy controls.
- Record exporter failures, dropped spans, queue utilization, memory limiter and retry metrics.
- Choose head/tail sampling based on actual incident needs and trace backend capacity.
- Document how fan-out, joins, batches, transactions and DLQs change trace lineage.
- Validate OTLP TLS, backend RBAC, data retention and redaction before any real traffic.

## 5. Twenty Kubernetes-first hands-on labs

### Lab 01 — Scope, approval and SLO design

**Objective and procedure:** Document disposable context, tracing objectives, trace sampling budget, PII policy, downstream boundaries, expected event age and allowed OTLP endpoints. Assign owners and abort gates.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 02 — Inspect Kafka KRaft and Strimzi inventory

**Objective and procedure:** Run kubectl get kafka,kafkanodepool,pods,pvc in kafka-lab, validate Kafka Ready and metadata quorum CLI, record installed Kafka/client/Strimzi versions and listener security.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 03 — Identify producer-to-consumer trace boundaries

**Objective and procedure:** Map HTTP ingress, producer send, broker append, consumer poll, processing and sink acknowledgment. Kafka brokers do not automatically propagate OpenTelemetry trace context.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 04 — Design W3C context in Kafka headers

**Objective and procedure:** Define traceparent/tracestate propagation through Kafka record headers using approved OpenTelemetry propagators. Keep baggage small and prohibit secrets/PII. Validate header byte limits.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 05 — Instrument a synthetic producer

**Objective and procedure:** Use OpenTelemetry SDK or Kafka client instrumentation compatible with the application runtime. Create producer send span with topic and messaging operation attributes, safe record ID, and callback status; avoid raw key/value.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 06 — Instrument a synthetic consumer

**Objective and procedure:** Extract Kafka headers, create consumer process span with linked/parent context according to chosen semantic convention, commit after processing, record errors and event age. Document batch/poll semantics.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 07 — Choose span parent versus link strategy

**Objective and procedure:** Test one-to-one messages, fan-out and batch processing. Use span links where multiple incoming contexts or async relationships make a single parent misleading.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 08 — Deploy an OTLP collector on Kubernetes

**Objective and procedure:** Review and deploy an approved pinned OpenTelemetry Collector image, ConfigMap, ServiceAccount, resource limits, liveness/readiness and NetworkPolicy. Validate version-specific config with collector dry-run.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 09 — Configure secure OTLP receiver and exporter

**Objective and procedure:** Enable TLS/mTLS where required, certificate verification, secret-mounted credentials, exporter timeout, bounded queues, retries and sink allowlist. Do not expose unauthenticated collector receivers externally.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 10 — Apply resource attributes and Kubernetes enrichment

**Objective and procedure:** Add cluster, namespace, workload, service name/version and bounded broker/client identifiers. Avoid full message payload, raw record keys, user IDs and high-cardinality topic-partition offsets as searchable dimensions.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 11 — Validate trace sampling and tail sampling

**Objective and procedure:** Compare parent-based head sampling, collector tail sampling and error/slow-path retention. Document incomplete traces under sampling, memory limits and collector outages.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 12 — Correlate trace IDs with structured logs

**Objective and procedure:** Emit trace_id/span_id in synthetic application logs and verify centralized log query with the same trace. Kafka broker logs may not carry application trace IDs; use time, topic and metrics for broker correlation.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 13 — Correlate spans with Kafka metrics

**Objective and procedure:** Compare producer callback duration, broker request metrics, consumer processing and event age. Do not label broker metrics with per-message trace IDs.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 14 — Measure queue dwell and event age

**Objective and procedure:** Use producer creation time, broker append timestamp semantics (CreateTime vs LogAppendTime) and consumer process start with clock-skew caveats. Distinguish queue wait from processing duration.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 15 — Trace retry, duplicate and replay semantics

**Objective and procedure:** Inject synthetic producer retry/consumer restart, record trace links and event ID reconciliation, distinguish retry attempts from distinct business events and preserve idempotent sink behavior.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 16 — Test consumer group rebalance correlation

**Objective and procedure:** Scale only synthetic consumer Deployment within partition bounds, capture rebalances, trace gaps and lag trends; do not modify shared groups or reset offsets.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 17 — Build service dependency and critical path views

**Objective and procedure:** Use a trace backend approved by the organization to visualize ingress, Kafka publish, consume, downstream API and sink; distinguish asynchronous links from synchronous critical path.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 18 — Validate cardinality, cost and privacy

**Objective and procedure:** Measure spans/s, sampling rate, exporter queue size, dropped spans, trace retention, tenant isolation and attribute cardinality. Perform secret/PII scanning on synthetic data.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 19 — Test collector outage and recovery safely

**Objective and procedure:** Block only test-only OTLP destination or use approved collector test sink, measure bounded queue/drops, verify application does not fail when tracing is unavailable, restore and reconcile synthetic traces.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

### Lab 20 — Execute verification and assessor handoff

**Objective and procedure:** Run verify-ch39.sh, capture client/collector config hashes, redacted trace screenshots, context propagation test, alert evidence, failure recovery, GitOps rollback and independent review.

**Execution evidence:** Record context, exact Kafka/Strimzi/OpenTelemetry/SDK versions, approved manifests, expected span topology, observed trace IDs, metrics and log correlation, error cases, security review and rollback. Mark Pending until run. For instrumentation tests use a synthetic KafkaTopic with RF3/minISR2, isolated consumer group and bounded message volume. A successful exporter connection alone does not prove propagation.

## 6. Trace context propagation pseudocode

The following is **language-neutral pseudocode**, not a copy-paste Kafka SDK example. Use the version-specific OpenTelemetry propagator API for your client language:

```text
producer:
  span = tracer.start_span("kafka publish")
  headers = new KafkaHeaders()
  W3CPropagator.inject(span.context, headers)
  producer.send(topic, synthetic_key, synthetic_payload, headers,
                callback=(metadata, error) => record_result(error))
  span.end_after_callback()

consumer:
  record = poll()
  extracted = W3CPropagator.extract(record.headers)
  span = tracer.start_span("kafka process", context=extracted)
  try:
    process_to_idempotent_sink(record)
    commit_offset_after_success()
    span.set_status(OK)
  catch error:
    span.record_exception(error)
    apply_reviewed_retry_or_dlq_policy()
  finally:
    span.end()
```

**Caveat:** Actual producer span lifetime, callback threading, consumer group commits and tracing instrumentation depend on the client API. For batch/fan-out processing, span links may be preferable to parent-child relationships. Validate SDK behavior and exception handling in a real synthetic test.

## 7. OpenTelemetry Collector pipeline design sketch

This is an **illustrative configuration shape**, not a deployable release-pinned manifest:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
  batch: {}
exporters:
  otlp:
    endpoint: trace-backend.monitoring.svc:4317
    tls:
      insecure: false
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
```

**Do not deploy unchanged:** configure server TLS/auth for the receiver, trust roots/client identity for exporter, actual backend address, approved network policies, memory budget, retry and bounded queue, secret mounts, and compatible collector version. Listening on all interfaces without access controls is not acceptable for production.

## 8. Read-only Kubernetes verification script

Save as `verify-ch39.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/10] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Topic inventory'
kubectl -n "$NS" get kafkatopic -o wide
echo '[5/10] Client Pods'
kubectl -n "$NS" get pods -o wide
echo '[6/10] OTel Collector candidates (optional)'
kubectl get deploy,daemonset -A -l app.kubernetes.io/name=opentelemetry-collector -o wide || true
echo '[7/10] OTLP Services (inventory)'
kubectl get svc -A -l app.kubernetes.io/name=opentelemetry-collector -o wide || true
echo '[8/10] NetworkPolicy inventory'
kubectl -n "$NS" get networkpolicy
echo '[9/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo '[10/10] Kafka PVC inventory'
kubectl -n "$NS" get pvc -o wide
echo 'PASS: read-only tracing platform inventory.'
echo 'NOT PROVEN: W3C propagation, collector security, span completeness, sampling or end-to-end trace acceptance.'
```

Run `chmod +x verify-ch39.sh && ./verify-ch39.sh | tee evidence-ch39/preflight.txt`. The internal 9092 CLI is a disposable-lab convention only. Production-like client tests must use approved TLS/SASL and ACLs.

## 9. Trace acceptance and measurement matrix

| Test | Expected result | Evidence |
|---|---|---|
| Producer injects W3C context | traceparent in synthetic Kafka headers | redacted header inspection |
| Consumer extracts context | processing span linked/parented correctly | trace topology |
| Producer callback error | error status and exception captured | callback + span |
| Fan-out/batch | multiple upstream links handled correctly | span links |
| Replay/duplicate | event ID reconciliation without side-effect duplication | sink ledger |
| Queue dwell | computed with timestamp semantics and skew caveat | timeline |
| Collector outage | bounded queue, app remains healthy, drops accounted | collector metrics |
| TLS/auth | unauthorized export denied, authorized export succeeds | security evidence |
| Privacy | no raw payload/credentials/PII in spans | redaction review |
| SLO correlation | spans, metrics and logs share time window | Grafana/log query |

## 10. Twelve troubleshooting scenarios

### Scenario 1 — Missing trace context after Kafka publish

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 2 — Consumer spans appear as unrelated root traces

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 3 — Batch consumer has incorrect single parent

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 4 — Baggage leaks sensitive customer fields

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 5 — Trace IDs in broker logs expected but absent

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 6 — Collector receiver cannot authenticate clients

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 7 — Collector exporter queue fills under outage

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 8 — Tail sampling drops slow/error traces

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 9 — Producer retries create confusing duplicate spans

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 10 — Consumer rebalance breaks trace continuity

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 11 — Clock skew yields negative queue dwell time

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

### Scenario 12 — Tracing overhead increases producer p99

**Detect:** Compare expected synthetic event IDs, producer callback logs, Kafka headers, consumer span topology, collector queue/dropped-span metrics and trace backend search. **Diagnose:** Inspect W3C propagation, instrumentation versions, sampler decisions, batch/fan-out links, TLS, resource limits, clock skew and redaction. **Recover:** Apply a minimal approved application/collector change; do not weaken Kafka durability, ACLs or TLS. **Verify:** Re-run synthetic test and record before/after traces, missing spans and operational impact.

## 11. Eight production SRE runbooks

### Runbook A — Trace context propagation failure

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook B — Producer publish latency trace investigation

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook C — Consumer processing and queue-age investigation

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook D — OpenTelemetry Collector outage

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook E — Trace backend TLS and authorization failure

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook F — Sensitive attribute exposure and containment

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook G — Sampling/cost regression

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

### Runbook H — End-to-end trace incident forensic handoff

1. Identify incident scope, synthetic trace/event IDs, owner and time window.
2. Confirm Kafka/KRaft/ISR and Kubernetes health independently.
3. Inspect producer/consumer instrumentation, W3C headers, collector and backend.
4. Correlate traces with redacted application logs, Kafka metrics and event ledger.
5. Quantify missing spans, sampling, replay, queue dwell and error rate.
6. Apply approved remediation or GitOps rollback and verify SLO/security gates.
7. Preserve sanitized evidence, decisions and independent reviewer signoff.

## 12. Evidence package

```text
evidence-ch39/
  approval-and-scope.md
  preflight.txt
  version-matrix.md
  tracing-topology.md
  kafka-header-propagation.md
  producer-spans.json
  consumer-spans.json
  fanout-batch-links.md
  collector-deployment-review.yaml
  collector-security-review.md
  sampling-policy.md
  log-trace-correlation.md
  metric-trace-correlation.md
  event-age-analysis.csv
  retry-replay-traces.md
  rebalance-trace-timeline.md
  service-dependency-graph.md
  privacy-cardinality-budget.md
  collector-outage-drill.md
  acceptance-matrix.md
  independent-signoff.md
```

All evidence must record actual SDK/collector versions, source and destination, UTC time range, redaction status, expected/observed outcome and reviewer. Never fabricate a live trace or claim an unexecuted test passed.

## 13. 100-point enterprise assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, approval, trace SLOs and Kafka health | 10 | Yes |
| Producer W3C context injection and callbacks | 15 | Yes |
| Consumer context extraction and batch/fan-out semantics | 15 | Yes |
| Secure Kubernetes OTel Collector deployment | 15 | Yes |
| Logs, metrics and trace correlation | 10 | Yes |
| Queue dwell, event age and timestamp correctness | 10 | Yes |
| Retries, replay and rebalance tracing | 10 | Yes |
| Sampling, privacy, cardinality and cost controls | 10 | Yes |
| Outage drill, runbooks and independent signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** leaked credentials/PII, disabled TLS validation, unapproved production changes, missing context propagation, unbounded collector memory, fabricated traces or missing independent security review.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients, temporary collector test resources and trace data as allowed by retention policy. Do not delete Kafka PVCs, operator-managed Secrets, shared trace backends or production consumer offsets.

**References:** [OpenTelemetry messaging semantic conventions](https://opentelemetry.io/docs/specs/semconv/messaging/), [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/), [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/), [W3C Trace Context](https://www.w3.org/TR/trace-context/), [Strimzi documentation](https://strimzi.io/documentation/), [Apache Kafka documentation](https://kafka.apache.org/documentation/).

**Next:** Chapter 040 — Kafka Observability, Alerting, SLO Dashboards and Incident Detection SRE Capstone.

---

**Verification boundary:** Publication confirms only the GitHub document. Live distributed tracing, OpenTelemetry security, incident drills and independent acceptance remain Pending.
