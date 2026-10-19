# Chapter 010 — Enterprise Kafka on Kubernetes: KRaft Cluster Administration and Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 02 — Installation, KRaft and Cluster Administration (final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft  
**Audience:** Kafka platform engineers, SREs, DBREs, cluster administrators  
**Prerequisites:** Chapters 001–009 and [Kubernetes Lab Foundation](../kubernetes/README.md)  
**Publication:** Complete | **Live lab execution:** Pending | **Security review:** Pending

> **Production safety:** This is a disposable-cluster acceptance exercise. Do not perform failure injection, delete Pods or PVCs, alter KRaft voter membership, or apply sample plaintext listeners to production. Verify the Strimzi CRD API version and Kafka compatibility against your installed operator before applying manifests. No actual execution or independent security review is claimed.

## 1. Mission and learning outcomes

Build a Kubernetes-native Kafka KRaft platform, validate controller and broker readiness, prove a three-replica durability policy under a **single broker-Pod failure**, observe Strimzi reconciliation, demonstrate persistent storage and Kafka administration, and produce an auditable SRE acceptance report.

The candidate must demonstrate:

1. Kubernetes namespace, context and cluster isolation.
2. Version-pinned Strimzi Operator and Kafka compatibility.
3. Three dedicated controller-role Pods and three broker-role Pods.
4. Persistent volumes and stable node identity.
5. KafkaTopic RF=3, min ISR=2, partitions and keyed ordering.
6. Producer acknowledgment, consumer replay and end-to-end record accounting.
7. Metadata quorum inspection and healthy controller majority.
8. One broker-Pod failure and automated recovery without reducing durability.
9. Safe configuration reconciliation and maintenance gates.
10. Evidence-backed incident response, cleanup and assessment.

## 2. Reference enterprise architecture

```text
                        Git / GitOps / Terraform
                                 |
                          Kubernetes API
                                 |
                        Strimzi Cluster Operator
                         /                \
                 KafkaNodePool          Kafka CR
                  /        \                |
             Controllers   Brokers        Services
               3 Pods      3 Pods           |
                |           |          Kafka clients
          metadata PVCs   data PVCs         |
                |           |        KafkaTopic / KafkaUser
                +------ KRaft quorum -------+
                            |
                  Prometheus / Grafana
                            |
                  SRE alerts / runbooks
```

Strimzi reconciles desired cluster state through Kubernetes custom resources. Controller quorum health, Kafka partition replication, Kubernetes scheduling and PVC availability are distinct reliability domains. A `Kafka` custom resource reporting Ready is necessary but insufficient evidence for application-level reliability.

### 2.1 Failure-domain design

| Layer | Design intent | Validation |
|---|---|---|
| Controllers | Three KRaft voters across failure domains | Quorum status and controller Pod placement |
| Brokers | Three broker nodes across failure domains | Topic replica placement and broker readiness |
| Storage | Persistent claims with supported storage class | PVC Bound, restart persistence |
| Networking | Internal bootstrap Service, resolvable Pod DNS | CLI from same namespace |
| Security | TLS, authentication, Kafka ACLs and Kubernetes RBAC for production | Explicit security review |
| Observability | Operator events, Pod logs, broker and controller metrics | Before/during/after evidence |
| Delivery | Version-pinned manifests with reviewed changes | Git diff and rollback plan |

**Capacity gate:** a real HA lab needs enough independent worker nodes, CPU, memory, disk and StorageClass capacity to schedule all six Kafka Pods. A one-worker kind cluster is useful for learning CRDs but **cannot** demonstrate independent failure-domain resilience.

## 3. Compatibility and prerequisites

Use a dedicated cluster or namespace with no production workloads. The shared [Kubernetes Lab Foundation](../kubernetes/README.md) contains a Strimzi Kafka/KafkaNodePool manifest template, topic resource and CLI Pod instructions.

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get storageclass
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io
kubectl -n kafka-lab get deployments,pods
```

**Version checkpoint:** Strimzi API groups and CRD schema depend on the installed release. Confirm whether `strimzi.io/v1` and the selected Kafka version are supported; otherwise use the documented API version and release-specific examples. Do not guess the schema or install an arbitrary Kafka version.

Before applying the shared manifest:

```bash
kubectl -n kafka-lab get kafka sre-kafka --ignore-not-found
kubectl apply --dry-run=server -f kafka-lab.yaml
kubectl apply -f kafka-lab.yaml
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s
```

**Stop condition:** any admission/schema failure, unbound PVC, unschedulable controller, or operator error. Do not continue with fault injection.

## 4. Lab A — Kubernetes infrastructure acceptance

```bash
mkdir -p evidence-ch10
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch10/platform-before.txt

kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch10/kafka-cr-before.yaml

kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch10/events-before.txt
```

Check node pools:

```bash
kubectl -n kafka-lab get kafkanodepool controllers brokers -o yaml
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get pvc
```

**Acceptance:** three controller Pods and three broker Pods are scheduled and healthy; PVCs are Bound; Kafka reports Ready. Record the actual Pod names, labels, node assignments, images, and PVC mappings. Do not assume Strimzi-generated Pod names follow a fixed numbering scheme.

## 5. Lab B — Controller metadata quorum

Start the version-matched Kafka CLI Pod as described in the shared lab foundation, then:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status | tee evidence-ch10/quorum-before.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --replication | tee evidence-ch10/quorum-replication-before.txt
```

Inspect leader ID, leader epoch, high watermark and current voters. A three-voter quorum needs two healthy voting controllers. Do not mistake topic ISR for controller voting membership.

**Acceptance:** stable metadata leader, expected voter set, no sustained follower lag, and ability to read topic metadata. Record exact output rather than assuming a particular controller ID.

## 6. Lab C — Replicated KafkaTopic and record semantics

Create a dedicated capstone topic:

```bash
cat > kafka-topic-ch10.yaml <<'YAML'
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-capstone-ch10
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
YAML
kubectl apply --dry-run=server -f kafka-topic-ch10.yaml
kubectl apply -f kafka-topic-ch10.yaml
kubectl -n kafka-lab get kafkatopic sre-capstone-ch10 -o yaml \
  > evidence-ch10/topic-cr-before.yaml
```

If the installed Strimzi version uses a different supported API version, update this manifest accordingly before server-side validation.

Inspect Kafka partition placement:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-capstone-ch10 \
  | tee evidence-ch10/topic-before.txt
```

Require each partition to have three replicas in ISR before continuing.

Produce four keyed events:

```bash
printf '%s\n' \
  'customer-101:created' \
  'customer-101:validated' \
  'customer-202:created' \
  'customer-202:validated' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-ch10 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Consume:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-ch10 --from-beginning --max-messages 4 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true
```

**Interpretation:** ordering is guaranteed per partition, not across the topic. Keys map consistently to partitions only while partition count and partitioner behavior remain stable. Exactly-once end-to-end delivery requires more than enabling producer idempotence.

## 7. Lab D — Consumer replay and audit evidence

Use an isolated consumer group:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-ch10 \
  --group sre-capstone-group-ch10 \
  --from-beginning --max-messages 4
```

Inspect committed group offsets:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-capstone-group-ch10 \
  | tee evidence-ch10/group-offsets.txt
```

For a replay demonstration, use a **new** group name rather than resetting offsets of a shared consumer group. Reconcile the four expected event IDs and their payloads; do not infer business processing completion solely from Kafka offset commits.

## 8. Lab E — Single broker-Pod fault injection

**Preflight:** verify three healthy broker Pods, three controller Pods, topic ISR=3 for all partitions, Kafka Ready=True, and no active incident. Confirm the selected Pod is **broker-only** and belongs to the disposable capstone cluster.

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get kafkanodepool brokers -o yaml
kubectl -n kafka-lab get kafka sre-kafka -o yaml
```

Select the broker Pod manually from actual operator-generated labels and pool membership:

```bash
BROKER_POD=<EXACT_BROKER_ONLY_POD_NAME>
kubectl -n kafka-lab get pod "$BROKER_POD" -o yaml \
  > evidence-ch10/selected-broker-before.yaml
```

Only after reviewing that the Pod is in the **brokers** node pool:

```bash
kubectl -n kafka-lab delete pod "$BROKER_POD" --wait=false
kubectl -n kafka-lab get pods -o wide
```

This simulates an **abrupt Pod failure**, not a graceful operator-managed rolling restart. Strimzi should reconcile the desired broker count. Do not delete PVCs, KafkaNodePool resources, or another Pod.

Observe partition leaders/ISR and metadata quorum:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-capstone-ch10 \
  | tee evidence-ch10/topic-during-failure.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status | tee evidence-ch10/quorum-during-failure.txt
```

Attempt a bounded write while one broker is unavailable:

```bash
printf 'customer-303:created-during-fault\n' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-ch10 \
  --producer-property acks=all \
  --producer-property delivery.timeout.ms=15000 \
  --property parse.key=true --property key.separator=:
```

**Expected if healthy:** two ISR replicas remain and `acks=all` writes can succeed with min ISR=2. A failure is a stop-and-investigate signal; never lower min ISR to force success.

## 9. Lab F — Recovery and persistence acceptance

Wait for Strimzi reconciliation:

```bash
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s

kubectl -n kafka-lab get pods,pvc -o wide \
  | tee evidence-ch10/platform-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-capstone-ch10 \
  | tee evidence-ch10/topic-after.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  describe --status | tee evidence-ch10/quorum-after.txt
```

**Acceptance:** broker Pod replacement completed, PVCs retained, all topic replicas returned to ISR, metadata quorum healthy, and original records plus the fault-window event remain readable.

**Important:** a Ready condition does not prove full ISR restoration; inspect Kafka topic metadata separately. Likewise, four or five consumed records are a bounded test, not a complete data-loss guarantee for production workloads.

## 10. Lab G — Kubernetes configuration and GitOps drift

Read operator-managed desired configuration:

```bash
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch10/kafka-desired.yaml

kubectl -n kafka-lab get kafkatopic sre-capstone-ch10 -o yaml \
  > evidence-ch10/topic-desired.yaml
```

For a safe configuration exercise, edit **only the disposable KafkaTopic** in a reviewed manifest. Example: set `retention.ms: 86400000` for the capstone topic, run `kubectl apply --dry-run=server`, apply, observe reconciliation, then restore the prior manifest. This demonstrates declarative reconciliation without editing controller quorum settings or restarting production brokers.

**Drift rule:** direct Kafka Admin API changes may conflict with Strimzi-managed resources. Define ownership and reconcile desired versus effective configuration rather than issuing ad hoc overrides.

## 11. Automated acceptance test

Save as `verify-ch10.sh`. The script is read-only apart from temporary local evidence files; it does not inject failures.

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
CLUSTER=sre-kafka
TOPIC=sre-capstone-ch10
BOOTSTRAP=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
mkdir -p evidence-ch10

echo '[1/7] Kubernetes and Strimzi API'
kubectl get crd kafkas.kafka.strimzi.io kafkanodepools.kafka.strimzi.io >/dev/null

echo '[2/7] Kafka Ready condition'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[3/7] Node pools and persistent volumes'
kubectl -n "$NS" get kafkanodepool controllers brokers
kubectl -n "$NS" get pvc

echo '[4/7] CLI Pod connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BOOTSTRAP" >/dev/null

echo '[5/7] Metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BOOTSTRAP" describe --status \
  | tee evidence-ch10/automated-quorum.txt

echo '[6/7] Topic metadata'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BOOTSTRAP" --describe --topic "$TOPIC" \
  | tee evidence-ch10/automated-topic.txt

echo '[7/7] Check all three partitions have three ISR members'
awk '
  /Partition:/ && /Isr:/ {
    n=split($0,a,"Isr: ")
    if (n < 2) next
    split(a[2],b," ")
    members=split(b[1],ids,",")
    checked++
    if (members != 3) bad++
  }
  END {
    if (checked != 3 || bad != 0) {
      print "FAIL: partitions=" checked " degraded=" bad
      exit 1
    }
    print "PASS: three partitions each with ISR=3"
  }
' evidence-ch10/automated-topic.txt

echo 'PASS: Kubernetes Kafka metadata and topic readiness'
```

```bash
chmod +x verify-ch10.sh
./verify-ch10.sh
```

**Test limitations:** it assumes three partitions and three ISR members, and relies on Kafka CLI topic description formatting. It does not check Pod role counts, storage topology, producer/consumer data correctness, TLS, security policies, or controller fault tolerance. Those require the manual evidence gates and additional automation before production approval.

## 12. Production incident simulations and response

### Incident A — Broker Pod CrashLoopBackOff

**Signals:** Pod repeatedly restarts, broker registration absent, ISR degraded.

**Investigate:** `kubectl describe pod`, previous container logs, Strimzi operator logs, volume mounts, `node.id`, memory limits, disk pressure.

**Mitigate:** correct resource/config/storage root cause; let Strimzi reconcile. Do not delete PVCs or change cluster ID.

### Incident B — PVC Pending

**Signals:** Kafka node pool cannot schedule; PVCs unbound.

**Investigate:** StorageClass, CSI controller, topology constraints, quotas, available capacity, access modes.

**Mitigate:** restore provisioner/capacity or fix compatible storage configuration. Avoid unsafe PV reassignment.

### Incident C — Controller quorum majority lost

**Signals:** metadata operations stall, elections fail, leader unavailable.

**Investigate:** controller-role Pods, network partition, metadata storage, voter list, KRaft replication output.

**Mitigate:** restore original majority using release-supported procedures. Do not format metadata volumes or force arbitrary membership edits.

### Incident D — Kafka Ready but topic ISR degraded

**Signals:** Kafka CR reports Ready, yet topic describe shows missing ISR members.

**Investigate:** broker Pod health, replica fetch lag, disk latency, leader placement, network.

**Mitigate:** restore replicas and validate topic-level durability. Do not accept Ready condition alone.

### Incident E — Strimzi reconciliation conflict

**Signals:** operator repeatedly changes resources; direct edits are reverted.

**Investigate:** Kafka/KafkaNodePool/KafkaTopic desired state, operator logs, GitOps controllers, ownership.

**Mitigate:** fix the source-of-truth manifest and coordinate changes; avoid modifying operator-owned StatefulSets directly.

### Incident F — Consumer replay after Pod failure

**Signals:** duplicate business actions after consumer restart.

**Investigate:** offset commit timing, downstream write atomicity, group membership, event IDs.

**Mitigate:** idempotent sink processing and reconciliation; producer idempotence does not protect arbitrary downstream databases.

### Incident G — AZ/node outage

**Signals:** multiple Kafka Pods unavailable due to shared worker or zone.

**Investigate:** Pod anti-affinity, topology spread, PV zone binding, node pool placement, controller majority.

**Mitigate:** recover the affected failure domain and restore capacity. One-Pod lab success does not establish AZ failure tolerance.

### Incident H — Unsafe operator/Kafka upgrade

**Signals:** incompatible CRDs, failed reconciliation, mixed-version errors, feature-level mismatch.

**Investigate:** pinned operator and Kafka versions, release notes, CRD conversion, metadata feature level, rollout sequence.

**Mitigate:** stop rollout, use documented compatibility and rollback procedures; downgrade may be unsupported after feature finalization.

## 13. Enterprise troubleshooting matrix

| Symptom | Kubernetes first check | Kafka first check | Stop condition |
|---|---|---|---|
| Kafka CR not Ready | Operator logs and CR conditions | Broker/controller registration | Reconciliation errors persist |
| PVC Pending | StorageClass/CSI/events | No healthy replica storage | Any unbound critical PVC |
| Controller instability | Controller Pod placement/restarts | Quorum leader epochs/lag | Majority at risk |
| Producer errors | Broker Pod status/network | ISR, min ISR, acks | SLO breach |
| Consumer lag | Consumer Pod resources | Group offsets/partition lag | Backlog outside policy |
| Unexpected restarts | Pod events and OOMKilled | Broker recovery logs | Repeated failures |
| Missing records | Volume history and topic CR | Retention, offsets, replication | Suspected data loss |
| Config drift | GitOps and Strimzi logs | Effective dynamic overrides | Unknown ownership |

## 14. SRE incident and maintenance runbooks

### Runbook 1 — Pre-change safety gate

1. Confirm namespace/context, environment, Kafka and Strimzi versions.
2. Confirm approved change, responsible operator, maintenance window and abort owner.
3. Record Kafka CR, node pools, Pod placements, PVCs and controller quorum.
4. Confirm no offline partitions and full ISR for critical topics.
5. Check error rates, p99 latency, consumer lag and disk headroom.
6. Establish rollback procedure and evidence directory.

### Runbook 2 — One broker-Pod failure

1. Select one **broker-only** Pod from the dedicated test cluster.
2. Capture UID, labels, node, PVC and ISR before the test.
3. Delete only that Pod to simulate abrupt failure.
4. Observe operator reconciliation, partition leaders, ISR and producer errors.
5. Wait for full ISR restoration and Kafka Ready.
6. Compare expected business event IDs and record recovery time.
7. Abort additional tests if recovery fails.

### Runbook 3 — Controller incident

1. Freeze disruptive changes and controller restarts.
2. Identify voters, leader, epochs, quorum replication and failure domains.
3. Inspect controller Pods, logs, network and metadata PVCs.
4. Restore original healthy voters using version-supported recovery.
5. Verify quorum majority, stable leader, metadata progress and broker registrations.
6. Confirm partition health and application data path separately.

### Runbook 4 — Strimzi configuration change

1. Review Git diff and CRD schema.
2. Record current desired and effective config.
3. Run server-side dry run and stage validation.
4. Apply reviewed change to the correct Kafka or KafkaTopic resource.
5. Observe reconciliation and client SLOs.
6. Restore previous manifest if gates fail.
7. Capture operator events, metrics and final desired/effective state.

### Runbook 5 — Recovery and incident closure

1. Verify Kafka CR Ready, controller quorum, all Pods, PVCs and ISR.
2. Run bounded producer/consumer smoke tests.
3. Reconcile event IDs, consumer offsets and downstream side effects.
4. Record actual impact, RTO, potential RPO and residual risk.
5. Attach sanitized logs, commands, outputs and approvals to the incident ticket.
6. File root cause and preventive actions.

## 15. Acceptance gates and evidence matrix

| Gate | Evidence | Pass condition |
|---|---|---|
| Kubernetes isolation | Context/namespace | Dedicated lab confirmed |
| Strimzi compatibility | Operator version, CRD schema | Supported combination documented |
| Controller readiness | KafkaNodePool, Pods, quorum | Three voters, healthy majority |
| Broker readiness | KafkaNodePool, Pods | Three brokers healthy |
| Persistent storage | PVCs, Pod mounts | All claims Bound; data survives Pod recreation |
| Topic durability | Topic describe | RF=3, min ISR=2, ISR=3 before/after |
| Data correctness | Event IDs and consumer output | Expected records accounted for |
| Failure recovery | Before/during/after snapshots | One broker-Pod fault recovered |
| Administration | Kafka/KafkaTopic desired/effective configs | Reviewed change reconciled |
| Observability | Operator logs, metrics, incident timeline | Evidence retained |
| Security | TLS, RBAC, ACL and NetworkPolicy review | Required for production approval |
| DR readiness | Recovery procedure and backups | Separate DR validation required |

## 16. Final assessment — 100 points

| Domain | Points |
|---|---:|
| Kubernetes architecture and Strimzi operator design | 10 |
| Version compatibility and manifest validation | 10 |
| KRaft quorum, leader and metadata replication | 10 |
| Broker node pools, PVCs and failure-domain planning | 10 |
| KafkaTopic replication, partitions and ISR | 10 |
| Keyed production, acknowledgments and consumer replay | 10 |
| Safe broker-Pod fault injection and recovery | 10 |
| Automated readiness and acceptance tests | 10 |
| Incident response, troubleshooting and rollback runbooks | 10 |
| Evidence, security gaps, RTO/RPO and final report | 10 |

**Pass:** 85/100 or higher **and** no critical safety violation. Any unauthorized production fault, deletion of persistent data, or unapproved quorum mutation is an automatic fail. Publication is not an assessment result.

## 17. Acceptance report template

```markdown
# Kafka Kubernetes Capstone Acceptance
- Date / operator / reviewer:
- Kubernetes cluster and namespace:
- Strimzi version and Kafka version:
- CRD API version:
- Controller/broker node pools:
- PVC and failure-domain placement:
- Quorum status and leader epoch:
- Topic RF / min ISR / ISR:
- Producer/consumer evidence:
- Failure injected and affected Pod:
- Detection / recovery duration:
- Event reconciliation outcome:
- Automated test results:
- Security and DR gaps:
- Change ticket and evidence references:
- Score / 100:
- Reviewer sign-off:
```

Do not mark any test as Passed unless the output is captured. Record Pending or Blocked when the environment cannot support the scenario.

## 18. Cleanup

Remove only resources explicitly created for this capstone:

```bash
kubectl -n kafka-lab delete kafkatopic sre-capstone-ch10 --ignore-not-found
kubectl -n kafka-lab delete pod kafka-cli --ignore-not-found
```

Do not delete the Kafka cluster, KafkaNodePools or PVCs unless the entire isolated environment is intentionally being retired with evidence and data-retention approval.

## 19. References and next chapter

- [Strimzi documentation](https://strimzi.io/documentation/)
- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kubernetes documentation](https://kubernetes.io/docs/)
- [Shared Kubernetes lab foundation](../kubernetes/README.md)

**Next:** Chapter 011 — Kafka Brokers, Kubernetes Scheduling, Storage and Partition Placement.

---

**Verification boundary:** This chapter has been authored for Kubernetes/Strimzi and published to GitHub. Its manifests, fault scenarios, automated tests, security assumptions and production suitability require independent execution and review.
