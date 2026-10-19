# Chapter 018 — Kafka Consumer Groups, Rebalancing Protocols and Kubernetes Horizontal Scaling

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 04 — Producers, Consumers and Consumer Groups  
**Platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–017; [Kubernetes-first lab foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers and streaming application owners  
**Publication:** Complete · **Live execution:** Pending · **Independent security review:** Pending

> **Safety:** Consumer-group changes can interrupt processing, replay messages, or violate ordering. Use a disposable Kafka topic and isolated group IDs. Do not reset offsets, change partition counts, or scale production consumers without an approved rollout, business-event deduplication plan, and lag/error-budget checks. This chapter does not require broker disruption.

## 1. Learning objectives

1. Explain consumer group coordinators, membership, generations, assignment and committed offsets.
2. Distinguish classic and newer consumer group protocols and identify client-version compatibility constraints.
3. Compare eager versus cooperative rebalancing and supported static membership behavior.
4. Determine why consumer parallelism is bounded by partition count for a normal subscribed group.
5. Operate a Kubernetes Deployment with safe resource requests, termination grace, rolling-update controls and explicit group IDs.
6. Observe partition assignment as replicas scale from one to two and then four for a three-partition topic.
7. Diagnose rebalance storms, stuck group members, hot partitions, Pod churn and lag.
8. Design HPA/KEDA-style scaling from validated consumer lag and business processing SLOs.
9. Produce acceptance evidence, incident runbooks and a 100-point assessment.

## 2. Architecture and responsibility boundaries

```text
                      GitOps / change review
                               |
                       Kubernetes Deployment
                       replicas: 1 -> 2 -> 4
                          |     |      |
                    Consumer Pods in one group
                          |     |      |
                      Kafka coordinator
                               |
                    membership + assignments
                               |
                    topic: 3 partitions
                      P0      P1      P2
                               |
                   broker leaders / ISR
                               |
                     __consumer_offsets
                               |
              metrics: lag, event age, rebalances
                               |
                  HPA / external scaler
```

Kubernetes schedules and restarts Pods; Kafka coordinates consumer group membership and assigns topic partitions. Scaling the Deployment does **not** increase topic partitions or guarantee more throughput. For a three-partition topic, at most three ordinary group consumers can actively own partitions at once.

## 3. Consumer group lifecycle

A subscribed consumer joins a group, participates in assignment, fetches from assigned partitions, processes records and commits next offsets. The coordinator maintains membership and progress. Group membership changes can trigger reassignment, including during rolling updates, Pod OOM, scaling and poll-loop stalls.

### 3.1 Terms

| Term | Meaning | Operational impact |
|---|---|---|
| Group ID | Identity of cooperating consumers | Changing it can create a new replay position |
| Coordinator | Broker handling group coordination | Coordinator connectivity affects membership/commits |
| Generation / epoch | Group assignment version | Stale members may be fenced |
| Assignment | Partitions owned by members | Governs concurrency |
| Rebalance | Membership/assignment transition | Can pause or shift processing |
| Committed offset | Next record offset for group recovery | Incorrect commits can replay or skip events |
| Static membership | Stable member identity across restarts | Can reduce churn but needs unique identities |
| Cooperative assignment | Incremental partition revocation when supported | May reduce disruption versus eager assignment |

**Protocol compatibility:** Kafka has classic and newer consumer group protocols. Client-side assignment strategy and heartbeat/session settings differ by protocol and release. Verify the exact Kafka broker, client, and Strimzi versions. Do not mix incompatible settings or assume the console consumer supports a specific assignment algorithm.

## 4. Eager, cooperative and static membership

**Eager rebalance:** participating members revoke their assignments during a rebalance, then receive new assignments. This can cause wider pauses.

**Cooperative rebalance:** supported assignors may revoke only partitions that need to move, reducing disruption. It is not zero-downtime by itself; applications must correctly handle revoke/assign callbacks and in-flight processing.

**Static membership:** `group.instance.id` can preserve a logical member identity across restarts when used correctly. Every simultaneously active member must have a **unique** instance ID. A Deployment with randomly named replacement Pods may not provide stable identities; a StatefulSet can offer stable ordinal identity, but changes to controller type require application and storage design review. Do not hard-code one static member ID for multiple replicas.

**New consumer protocol:** coordinator-driven assignment and heartbeat controls differ from classic behavior. Select an approach compatible with the installed client; do not force classic-only `partition.assignment.strategy` settings on a newer-protocol consumer.

## 5. Kubernetes scaling design

| Workload concern | Recommended design | Failure to avoid |
|---|---|---|
| Stable group ID | Explicitly configured and environment-scoped | Accidentally sharing prod/staging group |
| Graceful termination | Stop intake, finish/abandon in-flight work, commit completed offsets, close | SIGKILL before commit |
| Rolling updates | Conservative surge/unavailable settings and readiness | All members restart simultaneously |
| Resource sizing | CPU/memory requests, limits from measured profile | CPU throttling causes missed polls |
| Autoscaling | Lag **and** event-age/SLO signals with stabilization | Scaling thrash and rebalance storms |
| Max replicas | Account for partition count and downstream capacity | Many idle Pods |
| Pod disruption | PDB with realistic minimum availability | Blocks node drain or allows excessive disruption |
| Security | TLS/SASL, Kafka ACLs, NetworkPolicies, scoped Secrets | Plaintext production listeners |

## 6. Lab prerequisites and safety gate

Use [Kubernetes-first lab foundation](../kubernetes/README.md) with `kafka-lab`, cluster `sre-kafka`, a version-matched `kafka-cli` Pod and internal lab bootstrap `sre-kafka-kafka-bootstrap:9092`. This plaintext listener is for a disposable lab only.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch18
```

Confirm the KafkaTopic CRD API version in the installed Strimzi release; replace `kafka.strimzi.io/v1` below if required. Stop if the Kafka cluster or controller quorum is unhealthy.

## 7. Lab A — Create a three-partition topic

Save `topic-ch18.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-group-ch18
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

```bash
kubectl apply --dry-run=server -f topic-ch18.yaml
kubectl apply -f topic-ch18.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-group-ch18 \
  | tee evidence-ch18/topic-before.txt
```

**Acceptance:** exactly three partitions, RF=3, ISR=3, valid leaders.

## 8. Lab B — Produce a deterministic baseline

```bash
printf '%s\n' \
  'acct-A:event-1801' 'acct-A:event-1802' \
  'acct-B:event-1803' 'acct-B:event-1804' \
  'acct-C:event-1805' 'acct-C:event-1806' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-group-ch18 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

**Acceptance:** six unique event IDs. Note that keys can hash to the same partition; three keys do not guarantee one key per partition.

## 9. Lab C — Inspect a single-member group

In terminal A, start a long-running consumer:

```bash
kubectl -n kafka-lab exec -it kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-group-ch18 \
  --group sre-group-ch18-demo \
  --consumer-property auto.offset.reset=earliest
```

In terminal B:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-group-ch18-demo --members --verbose \
  | tee evidence-ch18/group-one-member.txt
```

**Acceptance:** one member assigned all three partitions. If the group has not stabilized, wait and inspect again; do not infer assignments from an empty response.

## 10. Lab D — Two members and partition redistribution

Keep terminal A running. In terminal C start a second consumer using the **same** group ID:

```bash
kubectl -n kafka-lab exec -it kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-group-ch18 \
  --group sre-group-ch18-demo \
  --consumer-property auto.offset.reset=earliest
```

Then repeat the `--members --verbose` describe command.

**Acceptance:** two members and three partitions distributed between them. Record any observed rebalance interruption; do not claim zero downtime without timing evidence.

## 11. Lab E — Four members with only three partitions

Launch two more independent console-consumer sessions with `sre-group-ch18-demo`. Inspect membership and partition assignment:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-group-ch18-demo --members --verbose \
  | tee evidence-ch18/group-four-members.txt
```

**Acceptance:** four members but at least one member with zero partitions (assuming all four are joined and assignment is stable). Close the extra sessions after recording results.

## 12. Lab F — Kubernetes Deployment scaling

For an operator-managed lab, use a consumer container that supports a **long-running** process and graceful shutdown. The following is a *reference manifest*; replace `<VERIFIED_CONSUMER_IMAGE>` with a reviewed image and adapt the command to your actual application. A console consumer is useful for assignment observation but is not a production-ready application.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: consumer-ch18
  namespace: kafka-lab
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: consumer-ch18
  template:
    metadata:
      labels:
        app: consumer-ch18
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: consumer
          image: <VERIFIED_CONSUMER_IMAGE>
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: sre-kafka-kafka-bootstrap:9092
            - name: KAFKA_TOPIC
              value: sre-group-ch18
            - name: KAFKA_GROUP_ID
              value: sre-group-ch18-deploy
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: "1"
              memory: 512Mi
```

**Implementation gate:** this manifest assumes the image's entrypoint reads those environment variables. Validate the image contract and signal handling before applying. If no reviewed consumer image is available, keep this as a design exercise and use the live CLI consumer sessions from Labs C–E as the executable scaling demonstration.

After validation:

```bash
kubectl apply --dry-run=server -f consumer-deployment-ch18.yaml
kubectl apply -f consumer-deployment-ch18.yaml
kubectl -n kafka-lab rollout status deployment/consumer-ch18 --timeout=180s
kubectl -n kafka-lab scale deployment/consumer-ch18 --replicas=2
kubectl -n kafka-lab rollout status deployment/consumer-ch18 --timeout=180s
kubectl -n kafka-lab scale deployment/consumer-ch18 --replicas=4
kubectl -n kafka-lab rollout status deployment/consumer-ch18 --timeout=180s
```

**Acceptance:** Pod counts match desired replicas, **and** Kafka group membership/assignments reflect actual connected consumers. Pod count alone is not evidence of successful group participation.

## 13. Lab G — Graceful rolling-update design

Document a SIGTERM handler for your consumer application:

```text
SIGTERM received
  -> stop accepting new work
  -> stop fetching or pause assigned partitions
  -> finish bounded in-flight records
  -> commit next offsets only for completed records
  -> close consumer and release group membership
  -> exit before Kubernetes termination grace expires
```

**Nuance:** callback behavior depends on the client protocol and assignor. Commit on revoke only if the application has tracked completed offsets per partition. Avoid blocking shutdown indefinitely. Validate this with a reviewed application implementation, not merely a console consumer.

## 14. Lab H — Lag and scaling signal review

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-group-ch18-demo \
  | tee evidence-ch18/group-lag.txt
```

For each partition, capture current offset, log end offset, lag and member assignment. Define a scaling decision using:

- Committed-offset lag **and** event age.
- Processing time per record and records per second.
- Number of topic partitions and current active members.
- Downstream rate limits and consumer CPU/memory.
- Stabilization/cooldown to avoid HPA-induced rebalance loops.

**Do not** configure a live HPA against a nonexistent metric. KEDA Kafka scaler requires installation, authentication, and supported configuration; it is optional and must be verified against the deployed version.

## 15. Lab I — KEDA/HPA design worksheet

Use this decision table before enabling external scaling:

| Input | Example question | Required evidence |
|---|---|---|
| Lag metric | Is lag committed-offset based? | Metric source and query |
| Target lag | How many events per consumer are acceptable? | Throughput and SLO baseline |
| Max replicas | Are replicas capped by partition count? | Topic partition inventory |
| Min replicas | Will zero replicas create unacceptable cold-start delay? | Recovery-time objective |
| Cooldown | Will downscale trigger repeated rebalances? | Rebalance and rollout history |
| Authentication | Can scaler read group offsets securely? | TLS/SASL/ACL validation |
| Failure mode | What happens if metrics disappear? | Alert and fallback policy |

**Acceptance:** reviewed scaling policy, no live scaler assumed, and a documented alert for lag metric loss.

## 16. Lab J — Automated read-only acceptance

Save as `verify-ch18.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
TOPIC=sre-group-ch18
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka readiness'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/6] Kafka partition metadata'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

echo '[4/6] Require RF=3 and full ISR on three partitions'
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++
    if(rf!=3 || isr!=3) bad++
  }
  END {
    if(seen!=3 || bad) {print "FAIL: partitions="seen" degraded="bad; exit 1}
    print "PASS: three partitions, RF=3, ISR=3"
  }'

echo '[5/6] Kafka connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[6/6] Consumer group (informational; may be stopped)'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-consumer-groups.sh" \
  --bootstrap-server "$BS" --describe --group sre-group-ch18-demo || \
  echo 'PENDING: consumer group is absent or has no committed offsets'

echo 'PASS: Kafka topic metadata only; group scaling and processing require separate evidence'
```

```bash
chmod +x verify-ch18.sh
./verify-ch18.sh | tee evidence-ch18/acceptance.txt
```

**Coverage:** read-only topic health, connectivity and informational group describe. Does not prove rebalance efficiency, correct application shutdown, real HPA behavior, no duplicates, or business SLO compliance.

## 17. Eight production incident scenarios

### Incident 1 — Rebalance storm during Deployment rollout

**Signal:** frequent group state changes, throughput collapse, lag growth.

**Investigate:** rollout history, Pod termination, membership, poll interval and protocol compatibility.

**Mitigate:** halt rollout, stabilize replicas, fix graceful shutdown and supported assignment strategy.

### Incident 2 — HPA thrash causes recurring membership churn

**Signal:** repeated scale up/down, assignment changes and unstable event age.

**Investigate:** lag metric quality, cooldown, target, missing metrics, downstream rate limits.

**Mitigate:** add stabilization and partition-aware bounds; do not disable lag alerts.

### Incident 3 — Fourth consumer idle with three partitions

**Signal:** extra Pod healthy but no partitions assigned.

**Investigate:** topic partition count, group assignment, active member count.

**Mitigate:** rightsize replicas or redesign partition count via approved migration; do not blindly increase partitions on a business-critical keyed topic.

### Incident 4 — Static member identity collision

**Signal:** group fencing or repeated membership failures after scale-out.

**Investigate:** `group.instance.id` values, Pod identity and group protocol.

**Mitigate:** assign unique stable identities; never share one static ID across concurrent Pods.

### Incident 5 — Cooperative rebalance upgrade incompatibility

**Signal:** group fails to stabilize after client/assignor change.

**Investigate:** client versions, assignment strategy compatibility and staged migration plan.

**Mitigate:** roll back the incompatible client/assignor change with a reviewed deployment.

### Incident 6 — Hot partition dominates lag

**Signal:** one partition lag grows while others are near zero.

**Investigate:** key skew, processing latency, leader/broker health, consumer assignment.

**Mitigate:** optimize hot-key processing, redesign partitioning when necessary, and use business-key migration safeguards.

### Incident 7 — Pod SIGKILL during processing

**Signal:** duplicate business effects or uncommitted offsets after forced termination.

**Investigate:** grace period, processing time, signal handling, commit timing.

**Mitigate:** implement bounded drain and idempotent downstream processing; reconcile affected event IDs.

### Incident 8 — Group offsets unexpectedly reset

**Signal:** large replay or apparent missing history after a group ID change.

**Investigate:** Deployment env/config changes, committed offsets, `auto.offset.reset`, retention.

**Mitigate:** stop consumers, preserve evidence, restore intended group ID/offsets with application-owner approval.

## 18. Troubleshooting matrix

| Symptom | Kubernetes checks | Kafka checks | Unsafe shortcut |
|---|---|---|---|
| Pods Ready, no progress | Logs, app health, CPU | Assignments, lag, commits | Assume readiness equals processing |
| Lag rises on rollout | ReplicaSet history, termination | Rebalance frequency | Unlimited HPA replicas |
| Idle Pods | Replica count | Partition/member mapping | Blind partition expansion |
| Group unstable | Pod restarts, OOM | Group protocol/assignor | Force offset reset |
| Duplicate effects | Shutdown/restart timing | Commit position | Ignore business IDs |
| Join failure | TLS/Secrets/NetworkPolicy | Group ACL/coordinator | Disable authentication |
| Hot partition | Pod resource saturation | Per-partition lag | Scale past partitions |
| Scale-down outage | PDB, HPA history | Member assignment | Kill all Pods |

## 19. Production runbooks

### Runbook A — Consumer group rebalance incident

1. Capture group ID, protocol, members, assignments and coordinator.
2. Correlate rebalances with Kubernetes rollout, HPA and Pod restart history.
3. Inspect poll interval, processing time and shutdown behavior.
4. Stabilize group membership and roll back incompatible changes.
5. Verify partition ownership, lag recovery and business event age.
6. Record incident timeline and corrective action.

### Runbook B — Kubernetes consumer scale-out

1. Confirm topic partition count, lag/event-age baseline and downstream headroom.
2. Validate image, group ID, resources, TLS/ACLs and graceful shutdown.
3. Scale one increment at a time with reviewed Deployment settings.
4. Observe group membership and assignment convergence.
5. Verify processing throughput, duplicate event rate and lag.
6. Stop scaling once partitions or downstream capacity are saturated.

### Runbook C — Graceful rolling upgrade

1. Verify stable group and no outstanding offset-recovery work.
2. Confirm PodDisruptionBudget and termination grace are appropriate.
3. Upgrade with controlled surge/unavailability.
4. Drain in-flight records and commit only completed offsets.
5. Monitor group assignment, p99 processing time and lag.
6. Roll back on sustained SLO regression or commit errors.

### Runbook D — Autoscaler instability

1. Identify scaler version, metric source, targets and recent HPA events.
2. Verify lag metric semantics and freshness.
3. Cap replicas to useful partition/downstream capacity.
4. Apply cooldown/stabilization and test in staging.
5. Monitor rebalances, Pod churn and event-age SLO.
6. Record rollback and alerting strategy.

### Runbook E — Group offset integrity

1. Stop active members before any reset.
2. Snapshot committed offsets and log start/end positions.
3. Identify business event replay/skip scope and deduplication requirements.
4. Preview changes and obtain application-owner approval.
5. Execute only the approved change, then restart gradually.
6. Reconcile unique event IDs and document any retention gap.

## 20. SLOs and alert design

Measure committed lag per partition, maximum event age, processing latency, group rebalance rate/duration, group membership churn, failed commits, Pod restarts, OOM kills, CPU throttling and downstream errors.

**SLO design:** define the fraction of events processed within a business-defined time window and maximum tolerated recovery duration after one consumer Pod loss. Derive alert thresholds from actual workload measurements; no example number in this chapter is a production SLO.

## 21. Enterprise readiness checklist

- [ ] Group ID and environment isolation approved.
- [ ] Client/broker protocol compatibility documented.
- [ ] Eager/cooperative/static membership trade-offs reviewed.
- [ ] Partition count bounds useful group parallelism.
- [ ] Kubernetes Deployment image and entrypoint verified.
- [ ] Graceful termination and offset commit behavior tested.
- [ ] TLS/SASL, Kafka ACLs, Secrets and NetworkPolicies reviewed.
- [ ] Lag, event-age and rebalance monitoring configured.
- [ ] Autoscaling target, cooldown and max replicas approved.
- [ ] Business event deduplication and offset-recovery plan available.
- [ ] Live execution and independent security review recorded separately.

## 22. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain group coordinator and offset storage | 10 |
| Explain eager/cooperative and protocol compatibility | 10 |
| Describe static membership identity constraints | 10 |
| Create topic and produce baseline events | 10 |
| Inspect one-member and two-member assignments | 10 |
| Demonstrate four members on three partitions | 10 |
| Validate Kubernetes Deployment scaling design | 10 |
| Design graceful termination and safe commits | 10 |
| Execute read-only acceptance and explain coverage | 10 |
| Deliver SLOs, incidents and production runbooks | 10 |

**Pass:** ≥85/100 with no critical safety violations and independently captured evidence. An unexecuted Deployment or autoscaler design remains Pending.

## 23. Cleanup and next chapter

After evidence capture, stop CLI consumer sessions and confirm all resources are disposable:

```bash
kubectl -n kafka-lab delete deployment consumer-ch18 --ignore-not-found
kubectl -n kafka-lab delete kafkatopic sre-group-ch18 --ignore-not-found
```

Topic deletion permanently removes its records. Do not delete the Kafka cluster, PVCs or unrelated groups.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Kubernetes Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).

**Next:** Chapter 019 — Kafka Delivery Semantics, Transactions, Exactly-Once Processing and Kubernetes Recovery.

---

**Verification boundary:** GitHub publication is separate from live lab execution, client/protocol compatibility verification, independent security review and production approval.
