# Chapter 014 — Kafka Replication Internals, ISR Management and Kubernetes Failure Recovery

**Track:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 03 — Brokers, Topics, Partitions and Replication  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–013; [Kubernetes-first lab foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, Kubernetes platform engineers  
**Publication:** Complete · **Live lab execution:** Pending · **Security review:** Pending

> **Operational safety:** Broker failure, controller failure, network partition, and replica manipulation are disruptive. All fault injection is opt-in and limited to a disposable Kubernetes cluster with dedicated storage. Never weaken `min.insync.replicas`, enable unclean leader election, delete PVCs, force-delete a controller, or mutate KRaft metadata to make a test pass. Record a baseline and explicit abort conditions before any fault.

## 1. Learning objectives

1. Trace leader and follower replication, fetch requests, high watermark (HW), log end offset (LEO), and in-sync replicas (ISR).
2. Explain why replication factor, ISR, `min.insync.replicas`, and producer acknowledgments are different controls.
3. Analyze broker Pod, worker node, and availability-zone failures without conflating Kubernetes readiness with Kafka durability.
4. Inspect topic partition leadership and replica state using a version-matched Kafka CLI Pod.
5. Simulate one broker-only Pod failure and prove convergence after Strimzi reconciliation.
6. Validate records acknowledged before, during, and after a failure using unique event IDs.
7. Diagnose under-replicated partitions, offline partitions, replica lag, storage failures, and KRaft quorum instability.
8. Build automated health gates, incident runbooks, and a scored reliability assessment.

## 2. Enterprise architecture

```text
                           Kubernetes API / GitOps
                                     |
                            Strimzi Operator
                              /           \
                    KafkaNodePool       Kafka CR
                      /     \
              Controllers   Brokers (3)
                 (3)         |  |  |
                  |          |  |  +---- Broker C / PVC-C / Zone C
             KRaft voters   |  +------- Broker B / PVC-B / Zone B
                             +---------- Broker A / PVC-A / Zone A
                                         |
                        topic orders (RF=3, minISR=2)
                         partition 0: A leader; B,C followers
                         partition 1: B leader; A,C followers
                         partition 2: C leader; A,B followers
                                         |
                             producer acks=all
                                         |
                           consumer group + audit
```

The diagram illustrates intended placement, **not guaranteed scheduling**. Kubernetes controls Pod scheduling and storage attachment; Kafka controls partition replica placement, leader election, and ISR. Strimzi reconciles Kubernetes resources but does not replace Kafka's replication protocol.

### 2.1 Critical concepts

| Concept | Meaning | Why SREs care |
|---|---|---|
| Replica | A broker's copy of a partition log | Redundancy and recovery |
| Leader | Replica serving partition writes and most reads | Client availability |
| Follower | Replica fetching from the leader | Catch-up and failover |
| ISR | Replicas sufficiently caught up under Kafka's lag policy | Eligible synchronized copies |
| LEO | Next offset to be appended to a replica log | Replica progress |
| HW | Committed offset boundary for partition reads | Visibility and durability reasoning |
| RF | Total assigned replica count | Failure tolerance potential |
| min ISR | Minimum ISR count required for eligible `acks=all` writes | Write admission under degradation |
| acks=all | Producer waits for the leader's required acknowledgment conditions | Stronger write durability |
| KRaft quorum | Controller voter majority managing cluster metadata | Metadata availability, separate from topic ISR |

**Nuance:** `acks=all` is not the same as “wait for every assigned replica,” and `min.insync.replicas` is not the configured replication factor. A partition with RF=3, ISR=2 and min ISR=2 can continue accepting eligible `acks=all` writes; if ISR falls below two, such writes should fail rather than silently weakening the durability contract.

## 3. Replication and failure-state reasoning

### 3.1 Normal path

1. Producer sends a keyed record to the partition leader.
2. Leader appends it to its local log.
3. Follower replicas fetch the new record.
4. Kafka advances the partition high watermark as required replicas catch up.
5. With `acks=all`, the producer receives a successful acknowledgment when the broker's configured durability conditions are satisfied.
6. Consumers read committed records, while application-level exactly-once outcomes still depend on downstream processing.

### 3.2 One broker lost

If three replicas were healthy and one broker fails, two replicas may remain in ISR. Kafka may elect a healthy follower leader if necessary. Availability depends on whether the affected partition has an eligible leader and the remaining ISR meets `min.insync.replicas`. Kafka can temporarily report under-replicated partitions even while clients continue to succeed.

### 3.3 Two brokers lost

With RF=3 and min ISR=2, two lost replicas can leave ISR=1. Writes requiring `acks=all` should fail; depending on leadership and the cluster state, reads or other operations may still be possible. **Do not** run a two-broker outage exercise in this chapter.

### 3.4 Controller quorum failure

Controller majority loss is distinct from broker ISR degradation. KRaft quorum instability can block metadata operations even when some existing data paths still work. Never infer quorum health from topic ISR alone.

## 4. Kubernetes prerequisites and compatibility

Use the [shared Kubernetes lab](../kubernetes/README.md) with a supported Strimzi/Kafka version pair. Confirm the actual CRD API version, six persistent Kafka Pods (three controllers and three brokers), the namespace `kafka-lab`, bootstrap service `sre-kafka-kafka-bootstrap:9092`, and a version-matched `kafka-cli` Pod.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
kubectl get nodes -L topology.kubernetes.io/zone
mkdir -p evidence-ch14
```

**Go/no-go:** do not proceed if the environment is shared, Kafka is not Ready, any critical PVC is unbound, controller majority is unstable, or broker capacity is insufficient. A one-node kind cluster is not a valid HA fault-test environment.

## 5. Lab A — Map broker replicas to Kubernetes failure domains

```bash
kubectl -n kafka-lab get kafkanodepool brokers controllers -o yaml \
  > evidence-ch14/nodepools-before.yaml
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch14/pods-before.txt
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch14/pvcs-before.txt
kubectl get nodes -L topology.kubernetes.io/zone \
  | tee evidence-ch14/nodes-zones.txt
```

Record actual broker IDs using Kafka metadata and operator-generated Pod labels. Do not assume Pod suffix equals broker ID. Build a table of broker ID → broker-only Pod → Kubernetes node → zone → PVC. If local nodes lack zone labels, record the limitation rather than claiming multi-AZ protection.

**Acceptance:** all three broker identities, PVCs, and failure domains are documented; controller-role Pods are clearly distinguished.

## 6. Lab B — Create a replicated chapter topic

Create `topic-ch14.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-isr-ch14
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
```

**Schema gate:** replace `kafka.strimzi.io/v1` if the installed Strimzi release requires another supported version. Verify with `kubectl api-resources` and the installed CRD.

```bash
kubectl apply --dry-run=server -f topic-ch14.yaml
kubectl apply -f topic-ch14.yaml
kubectl -n kafka-lab get kafkatopic sre-isr-ch14 -o yaml \
  > evidence-ch14/topic-cr-before.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-isr-ch14 \
  | tee evidence-ch14/topic-before.txt
```

**Acceptance:** exactly three partitions, three assigned replicas each, ISR of three per partition, and a leader for every partition. A Kubernetes KafkaTopic resource alone is not evidence that Kafka reconciliation succeeded.

## 7. Lab C — Baseline acknowledgments and record accounting

```bash
printf '%s\n' \
  'event-1401:baseline-created' \
  'event-1402:baseline-validated' \
  'event-1403:baseline-completed' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-isr-ch14 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Read records and record their partition/offset metadata:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-isr-ch14 --from-beginning --max-messages 3 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch14/records-before.txt
```

**Acceptance:** all three unique event IDs appear. A producer CLI exit status does not by itself prove business downstream processing; record consumer evidence and reconcile unique IDs.

## 8. Lab D — Metadata quorum versus partition ISR

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status \
  | tee evidence-ch14/quorum-before.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --replication \
  | tee evidence-ch14/quorum-replication-before.txt
```

Compare the controller voter set and metadata high watermark with the **different** partition leader/ISR metadata in `topic-before.txt`. Record the distinction in the incident worksheet.

## 9. Lab E — Controlled single broker-Pod failure

This is an **abrupt failure simulation** and must be performed only after approval in the disposable HA lab. It is **not** an operator-managed rolling restart.

### 9.1 Preflight

Confirm full ISR for all three partitions, Kafka Ready, controller quorum healthy, no competing maintenance, and exactly one broker-only Pod selected.

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get kafkanodepool brokers -o yaml
kubectl -n kafka-lab get pvc -o wide
```

Set `BROKER_POD` to the **actual broker-only Pod** after checking its labels and node pool:

```bash
BROKER_POD=<EXACT_BROKER_ONLY_POD_NAME>
kubectl -n kafka-lab get pod "$BROKER_POD" -o yaml \
  > evidence-ch14/selected-broker-before.yaml
```

### 9.2 Inject the fault

```bash
kubectl -n kafka-lab delete pod "$BROKER_POD" --wait=false
kubectl -n kafka-lab get pods -o wide
```

Do not delete the broker PVC, controller Pod, KafkaNodePool, or another broker. Strimzi should reconcile the missing Pod.

### 9.3 Observe degraded replication

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-isr-ch14 \
  | tee evidence-ch14/topic-during-failure.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status \
  | tee evidence-ch14/quorum-during-failure.txt
```

**Expected possibilities:** ISR may shrink from three to two, a leader may move, and some operations may briefly retry. A fast-recovering Pod may restore ISR before the snapshot; that is not a failed experiment, but record the timing honestly.

## 10. Lab F — Produce during the fault window

If the broker remains unavailable and ISR is at least two for the target partition, attempt a bounded write:

```bash
printf 'event-1404:during-single-broker-failure\n' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-isr-ch14 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --producer-property delivery.timeout.ms=15000 \
  --property parse.key=true --property key.separator=:
```

**Interpretation:** success with two ISR members is consistent with RF=3/minISR=2/acks=all. Failure is a diagnostic result, not a reason to weaken min ISR. The broker may already have recovered; inspect timing before attributing the outcome to degraded operation.

**Abort:** offline partition, controller quorum instability, ISR below min ISR, repeated producer failures, or an unexpected second Pod outage.

## 11. Lab G — Strimzi reconciliation and ISR restoration

```bash
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s

kubectl -n kafka-lab get pods,pvc -o wide \
  | tee evidence-ch14/pods-pvc-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-isr-ch14 \
  | tee evidence-ch14/topic-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status \
  | tee evidence-ch14/quorum-after.txt
```

**Acceptance:** three broker-role Pods healthy, original PVCs retained, all three topic partitions back to ISR=3, no offline partitions, and stable controller quorum. Kafka CR Ready alone is insufficient: inspect topic ISR and actual records.

## 12. Lab H — Post-failure record reconciliation

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-isr-ch14 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch14/records-after.txt
```

Compare `event-1401` through `event-1404` to the acknowledged write log. If the fault-window producer returned an error, do **not** assume `event-1404` was either definitely written or definitely absent; reconcile actual Kafka records before retrying. Idempotent producer settings do not prevent application-level duplicates across independent producer sessions.

## 13. Lab I — Operator and broker troubleshooting evidence

```bash
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  | tail -50 | tee evidence-ch14/kubernetes-events.txt

kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch14/kafka-cr-after.yaml

kubectl -n kafka-lab get kafkanodepool brokers controllers -o yaml \
  > evidence-ch14/nodepools-after.yaml
```

Identify the actual Strimzi operator deployment before collecting logs; do not assume a fixed operator Pod name or namespace:

```bash
kubectl get deployments -A | grep -i strimzi
kubectl -n kafka-lab describe pod <EXACT_BROKER_POD_NAME>
kubectl -n kafka-lab logs <EXACT_BROKER_POD_NAME> --all-containers --tail=200
```

If the operator runs in a different namespace, collect its logs from that namespace. Redact secrets, internal hostnames, client payloads, and credentials before attaching evidence.

## 14. Lab J — Failure-domain tabletop simulation

**No additional mutation.** Using the broker/zone/PVC mapping from Lab A, reason through:

1. Loss of one broker Pod.
2. Loss of one worker node hosting broker and controller Pods.
3. Loss of one availability zone.
4. Loss of one zonal PV.
5. Loss of controller majority.

For each case, predict surviving ISR, eligible leaders, controller voters, whether `acks=all` writes remain available, and how long volume reattachment may take. Do not claim an AZ test was executed if only a tabletop review was performed.

## 15. Read-only automated acceptance

Save as `verify-ch14.sh`. The script checks the dedicated topic after recovery and does not inject failures.

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
CLUSTER=sre-kafka
TOPIC=sre-isr-ch14
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka resource Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[2/6] Node pools and PVCs'
kubectl -n "$NS" get kafkanodepool brokers controllers
kubectl -n "$NS" get pvc

echo '[3/6] CLI and metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[4/6] Topic metadata'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

echo '[5/6] Require three partitions, RF=3, ISR=3 and leaders'
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
    if(seen!=3 || bad!=0) {
      print "FAIL: partitions="seen" unhealthy="bad
      exit 1
    }
    print "PASS: 3 partitions, RF=3, ISR=3, leaders present"
  }'

echo '[6/6] Broker connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo 'PASS: Kafka metadata and ISR acceptance; verify event IDs and PVCs separately'
```

```bash
chmod +x verify-ch14.sh
./verify-ch14.sh
```

**Coverage limits:** this checks one topic and basic metadata; it does not prove all-topic health, stable storage, multi-zone placement, client SLOs, TLS/ACL security, or business event accounting. Those are separate acceptance gates.

## 16. Eight production incident scenarios

### Incident 1 — Under-replicated partitions after broker restart

**Signal:** ISR remains below RF long after Pod Ready.

**Investigate:** topic describe, follower fetch lag, broker logs, PVC I/O, inter-broker network, broker registration.

**Mitigate:** restore healthy follower catch-up; do not reduce RF or min ISR to clear the alert.

### Incident 2 — `NOT_ENOUGH_REPLICAS` on `acks=all`

**Signal:** producer requests fail when ISR drops below min ISR.

**Investigate:** broker availability, topic min ISR, ISR, client retry behavior, disk/network saturation.

**Mitigate:** restore replicas; coordinate client retry/backoff and preserve idempotency. Do not weaken durability silently.

### Incident 3 — Offline partition after correlated worker failure

**Signal:** partition has no eligible leader.

**Investigate:** broker Pod placement, node availability, PV topology, replica set and unclean election policy.

**Mitigate:** restore an eligible in-sync replica and its storage through supported procedures. Do not force unclean election without explicit data-loss acceptance.

### Incident 4 — Broker Pod CrashLoopBackOff due to disk corruption

**Signal:** broker repeatedly fails startup and ISR shrinks.

**Investigate:** previous logs, filesystem errors, PV health, disk fullness, node identity and Kafka log diagnostics.

**Mitigate:** preserve evidence, follow documented Kafka/Strimzi recovery; never delete the PVC or reformat data to suppress the symptom.

### Incident 5 — KRaft controller quorum instability

**Signal:** metadata operations stall, leader epochs change rapidly, controller voters lag.

**Investigate:** controller-role Pods, quorum replication, network partitions, metadata PVCs, operator logs.

**Mitigate:** restore original majority, freeze disruptive changes and escalate unsupported voter changes.

### Incident 6 — Replica catch-up saturates network

**Signal:** producer p99 rises, fetch lag increases, ISR restoration slows.

**Investigate:** broker network, disk throughput, replica fetch metrics, concurrent reassignments, recovery throttle.

**Mitigate:** stop additional movement, restore headroom, apply supported throttling after review.

### Incident 7 — Broker Ready but wrong failure-domain placement

**Signal:** all replicas present but multiple broker Pods share a node or zone.

**Investigate:** Pod/node/zone mapping, StorageClass topology, Kafka replica-to-broker mapping.

**Mitigate:** adjust operator-supported scheduling and Kafka replica placement separately; test zone loss in a dedicated environment.

### Incident 8 — Ambiguous producer result during leader election

**Signal:** client timeout occurs, but event may have been committed.

**Investigate:** producer IDs, Kafka topic offsets, unique business event IDs, downstream processing, retries.

**Mitigate:** reconcile before retry, use idempotent processing and transactional patterns where applicable; never assume timeout equals failed write.

## 17. Troubleshooting matrix

| Symptom | Kubernetes first check | Kafka first check | Unsafe shortcut |
|---|---|---|---|
| Pod Pending | Events, affinity, PVC, node capacity | Missing broker registration | Delete PVC |
| Broker CrashLoop | Previous logs, OOM, filesystem | ISR and log recovery | Reformat storage |
| ISR below RF | Pod health, disk, network | Replica fetch lag | Lower RF |
| Writes rejected | Broker/network health | min ISR, ISR, acks | Lower min ISR |
| Leader unavailable | Replica Pod availability | Leader/ISR state | Unclean election |
| Controller errors | Controller Pods and PVCs | Quorum status | Arbitrary voter edits |
| Consumer duplicates | Consumer Pod restart | Offset commits | Blind offset reset |
| Post-recovery slow | CSI/network/CPU | Replica catch-up, throttles | Random broker restart |

## 18. SRE runbooks

### Runbook A — Replication degradation

1. Declare incident scope and capture Kafka topic leader/ISR metadata.
2. Confirm controller quorum and identify impacted broker IDs.
3. Map brokers to Pods, worker nodes, zones and PVCs.
4. Inspect replica fetch lag, disk, network and recent operator changes.
5. Restore healthy replicas using supported procedures.
6. Verify full ISR, producer SLOs, consumer lag and event IDs.
7. Record incident timeline, impact and preventive action.

### Runbook B — One broker-Pod failure

1. Confirm isolated lab or approved production incident procedure.
2. Capture broker Pod UID, Kafka ID, node, PVC and topic ISR.
3. Observe broker loss; do not disrupt another broker/controller.
4. Allow Strimzi to reconcile and restore the original persistent identity.
5. Validate Kafka Ready **and** full ISR separately.
6. Reconcile acknowledged records and close only after application recovery.

### Runbook C — Controller quorum incident

1. Freeze upgrades, scale operations and fault injection.
2. Inspect voter membership, leader, high watermark and controller Pod health.
3. Preserve metadata PVCs, logs and cluster identity.
4. Restore the original majority with version-supported recovery.
5. Verify stable quorum, broker registration and topic health.
6. Document residual data-loss or metadata risk.

### Runbook D — Producer ambiguity and data reconciliation

1. Collect producer errors, retries, event IDs and timestamps.
2. Determine Kafka topic/partition/offset records actually present.
3. Check consumer group offsets and downstream idempotency keys.
4. Retry only after reconciliation and approved deduplication strategy.
5. Report confirmed delivery, duplicates and unresolved event IDs.
6. Preserve sanitized evidence and correct application retry logic.

### Runbook E — Maintenance safety gate

1. Require healthy controller majority, Kafka Ready and full ISR for critical topics.
2. Check Pod placement, PVC capacity, disk/network headroom and client SLOs.
3. Approve only one broker operation at a time.
4. Use Strimzi release-supported rolling maintenance, not arbitrary StatefulSet edits.
5. Stop immediately on under-min-ISR, offline partitions or sustained client errors.
6. Restore baseline and capture after-state evidence.

## 19. SLOs, alerts and evidence

**Key indicators:** offline partitions, under-replicated partitions, under-min-ISR partitions, replica fetch lag, controller quorum status, broker Pod restarts, PVC latency/capacity, producer request failures, p99 produce latency, consumer processing lag and unique business event reconciliation.

**Suggested reliability gates:** zero offline partitions in steady state, no persistent under-min-ISR, full ISR before maintenance, bounded recovery time, and no unexplained acknowledged event loss. Establish actual numerical thresholds from workload baselines and approved error budgets.

**Evidence pack:** Kafka CR/node pools, Pod/node/PVC mapping, before/during/after topic describe, quorum status, producer results, consumed event IDs, operator logs, Kubernetes events, incident timeline and reviewer sign-off.

## 20. Enterprise readiness checklist

- [ ] Kafka/Strimzi compatibility and installed CRD schema checked.
- [ ] Controller voters and broker Pods placed across intended failure domains.
- [ ] Persistent storage capacity and zone affinity documented.
- [ ] Critical topics use approved RF/min ISR and producer acknowledgment policy.
- [ ] KafkaTopic desired state and Kafka metadata reconciled.
- [ ] Full ISR and stable controller quorum confirmed before disruption.
- [ ] Only one broker-only Pod selected for fault injection.
- [ ] No PVC, KafkaNodePool or KRaft metadata deletion performed.
- [ ] Post-fault full ISR, broker identity and event IDs verified.
- [ ] Monitoring and alert coverage reviewed.
- [ ] Incident runbooks and rollback boundaries documented.
- [ ] Security, DR and independent live lab review tracked separately.

## 21. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain leader/follower, HW/LEO and ISR mechanics | 10 |
| Distinguish RF, min ISR, acks and controller quorum | 10 |
| Map broker Pods, IDs, zones and PVCs | 10 |
| Create and validate RF=3/minISR=2 topic | 10 |
| Capture producer/consumer baseline evidence | 10 |
| Execute safe single broker-Pod fault | 10 |
| Explain fault-window acknowledgments and ambiguity | 10 |
| Prove full ISR, quorum and PVC recovery | 10 |
| Run automated acceptance and explain gaps | 10 |
| Deliver incident analysis and production runbooks | 10 |

**Pass:** ≥85/100, no critical safety violation, and independently captured evidence. A written chapter is not a passed lab.

## 22. Cleanup and next chapter

Only after evidence capture and explicit confirmation that the topic is disposable:

```bash
kubectl -n kafka-lab delete kafkatopic sre-isr-ch14 --ignore-not-found
```

Do not delete the Kafka cluster or PVCs. Retain the CLI Pod if needed for Chapter 015.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Pods](https://kubernetes.io/docs/concepts/workloads/pods/), [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 015 — Kafka Brokers, Topics, Replication and Kubernetes Reliability Acceptance Capstone.

---

**Verification boundary:** Authored and published to GitHub. Live Kubernetes execution, release-specific CRD validation, security review, and production acceptance remain Pending.
