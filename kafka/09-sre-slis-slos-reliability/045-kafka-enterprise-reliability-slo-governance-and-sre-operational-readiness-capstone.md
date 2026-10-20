# Chapter 045 — Kafka Enterprise Reliability, SLO Governance and SRE Operational Readiness Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 09 — SRE, SLIs, SLOs and Reliability (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–044, especially Chapters 036–044  
**Status:** Published · **Live capstone execution:** Pending · **Independent technical/security review:** Pending

> **Safety and certification boundary:** This is an enterprise SRE readiness *exercise*, not proof that a production Kafka platform has been validated. Use approved isolated Kubernetes and synthetic Kafka workloads. Do not intentionally fail production brokers/controllers, delete PVCs, reset shared offsets, weaken replication/minISR, disable TLS/ACLs, leak Secrets or page real production responders. A written test is Pending until independently executed and evidenced.

## 1. Capstone mission

Integrate the reliability engineering program from Chapters 041–044: service ownership, producer/consumer SLIs, SLOs and error budgets, multiwindow burn-rate alerts, Alertmanager escalation, incident command, blameless postmortems, Kubernetes/Strimzi/KRaft safety gates, GitOps rollback, read-only automation, toil reduction and governance. Deliver a defensible **Ready / Not Ready** decision based on measured synthetic outcomes, safety checks and independent signoff.

## 2. Learning objectives

- Define an end-to-end Kafka reliability service boundary from producer callback through unique durable processing.
- Validate KRaft metadata quorum, replication/ISR and Strimzi/Kubernetes readiness without relying solely on green dashboards.
- Review and calculate SLO eligibility, error budgets, burn-rate windows and No Data handling.
- Test lab-only Alertmanager routing, escalation, incident communications and postmortem actions.
- Demonstrate GitOps release freeze/rollback policy and namespace-scoped least privilege.
- Prove synthetic event ledger reconciliation and customer-facing recovery after bounded client-only incidents.
- Assess operational readiness, security, capacity, toil, ownership and governance with a 100-point gate.

## 3. Reference acceptance architecture

```text
Synthetic producer -> Strimzi Kafka KRaft -> Synthetic consumer -> idempotent sink
     |                      |                      |
  callbacks             quorum/ISR             event age/ledger
     +----------------------+----------------------+
                            |
                    Prometheus SLIs
                            |
              recording + burn-rate rules
                  /                  \
          Grafana SLOs            Alertmanager
                  \                  /
                 Incident command
                        |
              GitOps release gate
       Kafka safety + SLO + telemetry + RBAC
                        |
             independent SRE assessor
                        |
                  READY / NOT READY
```

**Platform health is not a business SLI.** Kafka CR Ready and KRaft quorum are necessary safety signals but do not prove accepted events reached downstream processing. Verify both producer acknowledgments and the durable unique-event ledger.

## 4. Acceptance contract and owners

| Domain | Owner | Required evidence | Fail condition |
|---|---|---|---|
| Kafka/KRaft | Kafka SRE/DBRE | quorum, ISR/minISR, Kafka CR and NodePool | unverified safety |
| Kubernetes/storage | Platform SRE | Pods, PVCs, CSI, capacity and rollback | storage or scheduling risk |
| Producer | Application owner | callback success/latency and accepted IDs | unaccounted failures |
| Consumer | Application owner | processed unique IDs, freshness, commits | unexplained data discrepancy |
| SLO governance | Service owner | targets, window, eligibility, budget policy | missing policy |
| Monitoring | Observability SRE | target inventory, rule tests, no-data handling | silent blind spot |
| Incident response | Incident commander | paging, escalation, updates and postmortem | unowned incident |
| Security | Security reviewer | TLS/SASL/ACLs, RBAC, secret hygiene | bypass or exposure |
| Change management | GitOps approver | release gate, exception, rollback | unauthorized mutation |

## 5. SLO and budget governance

**Illustrative synthetic SLOs:** 99.9% eligible producer acknowledgments over 30 days; 99.95% unique durable processing by an agreed deadline; 99.9% events processed within an agreed freshness threshold; KRaft/ISR safety as independent guardrails. These are examples, not measured or approved production targets.

```text
eligible = successful eligible events + failed eligible events
error_ratio = failed eligible events / eligible
budget_allowed = eligible * (1 - SLO_target)
budget_consumed = failed eligible events / budget_allowed
burn_rate = observed_error_ratio / (1 - SLO_target)
```

For 1,000,000 eligible events at 99.9% SLO, the allowed failure budget is 1,000 events. If 200 eligible events fail, 20% of the budget is consumed and 80% remains. **Zero traffic and missing telemetry must produce Unknown/No Data**, not green. Client retries must not inflate unique business-event success. Do not extrapolate a short synthetic drill to actual 30-day compliance.

## 6. Critical safety and change gates

A Kafka change is **BLOCKED** if KRaft quorum is degraded/unknown, under-minISR or offline partitions are present, critical telemetry is missing, fast SLO burn is active, PVC pressure is critical, required TLS/ACL or GitOps approvals are absent, or rollback is not reviewed. Approved exceptions must have a named risk owner, ticket, expiry, safeguards and evidence; an exception must never authorize uncontrolled data loss.

## 7. Twenty Kubernetes-first capstone labs

### Lab 01 — Approve capstone charter and abort criteria

**Objective and procedure:** Obtain test-only authorization, incident commander, SLO owner, security reviewer, Kubernetes context, rollback plan, synthetic data policy and explicit scope exclusions.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 02 — Verify Kubernetes/Strimzi/KRaft inventory

**Objective and procedure:** Capture Kafka CR and NodePools, Kafka version and CRD API, operator image, Pods, PVCs, StorageClasses, network policies, TLS listeners and KRaft quorum.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 03 — Verify quorum, ISR and durability contract

**Objective and procedure:** Record metadata quorum voters/leader, topic RF/minISR, acks=all synthetic producer contract, under-replicated/under-minISR signals and safety gates.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 04 — Verify application service ownership

**Objective and procedure:** Map each producer/consumer, event contract, topic, service tier, primary/backup on-call, runbook, escalation and risk owner.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 05 — Define producer SLI acceptance

**Objective and procedure:** Measure eligible callback attempts and successful acknowledgments with verified counters and synthetic event ledger, excluding duplicate retries appropriately.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 06 — Define end-to-end consumer SLI acceptance

**Objective and procedure:** Reconcile unique accepted IDs to durably processed IDs, commits, idempotent sink and event-age thresholds; record downstream dependency health.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 07 — Validate SLO and error-budget governance

**Objective and procedure:** Review 30-day window, targets, eligibility, exclusions, allowed failures, budget consumed and freeze/exception policy with business owner.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 08 — Validate Prometheus target and rule correctness

**Objective and procedure:** Check expected versus actual broker/controller/client/Strimzi/infra targets, metric types, rate and histogram aggregation, missing-series handling and promtool tests.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 09 — Validate multiwindow burn-rate alerts

**Objective and procedure:** Run synthetic 5m/1h fast-burn and 30m/6h medium-burn test series, minimum traffic guardrails and No Data detection.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 10 — Validate Alertmanager paging governance

**Objective and procedure:** Exercise lab-only receiver, owner labels, routing, grouping, inhibition, silence expiry, backup escalation, acknowledgment and audit receipts.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 11 — Validate Grafana SLO dashboards

**Objective and procedure:** Cross-check raw synthetic ledger with producer callback SLI, consumer freshness, error budget, KRaft/ISR, PVC pressure and telemetry blind spots.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 12 — Validate logs and OpenTelemetry traces

**Objective and procedure:** Correlate synthetic event IDs across producer/consumer logs, trace spans, Kafka headers, incident timeline, collector drops and redaction policy.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 13 — Validate Kubernetes storage and capacity gates

**Objective and procedure:** Inspect PVC actual utilization, storage IOPS/latency, node CPU/memory, broker disk forecasts and Kafka retention, separating allocation from usage.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 14 — Validate GitOps and RBAC security gates

**Objective and procedure:** Review namespace Roles/ServiceAccounts, Secrets access, TLS/SASL/ACLs, pinned images, CR spec changes, approvals and supported rollback.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 15 — Validate read-only reliability automation

**Objective and procedure:** Review CronJob least privilege, idempotency, bounded retries, missing-data UNKNOWN behavior, audit output and safe-stop procedures.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 16 — Run synthetic producer failure incident

**Objective and procedure:** Inject client-only callback failures, declare incident, verify SLO burn and on-call notification, restore client and reconcile unique accepted events.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 17 — Run synthetic consumer freshness incident

**Objective and procedure:** Pause only an isolated consumer Deployment briefly, observe event-age breach, escalate, resume, measure backlog drain and verify durable processing.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 18 — Run quorum/ISR tabletop and change freeze

**Objective and procedure:** Use synthetic incident cards/metrics, never kill Kafka controllers, validate owner decision, release BLOCK, exception policy and rollback readiness.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 19 — Complete incident command and postmortem

**Objective and procedure:** Write timestamped detection-to-recovery timeline, stakeholder updates, decisions, contributing factors, blameless corrective actions, owners and due dates.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

### Lab 20 — Execute independent readiness assessment

**Objective and procedure:** Re-run read-only verification, inspect evidence package, score 100-point rubric, reject untested critical gates and issue signed Ready/Not Ready decision.

**Evidence and acceptance:** Record the exact Kubernetes context, Kafka/Strimzi versions, approved scope, source query/command, expected and observed result, UTC timestamp, risk owner, security check, rollback and independent assessor. A lab is **Pending** until actually executed. All drills use synthetic data and bounded client-only changes.

## 8. Safe execution sequence

1. Confirm approval, cluster context, Kafka version, Strimzi compatibility, topic ownership, secure listener and test-only Alertmanager route.
2. Capture Kafka CR, KafkaNodePool, Pods, PVCs, KRaft quorum and actual ISR/under-minISR metrics before any synthetic incident.
3. Start a bounded synthetic producer/consumer workflow with unique event IDs and an idempotent sink.
4. Measure eligible attempts, successful callbacks, processed unique IDs, event age, source ledger and SLO ratios.
5. Validate Prometheus target inventory, rule semantics, fast/medium burn alerts and missing-series behavior.
6. Trigger only synthetic client-side errors or isolated consumer pause, then run incident command, lab paging and safe recovery.
7. Reconcile accepted and processed unique IDs; verify lag/event-age drain, Kafka quorum/ISR, alert resolution and GitOps gate behavior.
8. Produce postmortem, corrective actions, security review, readiness score and independent signoff.

**Abort immediately** if Kafka quorum/ISR degrades unexpectedly, a non-lab on-call route is paged, resource pressure affects shared namespaces, secrets appear in output or data integrity cannot be reconciled.

## 9. Read-only verification script

Save as `verify-ch45.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
mkdir -p evidence-ch45
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/12] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[5/12] PVCs and storage'
kubectl -n "$NS" get pvc -o wide
echo '[6/12] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[7/12] Kafka metrics configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[8/12] Monitoring CRDs'
for crd in prometheusrules.monitoring.coreos.com servicemonitors.monitoring.coreos.com; do
  if kubectl get crd "$crd" >/dev/null 2>&1; then echo "FOUND: $crd"; else echo "PENDING: $crd"; fi
done
echo '[9/12] PrometheusRule inventory'
kubectl get prometheusrules -A -o wide 2>/dev/null || true
echo '[10/12] RBAC and automation'
kubectl -n "$NS" get serviceaccounts,roles,rolebindings,cronjobs
echo '[11/12] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka reliability capstone platform inventory.'
echo 'NOT PROVEN: SLOs, alert routing, incident drills, security or enterprise readiness.'
```

Run `chmod +x verify-ch45.sh && ./verify-ch45.sh | tee evidence-ch45/preflight.txt`. This script checks platform inventory only. The internal plaintext 9092 bootstrap convention is for disposable labs; production-like client tests must use approved TLS/SASL and scoped Kafka ACLs.

## 10. Twelve capstone failure scenarios

### Scenario 1 — Kafka Ready but producer SLO failing

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 2 — Consumer lag low while event age grows

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 3 — KRaft quorum status unknown during change

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 4 — Under-minISR alarm muted by maintenance silence

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 5 — Error-budget denominator excludes failed events

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 6 — Prometheus missing broker target displayed as green

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 7 — Alertmanager test receiver does not acknowledge

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 8 — Synthetic event ledger reveals duplicates or loss

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 9 — TLS/ACL exception bypasses secure acceptance

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 10 — PVC capacity dashboard reports allocation not usage

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 11 — GitOps release proceeds under fast burn

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

### Scenario 12 — Postmortem closes without action owners or verification

**Detection:** Compare Kafka CLI/quorum and ISR with Prometheus targets, Alertmanager state, client callbacks and unique-event ledger. **Diagnosis:** Check SLO denominator, missing metrics, producer retries, consumer processing, Kubernetes PVC/Pod health, security, GitOps changes and incident ownership. **Response:** Freeze unsafe changes, escalate to accountable owners and apply only approved client/test remediation. **Acceptance:** Reconcile event IDs, restore SLI/freshness, validate alerts and preserve a redacted incident timeline.

## 11. Eight production SRE runbooks

### Runbook A — Kafka enterprise SRE readiness gate

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook B — KRaft quorum and under-minISR emergency

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook C — Producer acknowledgment and error-budget incident

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook D — Consumer freshness and durable processing incident

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook E — Prometheus/Alertmanager blind spot

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook F — Kubernetes node/PVC and Strimzi reconciliation

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook G — GitOps freeze, exception and rollback

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

### Runbook H — Incident command, postmortem and signoff

1. Identify affected service tier, SLO, incident severity and accountable on-call.
2. Verify Kafka Ready, KRaft quorum, ISR and Kubernetes/Strimzi state independently.
3. Reconcile synthetic producer callback and consumer unique-processing ledgers.
4. Validate Prometheus freshness, error-budget burn, alert routing and incident timeline.
5. Apply approved mitigation, change freeze or GitOps rollback without weakening durability.
6. Verify recovery, alert resolution, data integrity and residual risk.
7. Capture owner signoff, security review, corrective actions and audit evidence.

## 12. Evidence package

```text
evidence-ch45/
  capstone-charter-and-approval.md
  abort-and-rollback-policy.md
  context-and-version-matrix.md
  preflight.txt
  kafka-kraft-isr-baseline.md
  tls-acl-rbac-security-review.md
  service-ownership-raci.md
  producer-sli-and-ledger.md
  consumer-processed-ledger.md
  slo-governance-policy.md
  error-budget-calculation.csv
  prometheus-target-inventory.md
  promtool-rule-tests.md
  burn-rate-alert-receipts.md
  alertmanager-routing-escalation.md
  grafana-slo-dashboard-review.md
  logs-traces-correlation.md
  pvc-capacity-review.md
  gitops-rollback-and-freeze.md
  readonly-automation-review.md
  synthetic-producer-incident.md
  synthetic-consumer-incident.md
  quorum-isr-tabletop.md
  incident-timeline-and-updates.md
  blameless-postmortem.md
  corrective-action-tracker.csv
  readiness-scorecard.md
  independent-assessor-signoff.md
```

Every artifact must state source, exact version, UTC time window, expected/observed outcome, service owner, redaction, rollback, reviewer and retention. Missing evidence means Pending/Not Ready.

## 13. 100-point enterprise SRE readiness assessment

| Domain | Points | Critical |
|---|---:|---|
| Capstone approval, scope, abort and ownership | 10 | Yes |
| KRaft quorum, ISR, Kafka/Strimzi/Kubernetes safety | 15 | Yes |
| Producer callback and consumer unique-processing SLIs | 15 | Yes |
| SLO targets, eligibility, budgets and governance | 10 | Yes |
| Prometheus, burn alerts and no-data correctness | 10 | Yes |
| Alertmanager routing, escalation and dashboards | 10 | Yes |
| Safe incident drills, recovery and data reconciliation | 10 | Yes |
| GitOps gates, rollback, RBAC and security | 10 | Yes |
| Incident command, postmortem and corrective actions | 5 | Yes |
| Independent evidence review and final signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and **all critical gates evidenced and passed**. **Automatic Fail:** fabricated live results, uncontrolled broker/controller disruption, weakened durability, unreviewed TLS/ACL exception, unowned critical alert, missing telemetry interpreted as healthy, unaccounted synthetic events, no rollback or missing independent security/operational signoff.

**Readiness decision:** READY only when the full capstone is executed and accepted; otherwise NOT READY/PENDING. Chapter publication does not change this state.

## 14. Cleanup, references and next part

Remove only chapter-owned synthetic client workloads, test alert rules, test receivers and temporary CronJobs through approved GitOps. Preserve sanitized evidence and action backlog. Never delete Kafka PVCs, production offsets, shared Prometheus data or operator-managed Secrets.

**References:** [Google SRE Workbook](https://sre.google/workbook/), [Google SRE Book](https://sre.google/sre-book/table-of-contents/), [Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Prometheus](https://prometheus.io/docs/), [Kubernetes](https://kubernetes.io/docs/), [OpenTelemetry](https://opentelemetry.io/docs/).

**Part 09 — SRE, SLIs, SLOs and Reliability is fully published (Chapters 041–045).**

**Next:** Chapter 046 — Kafka Troubleshooting Methodology, Evidence Collection and Kubernetes Incident Triage, beginning Part 10 — Troubleshooting and Incident Response.

---

**Verification boundary:** GitHub publication verifies the document, not execution. All live capstone drills, alert routing, SLO validation, security review and independent readiness acceptance remain Pending.
