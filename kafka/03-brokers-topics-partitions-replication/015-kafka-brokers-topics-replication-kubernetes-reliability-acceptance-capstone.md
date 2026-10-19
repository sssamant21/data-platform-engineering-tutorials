# Chapter 015 — Kafka Brokers, Topics, Replication and Kubernetes Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 03 — Brokers, Topics, Partitions and Replication · Final capstone  
**Platform:** Kubernetes + Strimzi Operator + Apache Kafka KRaft  
**Prerequisites:** Chapters 001–014; [Kubernetes-first Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers, incident commanders  
**Publication:** Complete · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety boundary:** This is a controlled reliability assessment, **not** authorization to run chaos testing on production. Use a disposable Kubernetes cluster with dedicated Kafka storage and documented ownership. Any fault injection is opt-in, restricted to one broker-only Pod, and requires healthy ISR and controller quorum before starting. Never delete broker/controller PVCs, modify KRaft metadata manually, enable unclean leader election, lower min ISR to mask errors, or scale down a broker containing required replicas.

## 1. Mission and acceptance outcomes

You are the on-call Kafka platform engineer asked to certify an operator-managed KRaft cluster for a business-critical event stream. The assessment covers the **complete lifecycle**: Kubernetes scheduling and PVCs, broker identity, KafkaTopic policy, partition replica placement, safe scaling/reassignment design, single-broker failure, recovery, data reconciliation, alerting and operational handoff.

By completion, you must produce:

1. An architecture and failure-domain inventory mapping broker IDs to Pods, nodes, zones and PVCs.
2. An approved KafkaTopic with partition count, RF=3, minISR=2 and retention policy.
3. Baseline Kafka metadata, controller quorum and client delivery evidence.
4. A broker scale-out and replica-placement proposal with capacity analysis.
5. An opt-in single broker-Pod failure and full recovery evidence.
6. A validated unique-event reconciliation report with ambiguous outcomes identified.
7. Automated acceptance results, alert coverage, an incident report and rollback plan.
8. A signed 100-point scorecard that clearly separates **published**, **executed**, and **approved**.

## 2. Enterprise architecture

```text
       Git / Pull Request / Change Ticket / Approval
                          |
                  GitOps reconciler
                          |
                  Kubernetes API
                          |
                    Strimzi Operator
                     /          \
           KafkaNodePool       KafkaTopic
            /       \              |
      3 KRaft       3 brokers      Topic Operator
      controllers   /  |  \             |
       | | |        A   B   C        Kafka Admin API
       quorum       |   |   |             |
                 PVC-A PVC-B PVC-C        |
                   |   |   |             |
                 Zone A B C (target)     |
                    \  |  /              |
                    partition replicas / ISR
                            |
                    TLS/authenticated clients
                            |
                 producer -> Kafka -> consumer
                            |
                Prometheus / Grafana / alerting
```

**Reference production target:** three dedicated controller voters across independent failure domains, three or more dedicated broker-role Pods with persistent volumes, TLS/authentication, Kubernetes RBAC, network restrictions, and topic RF=3/minISR=2. A kind lab may lack true AZs or production-grade CSI; mark these controls **Not Tested**, not Passed. Verify Strimzi and Kafka version compatibility and release-specific CRD schemas before applying any manifest.

## 3. Reliability invariants and risk gates

| Invariant | Required proof | Failure action |
|---|---|---|
| Kafka CR Ready | Operator-reconciled condition | Block mutation |
| Controller quorum stable | Metadata quorum status and voter health | Block mutation |
| Three broker identities healthy | Kafka Admin API + Kubernetes Pod/PVC inventory | Block mutation |
| Critical topic RF=3, minISR=2 | KafkaTopic CR + Kafka effective config | Block mutation |
| Every partition has ISR=3 before fault | Kafka topic describe | Block mutation |
| No offline partitions | Kafka metadata and metrics where available | Abort |
| One broker-only Pod at most is disrupted | Node-pool mapping and change log | Abort |
| Original PVCs preserved | Before/after PVC inventory | Escalate if changed |
| No acknowledged event lost | Unique event ID reconciliation | Fail acceptance |
| Full ISR restored | Topic metadata and recovery timeline | Fail acceptance |
| No unresolved client SLO regression | Client logs and metrics | Fail acceptance |

**Fail closed:** unknown context, shared cluster, unhealthy storage, controller majority issue, pending reassignment, or missing incident owner means **no fault injection**.

## 4. Lab prerequisites

Use [Kubernetes-first Lab Foundation](../kubernetes/README.md). These labs assume a dedicated `kafka-lab` namespace, Kafka cluster `sre-kafka`, Strimzi-managed `brokers` and `controllers` KafkaNodePools, and a version-matched `kafka-cli` Pod. The internal plaintext bootstrap listener `sre-kafka-kafka-bootstrap:9092` is a **disposable lab-only example**; use TLS and authorized principals for real environments.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
kubectl get nodes -L topology.kubernetes.io/zone
mkdir -p evidence-ch15
```

**Version gate:** the examples use `kafka.strimzi.io/v1` for KafkaTopic. Confirm this API version exists in your installed Strimzi CRDs; use the supported version if different. Do not assume a Kafka version based solely on the chapter date.

## 5. Lab 01 — Freeze baseline and change-control evidence

```bash
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch15/kafka-before.yaml
kubectl -n kafka-lab get kafkanodepool brokers controllers -o yaml \
  > evidence-ch15/nodepools-before.yaml
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch15/pods-before.txt
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch15/pvcs-before.txt
kubectl get nodes -L topology.kubernetes.io/zone \
  | tee evidence-ch15/nodes-zones.txt
```

Record the change ticket, cluster context, operator/Kafka versions, assigned incident commander, abort conditions and recovery contact. Map each Kafka broker ID to its **broker-role** Pod, node, zone and PVC. Never assume the Pod ordinal is the broker ID.

**Acceptance:** evidence files exist; exact broker identities and failure domains documented.

## 6. Lab 02 — Validate KRaft controller quorum

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status | tee evidence-ch15/quorum-before.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --replication | tee evidence-ch15/quorum-replication.txt
```

Record controller leader, voter set and replication state. This is **not** the same as topic ISR. Stop if controller majority is unhealthy or voter membership is unexpected.

## 7. Lab 03 — Create the capstone KafkaTopic

Save as `topic-ch15.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-acceptance-ch15
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
    cleanup.policy: delete
```

```bash
kubectl apply --dry-run=server -f topic-ch15.yaml
kubectl apply -f topic-ch15.yaml
kubectl -n kafka-lab get kafkatopic sre-acceptance-ch15 -o yaml \
  > evidence-ch15/topic-cr-before.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-acceptance-ch15 \
  | tee evidence-ch15/topic-before.txt
```

**Acceptance:** six partitions, three replicas each, three ISR members each, and valid leaders. Inspect KafkaTopic status as well as actual Kafka metadata.

## 8. Lab 04 — Confirm effective topic policy

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-acceptance-ch15 \
  --describe | tee evidence-ch15/topic-config.txt
```

Verify effective `min.insync.replicas=2`, `retention.ms=86400000`, and `cleanup.policy=delete`. If operator-managed desired state and Kafka metadata differ, investigate reconciliation before proceeding. Do not apply out-of-band `--alter` commands to conceal drift.

## 9. Lab 05 — Baseline producer acknowledgments and unique IDs

```bash
printf '%s\n' \
  'acct-15:event-1501' \
  'acct-15:event-1502' \
  'acct-16:event-1503' \
  'acct-16:event-1504' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-acceptance-ch15 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-acceptance-ch15 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch15/records-before.txt
```

**Acceptance:** four unique event IDs visible. The two records for each account must preserve their order **within their assigned partition**. Kafka offers no global order across all six partitions.

## 10. Lab 06 — Partition and failure-domain review

Create a review worksheet:

| Partition | Leader broker ID | Replica broker IDs | ISR broker IDs | Broker zones | Finding |
|---|---|---|---|---|---|
| 0 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |
| 1 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |
| 2 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |
| 3 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |
| 4 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |
| 5 | Fill | Fill | Fill | Fill | Pass/Fail/Not Tested |

Check that replicas are placed on independent brokers and, for a real multi-AZ environment, independent failure domains. Pod spread and Kafka replica placement are separate controls. If zones are unavailable locally, do not certify multi-AZ resilience.

## 11. Lab 07 — Capacity and broker scale-out planning

**Read-only planning lab; no broker mutation required.** Capture KafkaNodePool replicas, PVC size, available worker resources, per-broker disk usage and target throughput. Calculate:

```text
retained logical bytes ≈ ingress bytes/s × retention seconds
total replica bytes ≈ retained logical bytes × RF
estimated bytes moved ≈ sum(new replica copy sizes)
lower-bound move duration ≈ bytes moved / sustained spare replication bandwidth
```

Prepare a four-broker target design, showing the new broker's node/zone, PVC requirements, and topic replica movement. Confirm that simply increasing KafkaNodePool broker replicas does **not** automatically rebalance existing partitions. Refer to Chapter 013 for the opt-in scale-out/reassignment procedure.

**Acceptance:** documented resource headroom, zone mapping, change gates and rollback boundaries. Do not claim a live scale-out was executed in this planning lab.

## 12. Lab 08 — Replica reassignment canary tabletop

Using actual broker IDs, propose moving one replica of one capstone partition to a hypothetical fourth broker while keeping RF=3. Explain:

1. Which replica will be added and which old replica will be removed.
2. How ISR and disk/network use may change during catch-up.
3. Which Kafka reassignment throttle you would apply and why.
4. How you would verify full ISR, leader distribution and retained events.
5. Why scale-in is blocked until **all topics** have evacuated replicas from a broker.

**Acceptance:** approved canary JSON **design**, not a live reassignment. An example target assignment is not safe to execute until broker IDs and zones are verified.

## 13. Lab 09 — Observability and alert readiness

Collect available evidence for:

- Under-replicated and under-min-ISR partitions.
- Offline partitions and broker Pod restarts.
- Controller quorum health and metadata leader stability.
- Replica fetch lag and broker disk/network saturation.
- PVC Pending, filesystem pressure, CSI attach errors.
- Producer error rate and p95/p99 latency.
- Consumer lag and business event processing age.
- Topic Operator reconciliation errors and unauthorized KafkaTopic changes.

Use Prometheus/Grafana only if deployed and configured. **Do not invent metric values or claim dashboards are live.** If observability is not installed, create a monitoring gap ticket with owners and severity, and mark metric-based acceptance Pending.

## 14. Lab 10 — Automated preflight acceptance

Save as `verify-ch15.sh`. This is a **read-only** check for the chapter topic; it does not authorize a production fault.

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
CLUSTER=sre-kafka
TOPIC=sre-acceptance-ch15
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/7] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[2/7] Node pools'
kubectl -n "$NS" get kafkanodepool brokers controllers

echo '[3/7] Persistent claims'
kubectl -n "$NS" get pvc

echo '[4/7] Metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[5/7] Broker API'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[6/7] Topic replica/ISR validation'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    n=split($0,a,"Replicas: "); if(n<2) next
    split(a[2],b," "); rf=split(b[1],r,",")
    n=split($0,c,"Isr: "); if(n<2) next
    split(c[2],d," "); isr=split(d[1],s,",")
    n=split($0,e,"Leader: "); if(n<2) next
    split(e[2],f," "); leader=f[1]
    seen++
    if(rf!=3 || isr!=3 || leader=="-1" || leader=="none") bad++
  }
  END {
    if(seen!=6 || bad!=0) {
      print "FAIL: partitions="seen" unhealthy="bad
      exit 1
    }
    print "PASS: 6 partitions, RF=3, ISR=3"
  }'

echo '[7/7] Effective topic config'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name "$TOPIC" --describe

echo 'PASS: metadata preflight only; capacity, zone and business checks remain mandatory'
```

```bash
chmod +x verify-ch15.sh
./verify-ch15.sh | tee evidence-ch15/automated-preflight.txt
```

**Coverage:** one topic and basic Kafka connectivity only. The script does not prove all-topic ISR, true HA placement, sufficient disk/network headroom, client SLOs, or data correctness.

## 15. Lab 11 — Opt-in single broker-Pod failure

**Disruptive exercise:** run only in a disposable, isolated cluster after preflight passes and all-topic health is reviewed. This is a failure simulation, **not** a routine maintenance procedure.

Select a broker-only Pod using its actual KafkaNodePool ownership:

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get kafkanodepool brokers -o yaml
BROKER_POD=<EXACT_BROKER_ONLY_POD_NAME>
kubectl -n kafka-lab get pod "$BROKER_POD" -o yaml \
  > evidence-ch15/selected-broker-before.yaml
```

Confirm controller quorum and full ISR **immediately before** injecting the fault. Then:

```bash
kubectl -n kafka-lab delete pod "$BROKER_POD" --wait=false

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-acceptance-ch15 \
  | tee evidence-ch15/topic-during-failure.txt
```

**Observe:** ISR may briefly fall from three to two, and leaders may move. Fast Strimzi reconciliation may restore the Pod before you capture a degraded snapshot. Report actual observations rather than manufacturing failure evidence.

**Abort:** second broker failure, controller quorum degradation, offline partitions, under-min-ISR, sustained client errors, or abnormal PVC state.

## 16. Lab 12 — Recovery, PVC continuity and event reconciliation

```bash
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s

kubectl -n kafka-lab get pods,pvc -o wide \
  | tee evidence-ch15/pods-pvc-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-acceptance-ch15 \
  | tee evidence-ch15/topic-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status \
  | tee evidence-ch15/quorum-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-acceptance-ch15 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch15/records-after.txt
```

**Acceptance:** Kafka Ready, full ISR=3 on all six partitions, stable quorum, original broker PVCs preserved, and all four unique baseline event IDs readable. Record elapsed time from fault to full ISR restoration. If a producer timed out during an incident, treat the outcome as ambiguous until reconciled by unique event ID.

## 17. Lab 13 — SRE incident command simulation

Run a tabletop incident with these injects (no additional Kubernetes mutations):

- At T+0: one broker Pod becomes unavailable.
- At T+2m: under-replicated partitions appear.
- At T+4m: a producer reports timeouts; some events may have been committed.
- At T+6m: replacement Pod cannot attach its zonal PVC.
- At T+10m: an operator proposes lowering min ISR to restore writes.
- At T+15m: business owners request evidence of no lost acknowledged events.

Deliver a timeline, impact statement, triage decisions, command log, recovery plan, escalation path, business event reconciliation and corrective actions. Reject durability-weakening shortcuts unless explicitly accepted through the proper risk process.

## 18. Lab 14 — Rollback and change-control drill

Design a rollback for each change class:

| Change | Safe rollback concept | Limitation |
|---|---|---|
| KafkaNodePool scheduling policy | Revert Git-reviewed desired state | PVC zone topology can prevent rescheduling |
| Broker scale-out | Evacuate all topic replicas, follow Strimzi-supported scale-in | Not safe while replicas remain |
| Partition reassignment | Approved reverse reassignment after health/capacity review | Additional data movement and risk |
| Topic retention change | Reapply approved KafkaTopic config | Deleted records cannot be restored by raising retention |
| Topic partition increase | Versioned-topic migration | Partition count cannot normally shrink in place |
| Pod fault injection | Allow operator reconciliation | Not a configuration rollback |
| Controller quorum failure | Restore supported voter majority and original metadata | Do not hand-edit metadata |

**Acceptance:** rollback boundaries and irreversible operations clearly documented. Do not execute scale-in, PVC deletion or topic partition shrink.

## 19. Lab 15 — Evidence packaging and final scorecard

Package sanitized evidence from `evidence-ch15/`, the topic manifest, acceptance script, architecture diagram, operator version, Kafka version, reviewer names, incident worksheet and monitoring gaps. Exclude Secrets, passwords, certificates/private keys, customer payloads and sensitive internal addresses.

Recommended evidence manifest:

```text
chapter-015/
  change-ticket.md
  architecture-and-failure-domains.md
  topic-ch15.yaml
  evidence-ch15/
  incident-timeline.md
  unique-event-reconciliation.md
  rollback-plan.md
  monitoring-gaps.md
  acceptance-scorecard.md
```

**Status values:** Passed / Failed / Pending / Not Applicable. **Never** mark a lab Passed merely because its instructions were published.

## 20. Ten production incident scenarios

### 20.1 Broker Pending due to PVC zone affinity

**Signals:** broker Pod unschedulable, CSI volume attachment fails, ISR remains degraded.

**Response:** inspect Pod events, PV node affinity, eligible nodes and CSI health. Restore capacity in the correct zone; do not delete the PVC.

### 20.2 Under-min-ISR and producer failures

**Signals:** `acks=all` requests fail, topic ISR below min ISR.

**Response:** restore healthy replicas, preserve durability and use bounded client retries; do not lower min ISR as an automatic fix.

### 20.3 Broker disk exhaustion during catch-up

**Signals:** disk full, follower lag, high p99 latency, ISR shrink.

**Response:** freeze reassignment, assess capacity, expand storage through supported Strimzi/CSI procedure if approved, and preserve logs.

### 20.4 Controller quorum leader instability

**Signals:** metadata operations fail or stall, voter lag, controller leader churn.

**Response:** freeze changes, inspect controller Pods/PVCs and quorum, restore original majority without unsupported voter edits.

### 20.5 Topic Operator configuration drift

**Signals:** KafkaTopic desired state differs from Kafka effective settings.

**Response:** inspect reconciliation conditions, operator logs and competing direct CLI/GitOps writes; restore single source of truth.

### 20.6 Incorrect replica placement across zones

**Signals:** RF=3 but replicas share a correlated node/zone fault domain.

**Response:** map broker IDs to Pod zones and plan approved placement correction; RF alone does not guarantee AZ diversity.

### 20.7 Broker removed before replica evacuation

**Signals:** offline partitions, ISR degradation, unavailable topic data.

**Response:** restore original broker/PVC where possible and follow approved replica evacuation; never force node ID replacement.

### 20.8 Producer timeout with ambiguous delivery

**Signals:** client reports timeout while Kafka may have committed the event.

**Response:** reconcile unique IDs and partition offsets before retries; use idempotent application processing.

### 20.9 Reassignment throttle left enabled

**Signals:** persistent replica catch-up slowness after maintenance.

**Response:** inspect actual throttle configuration and remove only stale overrides introduced by the approved change.

### 20.10 Kubernetes Ready but business SLO failing

**Signals:** Kafka resource Ready while producer p99 or consumer age breaches SLO.

**Response:** inspect application SLIs, broker request pressure, hot partitions, storage and network; close only after end-to-end recovery.

## 21. Troubleshooting matrix

| Symptom | Kubernetes checks | Kafka checks | Unsafe shortcut |
|---|---|---|---|
| Broker Pod Pending | Events, scheduling, PVC | Missing broker ID | Force-delete PVC |
| Pod CrashLoop | Previous logs, OOM, mounts | Replica lag/registration | Reformat log dir |
| Under-replicated partitions | Node/PVC/network | ISR and fetch lag | Reduce RF |
| Writes fail | Broker health | min ISR, leader, acks | Disable durability |
| Offline partition | Replica Pod placement | Leader and ISR | Unclean election |
| Slow reassignment | Disk/network/CSI | Throttle and fetch lag | Unbounded movement |
| Controller issue | Controller Pods/PVC | KRaft quorum | Hand-edit voter files |
| Ordering regression | Producer version/config | Partition count/key | Blind partition expansion |
| Consumer missing events | Client Pod/restart | Retention/log start offset | Random offset reset |
| SLO breach | Resource saturation | p99, lag, errors | Trust Ready alone |

## 22. Production runbooks

### Runbook A — Reliability preflight

1. Verify change approval, isolated target and responsible on-call.
2. Capture Strimzi/Kafka versions, CRDs, node pools, Pods, PVCs and zones.
3. Verify controller quorum and full ISR for all critical topics.
4. Check disk/network headroom, client SLIs and no competing maintenance.
5. Define abort thresholds and communication path.
6. Authorize only the planned single-broker exercise.

### Runbook B — Broker failure and ISR restoration

1. Declare incident and identify affected broker IDs and topic partitions.
2. Capture broker Pod, node, PVC, operator events and Kafka ISR.
3. Restore the original broker using supported Strimzi reconciliation.
4. Avoid second-broker disruption or controller changes.
5. Verify Kafka Ready, full ISR, stable quorum and client SLOs.
6. Reconcile acknowledged event IDs and document recovery duration.

### Runbook C — Data integrity investigation

1. Identify all producer acknowledgments, errors and ambiguous timeouts.
2. Collect unique event IDs, topic/partition/offset evidence.
3. Compare Kafka records and downstream consumer processing.
4. Resolve duplicates or missing IDs through application-approved workflows.
5. Preserve audit evidence and communicate unresolved uncertainty.
6. Close only after business owner acceptance.

### Runbook D — Broker scaling and reassignment

1. Inventory actual broker IDs, zones, PVCs, topic assignments and capacity.
2. Scale through KafkaNodePool only after node/PVC capacity approval.
3. Validate new broker registration separately from Pod Ready.
4. Design and review a small throttled reassignment canary.
5. Verify ISR, throughput, p99, leader distribution and event integrity.
6. Retire a broker only after all required replicas are evacuated.

### Runbook E — Controller quorum recovery

1. Freeze disruptive operations.
2. Capture KRaft quorum leader, voter status and metadata log diagnostics.
3. Preserve controller PVCs and cluster identity.
4. Restore original majority through supported, version-specific procedures.
5. Verify stable metadata operations, broker registration and topic health.
6. Record root cause, residual risks and preventive controls.

### Runbook F — Post-incident operational acceptance

1. Confirm zero offline partitions and full ISR for critical topics.
2. Verify quorum, Pods, PVCs, replica placement and application SLIs.
3. Reconcile unique event IDs and outstanding producer ambiguity.
4. Confirm monitoring and alert delivery, or open a tracked gap.
5. Complete incident review and rollback/change evidence.
6. Obtain independent reviewer approval before declaring production readiness.

## 23. Enterprise readiness checklist

- [ ] Kafka/Strimzi version pair and CRD API schema validated.
- [ ] Dedicated controller and broker node pools defined.
- [ ] Worker/PVC/zone failure-domain mapping recorded.
- [ ] Critical KafkaTopic RF, min ISR, retention and owner approved.
- [ ] Baseline controller quorum and full ISR documented.
- [ ] Broker scaling/reassignment capacity plan reviewed.
- [ ] Unique event ID and producer acknowledgment baseline recorded.
- [ ] Automated preflight executed with captured output.
- [ ] Single broker-only Pod failure completed safely or marked Pending.
- [ ] Original broker PVCs preserved and full ISR restored.
- [ ] Business event reconciliation passed.
- [ ] SLO dashboards/alerts verified or gap ticket created.
- [ ] Security controls, TLS, RBAC and Secrets handling reviewed.
- [ ] Rollback boundaries and irreversible operations documented.
- [ ] Independent reviewer signed off on execution evidence.

## 24. Final assessment — 100 points

| Assessment domain | Points | Evidence |
|---|---:|---|
| Kubernetes/Strimzi/KRaft architecture and failure domains | 10 | Broker/Pod/PVC/zone inventory |
| Controller quorum and Kafka metadata health | 10 | Quorum snapshots |
| KafkaTopic policy and actual metadata | 10 | CR, config and topic describe |
| Partition/replica/leader distribution | 10 | Placement worksheet |
| Producer acknowledgments and record reconciliation | 10 | Unique event IDs |
| Broker scale-out/reassignment capacity and canary design | 10 | Reviewed plan |
| Automated preflight and safety gates | 10 | Script output |
| Controlled broker fault and full ISR recovery | 10 | Before/during/after evidence |
| Incident investigation, SLOs and observability | 10 | Timeline and monitoring |
| Runbooks, rollback and independent review | 10 | Signed scorecard |
| **Total** | **100** | |

**Pass criteria:** ≥85/100, **all safety-critical controls satisfied**, zero unexplained acknowledged event loss, and independently reviewed evidence. If the fault was not run, its 10 points remain **Pending**, not automatically awarded. **Published ≠ Executed ≠ Security Approved ≠ Production Ready.**

## 25. Cleanup and next chapter

After saving evidence, confirm the chapter topic is disposable and then:

```bash
kubectl -n kafka-lab delete kafkatopic sre-acceptance-ch15 --ignore-not-found
```

This may permanently delete all topic records. **Do not** delete Kafka PVCs, scale down broker pools, or remove the Kafka cluster as routine capstone cleanup. Preserve the lab for Chapter 016.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/), [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 016 — Kafka Producer Architecture, Acknowledgments, Retries and Idempotence on Kubernetes. This begins Part 04 — Producers, Consumers and Consumer Groups.

---

**Verification boundary:** Chapter published to GitHub. Live Kubernetes execution, release-specific CRD verification, independent security review and production acceptance remain Pending.
