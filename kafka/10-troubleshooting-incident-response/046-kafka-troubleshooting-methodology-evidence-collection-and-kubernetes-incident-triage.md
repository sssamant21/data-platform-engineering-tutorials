# Chapter 046 — Kafka Troubleshooting Methodology, Evidence Collection and Kubernetes Incident Triage

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 10 — Troubleshooting and Incident Response (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–045, particularly 036–045  
**Publication:** Published · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety:** Use an approved disposable Kubernetes environment, a synthetic KafkaTopic and isolated client group. Never kill production controllers/brokers, delete PVCs, reset shared offsets, weaken acks/minISR, bypass TLS/SASL/ACLs, or change operator-owned workloads directly. Redact logs and avoid collecting Secret values. All incident simulations are client-only or tabletop unless separately approved.

## 1. Mission

Develop a repeatable, evidence-first Kafka troubleshooting method. Distinguish customer-impacting producer/consumer failures from Kafka KRaft quorum, replication/ISR, Strimzi reconciliation, Kubernetes scheduling/storage/networking and observability problems. Collect time-bounded evidence, test hypotheses safely, escalate with an accurate incident timeline, and validate recovery through end-to-end event reconciliation.

## 2. Symptom-to-layer decision tree

```text
Client-visible delivery / latency / freshness incident
                     |
             Validate synthetic SLI
                     |
          +----------+-----------+
          |                      |
   Producer failure         Consumer failure
    callback / acks          lag / event age
          |                      |
          +-----------+----------+
                      |
            Kafka partition health
             leader / ISR / minISR
                      |
               KRaft quorum
                      |
         Strimzi Kafka/KafkaNodePool CR
                      |
      Kubernetes Pods / Nodes / PVC / CSI
                      |
    DNS / TLS / SASL / ACL / NetworkPolicy
                      |
          Monitoring / logs / traces
                      |
             Hypothesis + evidence
                      |
        Approved mitigation + verification
```

**Key rule:** A healthy Kafka CR does not prove producer acknowledgments or downstream processing. Consumer lag is not equivalent to event age. Missing Prometheus metrics are not evidence of zero errors.

## 3. Incident triage workflow

| Stage | Question | Evidence | Safe response |
|---|---|---|---|
| Scope | Which users, topics and event contracts are affected? | synthetic ledger, SLI, incidents | assign commander and owner |
| Safety | Is KRaft quorum/ISR stable? | quorum CLI, topic metadata, Kafka CR | freeze risky changes |
| Platform | Are Strimzi, Pods, PVCs and nodes healthy? | kubectl status/events/logs | involve platform SRE |
| Connectivity | Can clients resolve and authenticate? | DNS, listener, TLS/SASL/ACL logs | correct approved config |
| Processing | Are consumers actually processing? | group offsets, event age, sink ledger | isolate client/sink issue |
| Observability | Are signals fresh and complete? | scrape targets, logs, metrics | declare telemetry blind spot |
| Recovery | Are accepted events durably processed? | unique-event reconciliation | close only after verification |

## 4. Read-only command toolkit

```bash
# Confirm context and scope before collecting evidence.
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp

# Strimzi Kafka CR condition and operator reconciliation.
kubectl -n kafka-lab get kafka sre-kafka -o yaml
kubectl get deploy -A | grep -i strimzi

# KRaft quorum via isolated lab Kafka CLI Pod.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status

# Topic and consumer-group inventory (substitute synthetic names).
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-triage-synthetic
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-triage-synthetic-group

# Time-bounded Pod logs; replace the Pod name after inventory.
kubectl -n kafka-lab logs POD_NAME --since=15m --timestamps --tail=300
```

**Important:** The internal plaintext 9092 listener and sample names are isolated-lab conventions, not production deployment advice. Production-like clients require reviewed TLS/SASL properties, least-privilege ACLs and supported Strimzi/Kafka versions. Inspect `kubectl api-resources` and actual Pod names before running commands.

## 5. Evidence quality and chain of custody

Capture UTC timestamps, cluster context, software versions, namespace, affected service, exact command/query, source revision, expected and observed output, redaction status, collector, reviewer and retention. Keep raw incident evidence access-controlled and sanitized exports in the repository. Do not paste credentials, token-bearing URLs, KafkaUser Secret contents or sensitive event payloads into Git.

A hypothesis must be falsifiable. Example: "Kafka replication failure causes producer errors" should be tested against actual ISR/minISR, callback errors, request timeouts, KRaft quorum and healthy synthetic traffic, not inferred from a single alert.

## 6. Twenty Kubernetes-first troubleshooting labs

### Lab 01 — Approve incident lab boundaries

**Objective and procedure:** Document namespace, context, synthetic workload, incident owner, scope, evidence redaction, abort criteria, change freeze and reviewer.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 02 — Establish baseline and version matrix

**Objective and procedure:** Record Kafka/Strimzi/Kubernetes versions, KRaft mode, CRDs, Kafka Ready, NodePools, listener/security configuration and deployment revision.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 03 — Collect Kubernetes events and workload state

**Objective and procedure:** Capture namespace events, Kafka/Strimzi Pods, restarts, readiness, scheduling and PVC state; correlate timestamps.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 04 — Collect KRaft metadata quorum evidence

**Objective and procedure:** Run metadata quorum describe --status from approved CLI Pod; compare leader, voter state and errors with broker/controller logs.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 05 — Inspect Kafka CR and operator reconciliation

**Objective and procedure:** Compare spec, observed generation, conditions, recent GitOps changes and operator logs; distinguish controller reconciliation from Kafka availability.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 06 — Inspect topic replication and ISR

**Objective and procedure:** Use kafka-topics.sh --describe with approved client config; identify RF, leader, ISR and partition anomalies without changing topic configs.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 07 — Inspect producer error paths

**Objective and procedure:** Capture callback failures, retries, request latency, quotas, acks configuration, bootstrap connectivity and auth failures from isolated synthetic producer.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 08 — Inspect consumer group symptoms

**Objective and procedure:** Run kafka-consumer-groups.sh --describe; compare offsets/lag with event age, poll failures, downstream sink and processing ledger.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 09 — Inspect DNS and Service discovery

**Objective and procedure:** Compare Kafka bootstrap/headless Services, endpoints, CoreDNS health and broker advertised listeners; use test Pod DNS lookup.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 10 — Inspect TLS and SASL authentication

**Objective and procedure:** Validate certificate trust, expiry, hostname verification, principal mapping and ACL-denial evidence without exposing private keys.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 11 — Inspect network policy and reachability

**Objective and procedure:** Review NetworkPolicy, Service ports, pod-to-broker TLS handshake and cluster firewall boundaries; avoid broad allow-all fixes.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 12 — Inspect PVC, filesystem and I/O signals

**Objective and procedure:** Correlate PVC Bound state, disk utilization, fsync latency, IOPS, CSI events and node pressure; avoid deleting PVCs.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 13 — Inspect JVM, CPU and memory signals

**Objective and procedure:** Review heap/GC, CPU throttling, OOMKilled, JVM thread pools and Kafka request queues; avoid arbitrary heap changes.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 14 — Inspect broker logs safely

**Objective and procedure:** Collect bounded, time-scoped redacted Kafka logs using kubectl logs --since; avoid indiscriminate log dumps or credentials.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 15 — Inspect operator and Kubernetes control plane

**Objective and procedure:** Correlate Strimzi operator reconciliation failures, API throttling, Pod scheduling and PDB constraints.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 16 — Correlate Prometheus/Grafana with raw evidence

**Objective and procedure:** Validate exporter freshness, metric names, quorum/ISR, producer SLO and event age; separate No Data from healthy.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 17 — Run synthetic producer failure triage

**Objective and procedure:** Trigger bounded client-only failure, declare incident, collect evidence, verify Kafka quorum unchanged and restore producer.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 18 — Run synthetic consumer pause triage

**Objective and procedure:** Pause only lab consumer Deployment briefly, observe lag/event age, restore, reconcile unique accepted/processed IDs.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 19 — Construct evidence timeline and hypothesis tree

**Objective and procedure:** Create UTC timeline, symptom-to-layer decision tree, competing hypotheses, falsification tests and rollback decision.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

### Lab 20 — Complete incident triage acceptance

**Objective and procedure:** Run read-only verifier, produce evidence package, rehearse communications, score 100-point rubric and request independent review.

**Expected evidence:** Save sanitized command/query, exact version and context, UTC timestamp, hypothesis, expected and observed result, incident owner, safe rollback/abort decision and independent reviewer. **Validation state:** Pending until live execution. Do not infer a passed lab from documentation alone.

## 7. Automated read-only triage preflight

Save as `verify-ch46.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
mkdir -p evidence-ch46
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/12] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[5/12] PVC inventory'
kubectl -n "$NS" get pvc -o wide
echo '[6/12] Kafka CR conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[7/12] Kafka metrics configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.metricsConfig}{"\n"}'
echo '[8/12] Strimzi deployment inventory'
kubectl get deploy -A | grep -i strimzi || true
echo '[9/12] PrometheusRule inventory'
kubectl get prometheusrules -A -o wide 2>/dev/null || true
echo '[10/12] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[11/12] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only Kafka/Kubernetes incident inventory.'
echo 'NOT PROVEN: root cause, customer SLO, data integrity, lab drills or security review.'
```

Run `chmod +x verify-ch46.sh && ./verify-ch46.sh | tee evidence-ch46/preflight.txt`. This checks inventory only. A Kafka Ready wait may fail during a real incident; record the failure and continue triage manually rather than treating it as a diagnostic conclusion.

## 8. Safe synthetic incident exercises

**Producer path:** Trigger bounded client-only callback errors against a dedicated synthetic topic. Capture retries, eligible attempts, failed callbacks, Kafka quorum/ISR, alert state and incident timeline. Restore the client and reconcile unique accepted IDs.

**Consumer path:** Pause only an isolated synthetic consumer Deployment briefly. Capture offsets, lag, event age, group state and unique processed ledger. Restore replicas and verify durable processing and backlog drain.

**KRaft/ISR path:** Use tabletop evidence or synthetic metrics; do not remove controller Pods or change minISR/replication settings to manufacture failures.

**Abort:** Stop immediately if the test affects shared namespaces, actual on-call receivers, quorum/ISR, PVC safety, credentials or unrelated clients.

## 9. Twelve troubleshooting scenarios

### Scenario 1 — Kafka CR Ready but producer fails

**Initial hypothesis and tests:** Validate application callbacks, TLS, bootstrap, quotas and actual broker/ISR state. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 2 — KRaft quorum uncertainty

**Initial hypothesis and tests:** Compare quorum CLI, controller logs and metric freshness; freeze changes. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 3 — Under-minISR and write errors

**Initial hypothesis and tests:** Verify replication state and producer acks; never weaken durability for green metrics. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 4 — Consumer lag grows after deployment

**Initial hypothesis and tests:** Inspect rebalances, poll interval, downstream processing, partitions and event age. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 5 — Consumer lag zero but freshness poor

**Initial hypothesis and tests:** Compare source event time, clock skew and unique durable processing ledger. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 6 — Kafka Pod Pending and PVC not Bound

**Initial hypothesis and tests:** Inspect CSI provisioning, topology, storage class and node scheduling. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 7 — Broker OOMKilled or CPU throttled

**Initial hypothesis and tests:** Correlate memory limits, GC, request queue and workload spikes. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 8 — TLS certificate or SASL principal mismatch

**Initial hypothesis and tests:** Inspect trust chain, SAN, expiry and Kafka authorization logs without secrets exposure. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 9 — NetworkPolicy blocks broker advertised endpoint

**Initial hypothesis and tests:** Validate advertised listener DNS, ports, policy and cross-node reachability. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 10 — Operator reconciliation stalled

**Initial hypothesis and tests:** Inspect CR conditions, operator events/logs and GitOps revision; avoid manual owner-resource patching. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 11 — Prometheus target missing during incident

**Initial hypothesis and tests:** Use independent Kafka CLI/client ledger and mark telemetry Unknown. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

### Scenario 12 — Incident resolved before ledger reconciled

**Initial hypothesis and tests:** Require unique-event processing, freshness, SLO and alert recovery gates. Compare Kafka CLI, Strimzi CR, Kubernetes Events, producer/consumer ledgers and raw Prometheus targets. **Recovery:** Apply the lowest-risk approved mitigation or rollback, preserve durability/security, and verify SLO and unique-event reconciliation. **Evidence:** UTC timeline, commands, expected/observed outcome, incident owner and reviewer.

## 10. Eight production incident runbooks

### Runbook A — First 15 minutes Kafka incident triage

**Trigger and actions:** Acknowledge, declare severity, appoint commander, freeze risky changes, identify customer SLO impact and capture immutable baseline. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook B — KRaft controller and quorum investigation

**Trigger and actions:** Check metadata quorum status, controller logs, voters and Kubernetes health; preserve safety and escalate before changes. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook C — Under-minISR, replication and produce failure

**Trigger and actions:** Inspect partition leaders/ISR, minISR, acks, storage and network; avoid data-loss-prone configuration changes. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook D — Consumer lag, event age and processing failures

**Trigger and actions:** Inspect group assignment, offsets, poll/rebalance, downstream sink and ledger reconciliation. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook E — Kubernetes Pod, Node and PVC incident

**Trigger and actions:** Review Pod conditions, events, CSI, node pressure, storage latency and approved capacity actions. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook F — TLS, SASL, ACL and networking incident

**Trigger and actions:** Validate DNS, advertised listeners, TLS identity and authorization using least privilege; do not disable controls. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook G — Strimzi reconciliation and GitOps drift

**Trigger and actions:** Inspect CR status, operator logs, desired/observed revision, approved rollback and ownership. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

### Runbook H — Evidence, communications and postmortem

**Trigger and actions:** Maintain UTC timeline, decisions, redacted evidence, updates, safe recovery verification and corrective actions. **Verification:** Compare independent Kafka quorum/ISR state, Kubernetes resources, client SLO and synthetic event ledger. **Exit criteria:** Approved mitigation, no unresolved data-integrity gap, recovered alerting, stakeholder update and corrective-action owner.

## 11. Evidence package

```text
evidence-ch46/
  scope-and-approval.md
  incident-severity-and-ownership.md
  context-version-matrix.md
  preflight.txt
  kafka-kraft-baseline.md
  kafka-cr-operator-reconciliation.md
  topic-isr-metadata.md
  producer-callbacks.md
  consumer-group-and-event-age.md
  dns-service-endpoints.md
  tls-sasl-acl-review.md
  networkpolicy-review.md
  pvc-storage-io.md
  jvm-cpu-memory.md
  bounded-broker-logs.md
  operator-control-plane.md
  prometheus-grafana-correlation.md
  synthetic-producer-drill.md
  synthetic-consumer-drill.md
  hypothesis-tree-and-utc-timeline.md
  incident-communications.md
  recovery-ledger.csv
  postmortem-and-actions.md
  independent-review.md
```

Every file must include actual source, version, UTC time, expected/observed result, data sensitivity/redaction, action owner and assessor. Missing or simulated evidence is labeled Pending/Simulated, not Passed.

## 12. 100-point SRE incident triage assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, approval, incident command and safety | 10 | Yes |
| Kafka/KRaft quorum and replication evidence | 15 | Yes |
| Strimzi/Kubernetes Pod, Node and PVC diagnosis | 15 | Yes |
| Producer and consumer client-visible SLIs | 15 | Yes |
| DNS, TLS/SASL/ACL and NetworkPolicy analysis | 10 | Yes |
| Metrics, logs, traces and missing-data detection | 10 | Yes |
| Synthetic incident response and recovery | 10 | Yes |
| Evidence chain, hypothesis testing and timeline | 10 | Yes |
| Independent security/technical review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** fabricated live tests, production disruption without approval, lost event reconciliation, weakened durability/security, exposed Secrets, unowned incident or absent independent review.

## 13. Cleanup, references and next chapter

Remove only chapter-owned synthetic producer/consumer resources, test alerts and temporary evidence collectors via approved GitOps. Retain sanitized incident evidence. Do not delete Kafka PVCs, shared monitoring data, production offsets or operator-managed Secrets.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/), [Google SRE Book — Managing Incidents](https://sre.google/sre-book/managing-incidents/), [Prometheus](https://prometheus.io/docs/).

**Next:** Chapter 047 — Kafka Broker, KRaft Controller, Replication and Storage Failure Troubleshooting.

---

**Verification boundary:** GitHub publication establishes document availability only. Live exercises, incident simulation, evidence validation and independent technical/security acceptance remain Pending.
