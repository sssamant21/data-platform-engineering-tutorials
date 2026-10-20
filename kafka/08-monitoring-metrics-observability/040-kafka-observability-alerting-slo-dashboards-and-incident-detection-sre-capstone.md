# Chapter 040 — Kafka Observability, Alerting, SLO Dashboards and Incident Detection SRE Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 08 — Monitoring, Metrics and Observability (5/5, final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–039, especially Chapters 036–039  
**Status:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety and acceptance boundary:** This is a reference SRE capstone, not a claim that Kafka monitoring or alerting is production-ready. Run only in an approved disposable Kubernetes cluster using synthetic clients and safe test alerts. Never disable TLS/ACLs, expose JMX, reset production offsets, stop Kafka brokers/controllers for alert testing, delete PVCs or send customer payloads to logs/traces. A dashboard that displays green without validated metrics is not an accepted system.

## 1. Mission

Integrate Chapters 036–039 into a reproducible Kafka observability and incident-detection acceptance exercise. The final deliverable is a monitored Kubernetes/Strimzi KRaft cluster with validated broker, controller, producer, consumer, operator, node and storage signals; reviewed PromQL; Grafana SLO dashboards; safe alerting; log/trace correlation; incident runbooks; evidence; and independent acceptance.

## 2. Outcomes

- Define Kafka reliability SLIs, SLOs, error budgets, and actionable alert thresholds.
- Prove Prometheus discovery, metric semantics, expected-target counts and missing-series behavior.
- Build broker/KRaft, producer, consumer, JVM, Kubernetes and PVC dashboards.
- Correlate Kafka client errors and event age with metrics, logs, traces and Kubernetes Events.
- Configure Alertmanager routing, grouping, escalation, ownership and safe tests.
- Detect failures in the monitoring pipeline itself.
- Run a synthetic client-only incident and produce a defensible incident timeline.
- Demonstrate secure, reviewed GitOps rollback and a 100-point enterprise SRE assessment.

## 3. Reference architecture

```text
Kubernetes + Strimzi Kafka KRaft
  +-- Kafka brokers/controllers -> JMX exporter
  +-- Strimzi operator -> reconciliation metrics
  +-- Producer/consumer Pods -> client metrics + OTLP spans
  +-- kube-state-metrics/cAdvisor/node + CSI/provider -> infra metrics
  +-- Container logs -> approved collector -> central logs
  |
  v
Prometheus / recording rules / expected-target inventory
  +-- Grafana SLO dashboards
  +-- Alertmanager -> owned on-call route + escalation
  +-- independent Kafka CLI / application event ledger validation
  |
  v
Incident command / error-budget review / SRE acceptance
```

A Kafka broker does not automatically propagate application trace context. Producers inject W3C headers and consumers extract them; the monitoring stack correlates by time, bounded labels, and synthetic event IDs in the application ledger. Kubernetes API audit events require separate control-plane audit support.

## 4. Reliability SLIs and example SLOs

| SLI | Numerator / denominator or measurement | Example lab objective | Caveat |
|---|---|---|---|
| Producer acknowledged delivery | successfully acknowledged / attempted synthetic records | ≥99.9% | not end-to-end processing |
| Producer p99 acknowledgment | client callback duration | ≤250 ms | depends on payload/load |
| End-to-end processed delivery | durably processed unique IDs / accepted IDs | 100% after recovery | duplicates handled by idempotent sink |
| Consumer event age p99 | time from event creation to durable processing | ≤2 s steady state | requires clock accuracy |
| Consumer recovery | time to drain synthetic backlog | ≤10 min | must use measured drain rate |
| Kafka availability | healthy Kafka Ready + quorum + ISR gates | no safety-gate violation | operator Ready alone insufficient |
| Telemetry coverage | expected critical targets and signals / required inventory | 100% critical coverage | absent data cannot equal zero |
| Critical alert delivery | delivered and acknowledged synthetic test notifications | 100% tested routes | synthetic tests not real failures |
| Monitoring data freshness | time since successful scrape/event ingest | within approved freshness SLO | account for scrape intervals |

These are **illustrative lab targets**, not production guarantees or measured results. Define real SLOs and exclusions with the service owner before execution. For a request-based SLI, error budget is `(1 - SLO target) × eligible requests` over the declared window; do not treat a 30-minute synthetic drill as a full monthly SLO evaluation.

## 5. Alert acceptance matrix

| Alert | Signal | Priority | Owner/runbook |
|---|---|---|---|
| KRaftQuorumDegraded | validated quorum/controller signal | Critical | Kafka SRE |
| UnderMinISR | sustained under-minISR partitions | Critical | Kafka SRE |
| KafkaNotReady | Kafka CR + Pod health | Critical | Kafka SRE |
| BrokerTargetMissing | expected broker inventory vs actual targets | High | Observability SRE |
| ProducerDeliveryErrors | callback error ratio and error budget | High | App/Kafka SRE |
| ProducerLatencySLO | verified client p99 | High | App/Kafka SRE |
| ConsumerEventAgeSLO | measured event-age percentile | High | App SRE |
| PVCStoragePressure | actual used bytes/IOPS/latency | High | Platform/DBRE |
| StrimziReconcileFailure | operator errors and CR status | High | Platform |
| OTelCollectorDrops | dropped spans or saturated queues | Medium | Observability SRE |
| AlertRoutingFailure | failed synthetic alert delivery | Critical | Observability on-call |

Thresholds, `for` windows, labels and exact PromQL must be derived from actual exporter series and approved SLOs. A generic `up == 0` rule cannot detect a broker target that has vanished entirely.

## 6. Twenty Kubernetes-first labs

### Lab 01 — Approve capstone, SLOs and abort thresholds

**Objective and procedure:** Record namespace/context, cluster and monitoring owners, change ticket, synthetic data policy, incident commander, safe test budget and independent assessor. Define what is explicitly out of scope.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 02 — Inventory Strimzi Kafka and KRaft health

**Objective and procedure:** Verify Kafka CR Ready, broker/controller KafkaNodePools, Pods, PVCs, services and KRaft metadata quorum; preserve baseline before monitoring tests.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 03 — Validate metric coverage and target discovery

**Objective and procedure:** Enumerate Prometheus broker/controller/operator, producer/consumer, kube-state/cAdvisor and PVC targets. Compare expected counts to actual; missing target must not be treated as healthy zero.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 04 — Validate exporter metrics and PromQL semantics

**Objective and procedure:** Check installed Kafka/Strimzi exporter mapping, actual metric names, counters/gauges/histograms, label joins, rate/reset behavior and p99 aggregation correctness.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 05 — Build golden-signal Kafka overview

**Objective and procedure:** Create reviewed Grafana panels for throughput, producer/consumer errors, request latency, saturation, Kafka Ready, under-minISR and KRaft quorum.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 06 — Build KRaft and replication reliability dashboards

**Objective and procedure:** Compare metadata quorum CLI with controller metrics, ISR/minISR, offline partitions and replica catch-up. Include per-broker detail and missing-series indicators.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 07 — Build producer SLI and latency dashboards

**Objective and procedure:** Capture synthetic producer acknowledged records, retries, errors, p95/p99 callback latency and offered/achieved rate. Do not equate broker acks with business processing.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 08 — Build consumer SLI and event-age dashboards

**Objective and procedure:** Correlate committed offsets, consumer group assignments, processed events, event age, rebalance rate and lag drain time with synthetic application ledger.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 09 — Build Kubernetes and storage saturation dashboards

**Objective and procedure:** Include CPU throttling, OOM/restarts, node pressure, broker PVC free bytes, IOPS/latency and collector/Prometheus capacity. Separate allocated PVC size from used filesystem.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 10 — Build Strimzi operator reconciliation dashboard

**Objective and procedure:** Observe operator reconciliation failures, Kafka CR observed generation, rollouts and NodePool readiness. Version-check metric mappings.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 11 — Integrate centralized logs and incident timeline

**Objective and procedure:** Validate broker/controller/operator/client logs, multiline parsing, UTC timestamps, redaction, log loss accounting and search correlation.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 12 — Integrate OpenTelemetry end-to-end traces

**Objective and procedure:** Verify W3C context in synthetic Kafka headers, producer and consumer spans, sampling policy, log/trace correlation and collector queue/drop metrics.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 13 — Define and review SLIs and SLOs

**Objective and procedure:** Write availability, acknowledged delivery, end-to-end processing, event-age and recovery SLIs with data sources, denominators, exclusions and error budgets. Set business-approved targets.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 14 — Implement Prometheus recording and alert rules

**Objective and procedure:** Build rules for Kafka Ready, KRaft quorum, under-minISR, under-replication, client errors, event-age breaches, PVC saturation and telemetry target disappearance. Validate with promtool.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 15 — Configure Alertmanager routing and escalation

**Objective and procedure:** Map severity to on-call owner, grouping/inhibition, runbook links, escalation, silence policy and delivery test. No alert should route to a nonexistent owner.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 16 — Run safe synthetic alert injection

**Objective and procedure:** Use test-only metric/PrometheusRule or a synthetic scrape target; validate pending/firing/resolved states, paging and acknowledgments without stopping Kafka brokers.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 17 — Run synthetic client incident drill

**Objective and procedure:** Cause an approved client-only timeout/restart, observe producer errors, consumer lag/event age, logs, traces and alerts, and confirm recovery with no data-integrity failure.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 18 — Test monitoring pipeline failure

**Objective and procedure:** Interrupt only an approved test collector/sink or synthetic scrape target; measure missing-series alert, buffer/drops, Grafana No Data and restoration. Avoid impacting shared observability.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 19 — Perform SLO/error-budget and incident review

**Objective and procedure:** Calculate error-budget consumption from measured synthetic data, document alert noise/false positives, incident timeline, response time, data integrity and remediation.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

### Lab 20 — Execute final acceptance and rollback

**Objective and procedure:** Run verify-ch40.sh, reconcile dashboards with independent Kafka CLI and client ledger, review security/cardinality/retention, demonstrate GitOps rollback and sign 100-point rubric.

**Validation and evidence:** Capture approved cluster context, versions, exact query/manifest, expected and observed results, timestamps, redacted screenshot or log, abort conditions, GitOps rollback and independent assessor status. A lab is **Pending** until actually executed. Critical alerts must be tested with synthetic signals, not broker disruption.

## 7. Practical Kubernetes and KRaft preflight

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch40
kubectl config current-context | tee evidence-ch40/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch40/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
kubectl -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch40/quorum.txt
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
kubectl get crd servicemonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com
```

The final CRD command requires Prometheus Operator and may fail if monitoring is not installed; record that as **Blocked/Pending**, not Pass. Internal plaintext 9092 is only a disposable-lab CLI convention; secure acceptance uses TLS/SASL and least-privilege ACLs.

## 8. PromQL and alerting correctness patterns

```promql
# Scrape health: inspect actual job labels
up{job=~".*kafka.*"}

# Detect all matching series absent; not one missing broker among many
absent(up{job="kafka-broker-metrics"})

# Example ONLY: replace with real Kafka exporter counter
sum by (cluster) (rate(kafka_server_brokertopicmetrics_bytesin_total[5m]))

# Example ONLY: requires real histogram bucket series
histogram_quantile(
  0.99,
  sum by (cluster, le) (rate(kafka_request_duration_seconds_bucket[5m]))
)
```

Never use `rate` on a gauge or average individual p99 gauges. Compare expected broker count to discovered targets using a reviewed inventory metric/recording rule. Use `promtool check rules` on reviewed rules and test alert routing through a synthetic test series or test-only rule.

## 9. Synthetic alert test procedure

1. Approve test window and confirm dedicated routing label (for example `environment="lab"`) and test recipient.
2. Create a **test-only** metric or reviewed temporary PrometheusRule whose expression is guaranteed to evaluate true in the test environment.
3. Observe Pending, Firing and Resolved transitions in Prometheus/Alertmanager.
4. Verify receiver, acknowledgment, escalation and runbook URL without paging unrelated production staff.
5. Remove the test rule through GitOps and verify no stale firing alerts.
6. Attach notification receipts, timestamps, alert labels and security review.

Never simulate a quorum or under-minISR failure by killing Kafka Pods for this exercise. A synthetic alert test proves routing, not real failure detection; metric-to-alert correctness must be reviewed separately.

## 10. Read-only automated verification script

Save as `verify-ch40.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/10] Context'
kubectl config current-context
echo '[2/10] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/10] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Kafka Pods'
kubectl -n "$NS" get pods -o wide
echo '[5/10] PVC inventory'
kubectl -n "$NS" get pvc -o wide
echo '[6/10] JMX exporter configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[7/10] Prometheus Operator CRDs'
for crd in servicemonitors.monitoring.coreos.com podmonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then echo "FOUND: $crd"; else echo "PENDING: $crd"; fi
done
echo '[8/10] Prometheus/Grafana inventory'
kubectl get pods -A -l app.kubernetes.io/name=prometheus -o wide || true
kubectl get pods -A -l app.kubernetes.io/name=grafana -o wide || true
echo '[9/10] NetworkPolicy inventory'
kubectl -n "$NS" get networkpolicy
echo '[10/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka observability preflight.'
echo 'NOT PROVEN: dashboards, alert routing, SLOs, tracing, logging, security or capstone acceptance.'
```

Run `chmod +x verify-ch40.sh && ./verify-ch40.sh | tee evidence-ch40/preflight.txt`. This script intentionally does not claim live SLO compliance or alert testing.

## 11. Twelve troubleshooting scenarios

### Scenario 1 — Kafka Ready but quorum metrics absent

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 2 — Under-minISR alert not delivered

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 3 — Grafana green due to missing data converted to zero

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 4 — Producer p99 calculated by averaging gauges

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 5 — Consumer lag improves while event age worsens

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 6 — Synthetic incident fails to trigger alert

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 7 — Alert storm from repeated Pod restarts

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 8 — Prometheus target DOWN after ServiceMonitor selector drift

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 9 — Collector drops spans and logs under load

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 10 — PVC latency saturates without storage alert

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 11 — Dashboard breaks after Strimzi exporter upgrade

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

### Scenario 12 — On-call route silently discards critical alert

**Detect:** Compare Grafana with Prometheus targets, raw exporter series, Kafka CLI and synthetic client ledger. **Diagnose:** Check metric type, labels, version-specific mapping, freshness, exporter/scrape failures, Alertmanager route, receiver status and recent GitOps changes. **Recover:** Apply approved monitoring or application correction; never hide genuine Kafka degradation. **Verify:** Repeat synthetic signal and document expected/observed alert state, root cause, security and rollback.

## 12. Eight production SRE runbooks

### Runbook A — Kafka/KRaft availability and quorum

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook B — Under-minISR and replication incident

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook C — Producer latency/error SLO breach

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook D — Consumer event-age and backlog incident

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook E — Kubernetes CPU/GC/PVC saturation

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook F — Telemetry target and collector outage

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook G — Alertmanager routing failure and false positives

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

### Runbook H — Capstone incident command and independent acceptance

1. Confirm incident scope, owner, severity, SLO and time window.
2. Validate Kafka/KRaft/ISR health independently of dashboards.
3. Inspect Prometheus targets, query correctness, alert state and routing.
4. Correlate producer/consumer metrics with logs, traces, Kubernetes and PVC signals.
5. Preserve redacted incident timeline, affected events and error-budget estimate.
6. Apply approved remediation or GitOps rollback, preserving durability and TLS/ACLs.
7. Verify recovery, alert resolution, data integrity and independent review.

## 13. Evidence package

```text
evidence-ch40/
  approval-and-scope.md
  context.txt
  inventory.txt
  quorum.txt
  version-and-exporter-matrix.md
  expected-target-inventory.csv
  promql-validation.md
  grafana-kraft-broker.json
  grafana-producer-consumer-slo.json
  grafana-kubernetes-storage.json
  strimzi-reconciliation.md
  logging-correlation.md
  tracing-correlation.md
  sli-slo-definitions.md
  recording-rules.yaml
  promtool-check.txt
  alertmanager-routing.md
  synthetic-alert-test.md
  client-incident-drill.md
  monitoring-outage-drill.md
  error-budget-review.md
  preflight.txt
  security-review.md
  gitops-rollback.md
  final-incident-report.md
  assessor-signoff.md
```

Record software versions, exact metric/label mapping, time window, expected/observed signal, target count, alert recipient, owner, synthetic event ledger, rollback and assessor. Missing evidence is Pending, not Pass.

## 14. 100-point enterprise observability acceptance

| Domain | Points | Critical |
|---|---:|---|
| Scope, approval, abort criteria and version inventory | 10 | Yes |
| Broker/KRaft/ISR/Strimzi metric correctness | 15 | Yes |
| Producer/consumer SLI and event-age accuracy | 15 | Yes |
| Kubernetes/JVM/PVC saturation monitoring | 10 | Yes |
| PromQL, Grafana and missing-series validation | 10 | Yes |
| Recording rules and Alertmanager routing | 15 | Yes |
| Safe synthetic alert and client incident drills | 10 | Yes |
| Logs, OpenTelemetry and incident correlation | 5 | Yes |
| Security, privacy, cardinality and retention | 5 | Yes |
| Runbooks, rollback and independent signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates passed with live evidence. **Automatic Fail:** unauthorized production disruption, exposed credentials or JMX, disabled TLS validation, false green missing-series dashboards, untested critical paging, missed KRaft/under-minISR signals, fabricated results or missing independent review.

**Publication is not capstone acceptance.** All live labs, alert drills, SLO tests and independent security review remain Pending until executed.

## 15. Cleanup, references and next part

Remove only chapter-owned synthetic alert rules, client test Pods and temporary monitoring resources through approved GitOps change. Retain sanitized evidence; do not delete broker PVCs, shared Prometheus TSDB, production offsets or operator-managed Secrets.

**References:** [Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Prometheus alerting](https://prometheus.io/docs/alerting/latest/overview/), [Prometheus recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/), [Grafana](https://grafana.com/docs/grafana/latest/), [OpenTelemetry](https://opentelemetry.io/docs/), [Kubernetes monitoring](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/).

**Part 08 — Monitoring, Metrics and Observability is complete (Chapters 036–040).**

**Next:** Chapter 041 — Kafka Reliability Engineering, SLIs, SLOs, Error Budgets and Kubernetes Service Ownership, beginning Part 09 — SRE, SLIs, SLOs and Reliability.

---

**Verification boundary:** Published Markdown only. Live Kafka observability, alert delivery, SLO attainment and independent security/operational acceptance remain Pending.
