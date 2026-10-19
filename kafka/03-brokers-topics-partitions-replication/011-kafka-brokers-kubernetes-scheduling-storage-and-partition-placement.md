# Chapter 011 — Kafka Brokers, Kubernetes Scheduling, Storage and Partition Placement

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 03 — Brokers, Topics, Partitions and Replication  
**Platform:** Kubernetes, Strimzi Operator, Apache Kafka in KRaft mode  
**Prerequisites:** Chapters 001–010 and [Kubernetes Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka platform engineers, SREs, DBREs and Kubernetes administrators  
**Publication:** Complete | **Live lab execution:** Pending | **Security review:** Pending

> **Safety boundary:** All labs use an isolated Kubernetes cluster and test Kafka topics. Do not change production scheduling, storage, replication or Strimzi-managed StatefulSets without change approval. Deleting a PVC can permanently destroy a Kafka replica. Never use `kubectl drain`, node termination, or forced volume deletion as an unreviewed production experiment.

## 1. Objectives

By the end of this chapter, you should be able to:

1. Map Kafka brokers to Strimzi KafkaNodePool resources, Kubernetes Pods, persistent claims, nodes and availability zones.
2. Explain the difference between Kubernetes Pod placement, Kafka partition replica placement, and Kafka leadership.
3. Design scheduling policies for brokers and controllers with realistic failure-domain independence.
4. Explain local versus network-attached persistent storage and CSI volume topology.
5. Verify broker identity and persistent volume continuity across Pod recreation.
6. Measure partition distribution and detect broker/zone imbalance.
7. Safely reason about replica reassignment, scaling and storage growth.
8. Build automated readiness checks and production incident runbooks.

## 2. Enterprise architecture and failure domains

```text
                   Kubernetes control plane
                            |
                  Strimzi Cluster Operator
                     /               \
           KafkaNodePool           Kafka CR
          /          \
   controllers      brokers (3)
   3 voter Pods     broker Pods + persistent PVCs
                         |
                 Kafka partition replicas
                         |
          +--------------+--------------+
          |              |              |
        Zone A         Zone B         Zone C
       broker-0       broker-1       broker-2
        PVC-A          PVC-B          PVC-C
          |              |              |
       replicas        replicas       replicas
          +--------------+--------------+
                 internal bootstrap
                      Service
                         |
              producer / consumer Pods
```

Three different placement decisions matter:

- **Pod placement:** Kubernetes scheduler chooses a node subject to affinity, topology spread, resource requests, taints, tolerations and volume topology.
- **Replica placement:** Kafka assigns partition replicas to broker IDs. Kubernetes Pod separation does not automatically guarantee that every topic replica spans distinct zones.
- **Leader placement:** Kafka elects a leader among eligible replicas. Leadership can become uneven after failures or maintenance.

**SRE rule:** validate all three independently. A green Kubernetes Deployment/Pod view is not evidence of balanced Kafka partition replicas or leaders.

### 2.1 Failure-domain table

| Failure | Kubernetes impact | Kafka impact | Required mitigation |
|---|---|---|---|
| Broker container crash | One Pod restarts | ISR may shrink, leaders may move | Full ISR and client recovery |
| Worker node loss | Pod eviction/replacement; volume reattach | Broker unavailable during recovery | Multi-node scheduling, spare capacity |
| AZ outage | Nodes and zonal PVCs unavailable | Correlated replica loss | Replica placement across zones; tested recovery |
| CSI outage | New PVC provisioning or attach fails | Broker cannot rejoin | Storage monitoring and escalation |
| Controller voter loss | Controller Pod unavailable | Metadata quorum may degrade | Majority across independent domains |
| Disk exhaustion | Broker may fail writes/recovery | Under-replication and errors | Capacity alerts and planned expansion |

## 3. Strimzi KafkaNodePool and scheduling

Strimzi manages Kafka Pods and their storage using Kafka and KafkaNodePool custom resources. Do not patch generated StatefulSets or Pods as your durable configuration source. Use release-supported KafkaNodePool fields and reconcile through GitOps.

A **reference scheduling fragment** for the broker pool follows. It is not a full manifest. Verify its schema using the installed Strimzi CRD and operator version before applying.

```yaml
spec:
  replicas: 3
  roles:
    - broker
  template:
    pod:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    strimzi.io/cluster: sre-kafka
                topologyKey: kubernetes.io/hostname
  storage:
    type: persistent-claim
    size: 20Gi
    deleteClaim: false
```

This preference encourages separation but does **not** guarantee one broker per node or zone. The selector above may match controller Pods too; refine selectors using the actual operator-generated labels and verify node-pool behavior. If using hard anti-affinity, insufficient worker nodes can leave Pods Pending.

**Preferred enterprise approach:** choose a Strimzi release-supported placement policy that spreads brokers across hosts and zones, and separately spreads controllers. Validate the resulting Pod topology and Kafka replica assignments. Use supported `topologySpreadConstraints` when available in the installed CRD; do not assume every Strimzi version supports every Kubernetes Pod template field.

## 4. Storage architecture and operational trade-offs

### 4.1 Persistent volumes

Kafka's logs must survive Pod recreation. A Kubernetes PVC binds to a PV provisioned through a StorageClass. In cloud environments, many block volumes are zonal and may only attach to nodes in the same availability zone.

Inspect:

```bash
kubectl get storageclass
kubectl -n kafka-lab get pvc -o wide
kubectl -n kafka-lab describe pvc <EXACT_BROKER_PVC>
kubectl get pv
```

**Key storage considerations:**

- `WaitForFirstConsumer` StorageClass binding can help coordinate volume provisioning with Pod scheduling.
- Zonal PV topology can constrain where a broker Pod can restart.
- Kafka durability depends on replication and acknowledgments, not PVCs alone.
- Network storage latency and throughput affect replica catch-up and produce/fetch tail latency.
- Strimzi-supported storage expansion depends on StorageClass expansion support and the installed operator version.
- `deleteClaim: false` helps preserve PVCs when related resources are removed, but it is **not** a backup policy.
- Avoid manual edits to `meta.properties`, `node.id` or KRaft metadata directories.

### 4.2 Capacity design

Estimate disk consumption using ingress rate, retention, replication and headroom:

```text
logical retained bytes ≈ ingress bytes/second × retention seconds
cluster replica bytes ≈ logical retained bytes × replication factor
per-broker average ≈ cluster replica bytes / broker count
```

These are planning approximations; add segment/index overhead, compaction effects, uneven partition distribution, reassignment duplication, peak load and operational headroom.

**Worked example:** 10 MiB/s of logical ingress retained for 24 hours is about 844 GiB of logical data. With RF=3, the cluster stores roughly 2.47 TiB of replicas before overhead; across three brokers that averages about 844 GiB per broker. A 20Gi lab PVC is therefore strictly for tiny test workloads, not this example's capacity.

## 5. Lab environment

Use the shared [Kubernetes Lab Foundation](../kubernetes/README.md). The target is a **disposable three-controller, three-broker Strimzi KRaft cluster** with a supported Kafka/Strimzi version combination and PVC-backed storage.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
```

**Stop** if the cluster is not Ready, PVCs are unbound, or there are insufficient worker nodes. Do not proceed with placement or failure exercises on a shared production cluster.

## 6. Lab A — Inventory broker Pods, nodes, zones and volumes

```bash
mkdir -p evidence-ch11

kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch11/pods-before.txt

kubectl -n kafka-lab get kafkanodepool brokers controllers -o yaml \
  > evidence-ch11/nodepools-before.yaml

kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch11/pvc-before.txt

kubectl get nodes -L topology.kubernetes.io/zone \
  | tee evidence-ch11/nodes-zones.txt
```

For each broker-role Pod, record its exact Pod name, broker ID, worker node, zone and PVC name. Use `kubectl describe pod` to inspect volume mounts and scheduling events.

**Acceptance:** three distinct broker identities; all broker PVCs Bound; each broker Pod Ready; intended node/zone separation documented. If your local cluster lacks zones, mark zone distribution **Not Applicable**, not Passed.

## 7. Lab B — Create a replicated topic and inspect assignments

Use the CLI Pod described in the shared lab guide.

```bash
cat > kafka-topic-ch11.yaml <<'YAML'
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-placement-ch11
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
YAML

kubectl apply --dry-run=server -f kafka-topic-ch11.yaml
kubectl apply -f kafka-topic-ch11.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-placement-ch11 \
  | tee evidence-ch11/partitions-before.txt
```

For each partition, inspect `Leader`, `Replicas` and `Isr`. With three brokers and RF=3, every partition should have all three broker IDs as replicas, but leaders may not be perfectly balanced.

**Acceptance:** six partitions, three assigned replicas each, three ISR members each. Do not claim cross-zone placement until you have mapped replica broker IDs to Kubernetes node zones.

## 8. Lab C — Verify key routing and per-partition ordering

```bash
printf '%s\n' \
  'acct-100:opened' \
  'acct-100:credited' \
  'acct-200:opened' \
  'acct-200:debited' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-placement-ch11 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-placement-ch11 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true
```

Verify the two events for each account retain their intended order within their assigned partition. Kafka does not provide a single global order across six partitions.

## 9. Lab D — Scheduling diagnostics without destructive node operations

Inspect the actual placement and relevant scheduling rules:

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab describe kafkanodepool brokers
kubectl -n kafka-lab get events --sort-by=.lastTimestamp | tail -40
kubectl describe nodes | grep -E 'Name:|Taints:|Allocatable:|topology.kubernetes.io/zone'
```

**Simulation by analysis (no mutation):** Suppose all broker Pods share one worker node. Determine which anti-affinity/topology spread rules, node capacity and PV constraints must change to meet the availability requirement. Create a proposed KafkaNodePool patch in Git and run schema validation in staging. Do **not** patch the live lab unless the change is approved and you have a recovery plan.

### Scheduling failure investigation

If a broker Pod is Pending, inspect:

```bash
kubectl -n kafka-lab describe pod <EXACT_PENDING_BROKER_POD>
kubectl -n kafka-lab get pvc
kubectl get nodes -o wide
```

Common causes: insufficient CPU/memory, node selectors with no matching nodes, taints without tolerations, impossible anti-affinity, PV zone conflicts or CSI provisioning failure.

## 10. Lab E — Persistence across a single broker-Pod recreation

**Safety preflight:** confirm three brokers healthy, six partitions with ISR=3, controller quorum healthy and no competing maintenance. Identify a **broker-only** Pod from the brokers node pool; do not delete a controller or PVC.

```bash
BROKER_POD=<EXACT_BROKER_ONLY_POD_NAME>
kubectl -n kafka-lab get pod "$BROKER_POD" -o yaml \
  > evidence-ch11/selected-broker-before.yaml
kubectl -n kafka-lab get pvc -o wide \
  > evidence-ch11/pvc-pre-fault.txt
```

In the isolated lab only:

```bash
kubectl -n kafka-lab delete pod "$BROKER_POD" --wait=false
kubectl -n kafka-lab get pods -w
```

**This is an abrupt fault simulation**, not an approved graceful maintenance method. Let Strimzi reconcile. Then:

```bash
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch11/pvc-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-placement-ch11 \
  | tee evidence-ch11/partitions-after.txt
```

**Acceptance:** original broker identity and PVC mapping preserved, all six partitions return to ISR=3, no sustained offline partitions, and the original four events are still readable. If any ISR member fails to recover, stop testing and escalate; do not delete the PVC to “fix” it.

## 11. Lab F — Replica placement and reassignment planning

Scaling brokers or changing Pod scheduling **does not necessarily rebalance existing Kafka partitions**. Reassignment is a separate Kafka operation, with bandwidth, disk, ISR and rollback consequences.

Read-only inventory:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-placement-ch11
```

Design a proposed replica distribution that keeps RF=3, spreads replicas across actual failure domains and avoids overloading a broker. Do not execute reassignment in this chapter; a later chapter covers Kafka reassignment planning, throttling and verification in depth.

### 11.1 Placement policy

- Separate broker Pods across nodes and zones when infrastructure permits.
- Separate controller Pods across independent nodes/zones.
- Ensure every critical topic's replica set spans failure domains.
- Verify leadership balance after maintenance or broker scaling.
- Avoid storing all replicas on one underlying storage fault domain.
- Account for PV topology during rescheduling and node replacement.
- Track partition count, replica count and disk utilization per broker.

## 12. Automated acceptance checks

Save as `verify-ch11.sh`. This script is read-only and assumes the dedicated lab's three-broker RF=3 topic.

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
TOPIC=sre-placement-ch11
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092

echo '[1/6] Kafka custom resource Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[2/6] KafkaNodePool inventory'
kubectl -n "$NS" get kafkanodepool brokers controllers

echo '[3/6] All Kafka namespace PVCs Bound'
pvc="$(kubectl -n "$NS" get pvc --no-headers)"
test -n "$pvc" || { echo 'FAIL: no PVCs'; exit 1; }
if printf '%s\n' "$pvc" | awk '$2!="Bound"{bad=1} END{exit !bad}'; then
  echo 'FAIL: one or more PVCs not Bound'
  exit 1
fi

echo '[4/6] Broker API connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[5/6] Metadata quorum read'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status >/dev/null

echo '[6/6] Six partitions with RF=3 and ISR=3'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    n=split($0,a,"Replicas: "); if(n<2) next
    split(a[2],b," "); r=split(b[1],rep,",")
    n=split($0,c,"Isr: "); if(n<2) next
    split(c[2],d," "); isr=split(d[1],members,",")
    seen++
    if(r!=3 || isr!=3) bad++
  }
  END {
    if(seen!=6 || bad!=0){print "FAIL: seen="seen" degraded="bad; exit 1}
    print "PASS: six partitions with RF=3 and ISR=3"
  }'

echo 'PASS: core placement and storage checks'
```

```bash
chmod +x verify-ch11.sh
./verify-ch11.sh
```

**Coverage limits:** this does not prove Pod spread, zone resilience, broker ID continuity, end-to-end correctness or production storage performance. Those require captured mapping evidence and separate chaos/recovery tests.

## 13. Eight SRE/DBRE incident scenarios

### 13.1 All broker Pods scheduled on one node

**Signal:** healthy Kafka API but single-node correlated failure risk.

**Root causes:** soft anti-affinity only, insufficient nodes, scheduling constraints, no topology policy.

**Response:** document actual placement, increase worker capacity, update supported KafkaNodePool scheduling rules, and validate replicas across failure domains.

### 13.2 Broker Pending due to zonal PVC

**Signal:** Pod cannot schedule after node/AZ change.

**Root causes:** PV node affinity, missing worker capacity in the PV zone, CSI attach failure.

**Response:** inspect Pod scheduling events and PV topology; restore eligible nodes or use supported recovery. Never forcibly attach a zonal volume across incompatible zones.

### 13.3 Disk exhaustion and replica fetch failures

**Signal:** log directory errors, ISR shrinks, produce latency rises.

**Root causes:** underestimated retention, skewed partition placement, compaction backlog, reassignment duplication.

**Response:** stop risky changes, restore safe capacity, review supported volume expansion, protect retention/durability policy.

### 13.4 ISR healthy but leaders concentrated

**Signal:** one broker has disproportionate request load.

**Root causes:** leader distribution imbalance, recent failure or recovery.

**Response:** inspect per-broker leader counts and CPU/network, use supported Kafka leader-balancing mechanisms after risk review; do not blindly restart brokers.

### 13.5 Pod OOMKilled repeatedly

**Signal:** broker restarts, GC/heap pressure, ISR churn.

**Root causes:** incorrect JVM heap-to-container limit ratio, insufficient memory headroom, workload spikes.

**Response:** inspect termination reason and metrics; adjust Strimzi-managed resources after staging tests; avoid changing generated Pods directly.

### 13.6 Replica reassignment overwhelms storage/network

**Signal:** catch-up lag, latency spikes, elevated disk/network usage.

**Root causes:** excessive concurrent movements, no throttle, insufficient headroom.

**Response:** pause or throttle using supported Kafka tooling, preserve ISR and prioritize critical traffic.

### 13.7 Node loss plus insufficient spare capacity

**Signal:** replacement Pod Pending; degraded ISR persists.

**Root causes:** cluster autoscaler limits, affinity constraints, insufficient instance types, quota.

**Response:** restore capacity in eligible failure domains and verify PVC attachment, then await ISR convergence.

### 13.8 Controller quorum and broker placement share a correlated fault

**Signal:** one infrastructure event impacts brokers and majority of controllers.

**Root causes:** controller/broker Pod co-location, common worker pool, common AZ.

**Response:** restore quorum safely, redesign failure-domain placement and document recovery limits.

## 14. Troubleshooting matrix

| Symptom | Kubernetes checks | Kafka checks | Avoid |
|---|---|---|---|
| Pod Pending | Events, affinity, taints, CPU/memory | Broker missing | Blind node deletion |
| PVC Pending | CSI logs, StorageClass, quota | Replica not starting | Deleting claims |
| CrashLoopBackOff | Previous logs, OOM, mounts | Registration/ISR | Reformatting storage |
| Under-replicated partitions | Pod/network/storage | Replica lag, ISR | Lowering min ISR |
| Leader imbalance | Broker Pod placement/resources | Partition leader counts | Random restarts |
| Slow replica recovery | Volume IOPS, network, throttling | Fetch lag | Increasing concurrency blindly |
| AZ failure | Node/PV topology | Replica distribution | Assuming RF=3 means multi-AZ |
| Operator drift | CR desired state, operator logs | Effective broker configs | Editing generated StatefulSets |

## 15. Production runbooks

### Runbook A — Broker scheduling incident

1. Confirm impacted cluster, KafkaNodePool and broker identity.
2. Capture Pod status, node/zone, PVC, events and operator logs.
3. Check partition ISR, controller quorum and client errors.
4. Diagnose resource, affinity, taint or PV topology constraints.
5. Restore capacity or correct approved KafkaNodePool desired state.
6. Validate broker registration, full ISR and application SLO recovery.
7. Preserve evidence and update scheduling policy.

### Runbook B — Broker storage incident

1. Check PVC Bound status, PV topology, filesystem errors and capacity.
2. Identify affected broker IDs and critical partitions.
3. Stop concurrent reassignments and disruptive maintenance.
4. Restore supported storage capacity without deleting log directories.
5. Verify replica catch-up, topic retention and event correctness.
6. Escalate suspected corruption or data loss for documented recovery.

### Runbook C — Placement change and rollback

1. Capture current KafkaNodePool YAML, node labels, Pod placement and PV mapping.
2. Review compatibility and proposed scheduling constraints.
3. Dry-run CR changes and validate enough eligible nodes exist.
4. Apply only through operator-supported desired state.
5. Monitor scheduling, Kafka Ready, ISR and SLOs.
6. Revert the reviewed manifest if health gates fail; recognize PV zone affinity may constrain rollback.
7. Document final broker/zone/replica mapping.

### Runbook D — Replica placement reliability review

1. Export topic partitions, replica sets, leaders and ISR.
2. Map broker IDs to Pod nodes, zones and storage fault domains.
3. Calculate replica, leader and disk skew.
4. Identify single-failure-domain exposure.
5. Prepare an approved, throttled reassignment plan if required.
6. Validate steady-state replication and SLOs after execution in a later exercise.

## 16. SLOs and alerting

Monitor:

- Broker Pod readiness and restarts, unschedulable Pods and PVC Pending.
- Storage utilization, disk IOPS/latency, CSI attach errors and node pressure.
- Under-replicated partitions, under-min-ISR partitions and offline partitions.
- Replica fetch lag, leader distribution and network saturation.
- Controller quorum leader stability and voter lag.
- Produce/fetch p95/p99 latency, error rate and consumer processing age.

**Example policy:** no sustained offline partitions; no prolonged under-min-ISR on critical topics; enough disk headroom to absorb broker recovery and peak ingress. Derive numerical alert thresholds from measured workload and approved SLOs.

## 17. Enterprise readiness checklist

- [ ] Operator/Kafka versions pinned and CRD schema validated.
- [ ] Dedicated controller and broker node pools defined.
- [ ] Worker and zone topology matches failure-domain objectives.
- [ ] Broker IDs, Pods, PVCs and zones inventoried.
- [ ] StorageClass supports required volume topology and expansion.
- [ ] Topic replicas span actual failure domains.
- [ ] Partition and leader skew reviewed.
- [ ] Capacity includes peak retention and recovery headroom.
- [ ] Full ISR verified before maintenance.
- [ ] Kafka CR and client SLIs observed together.
- [ ] Recovery, backup and reassignment procedures reviewed.
- [ ] Kubernetes RBAC, TLS, NetworkPolicies and audit controls approved.

## 18. Assessment — 100 points

| Requirement | Points |
|---|---:|
| Explain Pod placement versus Kafka replica/leader placement | 10 |
| Map KafkaNodePools to Pods, broker IDs, nodes and PVCs | 10 |
| Explain Kubernetes scheduling constraints and trade-offs | 10 |
| Validate persistent storage and zone topology | 10 |
| Create RF=3/minISR=2 topic and inspect replicas | 10 |
| Demonstrate keyed ordering and bounded consumer validation | 10 |
| Safely simulate one broker-Pod failure | 10 |
| Prove ISR and PVC recovery | 10 |
| Run automated acceptance and identify coverage gaps | 10 |
| Write incident report and production placement runbook | 10 |

**Pass:** at least 85/100, zero destructive safety violations, and independently captured lab evidence. Publication is not an execution result.

## 19. Cleanup and next chapter

```bash
kubectl -n kafka-lab delete kafkatopic sre-placement-ch11 --ignore-not-found
```

Preserve the Kafka cluster for Chapter 012. Delete the CLI Pod only if it is no longer needed. Never delete broker PVCs as part of routine chapter cleanup.

**References:** [Strimzi documentation](https://strimzi.io/documentation/), [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Kubernetes scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/), [Kubernetes persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 012 — Kafka Topic Administration, Partition Design and Kubernetes Operator Management.

---

**Verification:** Published content only; live Kubernetes execution, operator-version schema verification and independent security review remain pending.
