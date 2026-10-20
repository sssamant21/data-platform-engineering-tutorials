# Chapter 036 — Kafka Observability Architecture, JMX Exporter, Prometheus, Grafana and Kubernetes Monitoring Foundations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 08 — Monitoring, Metrics and Observability (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–035, especially security, KRaft, storage, performance and SRE capstones  
**Status:** Published · **Live labs:** Pending · **Independent security review:** Pending

> **Safety:** Use an approved disposable Kubernetes environment. JMX exporter, Prometheus and Grafana configurations are release-sensitive. Validate the Strimzi CRD, Kafka version, exporter rule mappings and monitoring Operator CRDs before applying anything. Never expose JMX remote management, broker secrets, private keys, tokens or tenant payloads through metrics. Plaintext port 9092 appears only for the isolated lab CLI baseline.

## 1. Objectives

Design an enterprise Kafka observability foundation that monitors brokers, KRaft controllers, Strimzi reconciliation, producers, consumers, Kubernetes Pods/nodes, storage and network dependencies. Build metrics pipelines, PromQL, dashboards, alert rules, operational runbooks, validation evidence and SLO-ready telemetry.

You will distinguish **telemetry collection**, **signal correctness**, **alert delivery** and **incident response**. A green dashboard without verified data and alert routing is not an accepted monitoring system.

## 2. Observability architecture

```text
Kafka KRaft / Strimzi on Kubernetes
  +-- Kafka broker and controller JMX
  |     -> Strimzi-supported JMX Prometheus Exporter
  +-- Strimzi Cluster Operator metrics
  +-- Producer / consumer application metrics
  +-- Consumer group lag / event age instrumentation
  +-- kube-state-metrics / kubelet-cAdvisor / node exporter
  +-- Cloud PVC / IOPS / network metrics
                 |
                 v
        Kubernetes Services / discovery
        ServiceMonitor / PodMonitor (if supported)
                 |
                 v
             Prometheus
        scrape / TSDB / rules
             /             \
            v               v
         Grafana        Alertmanager
      dashboards         paging / SRE
            \               /
             v             v
        SLO review / incident evidence
```

**Logs** support forensic diagnosis, **metrics** support trends and alerting, and **traces** support end-to-end request paths. JMX metrics are not distributed traces; instrument client applications separately. Chapter 036 establishes foundations; later Part 08 chapters deepen alerting, logging and distributed tracing.

## 3. Metrics taxonomy

| Layer | Critical signals | Primary owner |
|---|---|---|
| KRaft controller | Quorum health, metadata leader, election changes, metadata lag | Kafka platform |
| Broker | Under-replicated/under-minISR partitions, request queue, Produce/Fetch p99, bytes in/out | Kafka platform |
| JVM | Heap, GC pauses, direct memory, CPU | Kafka platform |
| Storage | PVC used/free, read/write latency, IOPS, queue, log growth | Infra/DBRE |
| Strimzi | Reconciliation failures/duration, operator availability | Platform |
| Kubernetes | Pod readiness, OOM, throttling, node pressure, scheduling | Kubernetes SRE |
| Producer | Acknowledged records, retries, errors, callback p99 | App team |
| Consumer | Processed records, group assignments, commits, lag, event age | App team |
| Security | TLS/SASL errors, authorization failures, certificate expiry | Security/platform |
| Monitoring | Target UP, scrape errors, rule failures, TSDB cardinality, Alertmanager routing | Observability SRE |

**Signal semantics:** Consumer lag in records is not latency in seconds. A client callback p99 is not end-to-end processing p99. Missing metrics are not healthy zeros. Exporter names and labels are version-dependent; inspect actual target output.

## 4. Prometheus and Grafana design principles

1. **Correctness before coverage:** validate every critical query against an independent Kafka or Kubernetes source.
2. **Low-cardinality labels:** cluster, namespace, broker, request type and bounded topic labels; never event IDs, payloads, user tokens or unbounded request IDs.
3. **Security:** namespace-restricted discovery, network controls, least-privilege dashboards, protected endpoints and redacted evidence.
4. **Availability:** alert when Kafka metrics disappear; use independent Kubernetes and quorum signals.
5. **Operational cost:** budget samples/second, retention, TSDB memory, PVC and remote-write traffic.
6. **Change control:** version exporter mappings, rules and dashboards in GitOps with review and rollback.
7. **KRaft correctness:** do not use ZooKeeper-era assumptions to validate metadata quorum.

## 5. Readiness checklist

Before deployment: approved cluster/context; compatible Kafka and Strimzi; metricsConfig schema verified; JMX exporter rules reviewed; Prometheus Operator present or approved for installation; NetworkPolicies checked; metrics PVC headroom; dashboard access controls; alerts with named owners; rollback and independent reviewer.

## 6. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve cluster and observability scope

Run `kubectl config current-context`, `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide`, and `kubectl -n kafka-lab get kafka sre-kafka -o yaml > evidence-ch36/kafka-before.yaml`. Confirm disposable cluster, resource budgets, approved scrape targets, Prometheus/Grafana ownership, TLS/RBAC, storage retention and change ticket. **Gate:** no instrumentation changes before authorization.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 02 — Verify Strimzi/Kafka/Prometheus versions

Run `kubectl get crd kafkas.kafka.strimzi.io -o jsonpath='{.spec.versions[*].name}'`; `kubectl -n kafka-lab get kafka sre-kafka -o jsonpath='{.status.kafkaVersion}'`; `kubectl get crd servicemonitors.monitoring.coreos.com` and `kubectl get crd podmonitors.monitoring.coreos.com`. The monitoring CRDs may be absent. Record supported Strimzi `metricsConfig` schema and installed Prometheus Operator version. **Gate:** do not apply an unsupported manifest.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 03 — Baseline KRaft and ISR

Run `kubectl -n kafka-lab exec kafka-cli -- /opt/kafka/bin/kafka-metadata-quorum.sh --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status`. Collect broker readiness, under-replicated partitions and controller metrics from available telemetry. Internal plaintext is a disposable-lab convention, never a production monitoring design. **Gate:** no pre-existing quorum or ISR degradation.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 04 — Map telemetry signals to owners

Create `evidence-ch36/signal-inventory.md` mapping producer/client, broker, controller, Strimzi operator, Kubernetes node/Pod, storage, DNS and networking signals to scrape endpoints, labels, owner and retention. Distinguish metrics from logs and traces. **Gate:** each critical failure mode has a source and an owner.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 05 — Configure broker JMX exporter

Use the exact Strimzi release's supported JMX Prometheus Exporter metrics configuration. Illustrative `Kafka.spec.kafka.metricsConfig` shape: `type: jmxPrometheusExporter` and `valueFrom.configMapKeyRef.name/key`, with a reviewed ConfigMap containing exporter rules. **Do not blindly apply**: rule names, Kafka CR API versions and ConfigMap schema vary. Prefer Strimzi-maintained example mappings adapted to installed version; do not expose unauthenticated JMX remote ports. **Gate:** operator reconciles Kafka Ready and broker metrics endpoint is internal only.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 06 — Configure KRaft controller metrics

Inspect KafkaNodePool roles and actual Strimzi controller metrics support. Capture quorum leader, voters, metadata log lag, election activity and controller health from version-supported metrics. Never use legacy ZooKeeper/controller metric assumptions to assert KRaft quorum health. **Gate:** metrics match `kafka-metadata-quorum.sh` status.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 07 — Configure operator metrics

Review Strimzi Cluster Operator deployment metrics configuration and service exposure for the installed release. Instrument reconciliation successes/failures, durations and watched resources. Restrict metrics access to Prometheus namespaces. **Gate:** operator reconciliation errors are visible without exposing credentials.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 08 — Install or validate Prometheus

In an approved monitoring namespace, inventory `kubectl get prometheus,servicemonitor,podmonitor -A` where CRDs exist. If absent, install an approved pinned Prometheus Operator/kube-prometheus-stack release through GitOps after security review; do not invent Helm versions. Apply Pod security, network isolation, retention, PVC capacity and RBAC. **Gate:** healthy Prometheus targets and resource budgets.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 09 — ServiceMonitor and PodMonitor discovery

Check `kubectl get crd servicemonitors.monitoring.coreos.com podmonitors.monitoring.coreos.com` and inspect target Service labels, namespace selectors and Prometheus serviceMonitorSelector/podMonitorSelector. A ServiceMonitor is not sufficient if labels, namespace selectors or port names do not match. Prefer the operator-supported Strimzi metrics Service and PodMonitor examples for the deployed version. **Gate:** expected targets appear UP in Prometheus.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 10 — Secure metrics endpoints

Verify Prometheus ServiceAccount RBAC only permits needed discovery, and NetworkPolicies allow monitoring ingress without broad namespace access. If cross-namespace scrapes use TLS or auth, configure approved credentials and trust bundles. Never put bearer tokens in dashboard queries or Git. **Gate:** authorized scrape succeeds; unauthorized Pod access is denied where policy/CNI support exists.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 11 — Inspect targets and exporter output

Use a reviewed, temporary `kubectl -n <monitoring-namespace> port-forward svc/<prometheus-service> 9090:9090` from an approved workstation, then inspect Prometheus Targets and API `/api/v1/targets`. Avoid copying metrics with tenant identifiers to public files. Record target UP, scrape duration, sample count and last scrape error. **Gate:** broker, controller, operator and kube-state/node targets classified Pass/Pending.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 12 — Build broker health PromQL

Use the **actual discovered metric names**. Example generic query: `up{job=~".*kafka.*"}`. For under-replicated partitions, verify exporter mapping before querying `kafka_server_replicamanager_underreplicatedpartitions` or its variant. Use `sum by (cluster, broker)` only where those labels exist. **Gate:** query matches source JMX metrics and correct broker counts.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 13 — Build producer/consumer observability

Instrument client-side producer send success/error, retry rate, record queue time, p95/p99 callback latency, consumer poll/processing latency, commits, rebalances and event age. Broker metrics alone cannot prove application delivery or consumer business completion. Consumer lag requires a supported group-offset exporter or application instrumentation with ACL/RBAC controls. **Gate:** client and broker data correlated by time, topic and sanitized client ID.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 14 — Build Kafka storage and JVM views

Collect JVM heap, GC pauses, process CPU, Pod throttling, broker network, log bytes, PVC utilization, IOPS, disk latency and queue depth. Metrics Server `kubectl top` does not supply throttling or disk latency. Separate heap from page cache and storage provider metrics. **Gate:** hot brokers identifiable individually, not hidden in cluster averages.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 15 — Build Grafana dashboards

Provision Grafana through approved deployment/GitOps with SSO/RBAC, read-only Prometheus data source and secret-free provisioning. Create panels for Kafka readiness, KRaft quorum, ISR, request latency, CPU/GC, PVC, ingress/egress, consumer lag, event age, Strimzi reconciliation and target health. Verify dashboard time ranges and units. **Gate:** dashboards distinguish absent data from healthy zero values.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 16 — Design recording rules

Create reviewed recording rules for broker health, produce/fetch p95/p99 where histograms are available, ISR deficits, target availability and consumer lag trends. Use `rate(...[5m])` for counters, not gauges; `histogram_quantile` requires valid bucket metrics. Recording rules must retain cluster/namespace identity without high-cardinality event IDs. **Gate:** expressions validated with promtool or supported equivalent.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 17 — Design alert routing

Define critical alerts for Kafka NotReady, under-minISR, KRaft quorum loss, persistent under-replication, metrics target down and PVC exhaustion; warnings for rising p99, GC, disk latency, consumer event age and operator reconciliation errors. Configure Alertmanager grouping, inhibition, silence ownership and runbook URLs. **Gate:** each alert has severity, owner, threshold, duration and tested routing.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 18 — Test synthetic failure signals safely

Use controlled **monitoring-only** injection such as stopping an approved synthetic metrics target or applying a temporary test alert rule; never stop Kafka brokers to prove alerting. Verify pending/firing/resolved states and escalation, then revert. **Gate:** notification evidence and no Kafka health impact.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 19 — Validate scrape cost and cardinality

Measure scrape interval, duration, samples scraped, active series, TSDB head memory, retention storage and remote-write backlog. Remove event IDs, unbounded topic labels and per-request IDs from metrics. Test that metric cardinality scales with partitions/brokers within approved limits. **Gate:** observability system remains reliable during Kafka load.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

### Lab 20 — Read-only verification and handoff

Execute the preflight script below, capture its exit status, review dashboards and alert routing, and obtain independent signoff. A successful inventory does **not** prove alert firing, query correctness, security or SLO compliance. **Gate:** every required test is Pass/Fail/Pending with linked evidence.

**Evidence:** record commands, exact software versions, expected/observed results, redacted screenshots or query output, rollback and assessor status (Pass/Fail/Pending).

## 7. Reference Strimzi metrics configuration pattern

The following **illustrates** the common Strimzi `metricsConfig` reference pattern; it is **not** a complete Kafka resource or a guarantee of compatibility. Verify served API and the official sample mapping for your installed Strimzi release.

```yaml
# Fragment only — merge into an existing approved Kafka CR:
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

A ConfigMap must contain version-appropriate exporter rules; do not use an empty ruleset and claim broker health coverage. KRaft controller metrics may require additional configuration depending on node roles and Strimzi release. An exporter endpoint should be reachable by approved Prometheus only.

## 8. ServiceMonitor discovery example

This is a **template** for a verified metrics Service, not a ready-to-apply Strimzi-specific ServiceMonitor. Replace labels, port name and namespace after inspecting the real Service and Prometheus selectors.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kafka-broker-metrics-ch36
  namespace: monitoring
  labels:
    monitoring-owner: kafka-sre
spec:
  namespaceSelector:
    matchNames:
      - kafka-lab
  selector:
    matchLabels:
      app.kubernetes.io/name: REPLACE_WITH_VERIFIED_METRICS_SERVICE_LABEL
  endpoints:
    - port: REPLACE_WITH_VERIFIED_NAMED_METRICS_PORT
      interval: 30s
      scrapeTimeout: 10s
```

Do not deploy this example unchanged. A ServiceMonitor requires Prometheus Operator CRDs and a matching Prometheus selector. A PodMonitor may be more appropriate for the installed Strimzi version. Verify discovery and endpoint authorization.

## 9. PromQL patterns and correctness tests

```promql
# General scrape availability; narrow to actual discovered jobs
up{job=~".*kafka.*"}

# Generic counter rate pattern (replace with real metric)
rate(kafka_server_brokertopicmetrics_bytesin_total[5m])

# Generic histogram pattern (only if matching bucket series exists)
histogram_quantile(
  0.99,
  sum by (le, cluster) (rate(kafka_request_duration_seconds_bucket[5m]))
)
```

The latter two names are **illustrative**, not guaranteed Kafka exporter output. Use actual series names from the Prometheus expression browser and the installed JMX mapping. Do not apply `rate` to gauges or `histogram_quantile` to non-histogram metrics. If only JMX percentile gauges exist, present them as per-instance gauges and do not incorrectly aggregate into a global p99.

## 10. Alert design and example rules

| Alert | Trigger concept | Priority | Required runbook |
|---|---|---|---|
| KafkaMetricsTargetDown | Expected target `up == 0` or absent for threshold | High | Telemetry outage |
| KafkaKRaftQuorumDegraded | Validated KRaft quorum signal indicates loss of redundancy | Critical | KRaft quorum |
| KafkaUnderMinISR | Any sustained under-minISR partitions | Critical | ISR/replication |
| KafkaUnderReplicated | Persistent under-replicated partitions | High | ISR/replication |
| KafkaProduceLatencySLO | Validated client/broker p99 exceeds target | High | Producer latency |
| KafkaConsumerEventAge | Application event-age SLO breached | High | Consumer lag |
| KafkaPVCFreeSpaceLow | Volume utilization exceeds approved limit | High | Storage capacity |
| KafkaStrimziReconcileFailure | Repeated operator reconciliation errors | High | Operator |
| PrometheusScrapeFailure | Target/scrape errors or missing expected series | High | Telemetry outage |
| PrometheusCardinalityGrowth | Series/sample budget exceeded | Medium | Cardinality |

Use alert `for` durations to avoid noise, but critical quorum/minISR failures may require faster paging. Alert rules must use **verified** metric names and real thresholds; the table is a design specification, not a ready-to-apply alert bundle.

## 11. Read-only verification script

Save as `verify-ch36.sh` and execute from a workstation with authorized Kubernetes access:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/9] Context'
kubectl config current-context
echo '[2/9] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/9] Kafka / NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/9] MetricsConfig presence'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[5/9] Prometheus Operator CRDs'
for crd in servicemonitors.monitoring.coreos.com podmonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then
    echo "FOUND: $crd"
  else
    echo "PENDING: $crd not installed"
  fi
done
echo '[6/9] Monitoring inventory (best effort)'
kubectl get pods -A -l app.kubernetes.io/name=prometheus -o wide || true
echo '[7/9] Kafka Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[8/9] PVC inventory'
kubectl -n "$NS" get pvc -o wide
echo '[9/9] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka observability inventory.'
echo 'NOT PROVEN: target discovery, metric accuracy, alert routing, TLS or dashboard acceptance.'
```

**Important:** The script is intentionally not an alert firing or Prometheus query test. Optional missing CRDs are reported as Pending; the reviewer must not convert them into Pass. It assumes the foundation's `kafka-cli` Pod exists.

## 12. Twelve troubleshooting scenarios

### 1. Broker target DOWN

Inspect Service/PodMonitor selectors, endpoint port names, network policy, exporter startup and Pod readiness; repair discovery before suppressing alerts. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 2. Prometheus target UP but Kafka metric missing

Inspect exporter mapping, Kafka/Strimzi version, JMX bean availability and relabel rules; never interpret missing as zero. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 3. KRaft leader metric contradicts quorum CLI

Validate metric mapping, freshness, scrape lag and broker/controller role labels; use quorum CLI as independent check. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 4. Under-replicated partitions not alerted

Check gauge name, broker labels, rule expression, evaluation interval and Alertmanager route; test with synthetic rule, not live ISR damage. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 5. Consumer lag dashboard flatlines

Check group exporter credentials, offsets, consumer inactivity and stale series; distinguish zero from absent data. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 6. p99 panel shows nonsense

Verify histogram buckets versus summary quantiles, units, label aggregation and request type; never average per-instance p99. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 7. Grafana shows No Data after upgrade

Review datasource UID, rule/dashboards provisioning, renamed exporter series and Prometheus target health. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 8. High metrics cardinality

Inspect unbounded labels, topic/partition dimensions, exporter rules and TSDB active series; remove event-specific labels. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 9. Scrapes timeout under load

Check exporter CPU, scrape timeout/interval, Pod throttling, network and Prometheus saturation; tune without harming brokers. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 10. Prometheus PVC nearly full

Review retention, TSDB growth and compaction; expand approved storage or reduce cardinality, never delete active TSDB files manually. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 11. Operator reconciliation alert storm

Check Strimzi operator logs/events, desired-state drift and restart loops; fix underlying CR errors and route by cluster. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

### 12. Unauthorized metrics access

Inspect Service exposure, NetworkPolicy, ingress, RBAC and TLS/auth; restrict access and rotate exposed credentials under incident process. **Evidence:** affected target/series, timestamps, root cause, fix and regression check.

## 13. Eight SRE runbooks

### Runbook A — Kafka telemetry outage

Confirm scope and missing targets; inspect exporter/ServiceMonitor/Prometheus; restore discovery; verify Kafka health independently; validate dashboards; document observability gap.

### Runbook B — KRaft quorum alert

Validate quorum CLI; check controller Pod/node/network/storage; escalate as critical; avoid unapproved controller restarts; restore quorum; review alert accuracy.

### Runbook C — ISR/under-minISR alert

Check partition/broker and replica fetch; stop synthetic load; restore broker/storage/network; confirm ISR; inspect producer errors; preserve timeline.

### Runbook D — Producer p99 regression

Correlate client callback latency with broker queue/replication, CPU, GC and PVC; identify stage; roll back approved change; validate p99 and errors.

### Runbook E — Consumer lag and event-age incident

Compare ingress and processed rate; check assignments/rebalances and downstream; apply bounded backpressure; verify drain; validate event integrity; document SLO.

### Runbook F — Metrics cardinality incident

Identify exploding labels and series; disable offending instrumentation via GitOps; verify TSDB stabilization; check lost visibility; add label governance; review capacity.

### Runbook G — Prometheus storage/capacity incident

Inspect PVC/TSDB growth and retention; check scrape rates; apply approved storage/cost changes; avoid manual TSDB deletion; confirm ingestion; update forecasts.

### Runbook H — Alert routing and game-day acceptance

Review owners and silences; trigger safe synthetic alert; confirm paging/acknowledgment; resolve; verify no secret leakage; attach signoff.

## 14. Evidence package

```text
evidence-ch36/
  approval-and-scope.md
  context.txt
  kafka-before.yaml
  version-compatibility.md
  quorum-before.txt
  signal-inventory.md
  metricsconfig-review.yaml
  exporter-mapping-review.md
  controller-metrics.md
  operator-metrics.md
  prometheus-operator-inventory.md
  servicemonitor-review.yaml
  networkpolicy-review.md
  target-health.csv
  broker-promql-validation.md
  client-instrumentation.md
  storage-jvm-dashboard.md
  grafana-dashboard-review.md
  recording-rules-review.md
  alert-routing-review.md
  synthetic-alert-test.md
  cardinality-cost.md
  verify-ch36-output.txt
  troubleshooting-log.md
  runbook-drill.md
  independent-signoff.md
```

Record target URL **without embedded credentials**, namespace, job/instance labels, software versions, metric mapping commit, scrape interval, query expression, expected/observed values, alert recipient, date and assessor. All unexecuted sections remain Pending.

## 15. 100-point acceptance assessment

| Domain | Points | Critical |
|---|---:|---|
| Change approval, topology and version compatibility | 10 | Yes |
| Broker JMX exporter and Strimzi configuration | 15 | Yes |
| KRaft controller and operator health signals | 10 | Yes |
| Prometheus target discovery and scrape correctness | 15 | Yes |
| Producer, consumer, lag and event-age signals | 10 | Yes |
| JVM, Kubernetes and PVC telemetry | 10 | Yes |
| Grafana dashboards and recording rules | 10 | No |
| Alert routing and safe synthetic test | 10 | Yes |
| Security, cardinality, retention and access controls | 5 | Yes |
| Evidence, runbooks and independent review | 5 | Yes |
| **Total** | **100** | |

**Pass:** at least 85/100 with all critical gates evidenced. **Fail:** exposed credentials or JMX, disabled TLS verification, fabricated metric coverage, missed quorum/minISR critical alerts, unapproved production change or missing independent acceptance evidence. Publication does not earn a score.

## 16. Cleanup, references and next chapter

Remove only chapter-owned temporary test alerts, approved diagnostics and synthetic resources after retaining redacted evidence. Do not delete shared Prometheus PVCs, Kafka PVCs, operator resources or dashboards without change approval.

**References:** [Strimzi documentation](https://strimzi.io/documentation/), [Apache Kafka monitoring](https://kafka.apache.org/documentation/#monitoring), [Prometheus documentation](https://prometheus.io/docs/), [Prometheus Operator](https://prometheus-operator.dev/), [Grafana documentation](https://grafana.com/docs/grafana/latest/), [Kubernetes monitoring](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/).

**Next:** Chapter 037 — Kafka Broker, KRaft, Producer and Consumer Metrics, PromQL and Advanced Grafana Dashboards.

---

**Verification boundary:** GitHub publication proves only that this chapter exists. Live metrics validation, alert drills, security review and independent operational acceptance remain **Pending**.
