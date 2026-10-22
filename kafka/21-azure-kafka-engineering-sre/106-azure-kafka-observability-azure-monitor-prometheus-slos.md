# Chapter 106 — Azure Kafka Observability, Azure Monitor, Prometheus and SLOs

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (6/10)  
**Primary platform:** Azure AKS, Strimzi-managed Apache Kafka in KRaft mode  
**Comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–105; Prometheus Operator, Grafana, Azure Monitor access  
**Publication:** Published after GitHub commit · **Live execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Run all configuration changes only in an isolated AKS lab after checking context, RBAC, namespace ownership and cost. Do not expose client credentials, sensitive record keys, personal data, SAS tokens or connection strings in telemetry. Metric names and Strimzi CRD fields vary by release: verify deployed versions and actual /metrics output before applying alerts.

## 1. Mission and outcomes

Build a Kubernetes-first observability stack for Kafka on AKS that correlates broker, KRaft, producer, consumer, Kubernetes, network and storage signals. Contrast Kafka-native monitoring with Azure Event Hubs platform metrics. Establish measurable SLIs, actionable multi-window SLO alerts, incident runbooks and evidence-based acceptance.

**Deliverables:** monitoring architecture, telemetry inventory, example manifests and queries, 20 isolated labs, 12 failure scenarios, 8 runbooks, 100-point assessment and independent review gate.

## 2. Architecture

```text
  AKS namespace kafka                      AKS namespace monitoring
  ┌─────────────────────┐                 ┌─────────────────────────┐
  │ Strimzi KRaft Kafka │─JMX exporter──►│ Prometheus Operator     │
  │ broker + controller │                 │ ServiceMonitor/PodMonitor│
  │ Producer / Consumer │─app metrics───►│ Prometheus + Alertmanager│
  │ Kafka exporter lag  │────────────────►│ Grafana dashboards      │
  └──────────┬──────────┘                 └────────────┬────────────┘
             │ Kubernetes events / logs                │ alerts
             ▼                                         ▼
       Azure Monitor / Log Analytics              On-call / incident
             ▲
  Azure Event Hubs namespace ─ Azure Monitor metrics / diagnostic logs
```

Kafka-on-AKS metrics and Event Hubs metrics are different telemetry surfaces. Event Hubs does not expose broker JMX, KRaft, ISR or Kafka disk internals. Use Azure Monitor's supported namespace/entity metrics and client instrumentation instead. Do not interpret missing broker metrics as zero incidents.

## 3. Safety preflight and discovery

```powershell
kubectl config current-context
kubectl get nodes
kubectl get kafka -A
kubectl get pods -n kafka -o wide
kubectl get svc -n kafka
kubectl get servicemonitor,podmonitor,prometheusrule -A
az account show --query '{subscription:id,tenant:tenantId}' -o json
```

Confirm active Azure subscription and AKS cluster; avoid storing unredacted output in evidence. Prometheus Operator CRDs must be installed before creating ServiceMonitor or PrometheusRule resources. Discover exporter ports and names rather than guessing.

## 4. Strimzi metrics and telemetry sources

Configure Strimzi Kafka JMX exporter through a version-compatible `metricsConfig` reference and approved ConfigMap. Verify the installed CRD and chart documentation before modifying the Kafka resource. Some metric series are not enabled by default; inspect actual series labels.

Monitor:
- **Brokers:** request handler utilization, request queue latency, bytes in/out, failed produce/fetch requests, active controller state where applicable, under-replicated/offline partitions, ISR changes, JVM heap/GC.
- **KRaft:** controller quorum health, leader elections, metadata log processing and catch-up, controller errors.
- **Clients:** produce success/error ratio, record-send latency, retries, consumer processing latency, committed offset progress, rebalance rate and dead-letter events.
- **Kubernetes:** pod restarts, OOM kills, CPU throttling, scheduling, PVC usage, disk latency and network failures.
- **Event Hubs:** ingress/egress, throttled requests, server errors, active connections and relevant consumer metrics as exposed by the chosen Azure Monitor API/tier.

Kafka consumer lag generally requires Kafka exporter or client instrumentation; it is not guaranteed by broker JMX alone.

## 5. Prometheus discovery

Example **illustrative** ServiceMonitor; adapt labels, namespace selector and port name to the actual Strimzi service and Prometheus selector.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kafka-broker-metrics
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames: [kafka]
  selector:
    matchLabels:
      app.kubernetes.io/name: kafka
  endpoints:
    - port: tcp-prometheus
      interval: 30s
      scrapeTimeout: 10s
```

**Do not apply without verification:** service labels and named ports shown here are placeholders. Inspect `kubectl get svc -n kafka --show-labels` and `kubectl get svc -n kafka -o yaml`, then use the actual matching labels/port. A successful CRD apply does not mean a target is discovered or scraped.

## 6. PromQL reference and correctness rules

Use metric names actually emitted by the deployed exporters.

```promql
# Scrape health
up{namespace="kafka"} == 0

# Kubernetes restarts over 15 minutes (kube-state-metrics required)
increase(kube_pod_container_status_restarts_total{namespace="kafka"}[15m]) > 0

# CPU throttling ratio (requires cAdvisor metrics)
sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="kafka"}[5m]))
/
clamp_min(sum by (pod) (rate(container_cpu_cfs_periods_total{namespace="kafka"}[5m])), 1e-9)
```

For Kafka-specific lag, partition ISR and request metrics, capture real series names using the Prometheus expression browser. Never publish an alert based on an unverified or absent metric. Guard against divide-by-zero, stale series, missing targets and cardinality explosions. Use separate alerts for missing telemetry and actual service degradation.

## 7. Azure Monitor and Log Analytics

Enable supported AKS monitoring integrations, Log Analytics ingestion and diagnostic settings using approved IaC. Confirm table availability and schema in the workspace before using queries.

Example KQL for Container Insights when `KubePodInventory` exists:

```kusto
KubePodInventory
| where TimeGenerated > ago(30m)
| where Namespace == "kafka"
| summarize Observations=count() by ClusterName, PodStatus
| order by Observations desc
```

This reports inventory observations, not unique pods or restart events. Check ingestion delay and cost before raising alert frequency. For Event Hubs, discover metric names and dimensions with Azure Monitor metric definitions for the actual namespace; do not assume Kafka broker counters exist.

## 8. SLI and SLO engineering

| SLI | Definition | Illustrative objective |
|---|---|---|
| Producer delivery success | Acknowledged records / attempted records within the measurement window | ≥99.9% |
| End-to-end processing latency | Time from accepted publish to durable sink effect | p99 <5 s under declared load |
| Consumer processing correctness | Unique IDs with expected durable effect / unique accepted IDs | 100% in bounded reconciliation |
| Pipeline availability | Good request windows / eligible request windows | ≥99.9% |
| DLQ handling | Quarantined poison records acknowledged and traceable | No unexplained loss |

**Example error budget:** At 99.9% availability across 30 days, allowed bad time is approximately 43.2 minutes if evaluated as time-based availability. Request-based error budgets use eligible request counts instead. Never conflate latency percentiles, missing IDs, and downtime into a single unqualified percentage.

For an availability SLO with 0.1% error budget, page on a sustained fast burn and ticket on a slower burn using paired windows (for example 1h/5m and 6h/30m). Implement only after instrumenting total and failed eligible events, verifying label joins and evaluating traffic minimums. Alerts must include owner, impact, dashboard and runbook links.

## 9. Alert policy

Classify as **page** for verified user-impacting data loss, critical unavailability, rapidly burning error budget, quorum risk or persistent large lag with threatened retention; **ticket** for capacity forecasts, slow burn, modest imbalance and telemetry gaps without known impact. Deduplicate notifications, enforce silence expiration and document maintenance windows. Do not page on a raw pod restart alone without service context.

## 10. Kubernetes-first labs (20)

Each lab records prerequisites, isolated change, verification, metrics screenshot/query result, expected versus actual behavior, cleanup and PASS/FAIL.

| # | Lab | Required evidence |
|---|---|---|
| 01 | Inventory Kafka and AKS monitoring | Context, query/command, sanitized output, result |
| 02 | Verify Strimzi metrics configuration | Context, query/command, sanitized output, result |
| 03 | Deploy Prometheus Operator in lab | Context, query/command, sanitized output, result |
| 04 | Inspect ServiceMonitor targets | Context, query/command, sanitized output, result |
| 05 | Collect Kafka broker JMX metrics | Context, query/command, sanitized output, result |
| 06 | Collect KRaft controller metrics | Context, query/command, sanitized output, result |
| 07 | Monitor partition under-replication | Context, query/command, sanitized output, result |
| 08 | Collect Kafka exporter consumer lag | Context, query/command, sanitized output, result |
| 09 | Instrument producer latency and errors | Context, query/command, sanitized output, result |
| 10 | Instrument consumer processing and DLQ | Context, query/command, sanitized output, result |
| 11 | Deploy Grafana dashboard | Context, query/command, sanitized output, result |
| 12 | Validate AKS Container Insights | Context, query/command, sanitized output, result |
| 13 | Query Azure Monitor Log Analytics | Context, query/command, sanitized output, result |
| 14 | Monitor Event Hubs ingress and throttling | Context, query/command, sanitized output, result |
| 15 | Implement PrometheusRule alert | Context, query/command, sanitized output, result |
| 16 | Test lag alert under bounded load | Context, query/command, sanitized output, result |
| 17 | Test broker failure detection | Context, query/command, sanitized output, result |
| 18 | Define burn-rate SLO alert | Context, query/command, sanitized output, result |
| 19 | Create incident evidence bundle | Context, query/command, sanitized output, result |
| 20 | Execute recovery and acceptance review | Context, query/command, sanitized output, result |

### Lab workflow

1. Establish baseline for at least one bounded synthetic producer/consumer run.
2. Validate telemetry source and Prometheus scrape target before querying.
3. Record baseline request rate, p99 latency, lag, Kafka/KRaft health and pod health.
4. Introduce one approved failure at a time in a disposable lab.
5. Verify alert transition, notification routing, mitigation and recovery.
6. Reconcile accepted and processed event IDs and capture all evidence.

Read-only triage:

```powershell
kubectl get kafka -n kafka
kubectl get pods -n kafka -o wide
kubectl describe pods -n kafka
kubectl get events -n kafka --sort-by=.lastTimestamp
kubectl get prometheus,alertmanager -n monitoring
kubectl get servicemonitor,prometheusrule -n monitoring
```

## 11. Failure scenarios (12)

| # | Failure | Detection and recovery objective |
|---|---|---|
| 1 | Missing scrape target | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 2 | Exporter crash loop | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 3 | High consumer lag | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 4 | Under-replicated partitions | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 5 | KRaft controller unavailable | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 6 | Producer error spike | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 7 | Event Hubs throttling | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 8 | AKS pod OOM/restarts | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 9 | Metrics cardinality explosion | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 10 | Log ingestion interruption | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 11 | Alert routing failure | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |
| 12 | False-positive SLO burn alert | Establish baseline → inject in isolated lab → confirm signal → contain → restore → reconcile event IDs |

**Scenario evidence:** trigger, blast-radius approval, expected alarm, actual telemetry, timeline, mitigation, rollback, and prevention. No destructive shared-cluster fault injection.

## 12. Production SRE runbooks (8)

| # | Runbook | Steps |
|---|---|---|
| 1 | Prometheus scrape outage | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 2 | Consumer lag incident | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 3 | Broker/ISR health incident | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 4 | KRaft quorum alert | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 5 | Producer error/latency breach | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 6 | Event Hubs quota throttling | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 7 | Monitoring pipeline degradation | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |
| 8 | SLO burn and incident closure | Assess user impact; verify signal integrity; correlate AKS, Kafka and client evidence; mitigate safely; validate SLO and correctness; close with RCA |

Each runbook requires incident owner, escalation path, read-only diagnostics, change approval boundary, rollback authority, recovery criteria and evidence retention.

## 13. Security, privacy and FinOps

Apply least-privilege RBAC to Prometheus/Grafana and Azure Monitor. Use TLS for telemetry endpoints, restrict scrape namespaces, redact event keys and payloads, keep secrets out of labels/logs, set retention limits and workspace cost budgets. Track ingestion volume, metric cardinality, scrape intervals, high-cardinality labels and query load. Separate operational metrics from regulated healthcare content.

## 14. 100-point assessment

| Gate | Points |
|---|---:|
| AKS/Strimzi telemetry architecture | 15 |
| Kafka broker and KRaft metrics | 15 |
| Producer, consumer and lag telemetry | 15 |
| Azure Monitor/Event Hubs coverage | 10 |
| Grafana dashboards and validated alerts | 15 |
| SLI/SLO and burn-rate design | 10 |
| Failure simulation and runbooks | 10 |
| Security, cost, rollback and evidence | 10 |
| **Total** | **100** |

**Proposed passing threshold:** 85/100 with no missing accepted event IDs, no critical security finding, validated telemetry coverage and demonstrated recovery. Written content alone cannot satisfy runtime acceptance.

## 15. Evidence manifest

```yaml
chapter: 106
environment: isolated-aks-lab
aks_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
prometheus_version: REPLACE
azure_monitor_workspace: REDACTED
commit_sha: REPLACE
executed_at_utc: null
labs: []
alerts_tested: []
slo_windows: []
event_reconciliation: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 107 — Azure Kafka Performance, Capacity, Disk and FinOps.** Publication, live lab execution, security review and runtime certification remain separately tracked.
