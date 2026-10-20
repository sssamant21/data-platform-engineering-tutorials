# Chapter 042 — Kafka Reliability Alerting, Multiwindow Burn Rates, Error-Budget Policies and Production Change Gates

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 09 — SRE, SLIs, SLOs and Reliability (2/5)  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 036–041  
**Status:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Run exercises in an approved disposable Kubernetes cluster with synthetic workloads. Alert injection must target a dedicated test receiver. Do not stop brokers, modify production ACLs/TLS, reset shared offsets, disable KRaft safety checks or execute a real Kafka upgrade as part of this chapter. Published rules are examples requiring metric/label and on-call policy validation.

## 1. Mission

Convert the Kafka service-level indicators and service ownership contracts from Chapter 041 into operational multiwindow burn-rate alerting, error-budget policies and auditable Kubernetes/GitOps change gates. Detect fast customer-impacting errors, avoid low-traffic false positives, protect durability and KRaft quorum during changes, and ensure an unowned or missing metric cannot silently green-light a rollout.

## 2. Reliability control plane

```text
Synthetic producer/consumer app event ledger
  | monotonic success/error/eligible counters
  v
Prometheus --> SLI recording rules --> 5m/1h and 30m/6h burn rules
  |                                        |
  v                                        v
Grafana SLO + budget panels            Alertmanager --> owned on-call
  |                                        |
  +------------ policy engine ------------+
                   |
                   v
       GitOps dry-run release gate
          | Kafka Ready/KRaft quorum
          | ISR/minISR + broker/PVC health
          | SLO budget + burn + telemetry freshness
          | security/owner approval + rollback
          v
       APPROVE / BLOCK / EXCEPTION
```

A release gate must distinguish Kafka platform safety (quorum/ISR/storage) from customer-facing SLOs. A healthy Kafka CR alone does not prove producer delivery or consumer processing success.

## 3. SLO, error budget and burn-rate mathematics

For a 99.9% example availability SLO, allowed error fraction = 0.001. With 1,000,000 eligible events in a 30-day window, the budget is 1,000 failed eligible events. A 2% observed bad-event ratio burns at 20× the allowed rate. If 300 eligible events fail, the budget consumed is 30%, leaving 70%. These are **illustrative synthetic values**.

```text
error_ratio(window) = bad_eligible_events(window) / eligible_events(window)
burn_rate(window)   = error_ratio(window) / (1 - SLO_target)
budget_events       = eligible_events(30d) * (1 - SLO_target)
budget_used         = bad_events(30d) / budget_events
```

If the eligible denominator is zero, mark No Traffic/Unknown. If a required metric is absent, mark Telemetry Missing. Neither state is equivalent to healthy zero errors. When errors are counted per callback attempt, retries may be multiple attempts for one business event; choose and document the SLI's unit of account.

## 4. Multiwindow burn-rate alert policy

| Policy | Short window | Long window | Example burn threshold | Response |
|---|---|---|---:|---|
| Fast burn | 5m | 1h | 14.4× | Page responsible on-call |
| Medium burn | 30m | 6h | 6× | Page or urgent escalation |
| Slow burn | 6h | 1d | 3× | Ticket/reliability review |
| Missing telemetry | scrape freshness | expected-target inventory | N/A | Monitoring incident |
| Quorum/under-minISR | validated Kafka safety signal | sustained/reviewed window | N/A | Block changes, incident triage |

These are reference patterns inspired by SRE multiwindow burn-rate alerting. The thresholds, windows, `for` durations, service traffic sufficiency and paging policies must be calibrated to the actual Kafka workload and on-call team. Both short and long window conditions are required to reduce noise.

## 5. Example Prometheus recording and alert rules

The following application metrics are **illustrative**. Instrument them in an isolated test app and validate labels and metric types before use. The example is a design starting point, not a production-ready universal ruleset.

```yaml
groups:
  - name: kafka-sre-slo-example
    interval: 30s
    rules:
      - record: kafka_sre:eligible:rate5m
        expr: sum by (service, cluster) (rate(kafka_sre_eligible_events_total[5m]))
      - record: kafka_sre:bad:rate5m
        expr: sum by (service, cluster) (rate(kafka_sre_bad_events_total[5m]))
      - record: kafka_sre:error_ratio:5m
        expr: kafka_sre:bad:rate5m / clamp_min(kafka_sre:eligible:rate5m, 1e-9)
      - record: kafka_sre:error_ratio:1h
        expr: sum by (service, cluster) (rate(kafka_sre_bad_events_total[1h])) /
          clamp_min(sum by (service, cluster) (rate(kafka_sre_eligible_events_total[1h])), 1e-9)
      - record: kafka_sre:error_ratio:30m
        expr: sum by (service, cluster) (rate(kafka_sre_bad_events_total[30m])) /
          clamp_min(sum by (service, cluster) (rate(kafka_sre_eligible_events_total[30m])), 1e-9)
      - record: kafka_sre:error_ratio:6h
        expr: sum by (service, cluster) (rate(kafka_sre_bad_events_total[6h])) /
          clamp_min(sum by (service, cluster) (rate(kafka_sre_eligible_events_total[6h])), 1e-9)
      - alert: KafkaSLOFastBurnExample
        expr: |
          (kafka_sre:error_ratio:5m > (14.4 * 0.001))
          and on(service, cluster)
          (kafka_sre:error_ratio:1h > (14.4 * 0.001))
          and on(service, cluster)
          (kafka_sre:eligible:rate5m > 0)
        for: 2m
        labels:
          severity: critical
          environment: lab
        annotations:
          summary: "Synthetic Kafka SLO fast burn"
          runbook_url: "https://example.invalid/replace-with-reviewed-runbook"
      - alert: KafkaSLOMediumBurnExample
        expr: |
          (kafka_sre:error_ratio:30m > (6 * 0.001))
          and on(service, cluster)
          (kafka_sre:error_ratio:6h > (6 * 0.001))
        for: 5m
        labels:
          severity: warning
          environment: lab
```

**Important:** `clamp_min` prevents division by zero but does not solve zero-traffic or missing-series semantics. Add a separately tested minimum-volume gate for every window and a missing-target alert based on expected inventory. Run `promtool check rules` against extracted rule groups, then `promtool test rules` with fixtures for resets, no traffic and missing series. Validate alert labels/receivers before applying a PrometheusRule through GitOps.

## 6. Kubernetes GitOps release gate

**Inputs:** approved SLO policy, current fast/medium burn, 30-day budget, expected Prometheus targets, Kafka CR/NodePool readiness, KRaft quorum, ISR/minISR, PVC capacity, maintenance exception, change approver, rollback plan.

**Decision:** BLOCK when critical health or telemetry is missing, a fast-burn policy is active, durability is degraded or required approval/rollback is absent. EXCEPTION requires explicit risk owner, expiration, ticket and rollback. APPROVE only when all gates pass. The gate is advisory until integrated into an authorized CI/CD approval workflow.

**Dry-run pseudocode:**

```text
if missing(approval, rollback, SLO_owner): BLOCK
if missing(critical_telemetry) or missing(quorum_state): BLOCK
if kafka_not_ready or quorum_degraded or under_min_isr: BLOCK
if pvc_critical or operator_reconcile_failed: BLOCK
if fast_burn or budget_policy_freeze: BLOCK
if approved_exception_with_expiry_and_audit: EXCEPTION
else: APPROVE
```

An exception must not bypass irreversible data-loss protections or regulatory controls. Real Kafka rollouts must follow Strimzi-supported reconciliation and maintenance procedures.

## 7. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve service SLO and on-call policy

**Objective and procedure:** Document Kafka cluster, service tier, SLI ownership, eligible traffic, 30-day window, synthetic test policy, alert receivers and security reviewer.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 02 — Baseline Kubernetes and KRaft

**Objective and procedure:** Capture Kafka Ready, KafkaNodePool roles, KRaft quorum, Pods, PVCs, ISR, operator health and Prometheus target inventory.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 03 — Implement synthetic producer counters

**Objective and procedure:** Instrument eligible callback attempts and failed acknowledgments as monotonic counters, with bounded service/cluster labels and no record IDs as metric labels.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 04 — Implement synthetic consumer processing counters

**Objective and procedure:** Record accepted unique IDs, durably processed unique IDs, processing failures and freshness breaches; reconcile application ledger to offsets.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 05 — Define no-traffic and missing-telemetry states

**Objective and procedure:** Distinguish zero eligible traffic, missing scrape targets and genuinely healthy zero errors. Test each state separately.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 06 — Validate counter semantics and resets

**Objective and procedure:** Exercise synthetic app Pod restart, inspect rate/increase behavior, avoid gauge-based ratios and detect duplicate metrics.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 07 — Calculate rolling error ratios

**Objective and procedure:** Evaluate 5m, 30m, 1h and 6h ratios from the same source counters; compare PromQL with independently calculated ledger values.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 08 — Calculate 30-day error budget

**Objective and procedure:** Compute allowed bad events, observed failures, fraction consumed and remaining budget. Record exact window and eligibility exclusions.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 09 — Design fast-burn multiwindow alert

**Objective and procedure:** Use reviewed 14.4× threshold over 5m and 1h for a 99.9% example SLO, require both windows, and validate minimum eligible traffic.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 10 — Design medium-burn multiwindow alert

**Objective and procedure:** Use reviewed 6× threshold over 30m and 6h for the example SLO, require both windows, and test low-traffic suppression.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 11 — Design slow-burn budget review

**Objective and procedure:** Track 1×–3× sustained burn as a ticket/weekly review rather than automatic paging unless approved by on-call policy.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 12 — Implement Prometheus recording rules

**Objective and procedure:** Use reviewed PrometheusRule resources with namespace selectors, rule linting and synthetic metric names, recording ratio and traffic series separately.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 13 — Test Alertmanager routing and inhibition

**Objective and procedure:** Validate ownership labels, group_by, repeat_interval, deduplication, silence expiration and lab-only receivers; do not page production on-call.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 14 — Test absent-series and telemetry failures

**Objective and procedure:** Remove only a test scrape target or simulate absent series; verify dedicated monitoring-blindness alert and dashboard No Data handling.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 15 — Implement Kafka safety guardrails

**Objective and procedure:** Define release blockers for KRaft quorum instability, under-minISR, offline partitions, PVC pressure, Strimzi reconciliation failure and monitoring blindness.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 16 — Build GitOps release gate

**Objective and procedure:** Create a dry-run gate checking SLO budget, current burn, Kafka health, security approvals and rollback artifacts; default to fail closed on missing critical data.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 17 — Validate planned maintenance exception

**Objective and procedure:** Review owner-approved exception with duration, risk, RPO/RTO, rollback and audit record; do not silently exclude all maintenance from customer SLIs.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 18 — Inject synthetic fast-burn scenario

**Objective and procedure:** Use synthetic counter increments or test-only PrometheusRule to exercise alert Pending/Firing/Resolved and route receipts without disrupting Kafka.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 19 — Exercise release freeze and recovery

**Objective and procedure:** Demonstrate a blocked synthetic GitOps change under high burn and successful re-evaluation after safe recovery; no real broker rollout required.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

### Lab 20 — Complete acceptance and independent review

**Objective and procedure:** Run read-only verifier, compare recording rules with raw ledger, verify security and change-gate policy, attach evidence and score 100-point assessment.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Prometheus versions, approved Kubernetes context, query or manifest, expected/observed metric and alert states, receiver receipt, SLO owner, risk, rollback and assessor. Do not mark Passed without actual execution. Use a bounded synthetic KafkaTopic and isolated consumer group.

## 8. Read-only Kubernetes verification script

Save as `verify-ch42.sh`:

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
echo '[3/10] Kafka/NodePool inventory'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Pod and PVC inventory'
kubectl -n "$NS" get pods,pvc -o wide
echo '[5/10] Kafka metric configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[6/10] Prometheus Operator CRDs'
for crd in prometheusrules.monitoring.coreos.com servicemonitors.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then echo "FOUND: $crd"; else echo "PENDING: $crd"; fi
done
echo '[7/10] Alert rule inventory'
kubectl get prometheusrules -A -o wide 2>/dev/null || true
echo '[8/10] NetworkPolicy'
kubectl -n "$NS" get networkpolicy
echo '[9/10] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[10/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka reliability platform inventory.'
echo 'NOT PROVEN: SLO counters, rule correctness, alert routing, GitOps gate, live drills or security acceptance.'
```

Run `chmod +x verify-ch42.sh && ./verify-ch42.sh | tee evidence-ch42/preflight.txt`. The internal 9092 bootstrap convention is isolated-lab-only; production-like client tests require approved TLS/SASL and scoped ACLs.

## 9. Safe synthetic validation

1. Create a lab-only synthetic SLI test target and isolated Kafka client group.
2. Establish baseline with valid eligible and bad-event counters; record expected burn.
3. Inject synthetic error increments to cross fast-burn thresholds in both windows.
4. Verify Prometheus rule evaluation, Alertmanager Pending/Firing/Resolved, correct lab receiver and acknowledgment.
5. Repeat for no traffic, missing scrape, counter reset and low-volume false-positive scenarios.
6. Feed the synthetic alert state into a dry-run GitOps gate; assert BLOCK while burning.
7. Restore test metrics, verify recovery and release decision, and remove only test resources.

Never manufacture a real KRaft/ISR outage merely to test alert routing. This synthetic exercise proves rule/routing behavior; actual Kafka failure detection requires separate controlled testing and review.

## 10. Twelve troubleshooting scenarios

### Scenario 1 — Fast burn hidden by aggregate fleet average

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 2 — Short window fires but long window does not

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 3 — No traffic displayed as 100% availability

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 4 — Missing scrape series incorrectly treated as zero errors

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 5 — Counter reset produces incorrect budget burn

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 6 — Retries double-count eligible business events

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 7 — Consumer event age breach hidden by offset lag

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 8 — Alertmanager receiver missing or misrouted

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 9 — Silence remains active after maintenance

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 10 — GitOps gate allows change during under-minISR

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 11 — Release gate blocks forever on stale telemetry

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

### Scenario 12 — Error-budget exclusion hides real customer impact

**Detect:** Compare source synthetic ledger, raw counters, Prometheus recording rules, Grafana and Alertmanager delivery. **Diagnose:** Verify metric type, label joins, expected targets, event eligibility, traffic sufficiency, window alignment, silence/inhibition and GitOps gate inputs. **Recover:** Correct the minimal application/monitoring/policy fault via approved change; preserve Kafka quorum/ISR, TLS and ACLs. **Verify:** Re-run the test, recompute budget from ledger and document alert and release-gate outcome.

## 11. Eight production SRE runbooks

### Runbook A — Fast-burn page and incident declaration

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook B — Medium-burn investigation and escalation

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook C — Error-budget exhaustion and release freeze

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook D — KRaft quorum/ISR reliability gate

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook E — Producer/consumer SLI disagreement

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook F — Monitoring blind spot and missing targets

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook G — Alert routing, inhibition and silence incident

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

### Runbook H — Change exception, rollback and audit review

1. Identify affected service, SLO, severity, owner and incident commander.
2. Validate Kafka/KRaft quorum, ISR and Kubernetes state independently.
3. Confirm eligible traffic, bad-event numerator, rule windows and telemetry freshness.
4. Correlate producer/consumer ledgers with logs, traces and Grafana.
5. Review alert routing, silence/inhibition, budget burn and release gate.
6. Apply approved mitigation or GitOps rollback, preserving durability and security.
7. Verify alert resolution, corrected SLO/budget and audit-ready incident timeline.

## 12. Evidence package

```text
evidence-ch42/
  approval-and-slo-policy.md
  preflight.txt
  version-and-target-inventory.md
  producer-counter-contract.md
  consumer-counter-contract.md
  no-traffic-missing-series-tests.md
  counter-reset-tests.md
  rolling-error-ratios.csv
  error-budget-calculation.csv
  fast-burn-rule-tests.md
  medium-burn-rule-tests.md
  slow-burn-policy.md
  recording-rules.yaml
  promtool-check.txt
  promtool-test.txt
  alertmanager-routing-receipts.md
  telemetry-blindness-test.md
  kafka-safety-gates.md
  gitops-dry-run-gate.md
  maintenance-exception-review.md
  synthetic-burn-drill.md
  release-freeze-recovery.md
  security-review.md
  assessor-signoff.md
```

Each artifact must record actual version, source, UTC time range, expected and observed outcome, service owner, redaction status, rollback and independent reviewer. Pending is not Passed.

## 13. 100-point enterprise SRE assessment

| Domain | Points | Critical |
|---|---:|---|
| Service SLO ownership and scope | 10 | Yes |
| Kafka/KRaft baseline and safety guardrails | 10 | Yes |
| Producer/consumer SLI counters and eligibility | 15 | Yes |
| Error-budget and rolling ratio correctness | 15 | Yes |
| Multiwindow fast/medium/slow burn rules | 15 | Yes |
| Missing data, no traffic and counter resets | 10 | Yes |
| Alertmanager routing, inhibition and test receipt | 10 | Yes |
| GitOps release freeze, exception and rollback | 10 | Yes |
| Security, runbooks and independent signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. **Automatic Fail:** fabricated tests, unsafe Kafka disruptions, missing critical alert receiver, misleading missing-data green state, release approved under degraded quorum/ISR, unreviewed security bypass or absent independent review.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic PrometheusRules, lab-only client workloads and temporary test receivers through approved GitOps. Preserve sanitized evidence; do not delete broker PVCs, production offsets, shared Prometheus data or operator-managed Secrets.

**References:** [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/), [Google SRE Workbook: Error Budget Policy](https://sre.google/workbook/error-budget-policy/), [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/), [Prometheus unit testing](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/), [Strimzi](https://strimzi.io/documentation/), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 043 — Kafka Reliability Incident Management, On-Call Operations, Escalation and Blameless Postmortems.

---

**Verification boundary:** Published Markdown only. Live alert rule tests, on-call delivery, GitOps enforcement, security review and independent acceptance remain Pending.
