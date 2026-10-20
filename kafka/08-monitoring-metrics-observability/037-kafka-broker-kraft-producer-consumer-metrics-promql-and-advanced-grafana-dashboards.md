# Chapter 037 — Kafka Broker, KRaft, Producer and Consumer Metrics, PromQL and Advanced Grafana Dashboards

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 08 — Monitoring, Metrics and Observability (2/5)  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 016–020 and 026–036  
**Status:** Published; live labs and independent security review Pending.

> **Safety:** Use a disposable approved Kubernetes cluster. Inspect installed Kafka/Strimzi versions and actual JMX exporter mappings before deploying PromQL. Never expose remote JMX, disable TLS hostname verification, change production broker configuration, reset shared offsets or publish credentials. Publication is not operational acceptance.

## 1. Objectives and architecture

Build version-aware Kafka dashboards covering KRaft controller health, broker requests and replication, producer acknowledgments, consumer lag and business processing, JVM/GC, Kubernetes CPU and PVC storage. Validate Prometheus discovery, query semantics, recording rules, dashboard-as-code, missing-series behavior and incident escalation.

```text
Kafka brokers/controllers -- JMX exporter -- ServiceMonitor/PodMonitor
Strimzi operator ----------------------------|
Producer/consumer app instrumentation -------|--> Prometheus --> Grafana
Kubernetes/cAdvisor/kube-state/node ---------|              --> Alertmanager
Cloud PVC IOPS and latency ------------------|              --> SRE runbooks
Kafka CLI and application event ledger ---------------------> independent validation
```

## 2. Metric semantic contract

| Signal | Source | Interpretation | Independent check |
|---|---|---|---|
| KRaft leader/voters | controller metrics | metadata quorum state | kafka-metadata-quorum.sh |
| Under-replicated partitions | ReplicaManager JMX | replica catch-up risk | topic describe/ISR |
| Under-minISR partitions | ReplicaManager JMX | durability/availability risk | ISR and topic minISR |
| Request Total/Queue/Local/Remote Time | RequestMetrics JMX | broker latency stages | client p99 and JMX |
| Request handler/network idle | Kafka JMX | saturation clues | CPU and queues |
| Broker bytes in/out | BrokerTopicMetrics | physical traffic class | client logical bytes |
| Heap/GC | JVM metrics | allocation/pause | Pod RSS and limits |
| CPU throttling | cAdvisor | CFS quota pressure | Pod requests/limits |
| PVC IOPS/latency | CSI/cloud provider | storage performance | volume identity |
| Producer retries/errors | client instrumentation | delivery attempts | callback ledger |
| Consumer lag | group exporter | offset difference, not time | end/committed offsets |
| Consumer event age | application metrics | processing delay | event timestamps |

Metric names and label sets depend on exporter mapping and version. A missing metric is not a zero value. Do not average per-broker p99 gauges. Only compute fleet p99 from valid pooled histogram buckets; summaries cannot generally be aggregated into a global quantile.

## 3. PromQL reference patterns

```promql
# Check Kafka targets; adapt actual job labels
up{job=~".*kafka.*"}

# Example only: verify metric is a counter and exists
sum by (cluster) (rate(kafka_server_brokertopicmetrics_bytesin_total[5m]))

# Example only: requires real histogram bucket series
histogram_quantile(
  0.99,
  sum by (cluster, le) (rate(kafka_request_duration_seconds_bucket[5m]))
)

# All Kafka target series missing; not sufficient for one missing broker
absent(up{job="kafka-broker-metrics"})
```

PromQL rules: use rate/increase only on counters, preserve le for histogram aggregation, verify units, compare expected broker inventory with discovered targets, and exclude unbounded event ID/client principal labels. All metric names above are illustrative and must be replaced by real exported names before acceptance.

## 4. Twenty Kubernetes-first labs

### Lab 01 — Validate Kafka/Strimzi/Kubernetes versions and approved namespace

**Objective:** Establish trustworthy, reproducible evidence for validate kafka/strimzi/kubernetes versions and approved namespace using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 02 — Inspect JMX exporter and Prometheus discovery

**Objective:** Establish trustworthy, reproducible evidence for inspect jmx exporter and prometheus discovery using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 03 — Verify KRaft quorum using metadata quorum CLI

**Objective:** Establish trustworthy, reproducible evidence for verify kraft quorum using metadata quorum cli using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 04 — Inventory metric names types units and labels

**Objective:** Establish trustworthy, reproducible evidence for inventory metric names types units and labels using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 05 — Build broker availability and ISR queries

**Objective:** Establish trustworthy, reproducible evidence for build broker availability and isr queries using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 06 — Analyze Produce and Fetch request latency stages

**Objective:** Establish trustworthy, reproducible evidence for analyze produce and fetch request latency stages using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 07 — Measure network and request-handler idle fractions

**Objective:** Establish trustworthy, reproducible evidence for measure network and request-handler idle fractions using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 08 — Measure broker bytes in/out and quota throttling

**Objective:** Establish trustworthy, reproducible evidence for measure broker bytes in/out and quota throttling using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 09 — Correlate JVM heap GC and native memory

**Objective:** Establish trustworthy, reproducible evidence for correlate jvm heap gc and native memory using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 10 — Correlate Pod CPU throttling memory and OOM

**Objective:** Establish trustworthy, reproducible evidence for correlate pod cpu throttling memory and oom using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 11 — Build PVC latency IOPS and capacity panels

**Objective:** Establish trustworthy, reproducible evidence for build pvc latency iops and capacity panels using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 12 — Instrument producer callbacks retries and errors

**Objective:** Establish trustworthy, reproducible evidence for instrument producer callbacks retries and errors using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 13 — Instrument consumer processing commits and rebalances

**Objective:** Establish trustworthy, reproducible evidence for instrument consumer processing commits and rebalances using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 14 — Reconcile consumer lag with event age

**Objective:** Establish trustworthy, reproducible evidence for reconcile consumer lag with event age using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 15 — Build broker and KRaft Grafana dashboards

**Objective:** Establish trustworthy, reproducible evidence for build broker and kraft grafana dashboards using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 16 — Build producer and consumer SLO dashboards

**Objective:** Establish trustworthy, reproducible evidence for build producer and consumer slo dashboards using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 17 — Test PromQL counter resets and absent series

**Objective:** Establish trustworthy, reproducible evidence for test promql counter resets and absent series using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 18 — Validate recording rules and metric cardinality

**Objective:** Establish trustworthy, reproducible evidence for validate recording rules and metric cardinality using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 19 — Run safe synthetic alert and dashboard regression

**Objective:** Establish trustworthy, reproducible evidence for run safe synthetic alert and dashboard regression using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

### Lab 20 — Complete independent evidence review and rollback

**Objective:** Establish trustworthy, reproducible evidence for complete independent evidence review and rollback using the approved synthetic Kafka cluster. **Procedure:** (1) Capture cluster context and Kafka/Strimzi/client/monitoring versions. (2) Inspect source metrics or Kubernetes resources and exporter mapping. (3) Query the matching Prometheus series, compare with Kafka CLI, Kubernetes or application counters. (4) Record query, units, labels, timestamp, expected/observed result and alert/dashboard screenshot. (5) Test a safe regression or a reviewed GitOps rollback where applicable.

**Commands and validation:** Use the version-compatible toolchain; begin with the read-only verification script below. For metrics tests, check Prometheus Targets and query API through an approved authenticated access path. For group lag, use kafka-consumer-groups.sh --describe against a synthetic group. For KRaft, compare with metadata-quorum CLI. For Pod/PVC checks, compare Kubernetes inventory with cAdvisor/CSI metrics. For Grafana, export reviewed dashboard JSON and verify panels do not render missing data as zero. Never apply production mutations.

**Acceptance:** Exact series and data source verified, expected target count met, sensitive labels excluded, no Kafka health degradation, and independent reviewer evidence. Mark Pending until executed.

## 5. Kubernetes preflight and independent verification

Save as verify-ch37.sh:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
echo '[1] Context'; kubectl config current-context
echo '[2] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4] JMX exporter configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[5] Monitoring CRDs'
for crd in servicemonitors.monitoring.coreos.com podmonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then echo "FOUND: $crd"; else echo "PENDING: $crd"; fi
done
echo '[6] Pods and Services'; kubectl -n "$NS" get pods,svc -o wide
echo '[7] PVCs'; kubectl -n "$NS" get pvc -o wide
echo '[8] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo '[9] Prometheus inventory'
kubectl get pods -A -l app.kubernetes.io/name=prometheus -o wide || true
echo '[10] Grafana inventory'
kubectl get pods -A -l app.kubernetes.io/name=grafana -o wide || true
echo 'PASS: read-only inventory; dashboard correctness, alert routing and security remain UNVERIFIED.'
```

Run: chmod +x verify-ch37.sh && ./verify-ch37.sh | tee evidence-ch37/preflight.txt. The 9092 listener is for an isolated plaintext CLI lab only. Repeat production-like verification through an approved TLS/SASL listener and ACLs.

## 6. Dashboard-as-code design

Provision Grafana dashboards from reviewed GitOps-managed JSON with a fixed data source UID, SSO/RBAC, cluster/namespace/broker variables, proper units and No Data handling. Dashboard pages: fleet overview; KRaft and ISR; Produce/Fetch request stages; producer callback SLO; consumer lag/event age; JVM/GC; Kubernetes throttling; PVC IOPS; monitoring target health. Include panel descriptions, owner, SLO threshold, query provenance, runbook link and change history.

## 7. Twelve failure scenarios

### Scenario 1 — Exporter target UP but JMX metric missing

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 2 — KRaft dashboard disagrees with quorum CLI

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 3 — Under-minISR metric missing or stale

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 4 — Incorrect p99 from averaged percentile gauges

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 5 — Counter reset creates misleading rate spike

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 6 — Consumer lag zero while processing has stopped

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 7 — High-cardinality labels exhaust Prometheus

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 8 — Broker CPU throttle hidden by average CPU

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 9 — PVC has free space but IOPS saturated

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 10 — Producer bytes differ from broker bytes

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 11 — Grafana panels break after exporter upgrade

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

### Scenario 12 — Unauthorized access exposes sensitive telemetry

**Detect:** Compare Grafana with source metrics, Prometheus target inventory and independent CLI/application evidence. **Triage:** Confirm series type, labels, freshness, units, recent exporter/Strimzi changes, security boundaries and broker health. **Recover:** Fix root cause via approved monitoring/GitOps change; never mask a Kafka failure with a dashboard override. **Verify:** Rerun query, check expected targets and record alert behavior, rollback and owner.

## 8. Eight SRE runbooks

### Runbook A — Metrics target outage

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook B — KRaft quorum alert

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook C — Under-minISR and replica health

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook D — Broker request latency regression

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook E — Producer acknowledgment errors

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook F — Consumer lag and event-age incident

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook G — Prometheus cardinality and storage incident

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

### Runbook H — Grafana dashboard deployment and rollback

1. Confirm scope, severity, incident commander and affected clusters.
2. Cross-check dashboard data with Kafka CLI, Kubernetes inventory and client counters.
3. Identify missing series, actual Kafka degradation, metric mapping or infrastructure bottleneck.
4. Preserve sanitized PromQL, target state, time window and logs.
5. Apply approved remediation without disabling TLS/ACLs or compromising KRaft/ISR.
6. Validate metrics, alerts, recovery SLO and runbook closure; record reviewer.

## 9. Evidence package

```text
evidence-ch37/
  approval-and-context.md
  preflight.txt
  version-matrix.md
  metric-catalog.csv
  kraft-quorum-cli.txt
  broker-health.promql
  request-stage.promql
  broker-throughput.promql
  producer-metrics.csv
  consumer-metrics.csv
  lag-reconciliation.md
  grafana-broker-overview.json
  grafana-client-slo.json
  grafana-jvm-pvc.json
  query-validation.csv
  recording-rules.yaml
  rule-lint.txt
  cardinality-budget.md
  safe-alert-test.md
  dashboard-acceptance.md
  independent-signoff.md
```

Every metric must include name, type, unit, exporter mapping version, query, labels, source, timestamp, expected and observed values. All unexecuted labs and reviews remain Pending.

## 10. 100-point enterprise assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, approvals and version compatibility | 10 | Yes |
| KRaft, broker and ISR metric correctness | 15 | Yes |
| Request-stage, throughput and p99 PromQL | 15 | Yes |
| JVM, CPU and PVC dashboards | 10 | Yes |
| Producer client metrics | 10 | Yes |
| Consumer lag, processing and event age | 10 | Yes |
| Grafana dashboard-as-code and No Data semantics | 10 | Yes |
| Recording rules, resets and cardinality | 10 | Yes |
| Safe alert test and security review | 5 | Yes |
| Runbooks and independent evidence signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** 85/100 or above with all critical gates evidenced. **Automatic fail:** invented live metrics, exposed secrets/JMX, disabled TLS verification, misleading p99/lag, unapproved production changes or missed KRaft/under-minISR critical signals.

## 11. Cleanup and references

Remove only chapter-owned test alerts and synthetic monitoring targets after approval; preserve redacted evidence. Do not delete Kafka PVCs, Prometheus TSDB, operator resources, Secrets or unrelated consumer groups.

References: [Kafka monitoring](https://kafka.apache.org/documentation/#monitoring), [Strimzi](https://strimzi.io/documentation/), [PromQL](https://prometheus.io/docs/prometheus/latest/querying/functions/), [Grafana](https://grafana.com/docs/grafana/latest/dashboards/), [Kubernetes metrics](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/).

**Next:** Chapter 038 — Kafka Centralized Logging, Kubernetes Log Pipelines, Audit Events and Incident Forensics.

**Verification boundary:** Published documentation only; live dashboard, alert, security and independent acceptance remain Pending.
