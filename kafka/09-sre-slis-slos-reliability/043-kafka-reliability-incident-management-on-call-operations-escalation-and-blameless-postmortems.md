# Chapter 043 — Kafka Reliability Incident Management, On-Call Operations, Escalation and Blameless Postmortems

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 09 — SRE, SLIs, SLOs and Reliability (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–042, especially monitoring (036–040) and SLO/change-gate engineering (041–042)  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** All drills use approved synthetic clients, test alerts, a disposable Kubernetes cluster and a lab-only communications channel. Do not page actual production on-call, restart brokers/controllers, delete PVCs, reset production consumer offsets, bypass TLS/ACLs or reduce replication safety. For high-risk failures use tabletop or synthetic metric injection, not a real Kafka outage. Publication does not establish that any drill was executed.

## 1. Mission and learning objectives

Operate Kafka as an accountable service, not merely a healthy set of brokers. Establish incident command, severity and escalation policy, on-call readiness, rapid diagnosis, reliable stakeholder communications, safe recovery and blameless learning. Connect customer-impacting producer/consumer SLIs to Kafka KRaft quorum, ISR, Strimzi reconciliation, Kubernetes Nodes/PVCs and observability. Build an evidence-based incident record and verify that accepted synthetic events are processed exactly as the application contract requires.

By completion, learners should be able to declare an incident, assign roles, gather independent evidence, protect durability, decide when to freeze/rollback changes, coordinate response across teams, confirm end-to-end recovery, write a blameless postmortem and track corrective actions.

## 2. Kafka incident response operating model

```text
Producer errors / consumer event-age / Kafka quorum / under-minISR
                      |
             Prometheus + Alertmanager
                      |
            On-call acknowledgment
                      |
        Severity + incident commander
                      |
       +--------------+----------------+
       |              |                |
  Kafka SRE       Platform SRE     App producer/
  KRaft/ISR       K8s/PVC/CSI      consumer owners
       |              |                |
       +--------------+----------------+
                      |
      Evidence + mitigation + GitOps decision
                      |
       Recovery SLI + data integrity checks
                      |
     Incident closure + blameless postmortem
```

**Separation of responsibilities:** The incident commander coordinates, sets priorities and approves communications; the technical lead diagnoses Kafka and application behavior; the communications lead reports impact and next updates; the safety observer enforces abort conditions in labs. A single person may fill multiple roles for small exercises, but each role must be explicit.

## 3. Severity, paging and escalation policy

| Severity | Example Kafka impact | Initial response | Escalation |
|---|---|---|---|
| SEV1 | confirmed widespread data-delivery failure, quorum/durability emergency, material business impact | immediate incident command and page | Kafka SRE, platform, app, security as needed |
| SEV2 | sustained SLO burn, under-minISR, major processing backlog | urgent on-call response | service owner + dependent teams |
| SEV3 | limited degradation with workaround, no current durability risk | assigned response during coverage | team owner |
| SEV4 | non-urgent defect or toil improvement | ticket and planned review | backlog owner |

Response-time targets and customer communications must be set by the organization; this table is a **design example**, not an existing organizational policy. Missing telemetry or a broken paging route may warrant an incident even when customer impact is not yet established.

## 4. On-call and incident command contracts

| Role | Responsibilities | Required handoff |
|---|---|---|
| Primary Kafka on-call | acknowledge, assess quorum/ISR/broker signals, engage commander | current status, open alerts, access/runbooks |
| Backup on-call | assume ownership on non-response or fatigue | incident ID, timeline, next actions |
| Incident commander | severity, roles, decisions, status cadence, risk/abort authority | decisions, owner assignments |
| Application owner | producer/consumer errors, event ledger, downstream health | accepted/processed reconciliation |
| Platform owner | Kubernetes, node, storage, network and Strimzi | resource and rollout evidence |
| Communications lead | internal/external updates and next-update time | verified impact and uncertainty |
| Security owner | identity, audit, privacy and break-glass oversight | access log and approved actions |

A reliable handoff states what is known, what is unknown, what has been changed, the next decision deadline, who owns each action and what would trigger escalation.

## 5. First 15 minutes: operational sequence

1. **Acknowledge:** Record alert, timestamp, affected service, owner and SLO.
2. **Declare:** Determine severity and appoint incident commander/technical lead.
3. **Protect:** Freeze risky deployments when quorum, ISR, storage or SLO burn is degraded.
4. **Verify:** Check Kafka Ready, KRaft quorum, ISR, broker/Pod/PVC health and client event ledger independently.
5. **Scope:** Identify affected topics, producers, consumer groups, tenants, regions and data integrity risk.
6. **Communicate:** Publish impact, mitigation underway, known uncertainty and next update time.
7. **Mitigate:** Apply the lowest-risk approved action with rollback and change audit.
8. **Validate:** Confirm producer callbacks, unique processed events, freshness, backlog drain and alert resolution.

Avoid guessing root cause during the initial update. An error-budget alert indicates service impact, not automatically a Kafka broker defect.

## 6. Kubernetes-first preflight and evidence commands

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch43
kubectl config current-context | tee evidence-ch43/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch43/inventory.txt
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp \
  | tee evidence-ch43/events.txt
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}' \
  | tee evidence-ch43/kafka-conditions.txt
kubectl -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch43/quorum.txt
```

The internal plaintext 9092 bootstrap convention is **isolated lab only**. For production-like clients, use a reviewed TLS/SASL listener and least-privilege ACLs. Redact any principal, address, token or sensitive log field before committing evidence.

## 7. Twenty hands-on incident response labs

### Lab 01 — Approve incident simulation and scope

**Objective and procedure:** Identify disposable cluster, owner, incident commander, safety observer, test receiver, synthetic producer/consumer group, change ticket and abort conditions. Prohibit real paging and broker disruption.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 02 — Build Kafka service ownership matrix

**Objective and procedure:** Assign Kafka SRE, Kubernetes platform, application producer/consumer, Strimzi/GitOps, observability, security, and communications owners with primary and backup escalation paths.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 03 — Capture healthy baseline

**Objective and procedure:** Check Kafka CR Ready, KafkaNodePools, Pods, PVCs, KRaft quorum, replication, Prometheus targets, synthetic producer acknowledgments and consumer event-age ledger.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 04 — Define incident severity taxonomy

**Objective and procedure:** Classify SEV1–SEV4 using customer impact, durability exposure, event-age SLO breach, KRaft/ISR safety, and unknown observability; map severity to response deadlines.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 05 — Design on-call rotation and handoff

**Objective and procedure:** Define coverage, backup, handoff checklist, runbook freshness, access prerequisites, least-privilege break-glass and fatigue/toil review.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 06 — Define alert-to-incident conversion

**Objective and procedure:** Map fast-burn, under-minISR, quorum, producer errors, consumer event-age, and missing telemetry alerts to incidents with deduplication and ownership.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 07 — Build incident commander checklist

**Objective and procedure:** Set roles, bridge/channel, situation report cadence, decision log, technical lead, communications lead and explicit stop/rollback authority.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 08 — Practice initial triage in Kubernetes

**Objective and procedure:** Use kubectl get Kafka/KafkaNodePool/Pods/Events and metadata-quorum CLI; compare raw Kafka metrics with synthetic event ledger without restarting brokers.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 09 — Practice KRaft quorum escalation tabletop

**Objective and procedure:** Simulate quorum degradation using mock metrics/incident cards; require platform safety owner and change freeze; do not remove controller Pods.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 10 — Practice under-minISR durability tabletop

**Objective and procedure:** Use an injected test-only alert to review RF/minISR, follower health, disk/network and produce acknowledgment implications; prohibit weakening acks/minISR.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 11 — Practice producer callback failure drill

**Objective and procedure:** Inject failures in isolated synthetic client, measure error ratio, retries, callback latency, eligible events and SLO burn, and escalate to application/Kafka owners.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 12 — Practice consumer backlog and freshness drill

**Objective and procedure:** Pause only an isolated synthetic consumer Deployment briefly, restore it, reconcile offsets, event age and unique processed IDs, and record time to recover.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 13 — Investigate node/PVC pressure scenario

**Objective and procedure:** Use safe historical/synthetic dashboards and Kubernetes events to distinguish CPU throttling, OOM, PVC capacity and disk latency; select approved remediation.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 14 — Correlate metrics, logs and traces

**Objective and procedure:** Reconstruct a synthetic incident timeline from Prometheus/Grafana, redacted broker/operator logs, OTel client spans, Kafka CLI and GitOps changes.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 15 — Practice stakeholder communications

**Objective and procedure:** Write an initial incident update, a scheduled follow-up, an internal escalation and a recovery notice with impact, mitigation, next update and uncertainty.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 16 — Practice escalation and ownership handoff

**Objective and procedure:** Simulate primary non-response, backup escalation, cross-team dependency, incident commander transfer and continuity of timeline/evidence.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 17 — Execute controlled rollback decision

**Objective and procedure:** Review a synthetic GitOps change causing client-only errors; document safe rollback, verification gates, approvals and why real Kafka CR rollback may be unsafe.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 18 — Validate recovery and data integrity

**Objective and procedure:** Verify Kafka Ready/quorum/ISR, client acknowledgment SLI, event-age drain, unique processed ledger, alert resolution and no unaccounted synthetic messages.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 19 — Write a blameless postmortem

**Objective and procedure:** Document customer impact, timeline, contributing technical/organizational factors, detection and response gaps, evidence, what went well and corrective actions with owners.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

### Lab 20 — Run post-incident acceptance review

**Objective and procedure:** Score response against the 100-point rubric, verify action ownership/due dates, review toil and alert noise, capture redacted evidence and independent signoff.

**Expected result:** A time-stamped, role-owned incident artifact with a clear decision, verified source evidence, customer-impact assessment, safe rollback or abort path and next action. **Evidence:** Save sanitized commands, query screenshots, synthetic event ledger, communication samples and assessor notes. Mark **Pending** until actually executed; a written scenario is not a passed drill.

## 8. Synthetic incident drill — client-side failures only

**Setup:** Use an isolated KafkaTopic and consumer group, a bounded producer, idempotent synthetic sink, approved monitoring stack and lab-only Alertmanager receiver. Record the unique accepted-event ledger and expected SLI.

**Injection:** Cause a test-only producer callback error or pause only the synthetic consumer Deployment briefly; do not affect shared consumer groups or Kafka brokers.

**Response:** Open an incident, appoint commander, verify KRaft/ISR health, compare synthetic error/freshness SLI to Prometheus, acknowledge a lab alert, communicate impact and mitigate the client issue.

**Recovery:** Restore client behavior, measure event-age drain, reconcile unique accepted/processed IDs, verify no unexplained loss, close alerts and document response latency. Distinguish duplicate delivery attempts from unique business events.

**Abort:** Stop the drill immediately if Kafka Ready/quorum/ISR becomes degraded, production receivers are paged, resource pressure rises unexpectedly or any unapproved namespace is affected.

## 9. Read-only verification script

Save as `verify-ch43.sh`:

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
echo '[3/10] Kafka/NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/10] Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[5/10] PVCs'
kubectl -n "$NS" get pvc -o wide
echo '[6/10] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[7/10] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[8/10] Prometheus Operator inventory'
kubectl get prometheusrules -A -o wide 2>/dev/null || true
echo '[9/10] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[10/10] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only incident response platform inventory.'
echo 'NOT PROVEN: paging, escalation, communications, synthetic drill, recovery or independent review.'
```

Run `chmod +x verify-ch43.sh && ./verify-ch43.sh | tee evidence-ch43/preflight.txt`. An inventory PASS is not incident-management acceptance.

## 10. Twelve troubleshooting and incident scenarios

### Scenario 1 — KRaft quorum appears degraded but dashboard stale

**Diagnosis and response:** Verify quorum CLI and scrape freshness before paging; block changes if quorum uncertain. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 2 — Under-minISR alert with active producer failures

**Diagnosis and response:** Confirm ISR/minISR and callback errors; do not reduce durability settings to restore apparent success. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 3 — Producer errors masked by retries

**Diagnosis and response:** Reconcile callback attempts and unique accepted events; escalate customer-impacting failures. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 4 — Consumer lag low while event age breaches SLO

**Diagnosis and response:** Check processing ledger, commits, stale group exporter and downstream bottleneck. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 5 — Broker Pod Pending due to PVC binding

**Diagnosis and response:** Inspect scheduling, PVC, CSI and node topology; avoid deleting stateful PVCs. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 6 — CPU throttling drives request latency

**Diagnosis and response:** Correlate cAdvisor CFS, JVM GC and request queue; review approved resources. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 7 — Alertmanager silence suppresses SEV1 alert

**Diagnosis and response:** Audit active silences, inhibition and route, restore coverage, notify on-call. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 8 — No primary on-call acknowledgment

**Diagnosis and response:** Escalate to backup and incident commander per policy; record elapsed time. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 9 — Strimzi reconciliation fails after GitOps change

**Diagnosis and response:** Inspect CR observed generation, operator logs and Git diff; choose supported rollback. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 10 — Monitoring outage obscures customer impact

**Diagnosis and response:** Use independent CLI and synthetic ledger; declare monitoring blindness and avoid false green. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 11 — Duplicate events after consumer restart

**Diagnosis and response:** Reconcile unique IDs and idempotent sink; separate duplicate attempts from business loss. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

### Scenario 12 — Premature incident closure before backlog drains

**Diagnosis and response:** Require event-age, unique processing and alert resolution gates; reopen if unmet. Confirm the customer-facing SLI, Kafka quorum/ISR, Pod/PVC status and relevant application ledger. **Communication:** State verified impact and uncertainty, incident owner and next update. **Evidence:** Preserve timestamps, metric/CLI comparison, change history, action owner and recovery gate. **Closure:** Do not close before SLO and data-integrity checks pass.

## 11. Eight production SRE runbooks

### Runbook A — Declare and coordinate Kafka SEV1/SEV2

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Verify severity, appoint commander, page platform and app owners, set update cadence, freeze risky changes and capture baseline. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook B — KRaft quorum or under-minISR emergency

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Check metadata quorum CLI and ISR, protect durability, escalate Kafka/platform SRE, follow approved recovery and verify safety. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook C — Producer delivery SLO breach

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Compare callbacks, retries, acks, quotas, request latency and broker health; mitigate safely and reconcile accepted IDs. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook D — Consumer event-age and backlog incident

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Inspect assignments, processing errors, commits, lag, downstream latency and event age; restore synthetic workload and verify drain. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook E — Kubernetes resource and PVC incident

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Correlate Pod/Node/PVC/CSI metrics, recent changes and Kafka storage; avoid unsafe PVC deletion or Pod disruption. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook F — Telemetry or paging outage

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Check targets, missing-series rules, Alertmanager routes/silences and alternative sources; test recovery using lab receiver. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook G — GitOps change freeze and rollback

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Check change ID, owner, Kafka/Strimzi supported rollback path, quorum/ISR gates, impact and post-rollback verification. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

### Runbook H — Postmortem, action tracking and on-call handoff

**Trigger:** An approved incident severity, customer-facing SLO breach or validated Kafka safety signal. **Actions:** Produce evidence-backed blameless timeline, contributing factors, owner/due-date actions, review acceptance and update runbooks. **Verification:** Reconcile source telemetry, independent Kafka CLI and client event ledger; check rollback and alert resolution. **Exit:** Incident commander signs off on impact, data integrity, residual risk, communications and follow-up actions.

## 12. Incident communications templates

**Initial update:** "We are investigating elevated Kafka event-processing latency affecting the synthetic lab service since [UTC time]. Kafka quorum and replication health are [verified status/unknown]. The incident commander is [role]. Next update by [UTC time]."

**Progress update:** "Impact remains [measured scope]. We have [confirmed evidence] and are [approved mitigation]. No data-loss conclusion is being made until the unique-event ledger is reconciled. Next update by [UTC time]."

**Recovery update:** "Synthetic producer acknowledgments and consumer processing have returned within the agreed SLO thresholds as of [UTC time]. Backlog drain and accepted-versus-processed reconciliation are [complete/pending]. We will publish a postmortem and corrective actions."

Replace placeholders only with verified facts. Do not claim "no data loss" based solely on Kafka Ready or green Grafana panels.

## 13. Blameless postmortem standard

Use this outline: summary and customer impact; timeline with UTC timestamps; detection and alerting; what happened technically; contributing factors across design, tooling, process and ownership; what worked; what slowed response; recovery and data-integrity evidence; corrective actions with owners, priority, due date and validation; unresolved questions; review and signoff.

A blameless review focuses on system conditions and decisions under the information available at the time. It does not suppress factual accountability, security incidents or required compliance investigations.

## 14. Evidence package

```text
evidence-ch43/
  approval-and-abort-criteria.md
  ownership-raci-and-escalation.md
  preflight.txt
  context.txt
  inventory.txt
  events.txt
  kafka-conditions.txt
  quorum.txt
  baseline-sli-and-isr.md
  severity-policy.md
  oncall-handoff.md
  incident-declaration.md
  commander-decision-log.md
  alert-to-incident-map.md
  client-error-drill.md
  consumer-backlog-drill.md
  kafka-safety-tabletop.md
  kubernetes-pvc-tabletop.md
  metrics-logs-traces-timeline.md
  stakeholder-updates.md
  escalation-test.md
  gitops-rollback-decision.md
  accepted-processed-ledger.csv
  recovery-acceptance.md
  blameless-postmortem.md
  corrective-action-tracker.csv
  assessor-signoff.md
```

Evidence must include source, UTC time range, software version, expected/observed outcome, service owner, redaction status, action owner, reviewer and retention policy. No fabricated live results.

## 15. 100-point enterprise incident response assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, safety approval and incident ownership | 10 | Yes |
| On-call rotation, severity and escalation | 15 | Yes |
| Kafka/KRaft/ISR and Kubernetes baseline | 15 | Yes |
| Incident command, decisions and communications | 15 | Yes |
| Producer/consumer customer-impact diagnosis | 10 | Yes |
| Synthetic incident and safe recovery | 10 | Yes |
| Data-integrity and SLO recovery verification | 10 | Yes |
| GitOps rollback and security controls | 5 | Yes |
| Blameless postmortem and corrective actions | 5 | Yes |
| Independent review and evidence quality | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** unapproved production paging/disruption, data-loss claims without reconciliation, bypassed quorum/ISR/TLS safeguards, missing incident ownership, fabricated drill results or absent independent security review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic client workloads, test alerts and temporary communication resources through approved procedures. Preserve redacted incident evidence and corrective actions; do not delete Kafka PVCs, production consumer offsets, shared monitoring data or operator-managed Secrets.

**References:** [Google SRE Workbook — Incident Response](https://sre.google/workbook/incident-response/), [Google SRE Book — Managing Incidents](https://sre.google/sre-book/managing-incidents/), [Google SRE Book — Postmortem Culture](https://sre.google/sre-book/postmortem-culture/), [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/).

**Next:** Chapter 044 — Kafka SRE Toil Reduction, Reliability Automation, Operational Readiness and Continuous Improvement.

---

**Verification boundary:** GitHub publication confirms the document only. Live drills, paging, escalation, data-integrity checks, postmortem review and independent security acceptance remain Pending.
