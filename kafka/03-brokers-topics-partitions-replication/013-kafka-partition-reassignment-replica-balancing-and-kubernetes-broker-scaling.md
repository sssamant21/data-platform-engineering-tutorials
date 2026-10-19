# Chapter 013 — Kafka Partition Reassignment, Replica Balancing and Kubernetes Broker Scaling

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 03 — Brokers, Topics, Partitions and Replication  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–012; [Kubernetes Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Publication:** Complete | **Live execution:** Pending | **Security review:** Pending

> **Operational boundary:** Partition reassignment moves live data and can cause broker disk/network saturation, lag, ISR shrinkage and client errors. Broker scale-down may strand replicas. All mutations below target a disposable Kafka cluster and a chapter-specific topic. Production execution requires approved change control, capacity checks, throttling, canary observation and tested recovery. Never delete Kafka PVCs or manually change KRaft node IDs.

## 1. Learning objectives

1. Separate Kubernetes Pod scheduling from Kafka partition replica assignment and leader balancing.
2. Explain Kafka reassignment phases, data transfer, ISR catch-up and completion verification.
3. Understand broker scale-out through Strimzi KafkaNodePool, and why scaling Pods alone does not rebalance topics.
4. Prepare a validated, throttled reassignment plan using Kafka's supported administration tools.
5. Evaluate replica spread across brokers, nodes and availability zones.
6. Detect unsafe broker scale-in, under-replication, disk headroom and network bottlenecks.
7. Automate read-only preflight checks and record before/during/after evidence.
8. Respond to stuck reassignment, leadership imbalance and Kubernetes storage scheduling incidents.

## 2. Architecture and operational separation

```text
                  GitOps / approved change
                           |
                   KafkaNodePool replicas
                           |
                    Strimzi Operator
                           |
               Kubernetes scheduler + CSI
                           |
                 broker Pods / broker IDs
                           |
         Kafka Admin API --alter partition reassignment
                           |
                  Kafka partition replicas
                           |
            leader placement / ISR / client SLOs
```

**Two separate workflows:**

- **Capacity scaling:** add Kafka broker-role Pods through a Strimzi KafkaNodePool, with persistent storage and node placement.
- **Data redistribution:** move selected topic partition replicas to target broker IDs through Kafka's partition reassignment mechanism or a compatible supported automation tool.

Adding broker Pods is not sufficient to place existing topic replicas on them. Conversely, changing replica assignments without capacity planning can overwhelm the brokers.

### 2.1 Scale-out versus scale-in

| Operation | Primary risk | Required gate |
|---|---|---|
| Add broker | PVC provisioning, scheduling, identity, idle new broker | Broker registered and healthy |
| Move replica | Disk/network amplification, ISR catch-up | Target disk headroom, throttling |
| Balance leaders | Uneven CPU/network, transient leadership changes | Client SLO baseline |
| Remove broker | Replica/leader stranding, data availability | No required replicas remain on removed broker |
| Replace worker | Zonal PV affinity and scheduling | Storage attach and node capacity |
| Resize PVC | CSI support and possible filesystem restart | StorageClass/Strimzi compatibility |

## 3. Kafka reassignment internals

Kafka stores partition replicas on broker IDs. A reassignment introduces target replicas, copies partition data, waits for the new replicas to catch up, and eventually removes old replicas when safe. Movement can increase disk reads/writes and inter-broker network traffic. Kafka's administration tooling can throttle replication traffic, but throttling may extend completion time.

The **leader** is a separate concern: moving replicas does not necessarily yield balanced leader distribution. After reassignment, verify leaders, ISR and workload skew rather than merely checking that the command completed.

### 3.1 Important constraints

- Never reduce replication factor below the approved durability policy.
- Do not remove the last healthy replica or allow an unclean election to “finish” a move.
- Avoid reassignment while a controller quorum or broker is degraded.
- Reassignment plans must use actual broker IDs, not Pod ordinal guesses.
- In multi-AZ deployments, inspect the broker-to-zone mapping before designing placement.
- Consider rack awareness and Kafka's `broker.rack` configuration as supported by your Strimzi release.
- Prefer small canary movements, then controlled batches; do not move all high-volume partitions simultaneously.
- If using Strimzi Cruise Control/KafkaRebalance, follow the operator release's supported API and approval workflow rather than combining independent controllers over the same partitions.

## 4. Capacity and safety mathematics

Estimate movement volume:

```text
estimated bytes to copy ≈ sum(logical sizes of new replica copies)
transfer duration lower bound ≈ bytes to copy / available sustained replication bandwidth
required headroom ≈ target replica bytes + peak ingress growth + operational reserve
```

**Illustrative example:** moving 150 GiB of replicas with 50 MiB/s of sustained spare transfer capacity has a best-case transfer time of roughly 51 minutes before catch-up and overhead. Actual completion depends on broker I/O, throttling, ongoing writes and network contention.

**Production gate:** collect per-broker disk usage, disk IOPS, network utilization, replica fetch lag, under-replicated partitions, client p99 and consumer lag. Reject the plan if headroom cannot absorb the transfer and normal workload concurrently.

## 5. Lab setup and isolation

Use the [Kubernetes Lab Foundation](../kubernetes/README.md), with three dedicated controller-role Pods, three broker-role Pods and a CLI Pod in `kafka-lab`. Confirm Strimzi/Kafka compatibility and the exact installed KafkaTopic CRD API version. The examples assume `kafka.strimzi.io/v1` is supported; substitute your release's actual supported version if different.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch13
```

**Stop:** unknown cluster context, unbound PVCs, missing controller majority, offline partitions or unresolved operator reconciliation errors.

## 6. Lab A — Baseline broker, node and partition inventory

```bash
kubectl -n kafka-lab get kafkanodepool brokers controllers -o yaml \
  > evidence-ch13/nodepools-before.yaml
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch13/pods-before.txt
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch13/pvc-before.txt
kubectl get nodes -L topology.kubernetes.io/zone \
  | tee evidence-ch13/nodes-zones.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status | tee evidence-ch13/quorum-before.txt
```

Record actual broker IDs from Kafka metadata and correlate them with Kafka broker Pods using operator labels and logs. Pod names and broker IDs are **not interchangeable**.

## 7. Lab B — Create a replica placement topic

```bash
cat > topic-ch13.yaml <<'YAML'
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-reassign-ch13
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
YAML
kubectl apply --dry-run=server -f topic-ch13.yaml
kubectl apply -f topic-ch13.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-reassign-ch13 \
  | tee evidence-ch13/topic-before.txt
```

Produce a small reproducible dataset:

```bash
printf '%s\n' \
  'order-1:created' 'order-1:paid' \
  'order-2:created' 'order-2:shipped' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-reassign-ch13 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

**Acceptance:** six partitions, RF=3, ISR=3 and four acknowledged records. Keep event IDs for post-reassignment reconciliation.

## 8. Lab C — Build a read-only reassignment proposal

**Crucial design constraint:** with exactly three brokers and RF=3, every partition already has a replica on every broker. You cannot redistribute replicas to a *new* broker until a fourth broker exists, and you cannot reduce RF to fake balancing.

Inspect topic assignments and available brokers:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-reassign-ch13
```

Draft a placement matrix (example only; replace IDs and zones with actual inventory):

| Partition | Current replicas | Proposed replicas after broker scale-out |
|---|---|---|
| 0 | A,B,C | A,B,D |
| 1 | A,B,C | A,C,D |
| 2 | A,B,C | B,C,D |
| 3 | A,B,C | A,B,D |
| 4 | A,B,C | A,C,D |
| 5 | A,B,C | B,C,D |

Maintain three replicas per partition and select broker IDs that span failure domains. The table is **not** an executable JSON plan; never substitute these letters into Kafka commands.

## 9. Lab D — Kubernetes broker scale-out design and execution

A Strimzi KafkaNodePool is the operator-managed source of truth for broker count. Verify worker-node and PVC capacity **before** scaling. Check whether the installed operator supports the requested scaling mechanism and storage layout.

Read the current pool:

```bash
kubectl -n kafka-lab get kafkanodepool brokers -o yaml \
  > evidence-ch13/brokers-original.yaml
kubectl -n kafka-lab get pvc -o wide
kubectl get nodes -o wide
```

**Opt-in isolated lab mutation:** after change review, scale the broker pool from three to four through the supported KafkaNodePool API:

```bash
kubectl -n kafka-lab patch kafkanodepool brokers \
  --type=merge -p '{"spec":{"replicas":4}}'
kubectl -n kafka-lab get kafkanodepool brokers
kubectl -n kafka-lab get pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
```

**Gate:** confirm a fourth **broker-role** Pod is Ready, its PVC is Bound, and Kafka Admin API reports the new broker ID. Do not proceed if the fourth broker has no eligible node, PVC cannot bind, or quorum/ISR degrades.

**Rollback warning:** scaling back to three before moving replicas can be appropriate only after confirming the new broker has no topic replicas or leadership; never scale down blindly. Operator scale-down semantics and node ID reuse vary by version.

## 10. Lab E — Generate a candidate Kafka reassignment plan

Kafka's `kafka-reassign-partitions.sh` supports `--generate`, `--execute`, `--verify`, and `--list` in supported releases. Confirm exact CLI flags with your installed Kafka version.

Identify actual broker IDs, then create a topic selection file on your workstation:

```bash
cat > topics-to-move-ch13.json <<'JSON'
{"topics":[{"topic":"sre-reassign-ch13"}],"version":1}
JSON
```

Copy it into the tools Pod:

```bash
kubectl -n kafka-lab cp topics-to-move-ch13.json \
  kafka-cli:/tmp/topics-to-move-ch13.json
```

Use the **actual** broker IDs from the cluster. Example only (replace `0,1,2,3`):

```bash
BROKER_IDS=0,1,2,3
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topics-to-move-json-file /tmp/topics-to-move-ch13.json \
  --broker-list "$BROKER_IDS" --generate \
  | tee evidence-ch13/generated-plan.txt
```

The tool prints current and proposed JSON assignments. **Review the generated proposal manually**: every partition must keep RF=3, all target broker IDs must be valid, and broker/zone placement must meet policy. Generated proposals may move more partitions than intended; select a small canary subset before executing.

## 11. Lab F — Canary reassignment with throttling

This exercise is deliberately **opt-in and disruptive**. Use a disposable cluster and only one or two partitions. Create a reviewed `reassignment-canary-ch13.json` from the generated proposed JSON, containing the exact target assignments for the chosen partitions. Example **shape only**:

```json
{
  "version": 1,
  "partitions": [
    {
      "topic": "sre-reassign-ch13",
      "partition": 0,
      "replicas": [0, 1, 3]
    }
  ]
}
```

**Replace** the broker IDs and proposed replica list with validated actual values. Do not run the example blindly. The topic's replica count must remain three.

```bash
kubectl -n kafka-lab cp reassignment-canary-ch13.json \
  kafka-cli:/tmp/reassignment-canary-ch13.json
```

Start a deliberately throttled canary (the value is illustrative and must be chosen based on measured spare bandwidth):

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --reassignment-json-file /tmp/reassignment-canary-ch13.json \
  --throttle 1048576 --execute
```

Verify until completion:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-reassign-partitions.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --reassignment-json-file /tmp/reassignment-canary-ch13.json \
  --verify | tee evidence-ch13/reassignment-verify.txt
```

**Important:** Kafka reassignment throttles may persist after completion depending on version and procedure. Confirm `--verify` output and the tool's cleanup behavior, and inspect any reassignment-related broker/topic throttled replica configuration. Remove only the throttle overrides introduced by this lab using version-supported commands; do not clear unrelated production throttles.

**Abort:** under-min-ISR, offline partition, sustained producer failures, unexpected disk saturation, or controller quorum instability. Stop further batches and use the documented Kafka cancellation/rollback workflow for your version; do not delete Pods or PVCs to cancel movement.

## 12. Lab G — Verify replica placement, leadership and data

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-reassign-ch13 \
  | tee evidence-ch13/topic-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-reassign-ch13 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true
```

Validate the canary partition has its intended target replicas, all partitions have three ISR members, and the original four event IDs remain readable. Capture before/after broker-to-node/zone mappings and leadership counts.

**Note:** moving a replica is not the same as electing a preferred leader. Treat leader balancing as a separate, approved operation.

## 13. Lab H — Safe broker scale-in decision (no deletion)

Before considering scale-in, check whether any replicas are still assigned to the fourth broker. In this chapter's canary exercise, at least one replica may have moved there, so **do not scale the pool back to three** until every replica on the target broker has been reassigned elsewhere and verified.

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-reassign-ch13

kubectl -n kafka-lab get kafkanodepool brokers -o yaml
```

**Decision:** if any topic (including internal topics) still has replicas on the candidate broker, scale-in is **Blocked**. Inventory **all** topics, not just the chapter topic, and follow Strimzi's supported broker removal procedure. Do not assume that a replica-free broker is automatically safe to remove without checking operator/KRaft metadata and storage requirements.

## 14. Read-only automated preflight

Save as `verify-ch13-preflight.sh`. It intentionally does not perform reassignment or scaling.

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
TOPIC=sre-reassign-ch13
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

kubectl -n "$NS" wait kafka/"$CLUSTER" --for=condition=Ready --timeout=120s
kubectl -n "$NS" get kafkanodepool brokers controllers
kubectl -n "$NS" get pvc

kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); r=split(b[1],rep,",")
    split($0,c,"Isr: "); split(c[2],d," "); i=split(d[1],members,",")
    seen++
    if(r!=3 || i!=3) bad++
  }
  END {
    if(seen!=6 || bad!=0){print "FAIL: partitions="seen" unhealthy="bad; exit 1}
    print "PASS: six partitions, RF=3, ISR=3"
  }'

echo 'PASS: metadata-only preflight; capacity, zone mapping and SLOs still require review'
```

```bash
chmod +x verify-ch13-preflight.sh
./verify-ch13-preflight.sh
```

**Automation limitations:** this checks one topic and a readiness condition. It does not prove that all cluster topics are healthy, that the target broker has spare capacity, that replica placement spans AZs, or that a proposed reassignment is safe. Those are mandatory manual/change-review gates.

## 15. Eight production incident simulations

### Incident 1 — New broker Pod Pending after scale-out

**Signals:** KafkaNodePool desired replicas=4, only three broker Pods Ready.

**Investigate:** `kubectl describe pod`, CPU/memory requests, affinity, taints, PVC and CSI events, worker quotas.

**Mitigate:** restore eligible node and volume capacity. Do not force a fourth broker onto an unsuitable node without topology review.

### Incident 2 — Reassignment saturates inter-broker network

**Signals:** producer p99 rises, replica fetch lag grows, network throughput hits limits.

**Investigate:** reassignment status, throttle, broker NIC, client error rate, affected partitions.

**Mitigate:** stop new batches, adjust supported reassignment throttle, preserve ISR and client SLOs.

### Incident 3 — Target broker disk fills mid-reassignment

**Signals:** disk utilization critical, broker log errors, ISR degrades.

**Investigate:** target PVC usage, retained bytes, duplicate copy headroom, segment sizes, storage IOPS.

**Mitigate:** pause further movement, restore supported capacity, evaluate safe cancellation; never delete log directories.

### Incident 4 — Reassignment stuck in progress

**Signals:** verify never completes, target replica remains behind.

**Investigate:** replica fetch lag, broker logs, network, storage latency, throttle configuration, ISR.

**Mitigate:** resolve bottleneck or use documented cancellation/rollback procedure for installed Kafka version.

### Incident 5 — Broker removed before replicas evacuated

**Signals:** offline partitions, under-replication, consumer/producer errors.

**Investigate:** removed broker ID, all topic assignments, PVC and operator events.

**Mitigate:** restore original broker/PVC if possible, recover ISR, then design safe evacuation. Never recreate with a different cluster ID.

### Incident 6 — Replica placement violates AZ policy

**Signals:** RF=3 but two or three replicas share a single failure domain.

**Investigate:** broker-to-node/zone mapping, `broker.rack`, reassignment target IDs, StorageClass topology.

**Mitigate:** plan controlled cross-zone replica placement and validate failover coverage.

### Incident 7 — Leader imbalance persists after data balancing

**Signals:** one broker receives most produce/fetch traffic despite even replica counts.

**Investigate:** per-broker leaders, partition throughput, client routing and hot keys.

**Mitigate:** perform separately approved leader balancing, monitor SLOs and avoid disruptive mass elections.

### Incident 8 — Reassignment throttle left configured

**Signals:** replica recovery remains unexpectedly slow after maintenance.

**Investigate:** Kafka broker/topic throttled replica settings and reassignment tool verify output.

**Mitigate:** remove only stale throttles introduced by the change, then verify normal replication and record audit evidence.

## 16. Troubleshooting matrix

| Symptom | Kubernetes evidence | Kafka evidence | Unsafe response |
|---|---|---|---|
| Broker not joining | Pod events, PVC, operator logs | Broker registration | Deleting PVC |
| Slow movement | Node/volume/network metrics | Replica lag, throttle | Removing all throttles blindly |
| ISR degraded | Broker Pod health | Partition describe | Lowering min ISR |
| Leader skew | Broker resource pressure | Leader distribution | Random restarts |
| Disk pressure | PVC usage, CSI capacity | Segment/reassignment growth | Deleting log segments |
| Scale-in blocked | KafkaNodePool desired state | All-topic replica assignments | Force scale-down |
| Zone imbalance | Pod/node/PV topology | Broker rack/replicas | Assuming RF means AZ spread |
| Controller issues | Controller Pod health | Metadata quorum | Arbitrary voter edits |

## 17. Production runbooks

### Runbook A — Broker scale-out

1. Confirm approved change, Kafka/Strimzi version and worker/PVC capacity.
2. Capture node pools, broker IDs, topics, ISR, quorum and SLO baseline.
3. Scale broker KafkaNodePool through operator-supported desired state.
4. Wait for Pod/PVC readiness and Kafka broker registration.
5. Verify the new broker's identity, node/zone and network reachability.
6. Plan separate canary reassignment and capture evidence.

### Runbook B — Partition reassignment

1. Export current partition assignments and validate healthy ISR.
2. Build target placement from actual broker IDs and zones.
3. Review RF preservation, disk/network headroom, hot partitions and business SLOs.
4. Generate proposal and select a small canary subset.
5. Apply a conservative throttle and execute the canary.
6. Verify completion, full ISR, event reconciliation and cleanup of lab-introduced throttles.
7. Expand only when gates pass; otherwise stop and follow rollback/cancel procedure.

### Runbook C — Stuck reassignment

1. Freeze new movement.
2. Capture Kafka reassignment status, target replica lag and broker errors.
3. Diagnose network, disk, throttling and source broker health.
4. Recover bottleneck; use version-specific cancel/revert only after review.
5. Confirm stable partition assignments and full ISR.
6. Reconcile business events and record RTO/RPO implications.

### Runbook D — Safe broker retirement

1. Inventory **all** topic replicas and leadership on candidate broker.
2. Check controller role and KRaft membership; do not retire controllers as brokers.
3. Move replicas and leadership through supported, approved procedures.
4. Verify no required replicas remain and cluster SLOs are healthy.
5. Use Strimzi-supported broker removal workflow and preserve PVCs until retention approval.
6. Verify topic availability, broker registration and residual capacity.
7. Document cleanup and rollback boundaries.

## 18. SLO, alerting and operational governance

Monitor under-replicated partitions, under-min-ISR partitions, offline partitions, replica fetch lag, reassignment progress, per-broker disk/network utilization, broker Pod scheduling, PVC pressure, controller quorum, produce/fetch error rates, p99 latency and consumer lag.

**Suggested acceptance gates:** zero offline partitions, no persistent under-min-ISR, full ISR before and after maintenance, no sustained application SLO regression, and no unauthorized KafkaNodePool changes. Numeric thresholds should be derived from workload baselines, not copied from a lab.

## 19. Final assessment — 100 points

| Domain | Points |
|---|---:|
| Explain broker scaling versus Kafka replica movement | 10 |
| Map broker IDs to Pods, PVCs and zones | 10 |
| Design capacity and transfer headroom | 10 |
| Create and validate RF=3 topic | 10 |
| Build a correct target replica placement plan | 10 |
| Scale broker KafkaNodePool safely in isolated lab | 10 |
| Generate and review a canary reassignment | 10 |
| Execute/verify a throttled canary and preserve data | 10 |
| Diagnose failure scenarios and recovery | 10 |
| Produce runbooks, evidence and rollback plan | 10 |

**Pass:** ≥85/100, all critical safety gates met, no unauthorized data deletion or unreviewed broker retirement. If no environment exists for the disruptive labs, mark them Pending rather than Passed.

## 20. Cleanup and handoff

```bash
kubectl -n kafka-lab delete kafkatopic sre-reassign-ch13 --ignore-not-found
```

**Do not blindly scale brokers from four to three.** First inventory all topics (including internal topics), verify the candidate broker has no required replicas, and follow the installed Strimzi release's safe scale-down process. Preserve PVCs and cluster evidence until approval.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/), [Kubernetes storage](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 014 — Kafka Replication Internals, ISR Management and Kubernetes Failure Recovery.

---

**Verification boundary:** Publication only. Live Kubernetes lab execution, version-specific CLI/CRD verification, security review and production acceptance are pending.
