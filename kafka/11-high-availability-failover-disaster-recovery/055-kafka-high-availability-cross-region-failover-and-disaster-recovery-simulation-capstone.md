# Chapter 055 — Kafka High Availability, Cross-Region Failover and Disaster Recovery Simulation Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 11 — High Availability, Failover and Disaster Recovery (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–054, especially 051–054  
**Status:** Published · **Live capstone drills:** Pending · **Independent technical/security review:** Pending

> **Safety boundary:** All broker/controller/AZ/region outage, DR cutover and failback exercises are tabletop unless a separate approved disposable-cluster drill is authorized. Do not disrupt production clusters, kill KRaft controllers, delete PVCs, reset offsets, weaken acks/minISR, disable TLS/ACLs, change production DNS or permit two active writers. Publication does not mean DR capability has been proven.

## 1. Mission

Combine HA architecture, Kafka broker/partition failover, KRaft quorum, Kubernetes/PVC failure domains, MirrorMaker 2, consumer checkpoint translation and business RPO/RTO into one independently assessed SRE disaster recovery capstone. Verify application-level delivery, not only Kafka readiness.

## 2. Outcomes

- Design and review independent primary and secondary Strimzi/KRaft clusters across realistic failure domains.
- Establish baseline broker ISR, controller quorum, client delivery SLO, replication watermarks and downstream durability.
- Rehearse single-broker, single-zone, controller-majority and regional outage decisions safely.
- Quantify or explicitly mark unknown RPO and RTO; prevent false zero-loss claims.
- Plan writer fencing, secure client routing, translated consumer offsets, replay and failback.
- Produce an evidence-backed RCA, corrective actions and independent technical/security acceptance.

## 3. Reference architecture

```text
Primary region (AZ-A/B/C)                    Secondary region (AZ-D/E/F)
  producers (acks=all)                          fenced DR producers
         |                                             |
  Kafka brokers + PVCs                         Kafka brokers + PVCs
  KRaft voters (majority)                      KRaft voters (majority)
         |                                             ^
  source topic / IDs --- MirrorMaker 2 / Connect ------|
         |              heartbeat/checkpoint           |
  source consumer                                DR consumer
         |                                             |
  durable sink                                idempotent DR sink
         \---------------- event-ID ledger -------------/
                  alerts / SLO / incident command
```

The reference assumes **independent** Kubernetes control planes, CSI/storage, network paths, authentication and operator availability. A local single-node kind lab cannot prove multi-AZ or regional DR.

## 4. Critical acceptance gates

| Gate | Evidence | Failed/unknown decision |
|---|---|---|
| Business recovery contract | signed RPO, RTO, event acceptance semantics | BLOCK |
| Primary and secondary quorum | controller leader, voters, independent majority | BLOCK |
| Kafka partition safety | RF, ISR/minISR, offline partitions, acks=all | BLOCK |
| Storage | PVC/CSI topology, backup/restore evidence | BLOCK |
| Replication | MM2 task status, topic allowlist, per-partition event watermark | UNKNOWN / ESCALATE |
| Consumer recovery | checkpoint/offset translation, replay, sink idempotence | BLOCK |
| Security | TLS/SASL/ACL, NetworkPolicy, secret rotation | BLOCK |
| Writer authority | confirmed fencing and single active writer | BLOCK |
| End-to-end durability | acknowledged unique IDs vs durable sink IDs | KEEP incident open |
| Independent review | technical, security, business DR authority | NOT READY |

**No-go rules:** Never equate a green Kafka CR or MM2 heartbeat with complete replication; never subtract source and destination offsets without validated translation; never claim zero RPO with missing watermarks.

## 5. RPO/RTO measurement

Define the business acceptance boundary (e.g., producer callback success with `acks=all`) and destination durable boundary (record confirmed in secondary Kafka, then optionally sink commit). Record **per topic-partition** the last accepted source ID, source offset and UTC timestamp, and the last independently verified replicated source ID, source offset and UTC timestamp. Report missing accepted IDs, duplicates and clock uncertainty.

```text
RPO:  maximum acceptable loss of acknowledged events
RTO:  maximum acceptable time to restore agreed service

Observed loss set = acknowledged source IDs - destination durable IDs
Observed outage = verified service restored UTC - incident start UTC
```

Example only: source acknowledged through 14:00:30 UTC and destination verified through 14:00:18 UTC yields a 12-second observed replication-age gap **at that observation**, not a guaranteed loss on disaster. If service is unavailable at 14:05 and end-to-end service is verified at 14:24, observed RTO is 19 minutes. A tabletop may calculate hypothetical values, but **must not** report them as measured live DR results.

## 6. Read-only Kubernetes and Kafka preflight

```bash
# Replace with approved disposable contexts; commands do not change cluster state.
PRIMARY_CTX=lab-primary
SECONDARY_CTX=lab-secondary
NS=kafka-lab

for CTX in "$PRIMARY_CTX" "$SECONDARY_CTX"; do
  echo "=== $CTX ==="
  kubectl --context "$CTX" -n "$NS" get kafka,kafkanodepool,pods,pvc,pdb -o wide
  kubectl --context "$CTX" -n "$NS" get svc,endpointslices,networkpolicy
  kubectl --context "$CTX" -n "$NS" get events --sort-by=.metadata.creationTimestamp
  kubectl --context "$CTX" get nodes -L topology.kubernetes.io/zone -o wide
done

# Lab-only CLI Pod / plaintext bootstrap; production requires TLS/SASL configs.
kubectl --context "$PRIMARY_CTX" -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl --context "$PRIMARY_CTX" -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-dr-synthetic

kubectl --context "$PRIMARY_CTX" api-resources | grep -i kafkamirrormaker2
kubectl --context "$PRIMARY_CTX" -n "$NS" get kafkamirrormaker2
```

Check installed Strimzi/Kafka/CRD compatibility and secure listener settings before running. The synthetic topic and CLI Pod are prerequisites. Do not export secrets or commit sensitive connector configurations.

## 7. Twenty Kubernetes-first DR capstone labs

### Lab 01 — Approve capstone scope and incident roles

**Procedure:** Assign incident commander, Kafka SRE, platform SRE, application owner, security reviewer, scribe and business DR decision authority; record isolated contexts and abort conditions.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 02 — Inventory both Kubernetes clusters

**Procedure:** Capture versioned Kafka/NodePool CRs, Pod/PVC/PDB, StorageClass, zones, operator readiness, GitOps revision and separate cloud dependencies.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 03 — Establish primary KRaft baseline

**Procedure:** Record quorum voters, leader, controller placement, metadata health and broker readiness before any synthetic scenario.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 04 — Establish secondary KRaft baseline

**Procedure:** Independently verify secondary quorum, broker ISR, storage and network; secondary Ready is not proof of replication.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 05 — Baseline per-topic partition replicas and ISR

**Procedure:** Record source/destination RF, leaders, replicas, ISR, minISR and topic allowlist for synthetic data.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 06 — Validate secure cross-cluster identities

**Procedure:** Audit TLS trust, mTLS/SASL, least-privilege ACLs, NetworkPolicies, Secret references and credential rotation plan.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 07 — Validate MirrorMaker 2 and Connect readiness

**Procedure:** Check KafkaMirrorMaker2 CRD, Connect worker/task states, topic selection, heartbeat/checkpoint and source connector health.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 08 — Establish unique-event acceptance ledger

**Procedure:** Generate a bounded set of synthetic event IDs with producer callback success timestamps and source partition/offset metadata.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 09 — Reconcile destination replication ledger

**Procedure:** Match source accepted event IDs to destination durable events per partition; report gaps, duplicates and lag uncertainty.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 10 — Measure RPO baseline

**Procedure:** Calculate acceptance-to-replication lag using observed source/destination event IDs and UTC timestamps, never raw offset subtraction.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 11 — Measure application RTO baseline

**Procedure:** Define service-unavailable and verified-recovered UTC timestamps; include client routing, authentication, replay and sink readiness.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 12 — Validate SLO alerting and missing telemetry

**Procedure:** Check producer success, consumer freshness, replication lag, KRaft quorum, ISR, Connect task failure and No Data alerts.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 13 — Run single-broker-loss tabletop

**Procedure:** Model a broker unavailable, leadership/ISR transition, acks=all callbacks and recovery gates without deleting Pods.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 14 — Run single-AZ-loss tabletop

**Procedure:** Remove a modeled AZ from topology worksheet and calculate surviving controller majority, ISR, PV and client availability.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 15 — Run controller-majority-loss tabletop

**Procedure:** Model metadata outage, change freeze and version-supported escalation; never mutate voter membership.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 16 — Run replication-outage tabletop

**Procedure:** Model MM2 task failure and RPO growth; record decision whether destination is safe for cutover.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 17 — Run secure connectivity client-only fault

**Procedure:** Use a dedicated synthetic client with invalid bootstrap/trust configuration, capture errors, restore and reconcile accepted IDs.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 18 — Rehearse regional DR cutover tabletop

**Procedure:** Declare disaster, quantify unknown data, approve writer fencing, verify secondary readiness, translate offsets and simulate client switch.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 19 — Rehearse failback and rollback tabletop

**Procedure:** Confirm authoritative writer, reverse replication, checkpoints, idempotent sink, rollback trigger and independent approval.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

### Lab 20 — Complete independent DR acceptance and RCA

**Procedure:** Review evidence package, RPO/RTO results or Unknown, 100-point rubric, corrective actions, technical/security signoff and final readiness state.

**Expected result and evidence:** Capture exact primary/secondary Kubernetes contexts, Kafka/Strimzi versions, UTC commands/queries, expected/observed condition, quorum/ISR safety, event-ID ledger, RPO/RTO status, security impact, rollback/abort decision and independent assessor. Mark **Pending** until executed. Label simulated failure outcomes **Tabletop**.

## 8. Read-only capstone verification script

Save as `verify-ch55.sh`. It performs inventory only and **does not** trigger a failover, cutover or topic mutation.

```bash
#!/usr/bin/env bash
set -euo pipefail
PRIMARY_CTX=lab-primary
SECONDARY_CTX=lab-secondary
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-dr-synthetic

for CTX in "$PRIMARY_CTX" "$SECONDARY_CTX"; do
  echo "=== Cluster context: $CTX ==="
  kubectl --context "$CTX" -n "$NS" get kafka,kafkanodepool,pods,pvc,pdb -o wide
  kubectl --context "$CTX" get nodes -L topology.kubernetes.io/zone -o wide
  kubectl --context "$CTX" -n "$NS" get svc,endpointslices,networkpolicy
  kubectl --context "$CTX" -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
  kubectl --context "$CTX" -n "$NS" get events --sort-by=.metadata.creationTimestamp
  kubectl --context "$CTX" -n "$NS" exec kafka-cli -- \
    "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
done

echo '=== Source synthetic topic ==='
kubectl --context "$PRIMARY_CTX" -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"

echo '=== MirrorMaker 2 inventory (if CRD exists) ==='
if kubectl --context "$PRIMARY_CTX" api-resources -o name | grep -q '^kafkamirrormaker2s.kafka.strimzi.io$'; then
  kubectl --context "$PRIMARY_CTX" -n "$NS" get kafkamirrormaker2 -o wide
else
  echo 'UNKNOWN/NOT CONFIGURED: MM2 CRD absent in primary context'
fi

echo 'PASS: read-only cross-cluster inventory completed.'
echo 'NOT PROVEN: MM2 replication, accepted-event integrity, actual failover, RPO/RTO, cutover, failback or independent acceptance.'
```

Run `chmod +x verify-ch55.sh && ./verify-ch55.sh | tee evidence-ch55/preflight.txt`. A failed inventory is an investigation signal, not permission to mutate production resources. Use actual test context names rather than trusting the examples.

## 9. Twelve integrated DR failure scenarios

### Scenario 1 — Primary broker fails and ISR shrinks

**Triage:** Inspect leader election, minISR and producer callback integrity. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 2 — Controller quorum majority lost

**Triage:** Freeze changes and invoke approved metadata recovery escalation. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 3 — One AZ unavailable

**Triage:** Assess controller voter, broker replica, PV/CSI and client failure domains. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 4 — Secondary PVCs remain zone-pinned

**Triage:** Reject unsupported restore assumptions and review CSI backup evidence. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 5 — MirrorMaker 2 task silently stops

**Triage:** Compare Connect task state, watermark freshness and alert routing. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 6 — Heartbeats pass while critical topic is excluded

**Triage:** Reconcile allowlist, topic mapping and accepted event IDs. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 7 — Destination lags beyond business RPO

**Triage:** Escalate quantified loss window and require business authority. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 8 — Consumer checkpoint missing at destination

**Triage:** Plan bounded replay and sink deduplication; do not copy offsets blindly. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 9 — Schema Registry or Kafka Connect sink unavailable

**Triage:** Include dependency restoration in measured RTO. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 10 — Primary writer resumes during DR promotion

**Triage:** Fence conflicting writer to prevent split brain. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 11 — DR TLS/ACL differs from primary

**Triage:** Diagnose trust chain, principals, ACL and network policy without bypass. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

### Scenario 12 — Application dashboard green but sink misses events

**Triage:** Keep incident open pending durable unique-event reconciliation. Gather read-only KRaft quorum, ISR, Pod/PVC/CSI, MM2/Connect, TLS/ACL, client callback, event-age and unique-ID evidence. **Decision:** Assign IC, freeze unsafe changes, quantify or mark unknown RPO, obtain DR authority and preserve single-writer fencing. **Acceptance:** UTC timeline, redacted evidence, rollback and independent review.

## 10. Eight production disaster recovery runbooks

### Runbook A — Incident declaration and DR authority

**Trigger and response:** Assign IC, determine impact, freeze risky changes, identify business approver and set communications cadence. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook B — Primary/secondary quorum and ISR verification

**Trigger and response:** Check both independent KRaft quorums, leaders, broker Pods/PVC and per-topic ISR/minISR. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook C — Multi-zone failure containment

**Trigger and response:** Map failed AZ, controllers, broker replicas, PV/CSI and client paths; block unsafe drain or PVC deletion. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook D — MirrorMaker 2 replication recovery

**Trigger and response:** Review Connect worker/task errors, topic selection, ACLs, network, source/destination watermark and backlog. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook E — RPO/RTO and event-ledger calculation

**Trigger and response:** Measure accepted vs durably replicated IDs, data loss uncertainty, recovery timeline and business objective. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook F — Secure regional cutover with writer fencing

**Trigger and response:** Require approved source fencing, destination readiness, offset translation, client routing and sink integrity. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook G — Failback, rollback and split-brain prevention

**Trigger and response:** Validate reverse replication, single writer, checkpoint mapping, replay, rollback and independent signoff. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

### Runbook H — Post-incident RCA and operational acceptance

**Trigger and response:** Build UTC timeline, root cause confidence, corrective-action tracker, security review and retest. **Safety gates:** No controller quorum edits, PVC deletion, unclean election, minISR/acks weakening, TLS/ACL bypass, unreviewed offset reset or dual active writers. **Exit:** Signed owner decision, healthy quorum/ISR, measured or explicitly unknown RPO/RTO, sink reconciliation, monitoring and follow-up action owner.

## 11. Incident command, cutover and failback state machine

```text
PRIMARY_ACTIVE
   |
   +-- declare incident + business approval --> ASSESS_PRIMARY_AND_SECONDARY
                                                  |
                        quorum/ISR, MM2, topic allowlist, watermarks
                                                  |
                          +-- unsafe --> HOLD / ESCALATE
                          |
                          +-- eligible --> FENCE_PRIMARY_WRITERS
                                                  |
                                            APPROVE_DR_CUTOVER
                                                  |
                                       ROUTE_CLIENTS / CONSUMERS
                                                  |
                                    TRANSLATE_OFFSETS / REPLAY
                                                  |
                                   RECONCILE_DURABLE_EVENT_IDS
                                                  |
                                            DR_ACTIVE
                                                  |
                                REVERSE_SYNC / FENCE / SIGNOFF
                                                  |
                                        APPROVED_FAILBACK
```

Do not treat restoration of the primary region as permission to automatically resume its writers. Verify single-writer authority and reverse-replication integrity before failback.

## 12. Blameless RCA and evidence package

```text
evidence-ch55/
  charter-severity-roles.md
  context-version-matrix.md
  preflight.txt
  primary-kraft-isr-pvc.md
  secondary-kraft-isr-pvc.md
  zone-storage-dependency-map.md
  security-principals-acls.md
  mm2-connect-topic-checkpoints.md
  source-accepted-events.csv
  destination-replicated-events.csv
  rpo-worksheet.md
  rto-timeline.md
  slo-alerting-no-data.md
  broker-loss-tabletop.md
  az-loss-tabletop.md
  quorum-loss-tabletop.md
  replication-outage-tabletop.md
  synthetic-client-fault.md
  dr-cutover-fencing-tabletop.md
  failback-rollback-tabletop.md
  unique-event-sink-reconciliation.csv
  incident-utc-timeline.md
  rca-and-contributing-factors.md
  corrective-action-tracker.csv
  independent-technical-security-review.md
  readiness-scorecard.md
  independent-business-signoff.md
```

Every artifact requires source, exact version, UTC timestamp, expected/observed result, owner, redaction, rollback/abort, reviewer and **Live** versus **Tabletop** label. If root cause cannot be established, record **Undetermined** and assign further investigation rather than guessing.

## 13. 100-point enterprise DR capstone assessment

| Domain | Points | Critical |
|---|---:|---|
| Incident charter, business RPO/RTO, safety and roles | 10 | Yes |
| Independent KRaft quorum, ISR and zone resilience | 15 | Yes |
| Kubernetes Pod/PDB/PVC/CSI and capacity | 10 | Yes |
| MM2/Connect, topic coverage and replication | 15 | Yes |
| Per-partition watermarks and RPO evidence | 15 | Yes |
| Consumer checkpoints, replay and sink integrity | 10 | Yes |
| Secure writer fencing, cutover and failback | 10 | Yes |
| RTO/SLO, incident response and RCA | 10 | Yes |
| Independent technical, security and business signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** fabricated DR execution, missing independent signoff, unapproved regional cutover, dual active writers, unquantified loss reported as zero, missing unique-event reconciliation, weakened Kafka durability/security or unsupported offset mapping.

**Readiness:** Pending/Not Ready until representative live drills and independent review actually pass. A successful tabletop proves planning maturity, not operational RPO/RTO compliance.

## 14. Cleanup, references and curriculum transition

Remove only chapter-owned synthetic clients, test topics, test alerts and approved MM2 test resources through GitOps after evidence retention. Never delete production PVCs, offsets, checkpoints, Connect internal topics or operator-managed Secrets.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Google SRE Workbook](https://sre.google/workbook/).

**Part 11 — High Availability, Failover and Disaster Recovery is fully published (Chapters 051–055).**

**Next:** Chapter 056 — Kafka Connect Architecture, Distributed Workers and Connector Lifecycle, beginning Part 12 — Kafka Connect, CDC and Schema Management.

---

**Verification boundary:** Publication establishes document availability only. Live HA/DR drills, MirrorMaker 2 replication, RPO/RTO measurements, event integrity and independent technical/security acceptance remain Pending.
