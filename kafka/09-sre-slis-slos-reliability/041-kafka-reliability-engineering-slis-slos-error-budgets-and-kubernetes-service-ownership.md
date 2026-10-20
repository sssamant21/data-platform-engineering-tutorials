# Chapter 041 — Kafka Reliability Engineering, SLIs, SLOs, Error Budgets and Kubernetes Service Ownership

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 09 — SRE, SLIs, SLOs and Reliability (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–040, especially Chapters 036–040  
**Status:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use an approved disposable Kubernetes cluster and synthetic Kafka clients. Do not stop production brokers/controllers, delete PVCs, change shared consumer offsets, disable TLS/ACLs or weaken ISR durability for SLO experiments. Error budgets are policy tools, not authorization to accept data loss. GitHub publication is not live reliability certification.

## 1. Mission and outcomes

Design an end-to-end Kafka SRE reliability model connecting **customer-visible outcomes** to Kafka brokers, KRaft quorum, Strimzi reconciliation, Kubernetes resources, storage and producer/consumer application ownership. Establish measurable SLIs, business-approved SLOs, error budgets, burn-rate alerts, release gates, incident ownership and evidence-based reliability reviews.

After this chapter, learners can distinguish platform health from successful event processing; calculate budget consumption without hiding missing data; explain why producer acknowledgments do not prove downstream durability; and operate a documented ownership/escalation model.

## 2. Kubernetes-first reliability architecture

```text
API / business event producer
    |
    | successful callback? (producer acknowledgment SLI)
    v
Strimzi Kafka KRaft cluster
    | Kafka Ready + controller quorum + ISR + storage
    | operator reconciliation + Kubernetes Pods/PVCs
    v
Consumer group
    | poll -> process -> idempotent sink -> commit
    | processed unique IDs and event age
    v
Business outcome
    |
    +-- application SLIs/SLOs --> Prometheus recording rules
    +-- platform metrics --------> Grafana + Alertmanager
    +-- logs / OTel traces ------> incident correlation
    +-- owner / on-call / GitOps -> change gates and rollback
```

**Service boundary matters:** A producer callback with `acks=all` means Kafka accepted a record under the configured replication and acknowledgment conditions. It does not prove a consumer processed the record or that an external sink committed the result. Kafka KRaft quorum health and ISR are vital platform guardrails, but they are not substitutes for a customer-facing SLI.

## 3. Ownership and operational contracts

| Layer | Accountable owner | Responsibilities | Escalation evidence |
|---|---|---|---|
| Kafka platform | Kafka SRE/DBRE | brokers, KRaft, ISR, quotas, storage, capacity | Kafka CR, quorum, broker metrics |
| Kubernetes | Platform SRE | nodes, networking, scheduling, PVC/CSI, disruption | Pod/node/PVC signals |
| Strimzi/GitOps | Platform owner | CRDs, reconciliation, upgrades, rollout/rollback | Git commit, operator status |
| Producer service | Application owner | callback errors, retries, idempotency, delivery contract | producer ledger |
| Consumer service | Application owner | processing, commits, lag, event age, downstream sink | consumer ledger |
| Observability | Monitoring owner | metric completeness, dashboards, alerts, routing | targets, rules, alert receipts |
| Security | Security owner | TLS/SASL/ACLs, identities, secrets, audit | access review and approved policy |
| Incident command | Assigned on-call | severity, communication, recovery coordination | incident timeline |

Document RACI, escalation timeout, runbook URL, service tier, critical hours and exception approver for every SLO. An unowned alert is not an operational control.

## 4. SLI definitions and example SLO policy

| SLI | Calculation / measurement | Illustrative lab target | Measurement caveat |
|---|---|---|---|
| Producer acknowledgment success | successful eligible callbacks / eligible send attempts | 99.9% over 30 days | retries not separate business events |
| Producer callback p99 | p99 callback latency | ≤250 ms steady state | workload-dependent |
| Unique durable processing | unique accepted IDs durably processed / accepted unique IDs | ≥99.95% over agreed deadline | reconcile eventual completion |
| Event freshness | percentage processed within freshness threshold | 99.9% within 2 s | event-time and clock skew |
| Platform quorum health | observed healthy KRaft quorum intervals / eligible intervals | 99.99% | separate platform SLI |
| Critical telemetry coverage | verified required series/targets / expected inventory | 100% critical coverage | missing ≠ zero |
| Recovery objective | elapsed time from detection to restored processing | service-tier-defined | RTO not same as RPO |

**These targets are examples, not promises or observed results.** Choose windows, eligibility, late-arrival policy, maintenance handling, business tiers, time zones and error budgets with the actual service owner. For low-volume streams, event-count SLIs may be statistically noisy; consider explicit event-age and availability probes.

## 5. Error budget mathematics

For an event-based SLO over a fixed window:

```text
Eligible = successful eligible events + failed eligible events
Error ratio = failed eligible events / eligible events
SLO target = 0.999
Budget fraction = 1 - SLO target = 0.001
Allowed failures = floor(eligible * budget fraction)
Budget consumed = failed eligible events / (eligible * budget fraction)
Budget remaining = max(0, 1 - budget consumed)
```

**Example (synthetic):** 1,000,000 eligible events, 99.9% target gives 1,000 allowed failures. With 250 failed eligible events, 25% of the budget is consumed and 75% remains. If the denominator is zero or telemetry is absent, return **No Data/Unknown**, not 100% reliability. A latency SLO requires a separately defined bad-event numerator or a statistically sound latency distribution; do not compute p99 by averaging per-instance p99 gauges.

## 6. Burn-rate alert design

Burn rate is observed bad-event ratio divided by the allowed bad-event fraction. For 99.9% SLO, a 1% observed error ratio is a 10× burn. Use approved multiwindow alerting and sufficient traffic to avoid noise. For example, design separate fast-burn and slow-burn recording rules with short/long windows; **do not copy a generic threshold into production** without service traffic, event volume and on-call review. Evaluate missing metrics independently from bad-event ratios.

## 7. Twenty Kubernetes-first hands-on labs

### Lab 01 — Establish ownership and service boundaries

**Objective and procedure:** Identify Kafka platform, application producers/consumers, KRaft quorum, Strimzi operator, Kubernetes, storage, network and on-call ownership. Document escalation and shared responsibility.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 02 — Approve reliability scope and risk

**Objective and procedure:** Record disposable cluster context, change ticket, synthetic data, error budget, SLO review window, allowed operations, security signoff and abort conditions.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 03 — Baseline Kafka KRaft health

**Objective and procedure:** Inspect Kafka/KafkaNodePool CRs, Pods, PVCs, Kafka Ready and metadata quorum. Capture current under-minISR, under-replicated partitions and broker availability.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 04 — Inventory customer journeys and event contracts

**Objective and procedure:** Define synthetic publish, acknowledge, consume, durable process and downstream confirmation boundaries. Differentiate accepted, produced, acknowledged, processed and deduplicated records.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 05 — Design producer availability SLI

**Objective and procedure:** Define eligible synthetic send attempts, successful callbacks with required acks, excluded client validation errors and measurement sources. Use numerator/denominator over a declared window.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 06 — Design producer latency SLI

**Objective and procedure:** Measure p95/p99 send-to-callback latency by synthetic load tier. Account for batching, retries, compression, quotas and client clock.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 07 — Design consumer processing SLI

**Objective and procedure:** Use accepted event ledger versus unique durably processed IDs, offset commit correctness and duplicate handling. Broker ack is not end-to-end success.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 08 — Design freshness and event-age SLI

**Objective and procedure:** Measure event creation-to-durable-processing age with clock-skew guardrails. Separate lag in records from age in seconds and detect silent consumer stalls.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 09 — Design durability and replication guardrails

**Objective and procedure:** Validate topic replication factor, min.insync.replicas, producer acks=all, ISR, under-minISR and KRaft quorum. Do not claim a guarantee solely from configuration.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 10 — Define Kafka platform health SLI

**Objective and procedure:** Combine actual broker/controller readiness, quorum and replication health; distinguish infrastructure indicators from customer-facing availability.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 11 — Define SLOs and measurement windows

**Objective and procedure:** Write example 99.9% producer acknowledgment, 99.95% processed delivery, p99 latency and freshness targets for a synthetic workload; agree actual thresholds with service owner.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 12 — Calculate error budgets

**Objective and procedure:** Compute 30-day eligible-event budget for 99.9% target, remaining budget and burn rate from synthetic counters. Handle zero denominator and missing data explicitly.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 13 — Build multiwindow burn-rate alerts

**Objective and procedure:** Design short/long window alerts (e.g., 5m/1h and 30m/6h) using recorded error ratios, traffic sufficiency and review-approved thresholds; test with synthetic metrics.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 14 — Define SLO reporting dashboard

**Objective and procedure:** Build service overview for availability, latency, event age, error budget remaining, Kafka quorum/ISR, producer/consumer ownership and missing telemetry.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 15 — Define release and change gates

**Objective and procedure:** Create policy for rolling Strimzi/KafkaNodePool changes, SLO burn, quorum/ISR, PVC pressure, rollback, change freeze and exceptions.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 16 — Implement toil and incident ownership

**Objective and procedure:** Track pages, toil hours, recurring root causes, incident severity, escalation response, runbook ownership and postmortem action closure.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 17 — Simulate client-only delivery errors

**Objective and procedure:** Use isolated producer application test failure or synthetic metric injection; do not stop brokers. Observe SLI denominator/numerator, alert and recovery.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 18 — Simulate consumer backlog and recovery

**Objective and procedure:** Pause only a synthetic consumer Deployment, measure event age and lag, resume and reconcile processed IDs. Avoid shared consumer groups or offsets.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 19 — Validate error-budget policy with scenarios

**Objective and procedure:** Compare fast burn, slow burn, low-traffic periods, missing series and false positives. Decide pause/continue/exception based on agreed policy.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

### Lab 20 — Run acceptance and independent review

**Objective and procedure:** Execute read-only preflight, compare dashboards with synthetic ledger and Kafka CLI, attach evidence, test safe rollback and complete 100-point rubric.

**Validation:** Record Kafka/Strimzi/client version, approved cluster context, SLI numerator and denominator, query or ledger evidence, timestamp, expected and observed result, abort condition, GitOps rollback and independent reviewer. The lab remains **Pending** until executed. Use a bounded synthetic topic, approved secure listener and isolated client group.

## 8. Sample SLI recording-rule design

PromQL metric names here are **application-defined examples**. Implement the counters in a synthetic producer/consumer service and verify exporter names, types and labels first.

```promql
# Example: 5m producer error ratio, only when denominator is nonzero
sum(rate(kafka_sre_producer_callback_failures_total[5m]))
/
clamp_min(sum(rate(kafka_sre_producer_callback_attempts_total[5m])), 1e-9)

# Example: 1h end-to-end processing error ratio (requires
# explicit failed-event classification and unique-event ledger)
sum(increase(kafka_sre_unique_events_failed_total[1h]))
/
clamp_min(sum(increase(kafka_sre_unique_events_eligible_total[1h])), 1)

# Example: telemetry absence; adapt to actual job labels
absent(up{job="kafka-sre-synthetic-producer"})
```

**Guardrail:** `clamp_min` prevents division by zero but can produce a misleading zero when no eligible traffic exists. Pair ratio rules with minimum-traffic conditions and a separate No Data alert. Do not sum counters across incompatible clusters, workloads or duplicate retry dimensions.

## 9. Read-only Kubernetes verification script

Save as `verify-ch41.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/10] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[5/10] PVCs'
kubectl -n "$NS" get pvc -o wide
echo '[6/10] Kafka metric configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[7/10] Monitoring CRDs'
for crd in servicemonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then echo "FOUND: $crd"; else echo "PENDING: $crd"; fi
done
echo '[8/10] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/10] NetworkPolicy inventory'
kubectl -n "$NS" get networkpolicy
echo '[10/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only platform inventory.'
echo 'NOT PROVEN: SLI correctness, SLO attainment, error budgets, alerts, ownership or security acceptance.'
```

Run `chmod +x verify-ch41.sh && ./verify-ch41.sh | tee evidence-ch41/preflight.txt`. The internal plaintext 9092 CLI convention is for isolated labs only; production-like acceptance must use TLS/SASL and scoped ACLs.

## 10. Safe reliability drills

**Producer drill:** Inject a bounded client-only synthetic failure, record eligible attempts, callback successes/errors, retries and resulting error-budget impact. Do not force Kafka broker or controller failure.

**Consumer drill:** Scale only an isolated synthetic consumer Deployment to zero for a short approved window, then restore replicas. Observe event age, lag, unique processed IDs and drain time. Do not reset offsets or affect shared consumer groups.

**Alert drill:** Inject a test-only SLI metric or reviewed temporary PrometheusRule with a lab-only receiver. Verify Pending/Firing/Resolved and acknowledgment, then remove it through GitOps.

**Change gate:** Block a planned Kafka rolling change when quorum/ISR guardrails fail, telemetry is missing, or a defined fast-burn policy is active. Exceptions require an accountable approver and documented recovery path.

## 11. Twelve troubleshooting scenarios

### Scenario 1 — Kafka CR Ready while producer requests fail

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 2 — Broker metrics green but end-to-end delivery missing

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 3 — SLO denominator excludes failed sends

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 4 — Client retries counted as unique successful records

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 5 — Consumer lag low while event age grows

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 6 — Under-minISR and quorum not part of change gate

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 7 — SLO burn alert misses low-volume service

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 8 — SLO burn alert pages on missing data

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 9 — Incorrect p99 aggregation hides tail latency

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 10 — Rolling change violates replica availability

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 11 — Error budget dashboard diverges from raw ledger

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

### Scenario 12 — Unowned service and runbook delay incident response

**Detect:** Compare synthetic event ledger, Kafka CLI/quorum, raw Prometheus metrics, Grafana and Alertmanager. **Diagnose:** Inspect numerator/denominator, retry deduplication, sampling, client processing, broker ISR, telemetry freshness and ownership. **Recover:** Apply approved application, monitoring or platform remediation without compromising TLS/ACLs, durability or production availability. **Verify:** Recalculate SLI and budget from source events, confirm alert resolution and capture a redacted incident timeline.

## 12. Eight production SRE runbooks

### Runbook A — Producer acknowledgment SLO breach

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook B — End-to-end processing and freshness breach

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook C — KRaft quorum and broker availability

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook D — Under-minISR and durability risk

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook E — Error-budget fast burn incident

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook F — Release freeze and rollback decision

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook G — Monitoring blind spot and SLI correctness

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

### Runbook H — Ownership escalation and postmortem

1. Identify affected service tier, SLO, incident severity and on-call owner.
2. Confirm Kafka/KRaft quorum, ISR and Kubernetes readiness independently.
3. Inspect producer/consumer event ledger, retries, processing and event age.
4. Validate SLI source, denominator, missing-series behavior and budget burn.
5. Correlate logs, traces, metrics and recent GitOps changes.
6. Apply approved remediation or rollback; preserve durable processing guarantees.
7. Recompute SLI and budget, validate alert routing and close with postmortem actions.

## 13. Evidence package

```text
evidence-ch41/
  approval-and-scope.md
  service-ownership-raci.md
  preflight.txt
  version-matrix.md
  kafka-quorum-isr-baseline.md
  event-contract-and-ledger.md
  producer-sli.md
  producer-latency-sli.md
  processing-sli.md
  freshness-sli.md
  durability-guardrails.md
  platform-sli.md
  slo-policy.md
  error-budget-calculation.csv
  burn-rate-rules.yaml
  grafana-slo-dashboard.json
  change-gate-policy.md
  toil-incident-review.md
  producer-drill.md
  consumer-drill.md
  budget-policy-scenarios.md
  security-review.md
  independent-signoff.md
```

Each artifact records source, software version, time window, event eligibility, exact query, expected/observed result, security/redaction, owner and reviewer. Missing evidence remains Pending.

## 14. 100-point enterprise SRE acceptance

| Domain | Points | Critical |
|---|---:|---|
| Service ownership, scope and approval | 10 | Yes |
| Kafka/KRaft/ISR platform guardrails | 15 | Yes |
| Producer acknowledgment and latency SLIs | 10 | Yes |
| End-to-end processing and freshness SLIs | 15 | Yes |
| SLO windows, eligibility and error-budget math | 15 | Yes |
| Burn-rate alerts and missing-data behavior | 10 | Yes |
| Kubernetes/Strimzi change gates and rollback | 10 | Yes |
| Safe client drills and event reconciliation | 10 | Yes |
| Runbooks, security and independent signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** fabricated results, data loss disguised as successful delivery, unowned critical alerts, misleading zero-traffic SLI, exposed credentials, disabled TLS validation, unsafe production changes or absent independent review.

## 15. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients, test rules and temporary monitoring resources via approved GitOps. Retain sanitized event ledger and review evidence. Do not delete Kafka PVCs, production consumer offsets, shared monitoring data or operator-managed Secrets.

**References:** [Google SRE Workbook: Implementing SLOs](https://sre.google/workbook/implementing-slos/), [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/), [Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Prometheus](https://prometheus.io/docs/), [Kubernetes](https://kubernetes.io/docs/).

**Next:** Chapter 042 — Kafka Reliability Alerting, Multiwindow Burn Rates, Error-Budget Policies and Production Change Gates.

---

**Verification boundary:** Published document only. Live SLI/SLO validation, incident drills, security review and independent acceptance remain Pending.
