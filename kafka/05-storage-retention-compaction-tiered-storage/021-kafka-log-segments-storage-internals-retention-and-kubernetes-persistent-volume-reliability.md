# Chapter 021 — Kafka Log Segments, Storage Internals, Retention and Kubernetes Persistent Volume Reliability

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 05 — Storage, Retention, Compaction and Tiered Storage  
**Primary lab:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 001–020, especially broker/replica reliability (011–015) and consumer offsets (017–020)  
**Audience:** Kafka SREs, DBREs, storage/platform engineers, application owners  
**Status:** Published · **Live lab validation:** Pending · **Security review:** Pending

> **Safety:** Kafka data directories and broker PVCs contain production-critical state. **Never edit or delete Kafka log segment files, index files, PVCs, or broker Pod volumes manually.** Never shrink a Kafka PVC or change a production retention policy without an approved impact assessment. All write operations in this chapter target one disposable KafkaTopic. Read-only broker filesystem inspection is optional and must respect cluster access controls.

## 1. Learning objectives

After this chapter you can:

1. Describe Kafka's partition log, active and rolled segments, offset/time/transaction indexes and log recovery.
2. Distinguish retention by time and size, segment rolling, retention checks and compaction.
3. Explain why topic retention is not an exact deletion deadline and why consumer offsets do not protect old records from retention.
4. Trace Strimzi broker storage from KafkaNodePool and Kafka CRs to Kubernetes PVCs, PVs and StorageClasses.
5. Identify storage IOPS, throughput, latency, free-space and inode exhaustion signals.
6. Safely create a disposable topic with explicit retention and segment settings.
7. Demonstrate log-segment rolling with deterministic records and **read-only** metadata inspection.
8. Explain filesystem failure, disk pressure, PVC binding and storage-class failure modes.
9. Implement storage capacity alerts, operational runbooks and an evidence-based 100-point assessment.

## 2. Kafka storage architecture

```text
 Producer -> Kafka partition leader (broker Pod)
                       |
              append-only partition log
                       |
           active segment (.log + indexes)
                       |
                segment roll
                       |
           older closed segments
                       |
        retention / compaction decisions
                       |
             broker filesystem
                       |
          mounted Kubernetes PVC
                       |
              PV / CSI driver
                       |
         cloud block disk / storage backend
```

A Kafka topic partition is an ordered append-only log. Its leader appends records and followers replicate. A partition is stored as multiple segments, with an **active segment** receiving new writes and older **closed segments** eligible for time/size retention or log cleaning. A broker's physical filesystem layout is an implementation detail; do not rely on a fixed mount path across Strimzi versions or storage types.

### 2.1 Segment file families

| File or artifact | Purpose | Operational concern |
|---|---|---|
| `.log` | Record batches for a log segment | Largest disk-space contributor |
| `.index` | Sparse offset-to-file-position index | Corruption can affect recovery |
| `.timeindex` | Timestamp-to-offset lookup | Helps time-based offset queries |
| `.txnindex` | Aborted transaction metadata when relevant | Important for read_committed |
| Leader epoch checkpoint | Leader epoch recovery metadata | Replica truncation/recovery |
| Partition checkpoints | Recovery/start-offset information | Broker recovery and consistency |

**Important:** Kafka internal file names and placement vary by release. Inspection is informational only. The broker owns these files; editing them outside supported Kafka administration workflows is unsafe.

## 3. Retention semantics and trade-offs

### 3.1 Time retention

`retention.ms` defines how long log data is eligible to be retained, subject to segment boundaries and the broker's retention evaluation cycle. A record is not guaranteed to disappear at exactly the configured age. Closed segments are deleted when eligible; active segments generally must roll first.

### 3.2 Size retention

`retention.bytes` is a **per-partition** retention size limit, not a per-topic or per-cluster quota. Actual disk use can exceed it temporarily due to segment granularity, active segments, indexes, replication and background cleanup.

### 3.3 Segment rolling

`segment.bytes` controls approximate maximum segment size; `segment.ms` controls time-based rolling. Very small segments increase file count, metadata/index overhead, filesystem pressure and recovery work. Production defaults must be tuned from workload and capacity data, not copied from the tiny lab settings below.

### 3.4 Compaction is different

`cleanup.policy=delete` removes eligible old segments. `cleanup.policy=compact` retains the latest record per key subject to cleaner behavior and tombstone rules; it is **not** equivalent to keeping all history forever. Combined `delete,compact` policies have additional implications covered in Chapter 023.

### 3.5 Retention versus consumer lag

Kafka's retention process does not generally wait for all consumer groups to finish reading. A slow or paused consumer can lose replay access when its committed offset falls behind the log start offset. Monitor **event age versus retention window**, not only record-count lag.

## 4. Kubernetes persistent storage architecture

Strimzi manages Kafka brokers and their persistent volumes using Kafka and KafkaNodePool custom resources. PVC naming, labels, volume IDs, filesystem paths and storage-class parameters depend on operator release and node-pool storage configuration.

```text
Kafka CR / KafkaNodePool broker role
       |
Strimzi reconciles broker Pods
       |
Pod volumeMount / PVC
       |
PVC -> StorageClass -> CSI PV
       |
cloud disk / local PV / storage backend
```

**KRaft note:** metadata controller storage and broker partition-log storage are separate operational concerns even when both use PVCs. Never delete a controller PVC to address broker disk usage.

### 4.1 StorageClass and topology

Check whether the StorageClass uses `WaitForFirstConsumer`, volume expansion, reclaim policy, encryption, zone topology and the intended CSI driver. Zonal block volumes constrain Pod placement. A bound PVC does not guarantee that the broker can schedule in a different zone after a node failure.

### 4.2 Storage expansion

PVC expansion is supported only when the StorageClass/CSI driver and Strimzi storage configuration support the desired change. Expanding a PVC is not the same as expanding filesystem availability immediately, and many storage backends cannot shrink volumes. Follow Strimzi's supported storage-change workflow rather than editing a PVC or KafkaNodePool spec blindly.

## 5. Lab environment and safety gates

Use the shared [Kubernetes-first lab foundation](../kubernetes/README.md): namespace `kafka-lab`, Strimzi cluster `sre-kafka`, a healthy `kafka-cli` Pod, and internal lab bootstrap `sre-kafka-kafka-bootstrap:9092`.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl get crd kafkatopics.kafka.strimzi.io -o jsonpath='{.spec.versions[*].name}{"\n"}'
mkdir -p evidence-ch21
```

Stop if Kafka is not Ready, KRaft quorum is unhealthy, PVCs are failing, or the test namespace is shared with production workloads. KafkaTopic examples use `kafka.strimzi.io/v1`; substitute a supported served CRD API version if required.

## 6. Lab A — Inventory broker storage without mutations

```bash
kubectl -n kafka-lab get kafkanodepool -o yaml \
  > evidence-ch21/nodepools-before.yaml
kubectl -n kafka-lab get pvc -o wide \
  | tee evidence-ch21/pvc-inventory.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch21/pod-placement.txt
kubectl get storageclass -o wide \
  | tee evidence-ch21/storageclasses.txt
```

For each **broker** node pool, document storage type, requested capacity, volume IDs (if JBOD), StorageClass, PVC Bound status, zone/node placement and expansion support. Do not confuse controller PVCs with broker PVCs.

**Acceptance:** inventory maps each broker Pod to its PVC(s) and backing StorageClass. Do not infer this solely from a PVC name; inspect actual Pod volume references.

## 7. Lab B — Inspect the broker Pod/PVC relationship

First identify broker-role Pods from the KafkaNodePool inventory and Strimzi labels. Then inspect a **specific verified broker Pod**:

```bash
kubectl -n kafka-lab get pods --show-labels
kubectl -n kafka-lab describe pod <VERIFIED_BROKER_POD_NAME> \
  | tee evidence-ch21/broker-pod-describe.txt
kubectl -n kafka-lab get pod <VERIFIED_BROKER_POD_NAME> -o jsonpath='{range .spec.volumes[*]}{.name}{" -> "}{.persistentVolumeClaim.claimName}{"\n"}{end}'
```

Record actual PVC claims and volume mounts. `describe` output may contain environment or configuration details; sanitize before sharing.

**Acceptance:** broker data PVC and corresponding Pod volume mount identified. No filesystem modification.

## 8. Lab C — Create a disposable retention/segment topic

Save `topic-ch21.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-storage-ch21
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 3600000
    segment.bytes: 1048576
    segment.ms: 60000
```

These deliberately small segment/time values are **lab-only** and can create additional segment files. Do not use them for production topics.

```bash
kubectl apply --dry-run=server -f topic-ch21.yaml
kubectl apply -f topic-ch21.yaml
kubectl -n kafka-lab get kafkatopic sre-storage-ch21 -o yaml \
  > evidence-ch21/topic-cr.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-storage-ch21 \
  | tee evidence-ch21/topic-describe.txt
```

**Acceptance:** three partitions, RF=3, ISR=3, configured retention/segment settings reconciled.

## 9. Lab D — Verify effective topic retention configuration

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-storage-ch21 \
  --describe \
  | tee evidence-ch21/topic-effective-config.txt
```

Confirm `retention.ms=3600000`, `segment.bytes=1048576`, `segment.ms=60000` and `cleanup.policy=delete`. Broker defaults may still govern properties not explicitly set.

**Acceptance:** effective configuration matches approved lab manifest; no unreviewed broker-level override.

## 10. Lab E — Produce deterministic batches

```bash
printf '%s\n' \
  'device-A:event-2101' 'device-A:event-2102' \
  'device-B:event-2103' 'device-B:event-2104' \
  'device-C:event-2105' 'device-C:event-2106' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-storage-ch21 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Read back six records using a fresh group:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-storage-ch21 --from-beginning \
  --group sre-storage-ch21-verify --max-messages 6 \
  --property print.key=true --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch21/consumed-events.txt
```

**Acceptance:** six unique event IDs, valid partition offsets. Small test messages may **not** create multiple segments; the next lab is observational.

## 11. Lab F — Observe segment rolling safely

Wait longer than the configured `segment.ms`, then produce another small batch. Time-based rolling may require an append and depends on broker internals and actual segment timestamps.

```bash
sleep 70
printf '%s\n' 'device-A:event-2107' 'device-B:event-2108' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-storage-ch21 \
  --producer-property acks=all \
  --property parse.key=true --property key.separator=:
```

**Optional read-only inspection:** if permitted, discover the Kafka broker's actual data mount and run `find`/`ls` **only** in the verified broker Pod, with no root escalation or file modification. Example after determining the real mount:

```bash
kubectl -n kafka-lab exec <VERIFIED_BROKER_POD_NAME> -- \
  sh -c 'find "<VERIFIED_KAFKA_DATA_MOUNT>" -maxdepth 4 -type f -name "*.log" -print'
```

This command is a template; validate shell/tool availability and substitute the actual path. If broker filesystem access is disallowed, use broker log-segment metrics and Kafka topic metadata instead. **Do not mark physical segment observation Passed without evidence.**

## 12. Lab G — Compare active and closed segment retention

Document the following:

- Active segments continue accepting writes and are not generally deleted by time retention while active.
- Segment rolling makes older segments eligible for cleanup.
- `retention.ms` is an eligibility boundary, not a precise expiration SLA.
- `retention.bytes` is per partition and evaluated with segment granularity.
- Broker retention checks, timestamp semantics and segment layout affect actual deletion.
- Consumer lag and group committed offsets do not prevent deletion of expired topic records.

**Acceptance:** a written retention timeline with an example of why a record can remain after its configured age. This is a design exercise, not a destructive deletion demonstration.

## 13. Lab H — Read-only storage pressure inventory

```bash
kubectl -n kafka-lab get pvc -o json \
  > evidence-ch21/pvc-inventory.json
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch21/k8s-events.txt
kubectl -n kafka-lab describe node <VERIFIED_BROKER_NODE_NAME> \
  > evidence-ch21/node-storage-pressure.txt
```

Use your installed storage/Prometheus metrics to collect PVC available bytes, filesystem usage, write latency, broker log size, under-replicated partitions and offline partitions. Kubernetes PVC **requested capacity** is not a filesystem-free-space metric. CSI capacity reporting and kubelet volume metrics depend on driver and deployment.

**Acceptance:** evidence identifies data-disk usage and alert sources without inferring utilization from PVC size alone.

## 14. Lab I — Capacity and replication math

Estimate logical log storage:

```text
logical_data_bytes ≈ sustained_ingest_bytes_per_second × retention_seconds
replicated_bytes ≈ logical_data_bytes × replication_factor
provisioned_capacity > replicated_bytes + indexes + overhead + headroom
```

**Example:** 10 MiB/s sustained ingest × 24 hours ≈ 843.75 GiB logical. RF=3 ≈ 2.47 TiB replicated before index, compaction, rebalancing, filesystem and headroom overhead. This is a **cluster-wide planning estimate**, not an exact per-broker allocation.

For capacity acceptance, calculate:

1. Ingest rate and burst factor by topic.
2. Retention policy and replication factor.
3. Per-broker partition placement, uneven hot partitions and leader load.
4. Recovery/reassignment temporary storage overhead.
5. Reserved disk headroom and expansion lead time.
6. IOPS, write throughput and p99 storage latency.
7. Controller metadata PVC capacity separately from broker data PVCs.

**Acceptance:** documented forecast with assumptions and alert thresholds justified by measured growth.

## 15. Lab J — PVC expansion tabletop and change review

**Do not expand a live PVC in this lab.** Prepare a change plan:

1. Check `allowVolumeExpansion` on the actual StorageClass.
2. Verify CSI driver and Strimzi-supported KafkaNodePool storage change semantics.
3. Identify broker PVCs, JBOD volume IDs and topology.
4. Calculate expansion target, cost and filesystem growth expectations.
5. Plan one change at a time with replica/ISR health gates.
6. Observe PVC resize conditions, filesystem size and broker recovery.
7. Document rollback limitations: PVC shrink is generally unsupported.

**Acceptance:** approved plan and explicit no-go criteria; no direct mutation.

## 16. Lab K — Disk pressure incident tabletop

Simulate **only on paper** a broker data volume reaching 95% utilization. Explain:

- Why writes, segment cleanup, follower replication and recovery may be impacted.
- Why deleting random Kafka files risks corruption and data loss.
- Why changing retention is a business data-governance decision.
- Why broker/partition placement and temporary reassignment space matter.
- When to expand storage, reduce ingest, rebalance with safeguards or invoke a data-retention change.

**Acceptance:** a prioritized incident decision tree and evidence plan. No deliberate disk-fill workload.

## 17. Lab L — Automated read-only storage preflight

Save `verify-ch21.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
TOPIC=sre-storage-ch21
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/6] Kafka Ready'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] KafkaNodePool and PVC inventory'
kubectl -n "$NS" get kafkanodepool
kubectl -n "$NS" get pvc -o wide

echo '[3/6] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[4/6] Topic partition health'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++; if(rf!=3 || isr!=3) bad++
  }
  END {
    if(seen!=3 || bad){print "FAIL: partition count/RF/ISR";exit 1}
    print "PASS: 3 partitions, RF=3, ISR=3"
  }'

echo '[5/6] Topic retention configuration'
configs="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name "$TOPIC" --describe)"
printf '%s\n' "$configs"
for expected in 'retention.ms=3600000' 'segment.bytes=1048576' \
                'segment.ms=60000' 'cleanup.policy=delete'; do
  if ! grep -Fq "$expected" <<<"$configs"; then
    echo "FAIL: missing config $expected" >&2
    exit 1
  fi
done

echo '[6/6] Metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: read-only metadata preflight; free space, segment rolling and retention deletion need separate evidence'
```

```bash
chmod +x verify-ch21.sh
./verify-ch21.sh | tee evidence-ch21/acceptance.txt
```

**Limitations:** this script does not prove actual filesystem free space, PVC expansion support, segment rolling, retention deletion, disk latency or data recovery. It assumes a three-broker RF3 lab and full ISR; stop rather than relax these conditions to pass.

## 18. Ten production incident scenarios

### 18.1 Broker disk full

**Signals:** write failures, broker I/O errors, disk utilization critical.

**Investigate:** filesystem usage, segment growth, topic ingest, retention, PVC metrics, broker logs.

**Mitigate:** protect quorum/ISR, reduce ingest if needed, follow approved storage expansion or retention change; never delete Kafka files manually.

### 18.2 PVC Pending after broker scheduling

**Signals:** broker Pod Pending, PVC unbound, CSI events.

**Investigate:** StorageClass, zone affinity, quotas, available capacity, WaitForFirstConsumer.

**Mitigate:** correct storage provisioning and scheduling constraints through supported Strimzi/Kubernetes workflow.

### 18.3 Slow disk causes replica lag

**Signals:** under-replicated partitions, follower fetch latency, producer p99 increase.

**Investigate:** CSI latency, disk IOPS/throughput, broker CPU, network and placement.

**Mitigate:** restore storage performance and ISR; do not lower min ISR.

### 18.4 Retention unexpectedly removes replay data

**Signals:** consumer OffsetOutOfRange, log start offset ahead of committed offset.

**Investigate:** effective retention, segment roll, consumer outage duration, lag/event age.

**Mitigate:** recover from upstream/backup; an offset reset cannot restore deleted records.

### 18.5 Retention does not immediately free disk

**Signals:** topic remains large after policy update.

**Investigate:** active segment, retention check cadence, cleanup policy, compaction, segment size.

**Mitigate:** monitor expected cleanup; avoid manually deleting log segments.

### 18.6 Too many small segments

**Signals:** high open-file count, recovery slowdown, metadata/index overhead.

**Investigate:** `segment.bytes`, `segment.ms`, topic count, partition count, log cleaner behavior.

**Mitigate:** tune after benchmarking and approved change.

### 18.7 Storage zone failure

**Signals:** broker Pod cannot reattach volume in another zone.

**Investigate:** PV node affinity, CSI topology, StorageClass binding mode, broker replica placement.

**Mitigate:** restore zonal infrastructure or use approved replacement/reassignment strategy with ISR gates.

### 18.8 PVC expansion stuck

**Signals:** PVC resizing condition persists, filesystem size unchanged.

**Investigate:** CSI expansion support, quota, node filesystem resize requirements, Strimzi reconciliation.

**Mitigate:** follow vendor/CSI documented recovery; never shrink PVC to undo expansion.

### 18.9 Hot partition fills one broker faster

**Signals:** broker-level disk skew despite healthy cluster-wide capacity.

**Investigate:** partition placement, key skew, per-broker log bytes and leader distribution.

**Mitigate:** reviewed replica reassignment or workload redesign, with free-space and ISR prechecks.

### 18.10 Broker recovery stalls on corrupt index or storage error

**Signals:** broker restart loop, recovery exceptions, storage I/O errors.

**Investigate:** broker logs, PV/CSI health, replica availability, checkpoint state.

**Mitigate:** preserve evidence and use supported Kafka/Strimzi recovery procedures; do not edit `.index` or `.log` files manually.

## 19. Troubleshooting matrix

| Symptom | Kubernetes checks | Kafka checks | Unsafe shortcut |
|---|---|---|---|
| PVC Pending | StorageClass, CSI, topology | Broker availability | Delete PVC |
| Disk nearly full | Filesystem metrics, PV size | Retention, log size | Delete segment files |
| Writes fail | Pod logs, disk latency | ISR, leader, acks | Lower min ISR |
| Retention slow | Storage utilization | Segment roll/cleanup | Force filesystem rm |
| Consumer out of range | Pod outage history | Log start vs committed offset | Reset to latest |
| Uneven disk use | Pod/PV placement | Partition replica placement | Blind reassignment |
| Expansion incomplete | PVC conditions, CSI | Broker health | Shrink PVC |
| Recovery loops | Pod events, CSI errors | Replica/leader recovery | Modify Kafka indexes |

## 20. Six production runbooks

### Runbook A — Disk pressure and capacity incident

1. Identify affected brokers, volumes, partitions and business impact.
2. Capture disk usage, growth rate, IOPS/latency, Kafka ISR and offline partitions.
3. Stop unsafe changes and preserve data durability.
4. Coordinate ingest throttling, approved expansion or retention action with owners.
5. Validate filesystem headroom, ISR and producer recovery.
6. Record timeline, capacity forecast and alert improvements.

### Runbook B — PVC provisioning failure

1. Inspect broker Pod scheduling, PVC status, StorageClass and CSI events.
2. Identify zone/affinity/quota or provisioner mismatch.
3. Preserve existing PVC/PV identities and data.
4. Correct infrastructure using supported Strimzi/Kubernetes workflow.
5. Verify broker recovery, replica catch-up and Kafka Ready.
6. Document root cause and preventive policy.

### Runbook C — Retention policy change

1. Identify topic owner, compliance/retention requirements and consumers.
2. Capture current effective settings, log start/end offsets and lag.
3. Estimate data loss/replay impact and storage savings.
4. Approve and apply change through KafkaTopic GitOps.
5. Monitor segment cleanup, consumer recovery and storage trends.
6. Retain change ticket and audit evidence.

### Runbook D — Storage performance degradation

1. Correlate producer latency and under-replicated partitions with disk latency.
2. Check per-broker IOPS, throughput, CPU, network and hot partitions.
3. Identify CSI/backend throttling or storage contention.
4. Restore performance and reduce load within approved limits.
5. Verify follower catch-up, ISR and application SLOs.
6. Update storage sizing and monitoring baselines.

### Runbook E — Broker PVC expansion

1. Confirm storage driver, StorageClass and Strimzi expansion support.
2. Capture current PVC sizes, Pod mapping and replica health.
3. Obtain approval for capacity/cost and one-change-at-a-time plan.
4. Execute only the vendor-supported expansion workflow.
5. Validate PVC status, filesystem capacity, broker Ready and ISR.
6. Document irreversibility and follow-up headroom alerts.

### Runbook F — Data recovery and audit

1. Preserve broker/CSI errors, topic config and incident timestamps.
2. Determine whether replicas, upstream sources or backups can recover data.
3. Avoid filesystem-level edits and destructive PVC replacement.
4. Perform supported recovery with change authorization.
5. Reconcile log offsets, producer IDs and consumer replay boundaries.
6. Capture assessor and data-owner signoff.

## 21. Observability and storage SLOs

Monitor:

- Per-broker filesystem available bytes, used percentage, inode availability and growth rate.
- PVC and CSI provisioning/resizing failures, attach/detach errors and topology constraints.
- Disk IOPS, throughput, queue depth, p95/p99 latency and throttling.
- Kafka log size, segment count, log cleaner activity, under-replicated/offline partitions.
- Producer request latency, error rate, consumer event age and OffsetOutOfRange events.
- Retention policy changes, topic ownership and audit events.

**Example alert policy (design only):** warning based on projected days-to-full, critical based on headroom needed for recovery/reassignment, and immediate page for broker I/O errors or offline partitions. Calibrate from measured workload and storage lead times, not arbitrary global percentages.

## 22. Evidence and acceptance checklist

```text
evidence-ch21/
  cluster-context-and-approval.md
  nodepools-before.yaml
  pvc-inventory.txt
  pod-placement.txt
  storageclasses.txt
  broker-pod-describe.txt
  topic-cr.yaml
  topic-describe.txt
  topic-effective-config.txt
  consumed-events.txt
  segment-observation.txt
  capacity-forecast.md
  expansion-change-plan.md
  disk-pressure-tabletop.md
  acceptance.txt
  incident-review.md
  security-signoff.md
```

For each lab record timestamp, command, expected result, actual result, evidence path, reviewer and status. Do not mark filesystem/segment labs Passed when access is restricted or evidence is absent.

## 23. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain Kafka segment files and recovery | 10 |
| Explain retention time/size and segment boundaries | 10 |
| Inventory Strimzi broker PVCs and StorageClasses | 10 |
| Verify broker Pod-to-PVC mappings | 10 |
| Create and validate retention test topic | 10 |
| Produce/consume deterministic events | 10 |
| Observe segment roll or document limitation | 10 |
| Capacity, IOPS and retention forecasting | 10 |
| Execute read-only preflight and interpret evidence | 10 |
| Incident scenarios, runbooks and safe storage changes | 10 |
| **Total** | **100** |

**Pass:** ≥85/100, no critical safety violations, evidence captured. A documented limitation is useful but does not automatically earn execution points for an unperformed lab.

## 24. Cleanup and next chapter

After evidence capture and explicit confirmation the topic is disposable:

```bash
kubectl -n kafka-lab delete kafkatopic sre-storage-ch21 --ignore-not-found
```

Topic deletion removes data. Do **not** delete Kafka broker/controller PVCs, PVs, KafkaNodePools or the cluster.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/).

**Next:** Chapter 022 — Kafka Retention Policies, Segment Lifecycle, Storage Capacity and Kubernetes Operational Governance.

---

**Verification boundary:** Publication proves only that chapter content exists. Live Kubernetes execution, physical segment observation, capacity measurement, security review and production readiness remain pending until independently verified.
