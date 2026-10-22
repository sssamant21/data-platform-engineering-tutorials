# Chapter 116 — Google Cloud Kafka Observability, Cloud Monitoring, Prometheus and SLOs

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (6/10)  
**Primary platform:** GKE + Strimzi Kafka KRaft  
**Managed alternative:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–115, isolated GKE cluster, approved Kafka backend and metrics access  
**Publication:** Published · **Live labs:** Pending · **Independent review:** Pending · **Runtime certification:** Not claimed

> **Safety:** Use synthetic event data only. Do not publish Kafka payloads, patient identifiers, tokens or certificate material as metric labels. Verify metrics against actual exporter versions and managed-service documentation; metrics and alert APIs evolve. Use isolated environments for alert and failure testing.

## 1. Mission and learning outcomes

Design end-to-end observability for Kafka on Google Cloud, from Kubernetes infrastructure and Strimzi reconciliation through KRaft quorum, brokers, topics, producers, consumers, DLQs and business-event correctness. Combine Prometheus/Grafana with Cloud Monitoring where appropriate, define measurable SLOs, test alerts and produce incident evidence.

**Deliverables:** telemetry architecture, metrics inventory, dashboards, alert rules, SLO definitions, error-budget policy, 20 hands-on labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Reference architecture

```text
GKE Strimzi KRaft
  Kafka broker / controller JMX exporter
  Strimzi operator and Kafka exporter (where configured)
  kube-state-metrics / node / PVC / GKE metrics
          |
       Prometheus → alert rules → Alertmanager/on-call
          |
        Grafana
          |
GKE synthetic producer + consumer → application metrics
  accepted IDs / sink effects / lag / DLQ / latency
          |
     Cloud Monitoring dashboards and alert policies

Managed Kafka alternative:
  supported Google Cloud service metrics + GKE client metrics
  (do not assume broker JMX or Strimzi operator access)
```

A monitoring system that reports broker availability but cannot detect missing acknowledged event IDs or an unhealthy downstream sink is insufficient for a production data pipeline.

## 3. Metrics ownership and cardinality

| Layer | Signals | Owner |
|---|---|---|
| GKE | Pod restarts, CPU throttling, node readiness, PVC health | Platform/SRE |
| Strimzi | Operator reconciliation, Kafka CR conditions | Kafka platform |
| KRaft | Controller quorum health, controller elections | Kafka platform |
| Broker | Offline partitions, ISR, request latency, network, JVM | Kafka platform |
| Producer | Accepted/error rate, retries, latency, timeout | Application |
| Consumer | Lag, rebalance, processing latency, errors | Application |
| Pipeline | Sink effects, missing IDs, DLQ, replay progress | Data owner |
| Managed Kafka | Service-exposed health, quotas, throughput | Shared ownership |

Never label metrics by `event_id`, patient ID, phone number, email or unbounded key values. Keep event-level reconciliation in an access-controlled evidence store, not a high-cardinality time series.

## 4. Kubernetes and metrics preflight

```powershell
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool -A
kubectl get pods -n kafka -o wide
kubectl get svc -n kafka
kubectl get servicemonitor,podmonitor -A
kubectl get pvc -n kafka
gcloud config get-value project
```

`ServiceMonitor` and `PodMonitor` require the corresponding Prometheus Operator CRDs. If absent, choose a supported scraping mechanism; do not infer Kafka is unhealthy. Inspect the deployed Strimzi version and the exact JMX exporter configuration before writing dashboards.

## 5. Enable and validate Strimzi metrics

Configure the Strimzi-supported `metricsConfig` using a reviewed ConfigMap and compatible exporter configuration for the installed release. Separate broker and controller metrics where roles differ. Validate exporter availability through actual service/Pod metadata and Prometheus target health. Never assume a JMX metric exists without inspecting the exported `/metrics` endpoint.

```powershell
kubectl get configmap -n kafka
kubectl describe kafka gke-kafka -n kafka
kubectl get pods -n kafka -o wide
kubectl get endpointslice -n kafka
```

Capture exporter version, metric names, label dimensions, scrape interval, retention and failure behavior. Strimzi operator health is a separate signal from Kafka broker health.

## 6. Prometheus recording rules and alerts

The following are **illustrative** PromQL patterns. Confirm the actual metric name and labels in your exporter before enabling alerts.

```promql
# Example: process-level scrape health
up{namespace="kafka"} == 0

# Example: Kafka partition health (name may vary by exporter)
sum(kafka_server_replicamanager_underreplicatedpartitions) > 0

# Example: consumer lag when Kafka exporter supplies the series
sum by (consumergroup) (kafka_consumergroup_lag) > 10000
```

A zero-valued result is not equivalent to a missing metric. Alert separately on `absent()`, stale telemetry and scrape failure. Thresholds must be calibrated to topic volume, processing latency, retention and error budgets. Alert on sustained impact, not every transient rebalance.

## 7. Cloud Monitoring integration

Inventory the metrics actually exposed by GKE, Google Cloud Managed Service for Apache Kafka and your telemetry pipeline. Decide whether to use Google Managed Service for Prometheus, self-managed Prometheus or a supported collector integration. Review IAM, metrics ingestion, retention, cardinality, dashboard access and alert routing. Validate alert policies in a test notification channel before paging production on-call.

Managed Kafka may not expose broker JMX, controller metrics or every Kafka internal metric. Supplement provider metrics with client telemetry, synthetic probes, consumer lag and event correctness evidence. Unknown metrics must be documented as observability gaps.

## 8. SLI and SLO definitions

Define service-level indicators using the correct numerator, denominator, time window and source:

- **Producer acceptance SLI:** successful acknowledged send operations / attempted send operations, excluding only explicitly defined invalid requests.
- **Pipeline delivery correctness:** accepted unique event IDs with a durable sink effect or approved durable quarantine within the objective window / accepted unique event IDs eligible for processing.
- **End-to-end latency SLI:** fraction of eligible accepted events processed within the target latency.
- **Consumer freshness:** fraction of observation windows where oldest unprocessed event age stays below target.
- **Recovery:** measured RTO and RPO during approved fault/restore drills.

Example **lab-only** objective: ≥99.9% producer acceptance over 30 days, ≥99.95% eligible event delivery within 5 minutes, and p99 processing latency below 5 seconds at the declared synthetic load. Do not claim these are measured.

## 9. Error-budget calculation

For an availability SLO of 99.9% over 30 days, the permitted error fraction is 0.1%. That corresponds to approximately 43.2 minutes of equivalent full unavailability, **only when time-based availability is the selected SLI**. For request/event-based SLIs, calculate budget in eligible operations, not downtime minutes.

Use multiwindow burn-rate alerting where appropriate, with a clear denominator, minimum traffic safeguards and explicit missing-data handling. Document release freeze and escalation policy for exhausted budgets.

## 10. Event correctness and synthetic probes

Publish bounded synthetic records with deterministic `event_id`, `aggregate_id` and payload hash. Record acknowledged IDs independently. Consumer writes idempotent durable effects and only then commits offsets. Compare accepted IDs, unique sink effects, DLQ IDs and unresolved/missing IDs. Alert on unresolved accepted IDs after the defined processing deadline. A dashboard showing zero consumer lag does not guarantee correctness.

## 11. Hands-on labs (20)

Every lab records prerequisites, version, exact commands/queries, expected and observed results, dashboard screenshots or metric exports, rollback and PASS/FAIL. Publication does not imply lab execution.

| # | Lab | Required evidence |
|---|---|---|
| 01 | Verify GKE observability access | Timestamped query, observed value, alert result and rollback |
| 02 | Inventory Strimzi metrics endpoints | Timestamped query, observed value, alert result and rollback |
| 03 | Validate Kafka JMX exporter configuration | Timestamped query, observed value, alert result and rollback |
| 04 | Inspect Prometheus targets and scrape health | Timestamped query, observed value, alert result and rollback |
| 05 | Build broker availability dashboard | Timestamped query, observed value, alert result and rollback |
| 06 | Monitor KRaft controller quorum | Timestamped query, observed value, alert result and rollback |
| 07 | Monitor under-replicated/offline partitions | Timestamped query, observed value, alert result and rollback |
| 08 | Measure broker CPU, heap and GC | Timestamped query, observed value, alert result and rollback |
| 09 | Monitor PVC space and disk latency | Timestamped query, observed value, alert result and rollback |
| 10 | Instrument producer acknowledgement errors | Timestamped query, observed value, alert result and rollback |
| 11 | Instrument producer p95/p99 latency | Timestamped query, observed value, alert result and rollback |
| 12 | Instrument consumer processing latency | Timestamped query, observed value, alert result and rollback |
| 13 | Measure consumer lag and age | Timestamped query, observed value, alert result and rollback |
| 14 | Monitor DLQ and idempotent sink | Timestamped query, observed value, alert result and rollback |
| 15 | Build synthetic event reconciliation panel | Timestamped query, observed value, alert result and rollback |
| 16 | Discover managed Kafka service metrics | Timestamped query, observed value, alert result and rollback |
| 17 | Configure Cloud Monitoring alert policy | Timestamped query, observed value, alert result and rollback |
| 18 | Test alert routing and on-call notification | Timestamped query, observed value, alert result and rollback |
| 19 | Calculate rolling SLO and error budget | Timestamped query, observed value, alert result and rollback |
| 20 | Run incident tabletop and evidence review | Timestamped query, observed value, alert result and rollback |

### Lab execution protocol

1. Confirm project, GKE context, Kafka backend and telemetry permissions.
2. Record baseline metrics and synthetic event counts.
3. Enable one metric, dashboard or alert in the isolated environment.
4. Validate a positive signal and a negative/missing-data condition.
5. Test alert notification delivery and owner acknowledgement.
6. Correlate telemetry with synthetic event correctness and service impact.
7. Restore baseline and attach sanitized evidence.

## 12. Failure scenarios (12)

| # | Failure | Recovery requirement |
|---|---|---|
| 1 | Prometheus scrape target down | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 2 | Exporter configuration mismatch | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 3 | KRaft quorum metrics absent | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 4 | ISR alert not firing | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 5 | PVC disk saturation hidden | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 6 | Consumer lag metric stale | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 7 | Producer errors without alerts | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 8 | Cloud Monitoring IAM denial | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 9 | Managed metric unavailable | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 10 | High-cardinality label explosion | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 11 | Alert fatigue during rebalance | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |
| 12 | SLO calculation misclassifies missing data | Distinguish data-plane failure from telemetry failure; restore signal and verify pipeline correctness |

Every scenario includes trigger, expected alert, actual evidence, severity, blast radius, owner, rollback and preventive action. Never inject destructive faults into shared or production clusters.

## 13. SRE runbooks (8)

| # | Runbook | Standard workflow |
|---|---|---|
| 1 | Telemetry pipeline outage | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 2 | KRaft quorum alert | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 3 | Under-replicated partitions | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 4 | Disk and PVC saturation | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 5 | Producer error-budget burn | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 6 | Consumer lag incident | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 7 | Cloud Monitoring integration | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |
| 8 | Alert tuning and incident review | Confirm impact → correlate metrics/logs → approved remediation → verify SLI → RCA |

Runbooks require on-call ownership, escalation, safe diagnostic commands, rollback gates, customer communication and evidence retention.

## 14. 100-point observability acceptance

| Gate | Points |
|---|---:|
| GKE and Strimzi telemetry coverage | 15 |
| KRaft, broker, ISR and storage signals | 15 |
| Producer and consumer instrumentation | 15 |
| Synthetic event correctness monitoring | 15 |
| Prometheus/Grafana and Cloud Monitoring | 15 |
| Actionable alerts and notification test | 10 |
| SLO, error budget and burn-rate policy | 10 |
| Evidence and independent review | 5 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 with mandatory detection of producer failure, consumer backlog, critical Kafka unavailability, missing telemetry and unresolved accepted events. Independent review and actual alert tests are required before runtime certification.

## 15. Evidence manifest

```yaml
chapter: 116
environment: isolated-gke-kafka-observability
backend: REPLACE_STRIMZI_OR_MANAGED
gke_context: REPLACE
strimzi_version: REPLACE
prometheus_version: REPLACE
metrics_inventory: []
dashboard_links: []
alert_tests: []
producer_slo_observed: null
pipeline_delivery_slo_observed: null
consumer_freshness_slo_observed: null
missing_accepted_ids: null
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 117 — Google Cloud Kafka Performance, Capacity, Storage and FinOps.**
