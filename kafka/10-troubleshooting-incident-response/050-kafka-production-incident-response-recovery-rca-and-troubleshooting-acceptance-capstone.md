# Chapter 050 — Kafka Production Incident Response, Recovery, RCA and Troubleshooting Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 10 — Troubleshooting and Incident Response (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–049, especially 041–049  
**Status:** Published · **Live capstone execution:** Pending · **Independent technical/security review:** Pending

> **Safety and acceptance boundary:** This chapter models production-grade incident response but authorizes only disposable Kubernetes labs, synthetic Kafka clients and tabletop quorum/storage failures. Never kill production brokers/controllers, delete PVCs, reset shared offsets, weaken acks/minISR, disable TLS/SASL/ACLs or send test pages to real responders. Do not claim a passed drill, RCA or readiness decision until independently executed and evidenced.

## 1. Mission

Integrate Chapters 046–049 into one end-to-end Kafka incident response exercise. Detect and classify customer impact, investigate Kafka KRaft quorum/ISR and Strimzi/Kubernetes conditions, diagnose producer/consumer and secure connectivity failures, coordinate recovery through approved change gates, reconcile unique accepted/processed events, write an evidence-based blameless RCA and earn independent SRE operational acceptance.

## 2. Learning objectives

- Operate an incident command structure with clear severity, escalation, communications and stop authority.
- Gather reproducible, time-bounded, redacted evidence across Kafka CLI, Kubernetes, Strimzi, Prometheus, logs and client ledgers.
- Separate KRaft/controller, broker/ISR, PVC/CSI, networking/TLS/ACL and application failures.
- Choose safe mitigation and GitOps rollback without trading durability or security for apparent availability.
- Verify recovery with producer callback SLI, consumer event-age and durable unique-event reconciliation.
- Produce RCA, contributing-factor analysis, corrective-action tracker, runbook changes and independent acceptance.

## 3. Incident architecture and escalation flow

```text
Synthetic producer --> Kafka Strimzi/KRaft --> Synthetic consumer --> idempotent sink
       |                  |                       |                |
   callbacks         quorum / ISR              lag / age       event ledger
       +------------------+-----------------------+----------------+
                              |
                        SLO and alert
                              |
                   Incident commander (IC)
                     /        |        \
                Kafka SRE  Platform SRE  Application owner
                     \        |        /
                       Evidence scribe
                              |
                    Hypothesis + safety gate
                              |
                    Approved mitigation
                              |
             End-to-end recovery verification
                              |
                 RCA + independent signoff
```

## 4. Incident severity, governance and change gates

| Gate | Evidence | Decision if absent or failing |
|---|---|---|
| Scope/ownership | affected service, topic, on-call and IC | ESCALATE |
| KRaft quorum | leader, voters, health and controller logs | BLOCK changes |
| Replication safety | leaders, ISR/minISR, offline partitions | BLOCK unsafe changes |
| Storage | PVC, CSI, disk pressure and latency | BLOCK storage mutations |
| Security | TLS/SASL/ACL, RBAC and secret hygiene | BLOCK bypass |
| Observability | target freshness, SLO and no-data status | UNKNOWN/ESCALATE |
| Application delivery | acknowledged unique IDs vs durable sink | KEEP incident open |
| GitOps rollback | approved diff, blast radius, owner | BLOCK |
| Communications | timestamps, update owner, incident channel | ESCALATE |

**Do not assume that Kafka CR Ready, low consumer lag or a green dashboard proves successful end-to-end processing.**

## 5. Production incident response timeline

| Time | Expected action | Evidence |
|---|---|---|
| 0–5 minutes | acknowledge, assess impact, appoint IC, freeze unsafe changes | incident ID, severity, affected SLIs |
| 5–15 minutes | validate Kafka quorum/ISR, client symptoms, platform and telemetry | UTC snapshot, alerts, topic metadata |
| 15–30 minutes | form/falsify hypotheses, assign workstreams, send stakeholder update | decision log and source evidence |
| 30+ minutes | execute only approved mitigation, monitor side effects | change ticket, rollback and outcome |
| Recovery | reconcile unique events and processing deadlines | producer/consumer/sink ledger |
| Postincident | blameless RCA, corrective actions, owners and verification | reviewed report and action tracker |

Timings are practice targets, not service commitments; real incident priorities depend on severity and response policies.

## 6. Safe read-only evidence commands

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc,svc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get kafka sre-kafka -o jsonpath='{.status.conditions}{"\n"}'
kubectl -n kafka-lab get networkpolicy

# Approved isolated Kafka CLI Pod; plaintext 9092 is lab-only.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-incident-synthetic
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-incident-synthetic-group

# Bounded logs, selected from actual Pod inventory.
kubectl -n kafka-lab logs SYNTHETIC_CLIENT_POD --since=15m --timestamps --tail=300
```

In production-like settings use approved TLS/SASL, scoped Kafka ACLs, version-supported CLI properties and sanitized output. The isolated lab topic/group and CLI Pod are prerequisites, not assumed existing resources.

## 7. Twenty Kubernetes-first capstone labs

### Lab 01 — Approve enterprise incident capstone charter

**Objective and procedure:** Record test-only context, service tier, incident commander, security reviewer, observers, abort gates, change freeze, rollback and synthetic data retention.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 02 — Verify Kafka/Kubernetes/KRaft baseline

**Objective and procedure:** Capture Kafka/NodePools, operator version, Pod/PVC/CSI, quorum, topic ISR, listener security, monitoring freshness and owner roster.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 03 — Define severity and escalation policy

**Objective and procedure:** Map producer callback SLI, consumer freshness, accepted-event integrity and business impact to SEV thresholds and on-call escalation.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 04 — Validate incident detection and alert routing

**Objective and procedure:** Exercise test-only Prometheus/Alertmanager receivers, missing-target alerts, severity labels, runbook links and escalation receipts.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 05 — Build evidence collection bundle

**Objective and procedure:** Capture UTC command output, Kubernetes Events, bounded broker/controller/client logs, Kafka CR generation, metrics and sanitized metadata.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 06 — Validate incident command roles

**Objective and procedure:** Assign commander, technical leads, scribe, communications owner and decision authority; establish update cadence and handoff.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 07 — Triage KRaft quorum tabletop

**Objective and procedure:** Use synthetic leader/voter loss evidence, determine quorum safety, freeze change and propose version-supported escalation without controller disruption.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 08 — Triage under-minISR tabletop

**Objective and procedure:** Analyze synthetic follower lag, offline partitions and acks=all errors; reject weakening durability and document capacity/network hypotheses.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 09 — Triage PVC and storage tabletop

**Objective and procedure:** Review CSI attach, disk latency, queue, capacity and log-dir evidence; prohibit broker PVC deletion and unreviewed reassignment.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 10 — Triage Strimzi reconciliation incident

**Objective and procedure:** Compare desired GitOps revision, Kafka/NodePool status, operator logs, observed generation and supported rollback.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 11 — Run synthetic producer callback incident

**Objective and procedure:** Inject bounded test-client errors, measure callback SLI and retries, restore and reconcile accepted unique IDs.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 12 — Run synthetic consumer lag/freshness incident

**Objective and procedure:** Pause only isolated consumer Deployment, observe lag/event age and downstream sink, resume and verify backlog drain.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 13 — Run synthetic DNS and listener incident

**Objective and procedure:** Use invalid hostname in isolated client, inspect DNS, Service/EndpointSlice and advertised metadata, then restore.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 14 — Run synthetic TLS/SASL/ACL denial

**Objective and procedure:** Use restricted test principal against synthetic topic/group, capture denial, restore approved identity and confirm no broad permissions.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 15 — Validate telemetry-blind-spot handling

**Objective and procedure:** Use test-only missing-series scenario, ensure Unknown/No Data and incident escalation rather than green status.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 16 — Validate incident communication cadence

**Objective and procedure:** Prepare initial alert, status update, mitigation approval, customer-facing impact note and closure with UTC timestamps.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 17 — Validate recovery and data integrity

**Objective and procedure:** Reconcile producer-acknowledged unique IDs, topic offsets, durable sink IDs, duplicates and processing deadline; preserve unresolved gaps.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 18 — Validate rollback and error-budget governance

**Objective and procedure:** Demonstrate GitOps release BLOCK/EXCEPTION/APPROVE with quorum/ISR, SLO burn, telemetry and security approval gates.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 19 — Write blameless RCA and corrective actions

**Objective and procedure:** Build evidence-based causal graph, timeline, detection/mitigation/recovery metrics, contributing factors, owners, dates and verification tests.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

### Lab 20 — Complete independent acceptance review

**Objective and procedure:** Execute read-only verifier, review all artifacts, score 100-point rubric, document Ready/Not Ready and independent security signoff.

**Evidence and acceptance:** Record exact Kubernetes context, Kafka/Strimzi/client versions, UTC timestamps, source command/query, incident decision, expected/observed result, SLO and event ledger, security impact, abort/rollback and independent assessor. Mark **Pending** until executed. Tabletop drills must be labeled Simulated.

## 8. Read-only capstone verifier

Save as `verify-ch50.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-incident-synthetic
GROUP=sre-incident-synthetic-group
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/12] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods/PVCs'
kubectl -n "$NS" get pods,pvc -o wide
echo '[5/12] Services/EndpointSlices'
kubectl -n "$NS" get svc,endpointslices -o wide
echo '[6/12] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[7/12] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[8/12] Topic metadata'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo '[9/12] Consumer group'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-consumer-groups.sh" --bootstrap-server "$BS" --describe --group "$GROUP"
echo '[10/12] Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[11/12] Monitoring rule inventory'
kubectl get prometheusrules -A -o wide 2>/dev/null || true
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka incident capstone inventory.'
echo 'NOT PROVEN: incident execution, SLO, data integrity, RCA, security or acceptance.'
```

Run `chmod +x verify-ch50.sh && ./verify-ch50.sh | tee evidence-ch50/preflight.txt`. If Kafka is unhealthy, a failed `wait` is evidence, not permission to stop investigation or force a restart.

## 9. Twelve integrated failure scenarios

### Scenario 1 — Kafka Ready but customer acknowledgments fail

**Diagnose:** Compare callbacks, quotas, ISR, listener reachability and unique-event ledger. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 2 — KRaft quorum leader unavailable

**Diagnose:** Check voter majority, controller logs and metadata quorum; freeze mutations. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 3 — Under-minISR triggers producer failures

**Diagnose:** Inspect follower lag and disk/network pressure; preserve acks=all and minISR. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 4 — Broker Pod Pending because PVC not mounted

**Diagnose:** Inspect CSI/StorageClass/Node topology, events and approved recovery. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 5 — Strimzi reconciliation loops after GitOps change

**Diagnose:** Compare CR generation, operator errors, policy gates and reviewed rollback. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 6 — Producer TLS trust fails after rotation

**Diagnose:** Validate chain, SAN, truststore and application rollout; never disable TLS. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 7 — SASL succeeds but topic ACL denies

**Diagnose:** Correlate principal, resource and operation; avoid wildcard grants. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 8 — Consumer lag appears normal while sink is stale

**Diagnose:** Compare event timestamps, processing ledger and downstream commit. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 9 — Consumer group rebalance storm

**Diagnose:** Review poll interval, Pod churn, coordinator and assignments. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 10 — Prometheus target disappears during incident

**Diagnose:** Declare monitoring blind spot and use independent CLI/client ledger. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 11 — Rollback restores service but data discrepancy remains

**Diagnose:** Keep incident open until unique accepted events are reconciled. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

### Scenario 12 — Incident closed without owner or corrective-action validation

**Diagnose:** Reject acceptance; require signed action tracker and retest. Build a falsifiable hypothesis using Kafka CLI, KRaft/ISR, Strimzi CR, Kubernetes Events, client logs, Prometheus freshness and unique-event ledger. **Mitigate:** Only reviewed client-side lab action or tabletop-approved runbook; preserve security and durability. **Verify:** Independent SLI, data-integrity and recovery checks plus redacted UTC incident timeline.

## 10. Eight enterprise incident runbooks

### Runbook A — SEV declaration and first 15 minutes

**Trigger and response:** Acknowledge alert, appoint commander, freeze unsafe changes, verify SLO impact and collect baseline. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook B — KRaft quorum and metadata recovery escalation

**Trigger and response:** Verify quorum voters/leader, controller logs and approved vendor recovery; never alter voters ad hoc. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook C — Under-minISR and broker/replication recovery

**Trigger and response:** Inspect RF/ISR, follower lag, Pod/PVC and storage, preserve durability and verify producer callbacks. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook D — PVC, CSI and storage pressure incident

**Trigger and response:** Inspect mount, provisioning, IOPS, fsync and capacity; approve safe storage remediation. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook E — Producer/consumer end-to-end data incident

**Trigger and response:** Reconcile callbacks, topic offsets, consumer processing, sink commits, duplicates and freshness. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook F — Secure connectivity and authorization incident

**Trigger and response:** Inspect DNS, advertised listeners, TLS/SASL/ACL and NetworkPolicy without bypassing security. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook G — Strimzi GitOps freeze, rollback and change approval

**Trigger and response:** Review CR diff, reconciler status, safety gates, exception expiry and evidence. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

### Runbook H — Incident communications, RCA and closure

**Trigger and response:** Maintain UTC timeline, updates, safe recovery, root-cause confidence, action owners and independent signoff. **Safety gates:** Preserve KRaft quorum, ISR/minISR, TLS/SASL/ACLs and broker PVCs. **Closure:** Verify producer acknowledgments, durable sink ledger, event age, alert resolution, approved rollback, stakeholder update and independent reviewer.

## 11. Blameless RCA template

```md
# Incident INC-YYYYMMDD-NNN
Severity / service / topic / UTC start and end:
Incident commander / technical leads / reviewer:
Customer impact and affected SLI/SLO:
Detection path and detection delay:
Timeline (UTC, source-linked):
Competing hypotheses and tests:
Root cause (evidence-backed; otherwise "undetermined"):
Contributing factors:
Mitigation, recovery and rollback:
Kafka quorum/ISR and PVC safety evidence:
Unique accepted vs durably processed event reconciliation:
Security and data privacy review:
What worked / what did not:
Corrective action | Owner | Due date | Verification:
Independent approval and remaining risk:
```

A correlation is not necessarily root cause. If evidence is insufficient, state **Root cause undetermined** and assign follow-up investigation; do not manufacture certainty.

## 12. Evidence package

```text
evidence-ch50/
  capstone-approval-and-safety.md
  context-and-version-matrix.md
  preflight.txt
  severity-and-escalation.md
  alertmanager-test-routing.md
  kafka-kraft-isr-baseline.md
  kubernetes-pod-pvc-csi.md
  strimzi-gitops-reconciliation.md
  controller-quorum-tabletop.md
  replication-isr-tabletop.md
  storage-pressure-tabletop.md
  producer-client-drill.md
  consumer-freshness-drill.md
  dns-listener-drill.md
  tls-sasl-acl-drill.md
  telemetry-blind-spot.md
  incident-command-and-communications.md
  accepted-processed-ledger.csv
  rollback-and-error-budget-gates.md
  incident-utc-timeline.md
  rca-and-contributing-factors.md
  corrective-action-tracker.csv
  readiness-scorecard.md
  independent-security-review.md
  independent-acceptance-signoff.md
```

Each artifact must include source, exact versions, UTC timestamp, expected and observed results, owner, redaction, rollback and reviewer. Mark synthetic/tabletop outcomes accurately. Publication is not a passed capstone.

## 13. 100-point enterprise incident acceptance

| Domain | Points | Critical |
|---|---:|---|
| Scope, safety, severity and incident command | 10 | Yes |
| Kafka/KRaft quorum, ISR and broker diagnosis | 15 | Yes |
| Kubernetes/Strimzi Pod, PVC, CSI and GitOps | 15 | Yes |
| Producer and consumer incident triage | 15 | Yes |
| DNS/TLS/SASL/ACL and secure connectivity | 10 | Yes |
| Alerting, SLOs and telemetry blind spots | 10 | Yes |
| Recovery and unique-event reconciliation | 10 | Yes |
| RCA, communications and corrective actions | 10 | Yes |
| Independent security/technical signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced and passed. **Automatic Fail:** fabricated drills, unapproved broker/controller/PVC disruption, data-integrity gap, weakened acks/minISR, TLS/ACL bypass, missing critical telemetry marked green, unowned corrective actions or absent independent review.

**Readiness state:** Pending/Not Ready until real lab evidence and independent acceptance exist.

## 14. Cleanup, references and next part

Remove only chapter-owned synthetic client Deployments, test KafkaUser/topic, test alerts and temporary evidence collectors through approved GitOps after evidence retention. Never delete production PVCs, offsets, topics, monitoring stores or operator-managed Secrets.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Debugging](https://kubernetes.io/docs/tasks/debug/), [Google SRE Book — Managing Incidents](https://sre.google/sre-book/managing-incidents/), [Google SRE Workbook](https://sre.google/workbook/).

**Part 10 — Troubleshooting and Incident Response is fully published (Chapters 046–050).**

**Next:** Chapter 051 — Kafka High Availability Architecture, Failure Domains and Kubernetes Resilience, beginning Part 11 — High Availability, Failover and Disaster Recovery.

---

**Verification boundary:** GitHub publication establishes document availability only. Live capstone drills, RCA acceptance, data-integrity checks, independent security review and production readiness remain Pending.
