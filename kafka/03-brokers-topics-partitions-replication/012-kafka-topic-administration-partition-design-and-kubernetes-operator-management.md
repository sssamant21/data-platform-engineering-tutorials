# Chapter 012 — Kafka Topic Administration, Partition Design and Kubernetes Operator Management

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 03 — Brokers, Topics, Partitions and Replication  
**Platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–011 and [Kubernetes Lab Foundation](../kubernetes/README.md)  
**Audience:** Kafka administrators, platform engineers, SREs and DBREs  
**Publication:** Complete | **Live lab execution:** Pending | **Security review:** Pending

> **Safety:** Topic deletion, retention changes, partition expansion and reassignment can permanently change replay guarantees, ordering, cost and application behavior. Use only disposable topics in an isolated Kubernetes cluster. Production topic lifecycle changes require ownership, retention/legal review, backup or replay plan, consumer impact assessment and approved change control.

## 1. Learning objectives

By the end of this chapter you can:

1. Explain Kafka topics, partition counts, replicas, ISR and leader assignments.
2. Administer topics declaratively through Strimzi KafkaTopic custom resources.
3. Distinguish KafkaTopic desired state, Topic Operator reconciliation and actual Kafka metadata.
4. Design partitions using workload, key cardinality, throughput and consumer parallelism.
5. Identify why partition expansion changes key-to-partition mapping and cannot be undone in place.
6. Apply safe retention and durability policies without compromising business data.
7. Inspect topic drift, errors, finalizers and Kubernetes events.
8. Automate topic validation and produce incident response runbooks.

## 2. Enterprise topic control plane

```text
             Git / pull request / change approval
                           |
                    GitOps controller
                           |
                Kubernetes API server
                           |
                 KafkaTopic custom resource
                           |
                  Strimzi Topic Operator
                           |
                   Kafka Admin API
                           |
                 KRaft metadata quorum
                           |
          Kafka brokers / topic partitions / replicas
                           |
                  Producers and consumers
```

KafkaTopic is a **declarative representation** of topic intent. The Topic Operator reconciles supported topic settings against Kafka. Not all Kafka Admin API operations are safely or fully represented by KafkaTopic fields; broker reassignment, ACLs, and some advanced lifecycle procedures require separate, version-specific workflows.

### 2.1 Resource responsibilities

| Resource | Primary responsibility | SRE validation |
|---|---|---|
| Kafka | Broker-level desired config, listeners, cluster | Kafka Ready, effective settings |
| KafkaNodePool | Broker/controller role, replicas, storage | Pod identities, PVCs, scheduling |
| KafkaTopic | Topic partitions, replicas and config | CR Ready/status plus Kafka metadata |
| KafkaUser | Identity and supported auth/authorization | Principal, ACLs, secret rotation |
| Kubernetes Secret | Credentials/certificates | Scope, RBAC, rotation |
| Kafka Admin API | Actual topic metadata and admin actions | Describe, list, config source |

**Source-of-truth rule:** when the Topic Operator manages a topic, use Git-reviewed KafkaTopic changes instead of racing the operator with direct Kafka CLI mutations. Direct reads are valuable; direct writes need explicit ownership coordination.

## 3. Partition design theory

A topic consists of partitions. Each partition has an independent offset sequence and leader; a consumer group can process different partitions in parallel. A key determines routing under the configured partitioner, so events for the same key can retain order within a partition.

### 3.1 Partition count considerations

- **Throughput:** more partitions can increase parallelism, but broker/network/disk bottlenecks and producer batching also matter.
- **Consumer parallelism:** for a conventional consumer group, active consumers cannot exceed the number of partitions they own.
- **Key ordering:** same-key records preserve partition order under stable partitioner and partition count.
- **Operational overhead:** more partitions increase metadata, replica files, leader management, recovery and monitoring load.
- **Hot keys:** increasing partitions may not fix one dominant key; one key generally routes to one partition.
- **Expansion:** increasing partitions is supported; reducing an existing topic's partition count is not a normal in-place operation.
- **Retention:** topic data lifetime is independent of consumer commits; a consumer can lag past retention and lose replayability.

### 3.2 Sizing method

Start with measured ingress/egress throughput and client parallelism:

```text
partitions_by_write ≈ ceil(peak topic write throughput / sustainable write throughput per partition)
partitions_by_read  ≈ ceil(peak read workload / sustainable read throughput per partition)
partitions_by_group ≈ desired concurrent consumers in the largest consumer group
target partitions   ≈ max(the three estimates), adjusted for hot keys and overhead
```

**Example (illustrative only):** a topic with 80 MiB/s peak ingress and a measured 8 MiB/s per-partition write limit needs at least 10 partitions for the write target. If the consumer design needs 12 active members, consider 12 or more partitions, then benchmark on the actual Kubernetes storage/network environment. These are not universal Kafka throughput limits.

### 3.3 Durability policy

For critical topics, RF=3 and min ISR=2 with producer `acks=all` is a common starting design, **not** a guarantee of no data loss under every failure. Evaluate unclean leader election, rack/AZ placement, producer retries/idempotence, storage durability, and disaster recovery separately.

## 4. Lab prerequisites

Use the shared Kubernetes-first lab: a version-compatible Strimzi Operator, three dedicated KRaft controllers, three broker Pods, PVCs and a Kafka CLI Pod. The examples below assume the installed Strimzi CRDs support `kafka.strimzi.io/v1`. **Check and substitute the actual supported API version before applying.**

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl api-resources | grep -E 'kafkatopics|kafkas'
kubectl -n kafka-lab get pod kafka-cli
mkdir -p evidence-ch12
```

Stop if the cluster is not healthy, the CLI Pod is missing, or the namespace/context is not the disposable lab.

## 5. Lab A — Create topics declaratively

Create `topic-ch12.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-orders-ch12
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

Apply with server-side validation:

```bash
kubectl apply --dry-run=server -f topic-ch12.yaml
kubectl apply -f topic-ch12.yaml
kubectl -n kafka-lab get kafkatopic sre-orders-ch12 -o yaml \
  | tee evidence-ch12/topic-created.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-orders-ch12 \
  | tee evidence-ch12/topic-metadata.txt
```

**Acceptance:** six partitions, three assigned replicas each, three ISR members each after reconciliation. A KafkaTopic CR existing in Kubernetes does not by itself prove Kafka creation succeeded; inspect its status and Kafka metadata.

## 6. Lab B — Validate keys, offsets and ordering

Produce records for two customers:

```bash
printf '%s\n' \
  'order-101:created' \
  'order-101:validated' \
  'order-101:paid' \
  'order-202:created' \
  'order-202:cancelled' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-orders-ch12 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Consume with metadata:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-orders-ch12 --from-beginning --max-messages 5 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true
```

**Validate:** the three `order-101` records have the same partition and increasing offsets; the two `order-202` records likewise. There is no cross-partition global order.

## 7. Lab C — Topic configuration inspection and drift

Inspect desired state:

```bash
kubectl -n kafka-lab get kafkatopic sre-orders-ch12 -o yaml \
  > evidence-ch12/desired-topic.yaml
```

Inspect actual Kafka topic overrides:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-orders-ch12 \
  --describe | tee evidence-ch12/effective-config.txt
```

Check `retention.ms=86400000`, `cleanup.policy=delete`, and `min.insync.replicas=2`. If Kafka metadata disagrees with the KafkaTopic CR, inspect Topic Operator logs, reconciliation conditions and conflicting direct Admin API changes.

**Safety:** do not “repair” drift by randomly applying direct `kafka-configs.sh --alter` operations to operator-managed topics.

## 8. Lab D — Safe declarative configuration change

Change the disposable topic's retention to two days (172800000 milliseconds) by editing the Git-reviewed KafkaTopic manifest, then:

```bash
kubectl apply --dry-run=server -f topic-ch12.yaml
kubectl apply -f topic-ch12.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-orders-ch12 \
  --describe
```

The displayed command applies whatever value is in `topic-ch12.yaml`; **edit the file first**. Confirm the effective retention equals 172800000, then restore the original 86400000 setting using the reviewed manifest.

**Operational warning:** decreasing retention can cause irreversible deletion after eligible cleanup; do not use production topics for this lab. A retention change may not take effect immediately because cleanup is asynchronous.

## 9. Lab E — Partition expansion design and consequences

**Do not execute this lab on any topic with production data or ordering contracts.** First document the risk: after expanding a keyed topic from six to nine partitions, a key's hash-to-partition mapping can change, so future events for the same key may land in a different partition from historical events. Consumers relying on stable per-key history must be redesigned or migrated.

In the disposable topic manifest, change:

```yaml
spec:
  partitions: 9
```

Then:

```bash
kubectl apply --dry-run=server -f topic-ch12.yaml
kubectl apply -f topic-ch12.yaml

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-orders-ch12 \
  | tee evidence-ch12/topic-expanded.txt
```

**Expected:** nine partitions after successful reconciliation. Partition expansion is **not reversible by setting the count back to six**. Keep this disposable topic at nine partitions until cleanup; do not falsely claim rollback.

### Migration alternative for strict ordering

Create a new versioned topic with the desired partition count, dual-write or migrate through a controlled cutover, validate downstream semantics, and retire the old topic only after replay/retention obligations are satisfied. Design consumer group transitions explicitly.

## 10. Lab F — Ownership and policy governance

A production topic request should capture:

| Field | Required detail |
|---|---|
| Topic owner | Team, application, pager/escalation |
| Data classification | PII/PHI/regulated data as applicable |
| Retention | Business need, legal hold, replay requirements |
| Partition design | Peak throughput, key choice, hot-key analysis |
| Durability | RF, min ISR, producer acks and failure domains |
| Consumers | Groups, replay window, processing SLIs |
| Access | Producer/consumer principals and ACL scope |
| Lifecycle | Creation, config changes, deprecation, deletion |
| Cost | Retention bytes, replicas, network and recovery headroom |
| Change review | Approval, test evidence, rollback/migration plan |

**Governance exercise:** draft a pull request for `sre-orders-ch12` that includes the table above and the KafkaTopic manifest. Do not include credentials in Git.

## 11. Automated topic acceptance script

Save as `verify-ch12.sh` in your lab directory. This script is read-only and expects the topic to have **nine partitions after Lab E**; set `EXPECTED_PARTITIONS=6` if running it before expansion.

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
TOPIC=sre-orders-ch12
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
EXPECTED_PARTITIONS="${EXPECTED_PARTITIONS:-9}"

echo '[1/6] Kafka cluster readiness'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Topic CR exists'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/6] Kafka Admin API accessible'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[4/6] Kafka metadata'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"

echo '[5/6] Partition and ISR validation'
printf '%s\n' "$desc" | awk -v expected="$EXPECTED_PARTITIONS" '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); r=split(b[1],rep,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],members,",")
    seen++
    if(r!=3 || isr!=3) bad++
  }
  END {
    if(seen!=expected || bad!=0) {
      print "FAIL: partitions="seen" expected="expected" degraded="bad
      exit 1
    }
    print "PASS: partitions="seen" RF=3 ISR=3"
  }'

echo '[6/6] Topic configuration'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" \
  --entity-type topics --entity-name "$TOPIC" --describe

echo 'PASS: KafkaTopic and metadata acceptance'
```

```bash
chmod +x verify-ch12.sh
./verify-ch12.sh
```

**Limitations:** this checks metadata and basic connectivity, not real throughput, key distribution, Topic Operator conditions, retention deletion timing, legal policy, or producer/consumer correctness. Those require additional evidence and independent review.

## 12. Production incident simulations

### Incident 1 — KafkaTopic CR exists but topic is absent

**Signals:** Kubernetes resource present, Kafka Admin API reports unknown topic.

**Causes:** Topic Operator unavailable, incorrect cluster label, invalid config, reconciliation errors.

**Investigate:** KafkaTopic status, Topic Operator logs, operator watch namespace, Kafka connectivity.

**Mitigate:** correct desired state and allow reconciliation; avoid duplicate out-of-band topic creation.

### Incident 2 — Unexpected key ordering regression after partition expansion

**Signals:** same key appears in different partitions across time.

**Causes:** partition count changed, partitioner/serializer changed, key representation changed.

**Investigate:** change history, producer configs, partition/offset metadata, event IDs.

**Mitigate:** stop further incompatible changes, redesign migration to versioned topic and consumer cutover.

### Incident 3 — Retention causes missing replay data

**Signals:** consumers cannot read expected old offsets.

**Causes:** retention.ms/bytes, cleanup policy, topic overrides, long consumer outage.

**Investigate:** retention configs, log start offsets, group committed offsets, deletion events.

**Mitigate:** restore retention policy for future data; recover lost history from upstream/backups where available. Already deleted data is not restored by increasing retention.

### Incident 4 — Hot partition despite many partitions

**Signals:** one broker/partition has high produce latency and disk/network usage.

**Causes:** skewed keys, one dominant customer/tenant, custom partitioner.

**Investigate:** key distribution, partition ingress, leader broker, client batching.

**Mitigate:** redesign key distribution with application owners; adding partitions may not resolve a single hot key.

### Incident 5 — Topic Operator reconciliation conflict

**Signals:** direct Kafka config updates are reverted or CR conditions fail.

**Causes:** competing GitOps and CLI owners, invalid configuration, drift.

**Investigate:** Git history, KafkaTopic desired config, Kafka effective config, operator logs.

**Mitigate:** establish single owner and reconcile through the approved manifest.

### Incident 6 — Under-min-ISR causes producer failures

**Signals:** `acks=all` writes fail after a broker outage.

**Causes:** degraded replicas, poor failure-domain placement, disk/network lag.

**Investigate:** topic RF/ISR, broker Pods, PVC health, replica fetch lag.

**Mitigate:** restore ISR and broker capacity. Do not lower min ISR without explicit durability-risk acceptance.

### Incident 7 — Accidental topic deletion

**Signals:** topic metadata and records disappear, consumers fail.

**Causes:** mistaken GitOps deletion, wrong namespace, unreviewed lifecycle automation.

**Investigate:** Kubernetes audit events, GitOps history, Topic Operator logs, Kafka metadata.

**Mitigate:** stop further deletions, preserve evidence, recreate only under approved recovery procedure and replay from upstream/backup. Topic recreation alone does not restore prior records.

### Incident 8 — Partition count overloads cluster

**Signals:** metadata load, open file count, recovery time or broker CPU rises.

**Causes:** excessive partition proliferation, over-sharded topics, insufficient broker capacity.

**Investigate:** partitions per broker, leaders, disk usage, controller metrics, quotas.

**Mitigate:** govern topic creation and plan migration/consolidation; do not assume partition count can be decreased in place.

## 13. Troubleshooting matrix

| Symptom | First checks | Avoid |
|---|---|---|
| Topic not created | KafkaTopic status, Topic Operator logs | Repeated blind create |
| Invalid topic config | CRD schema, Kafka validation errors | Disabling operator |
| Wrong partition count | Actual Kafka metadata, Git desired state | Attempting shrink |
| Missing replay records | Retention and log start offsets | Arbitrary offset reset |
| Hot partition | Key distribution, leader metrics | Adding partitions blindly |
| Topic deletion | Audit/Git history, backups | Recreating without recovery plan |
| ISR below min ISR | Broker Pods, replica lag, storage | Lowering min ISR |
| ACL denial | Principal, KafkaUser and ACLs | Disabling auth |
| Config drift | GitOps, Topic Operator, effective settings | Direct untracked edits |

## 14. SRE runbooks

### Runbook A — Topic creation/change approval

1. Verify owner, data classification, retention and replay requirements.
2. Review throughput, partition count, key strategy, RF and min ISR.
3. Confirm Kafka cluster capacity and failure-domain placement.
4. Validate KafkaTopic YAML with installed CRD and server-side dry run.
5. Apply through approved GitOps path.
6. Verify KafkaTopic reconciliation, actual topic metadata and client smoke test.
7. Capture change ticket, effective settings and rollback constraints.

### Runbook B — Topic drift and reconciliation failure

1. Capture KafkaTopic YAML/status, operator logs and Kafka metadata.
2. Identify whether drift came from GitOps, Kafka CLI or unsupported fields.
3. Pause conflicting automation only with incident approval.
4. Restore authoritative desired state and monitor reconciliation.
5. Validate partition/replica count, configs and client SLIs.
6. Document root cause and preventive policy.

### Runbook C — Retention or data-loss incident

1. Declare scope and preserve logs, offsets, topic configs and audit history.
2. Identify last available log start offset and missing event range.
3. Stop destructive changes; do not reset consumer offsets blindly.
4. Restore correct policy for future records.
5. Rehydrate missing data from supported upstream/backup sources where possible.
6. Reconcile downstream business records and communicate residual data gaps.

### Runbook D — Partition expansion migration

1. Confirm expansion is necessary and benchmark the proposed count.
2. Assess ordering, partitioner, consumer parallelism and downstream assumptions.
3. Prefer a versioned topic for strict ordering or schema contracts.
4. Prepare cutover, dual-write/backfill and rollback plan.
5. Execute only after approval and verify all producers/consumers.
6. Monitor partition skew, lag, costs and SLOs.
7. Record irreversible partition-count change or migration outcome.

## 15. Observability and SLO engineering

Monitor topic creation/reconciliation errors, topic count, partitions per broker, leaders per broker, under-replicated and under-min-ISR partitions, produce/fetch error rates, p99 latency, consumer lag, log start offsets, retention pressure and topic deletion events.

Define topic-level SLOs using business event age and delivery success, not merely KafkaTopic Ready. Alert on unauthorized KafkaTopic deletion and retention changes through Kubernetes audit/GitOps controls.

## 16. Enterprise readiness checklist

- [ ] Topic ownership and data classification documented.
- [ ] Strimzi Topic Operator management scope understood.
- [ ] Git-reviewed KafkaTopic manifests are authoritative.
- [ ] Partition count benchmarked and hot-key risk assessed.
- [ ] RF/min ISR/acks policy meets durability requirements.
- [ ] Topic replica placement spans failure domains.
- [ ] Retention, compaction and replay obligations approved.
- [ ] KafkaUser/ACL and Kubernetes RBAC least privilege reviewed.
- [ ] Topic deletion and expansion require special approval.
- [ ] Topic metadata and config drift monitoring enabled.
- [ ] Recovery and versioned-topic migration procedures tested.
- [ ] Audit evidence retained.

## 17. Assessment — 100 points

| Requirement | Points |
|---|---:|
| Explain topic architecture and operator reconciliation | 10 |
| Design partitions from measured throughput and consumers | 10 |
| Create a KafkaTopic with RF=3/min ISR=2 | 10 |
| Verify Kafka metadata and ISR | 10 |
| Demonstrate keyed ordering and offsets | 10 |
| Inspect desired and effective topic configuration | 10 |
| Perform reversible retention change in lab | 10 |
| Explain irreversible partition expansion consequences | 10 |
| Diagnose operator drift or missing topic incident | 10 |
| Deliver approved topic lifecycle and recovery runbooks | 10 |

**Pass:** at least 85/100 with no destructive safety violations and independently captured evidence. Publication does not mean labs were run.

## 18. Cleanup

After recording the irreversible partition-expansion result and saving evidence, delete **only** the disposable topic:

```bash
kubectl -n kafka-lab delete kafkatopic sre-orders-ch12 --ignore-not-found
```

Topic deletion can remove all topic data. Confirm this is not a shared topic and the operator's deletion behavior is understood. Preserve the Kafka cluster and PVCs for Chapter 013.

## 19. References and next chapter

- [Strimzi documentation](https://strimzi.io/documentation/)
- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kubernetes custom resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Lab Foundation](../kubernetes/README.md)

**Next:** Chapter 013 — Kafka Partition Reassignment, Replica Balancing and Kubernetes Broker Scaling.

---

**Verification boundary:** GitHub publication confirms written content. Kubernetes lab execution, version-specific CRD verification, failure tests and security review remain pending.
