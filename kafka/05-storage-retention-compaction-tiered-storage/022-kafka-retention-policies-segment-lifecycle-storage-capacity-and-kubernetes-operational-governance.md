# Chapter 022 — Kafka Retention Policies, Segment Lifecycle, Storage Capacity and Kubernetes Operational Governance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 05 — Storage, Retention, Compaction and Tiered Storage  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 011–021, especially Chapter 021 storage internals  
**Audience:** Kafka SRE, DBRE, platform operations, compliance, data owners  
**Status:** Published · Live execution pending · Independent security review pending

> **Safety boundary:** Retention changes can permanently remove replayable records. Do not change production retention, delete topics, reset consumer offsets, or remove Kafka broker files/PVCs without data-owner approval, an impact assessment, and a tested recovery plan. This chapter performs only reversible configuration changes on a disposable topic and read-only infrastructure inspection.

## 1. Objectives and operational outcomes

After completing this chapter, you can:

1. Distinguish Kafka retention by time, size, segment rolling, log compaction and topic deletion.
2. Explain how active segments, cleanup cycles, log start offsets and timestamp semantics affect deletion.
3. Apply a governed KafkaTopic retention policy through Kubernetes and Strimzi.
4. Calculate storage and replay-window requirements for production consumers.
5. Identify retention drift, orphaned policies, capacity hot spots and unsafe settings.
6. Design approval, GitOps promotion, audit evidence, rollback and exception handling.
7. Diagnose consumer `OffsetOutOfRange`, unexpectedly persistent segments and rapid disk growth.
8. Validate policy behavior through deterministic, bounded Kubernetes-first labs.
9. Deliver SRE/DBRE runbooks, monitoring controls and a 100-point acceptance assessment.

## 2. Reference architecture

```text
  Data owner + compliance retention requirements
                     |
          GitOps retention policy PR
                     |
       review / policy gate / approval
                     |
          KafkaTopic Kubernetes CR
                     |
             Strimzi Topic Operator
                     |
             Kafka topic configs
                     |
     broker partition logs / segment rolling
                     |
        closed segments eligible for cleanup
                     |
          Kafka log start offset moves
                     |
  consumer replay horizon + storage utilization
                     |
        SRE alerts / audit / reconciliation
```

The Strimzi operator reconciles the desired KafkaTopic state. Kubernetes PVCs hold Kafka broker data, but topic retention should be controlled through supported Kafka topic configuration, not by manipulating filesystem contents.

## 3. Retention control plane and data plane

| Layer | Control | Operational responsibility |
|---|---|---|
| Business | Data classification, replay need, regulatory constraints | Data owner / governance |
| GitOps | Reviewed KafkaTopic YAML | Platform engineering |
| Kubernetes | KafkaTopic custom resource, RBAC, audit | Kubernetes platform |
| Strimzi | Topic reconciliation | Kafka operator team |
| Kafka | Effective topic config and segment cleanup | Kafka administrators |
| Storage | Broker PVC capacity, filesystem headroom, CSI | SRE/storage |
| Consumers | Offset progression, replay horizon, event age | Application owner |

A valid YAML manifest is not evidence that Kafka's effective configuration has converged. Verify both KafkaTopic status and Kafka broker topic configuration.

## 4. Time-based retention

`retention.ms` is the maximum age used to determine when log segments become eligible for deletion under the delete cleanup policy. Kafka evaluates retention periodically and generally deletes **whole eligible closed segments**, not individual records at an exact timestamp.

Key nuances:

- The active segment may retain older records until it rolls.
- `segment.ms` and `segment.bytes` influence how quickly segments close.
- The broker's cleanup cadence affects actual reclamation time.
- Timestamp type and record timestamps affect retention eligibility.
- A low-traffic partition may roll differently from a high-throughput partition.
- Retention is not a guaranteed legal-erasure deadline or an exact data-expiration SLA.

For strict deletion requirements, involve legal/compliance owners and evaluate supported deletion workflows, backups, caches, downstream replicas and verification—not merely Kafka retention.

## 5. Size-based retention

`retention.bytes` is a **per-partition** cap used for deletion eligibility, not a topic-wide cap. A topic with 12 partitions and `retention.bytes=1 GiB` has a nominal per-replica logical retention budget of approximately 12 GiB before replica multiplication and overhead. Actual storage can temporarily exceed this due to active segments and cleanup timing.

When both time and size limits apply, either condition can make eligible segments removable; the more restrictive practical constraint may dominate. Do not assume setting both means the system retains data for the longer of the two windows.

## 6. Segment lifecycle and index files

```text
append records -> active .log segment
                    |
      offset/time indexes maintained
                    |
       segment.bytes or segment.ms
                    |
              segment roll
                    |
         older closed segments
                    |
        retention eligibility check
                    |
        segment deletion and log start
              offset advancement
```

Kafka also maintains offset indexes, time indexes and transactional metadata where applicable. Segment rolling and cleanup are background broker operations; direct `rm`, `truncate`, filesystem moves, or ad hoc edits of these files are forbidden in this curriculum.

## 7. Retention, compaction and tiered storage are different

| Mechanism | Primary purpose | Guarantee boundary |
|---|---|---|
| `cleanup.policy=delete` | Delete old eligible log segments | Replay window limited by policy |
| `cleanup.policy=compact` | Retain latest record per key over time | Not a full chronological history |
| `cleanup.policy=delete,compact` | Apply both cleaning strategies | Requires careful workload-specific design |
| Tiered/remote log storage | Offload eligible historical segments | Requires supported broker/platform configuration |
| Topic deletion | Remove an entire topic and data | Destructive, separate approval |

Compaction is covered in Chapter 023; tiered storage in Chapter 024. Do not infer that remote storage is enabled merely because a retention setting exists.

## 8. Kubernetes-first prerequisites

Assume namespace `kafka-lab`, Strimzi cluster `sre-kafka`, CLI Pod `kafka-cli`, and bootstrap `sre-kafka-kafka-bootstrap:9092`. Confirm the installed Strimzi version serves `kafka.strimzi.io/v1`; adapt the manifest API version if necessary.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
kubectl get crd kafkatopics.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'
mkdir -p evidence-ch22
```

**Go/no-go:** do not proceed if the context is production, the cluster is not Ready, broker replicas are under-replicated, topic ownership is ambiguous, or the lab is not authorized.

## 9. Lab A — Capture baseline Kafka storage health

```bash
kubectl -n kafka-lab get kafka,kafkanodepool,pvc -o wide \
  | tee evidence-ch22/platform-baseline.txt
kubectl -n kafka-lab get pods -o wide \
  | tee evidence-ch22/pod-baseline.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch22/kraft-baseline.txt
```

Capture storage metrics from the actual installed monitoring stack: per-broker free bytes, disk write latency, partition replica distribution, log size and segment count. PVC requested capacity is **not** the same as available filesystem space.

**Acceptance:** baseline includes KRaft health, broker/PVC inventory, measured storage headroom source and an approved test context.

## 10. Lab B — Create a governed retention topic

Save `topic-ch22.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-retention-ch22
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
    app.kubernetes.io/part-of: kafka-sre-curriculum
  annotations:
    sre.example.com/owner: "kafka-lab"
    sre.example.com/change-ticket: "LAB-CH22"
    sre.example.com/data-classification: "synthetic"
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 3600000
    retention.bytes: 104857600
    segment.bytes: 1048576
    segment.ms: 60000
```

These small segment settings are **only** for the disposable lab. Replace the placeholder governance annotations with your organization's approved metadata convention in real GitOps workflows.

```bash
kubectl apply --dry-run=server -f topic-ch22.yaml
kubectl apply -f topic-ch22.yaml
kubectl -n kafka-lab get kafkatopic sre-retention-ch22 -o yaml \
  | tee evidence-ch22/topic-cr.yaml
```

**Acceptance:** operator reconciles a three-partition RF3 topic with min ISR2. Do not assume a custom annotation itself enforces policy.

## 11. Lab C — Verify effective broker topic configuration

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-retention-ch22 \
  | tee evidence-ch22/topic-partitions.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-retention-ch22 --describe \
  | tee evidence-ch22/effective-config.txt
```

Verify `retention.ms=3600000`, `retention.bytes=104857600`, `segment.bytes=1048576`, `segment.ms=60000` and `cleanup.policy=delete`. Note which settings are topic overrides versus inherited broker defaults.

**Acceptance:** no configuration drift and all three partitions have healthy leaders/ISR.

## 12. Lab D — Produce and consume deterministic records

```bash
printf '%s\n' \
  'tenant-A:event-2201' 'tenant-A:event-2202' \
  'tenant-B:event-2203' 'tenant-B:event-2204' \
  'tenant-C:event-2205' 'tenant-C:event-2206' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch22 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch22 \
  --group sre-retention-ch22-baseline \
  --from-beginning --max-messages 6 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch22/consumed-baseline.txt
```

**Acceptance:** six unique synthetic IDs consumed. A console consumer is not a production offset-commit correctness test.

## 13. Lab E — Inspect log start/end offsets and replay horizon

The Kafka consumer group CLI reports committed offsets and log-end offsets for a group:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-retention-ch22-baseline \
  | tee evidence-ch22/consumer-offsets.txt
```

For log start offsets, use a **verified Kafka client version** and its supported `kafka-get-offsets.sh` options (or AdminClient `ListOffsets` with `OffsetSpec.earliest()` and `OffsetSpec.latest()`). CLI flags vary by Kafka release; confirm with `--help` before running.

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-get-offsets.sh --help
```

**Acceptance:** document each partition's earliest available offset, latest offset, committed group offset and the difference. Do not confuse log-end offset with last stable offset when transactions are open.

## 14. Lab F — Segment rolling without forced deletion

After the initial writes, wait beyond the disposable topic's 60-second segment rolling interval, then append a new record:

```bash
sleep 70
printf '%s\n' 'tenant-A:event-2207' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch22 \
  --producer-property acks=all \
  --property parse.key=true --property key.separator=:
```

Observe log-segment metrics or, only when explicitly permitted, read-only file listings in the verified broker Pod and its actual Kafka data mount. No file modifications or broker restarts.

**Acceptance:** segment roll observed through valid broker evidence, or marked Pending if metrics/filesystem visibility is unavailable. **This lab does not prove retention deletion**, because the configured retention is one hour.

## 15. Lab G — Governed retention change and rollback

This lab modifies **only** the disposable topic. Use GitOps PR/review in environments where the topic is managed by GitOps; avoid competing direct `kubectl apply` changes against an active reconciler.

Proposed change: extend retention from 1 hour to 2 hours.

```bash
cp topic-ch22.yaml topic-ch22-2h.yaml
python3 - <<'PY'
from pathlib import Path
p=Path("topic-ch22-2h.yaml")
s=p.read_text()
assert "retention.ms: 3600000" in s
p.write_text(s.replace("retention.ms: 3600000","retention.ms: 7200000"))
PY
kubectl apply --dry-run=server -f topic-ch22-2h.yaml
kubectl apply -f topic-ch22-2h.yaml
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --entity-type topics --entity-name sre-retention-ch22 --describe
```

Restore the original 1-hour policy **only after confirming the lab has no retention-dependent consumer or replay requirement**:

```bash
kubectl apply -f topic-ch22.yaml
```

**Acceptance:** record before/after effective configs and approvals. **Rollback caveat:** increasing retention later cannot recover records already deleted; restoring a shorter policy may make older segments eligible for deletion.

## 16. Lab H — Time/size retention calculations

Suppose a topic ingests 20 MiB/s sustained, has 12 partitions, RF=3 and a 48-hour retention requirement.

```text
logical retained ≈ 20 MiB/s × 172800 s = 3,456,000 MiB
                 ≈ 3.30 TiB
replicated retained ≈ 3.30 TiB × 3 = 9.89 TiB
```

This excludes segment/index overhead, filesystem headroom, temporary reassignment capacity, burst ingestion, compaction and uneven partition placement.

If `retention.bytes=50 GiB` per partition, the nominal topic-wide logical size budget is `12 × 50 GiB = 600 GiB`, far smaller than the 48-hour ingest estimate. A size limit this low would likely truncate the intended replay window.

**Acceptance:** provide a spreadsheet or documented forecast with ingest rate, burst factor, RF, partitions, segment size, storage headroom and minimum replay window. Include a per-broker distribution analysis.

## 17. Lab I — Consumer retention risk tabletop

Scenario:

- Consumer group is paused for 36 hours.
- Topic retention is 24 hours.
- Producer traffic continues.
- Committed offset is older than log start.

Questions:

1. Can the consumer resume from its old offset?
2. Does `auto.offset.reset=earliest` restore deleted records?
3. Which upstream source or backup could rebuild missing data?
4. Who approves an offset reset, and how is business state reconciled?
5. Which event-age alert should have fired before the replay horizon closed?

**Expected:** deleted records cannot be recovered from that Kafka log by changing offset reset behavior. The consumer may receive OffsetOutOfRange and must follow an approved replay/reconciliation strategy.

## 18. Lab J — Kubernetes storage and retention risk mapping

```bash
kubectl -n kafka-lab get kafkanodepool -o yaml \
  > evidence-ch22/nodepools.yaml
kubectl -n kafka-lab get pvc -o wide \
  > evidence-ch22/pvcs.txt
kubectl get storageclass -o wide \
  > evidence-ch22/storageclasses.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch22/k8s-events.txt
```

Map broker data PVCs to Pods and StorageClasses using actual Pod volume references. Identify CSI capacity, zone constraints, volume expansion support and storage alerting.

**Acceptance:** a storage risk register covering days-to-full, PVC resize lead time, hot partition skew, retention-driven disk pressure and broker recovery headroom.

## 19. Lab K — GitOps policy-as-code review

Example policy input:

```yaml
apiVersion: sre.example.com/v1alpha1
kind: RetentionPolicyRequest
metadata:
  name: sre-retention-ch22-request
spec:
  topic: sre-retention-ch22
  owner: kafka-lab
  classification: synthetic
  minimumReplayHours: 2
  requestedRetentionHours: 2
  approvalTicket: LAB-CH22
```

This is an **illustrative governance document, not a Kubernetes CRD**. Do not `kubectl apply` it unless your organization has built and installed the corresponding controller/schema.

Suggested policy checks:

- Require topic owner, classification and change ticket.
- Compare retention request to consumer replay and regulatory requirements.
- Require approvals for any reduction of the effective replay window.
- Reject production topics with lab-only segment settings.
- Validate `retention.bytes` against ingest rate and partition count.
- Block simultaneous uncontrolled changes from GitOps and direct Kafka CLI.

**Acceptance:** reviewed policy rules and a sample approved/rejected request with rationale.

## 20. Lab L — Automated metadata and governance preflight

Save `verify-ch22.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
BS=sre-kafka-kafka-bootstrap:9092
TOPIC=sre-retention-ch22
BIN=/opt/kafka/bin

echo '[1/6] Cluster ready'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/6] Topic CR'
kubectl -n "$NS" get kafkatopic "$TOPIC" >/dev/null

echo '[3/6] Partition health'
desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
printf '%s\n' "$desc" | awk '
  /Partition:/ && /Replicas:/ && /Isr:/ {
    split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
    split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
    seen++; if(rf!=3 || isr!=3) bad++
  }
  END {if(seen!=3 || bad){print "FAIL: partitions/RF/ISR";exit 1}
       print "PASS: 3 partitions, RF=3, ISR=3"}'

echo '[4/6] Effective config'
config="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
  --bootstrap-server "$BS" --entity-type topics \
  --entity-name "$TOPIC" --describe)"
printf '%s\n' "$config"
for expected in \
  'retention.ms=3600000' \
  'retention.bytes=104857600' \
  'segment.bytes=1048576' \
  'segment.ms=60000' \
  'cleanup.policy=delete'; do
  if ! grep -Fq "$expected" <<<"$config"; then
    echo "FAIL: missing $expected" >&2
    exit 1
  fi
done

echo '[5/6] KRaft metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[6/6] Storage inventory'
kubectl -n "$NS" get pvc -o wide
echo 'PASS: read-only metadata/config checks; actual retention deletion, storage capacity and compliance require separate evidence'
```

```bash
chmod +x verify-ch22.sh
./verify-ch22.sh | tee evidence-ch22/acceptance.txt
```

**Run the preflight only after restoring the original one-hour retention policy from Lab G.** This script does not measure filesystem free space or prove record deletion, legal compliance, SLOs or operational approval.

## 21. Ten production incident scenarios

### 21.1 Retention shortened accidentally

**Signal:** log start offset advances unexpectedly; consumers report OffsetOutOfRange.

**Investigate:** KafkaTopic Git history, effective config, audit logs and affected groups.

**Recover:** stop further unsafe changes, restore approved policy for future data, rebuild lost records from independent sources if possible. Increasing retention cannot recover deleted records.

### 21.2 Retention size cap overrides replay requirement

**Signal:** data disappears sooner than `retention.ms` suggests.

**Investigate:** per-partition `retention.bytes`, ingest rate and segment sizes.

**Recover:** resize policy with owner approval and verify future replay horizon.

### 21.3 Segment rolling delayed

**Signal:** expired data persists in active segment.

**Investigate:** `segment.ms`, `segment.bytes`, low-traffic partitions, broker cleanup cycle.

**Recover:** tune future policy safely; no manual segment deletion.

### 21.4 Broker PVC near full

**Signal:** disk free bytes low, write errors, replica lag.

**Investigate:** log growth, retention effectiveness, hot partitions, CSI latency.

**Recover:** approved capacity expansion or ingest controls; preserve min ISR.

### 21.5 GitOps retention drift

**Signal:** KafkaTopic desired config differs from effective broker config.

**Investigate:** operator reconciliation errors, unauthorized CLI edits, admission policies.

**Recover:** restore one source of truth, fix reconciliation and document drift.

### 21.6 Consumer outage exceeds replay window

**Signal:** committed offset behind earliest available offset.

**Investigate:** outage duration, retention, consumer event age and upstream recovery.

**Recover:** business-approved replay/rebuild; never assume reset-to-earliest restores deleted records.

### 21.7 Legal retention conflict

**Signal:** business replay requirement differs from regulatory deletion constraint.

**Investigate:** data classification, backups, downstream copies and retention policy.

**Recover:** escalate to data governance/legal; do not treat Kafka TTL as an erasure guarantee.

### 21.8 Segment count explosion

**Signal:** open-file growth, slower broker recovery.

**Investigate:** lab-sized segment settings applied to production, partition count.

**Recover:** tune with benchmarking and change review.

### 21.9 Hot partition drives uneven storage

**Signal:** one broker approaches full despite healthy cluster-wide capacity.

**Investigate:** replica placement, key skew, leader distribution.

**Recover:** approved balancing or application partition-key redesign.

### 21.10 Topic deletion mistaken for retention

**Signal:** entire topic unavailable.

**Investigate:** Kubernetes audit, Topic Operator events, GitOps deletions.

**Recover:** restore topic/config and data from upstream/backup where possible; prevent uncontrolled deletion with RBAC/admission policy.

## 22. Troubleshooting matrix

| Symptom | Kafka evidence | Kubernetes evidence | Avoid |
|---|---|---|---|
| Replay records missing | Log start, effective retention | KafkaTopic change/audit | Blind offset reset |
| Disk remains high | Segment roll, cleanup policy | PVC free bytes, CSI metrics | Manual rm |
| Config drift | Topic config vs CR | Operator events | Competing CLI edits |
| Segment count high | Segment settings, topic count | Broker file limits | Tiny production segments |
| Disk skew | Partition placement | PVC per-broker usage | Unplanned reassignment |
| Consumer lag > retention | Event age, offsets | Consumer Pod outage | Assume Kafka holds forever |
| PVC full | Broker I/O errors | Storage alerts | Lower min ISR |
| Unexpected topic loss | Topic metadata | CR deletion/audit | Assume retention alone caused it |

## 23. Six production runbooks

### Runbook A — Governed retention change

1. Identify topic owner, classification, consumers and legal requirements.
2. Snapshot effective topic config, earliest/latest offsets and storage trend.
3. Calculate replay-window and capacity impact.
4. Require change ticket and approvals for any retention reduction.
5. Apply via GitOps/Strimzi and verify reconciliation.
6. Monitor consumer event age, log start offset and storage for the agreed window.

### Runbook B — Consumer replay horizon incident

1. Capture group offsets and earliest retained offsets by partition.
2. Identify missing time/offset range and affected business processes.
3. Stop unsafe offset manipulation and preserve evidence.
4. Determine independent upstream/backfill availability.
5. Execute approved replay/reconciliation, including deduplication.
6. Extend monitoring and prevention controls.

### Runbook C — Disk pressure from retention

1. Identify affected brokers, PVCs, topics and growth rates.
2. Confirm effective retention and segment lifecycle.
3. Preserve ISR and producer durability.
4. Coordinate approved capacity, ingest or retention action.
5. Verify headroom and replay guarantees after recovery.
6. Record capacity forecast and alert adjustments.

### Runbook D — Retention configuration drift

1. Compare GitOps manifest, KafkaTopic CR and broker effective config.
2. Review operator status, events and audit logs.
3. Identify conflicting controllers or direct CLI changes.
4. Restore approved desired state and reconcile.
5. Verify topic and consumer behavior.
6. Update policy-as-code and RBAC controls.

### Runbook E — Data deletion/compliance escalation

1. Identify legal hold, classification and required deletion scope.
2. Map Kafka topics, replicas, backups and downstream consumers.
3. Confirm Kafka retention is insufficient for precise erasure.
4. Obtain governance/legal-approved deletion strategy.
5. Execute supported workflows with rollback limitations documented.
6. Preserve evidence of verification and outstanding copies.

### Runbook F — Retention incident command and postmortem

1. Declare impact, owner and severity.
2. Freeze unsafe policy changes; capture audit/config evidence.
3. Estimate lost replay horizon and business impact.
4. Coordinate recovery with application, platform and governance teams.
5. Verify offsets, event reconciliation, storage and SLO recovery.
6. Publish corrective actions with accountable owners and deadlines.

## 24. Operational monitoring and SLOs

Track:

- Earliest retained offset versus committed offset for every critical consumer group.
- Oldest unprocessed event age relative to guaranteed replay window.
- Topic effective retention policy and changes over time.
- Broker disk used/free bytes, projected days-to-full, segment count and cleanup activity.
- Consumer OffsetOutOfRange and failed replay events.
- Topic Operator reconciliation failures and configuration drift.
- Kubernetes PVC provisioning, attach/resize errors and broker recovery.
- Audit trail for retention reductions, topic deletions and manual CLI changes.

**Suggested governance control:** page before projected consumer catch-up time exceeds remaining replay window. Thresholds must be based on measured ingest, processing throughput, retention and business recovery requirements.

## 25. Evidence manifest and acceptance checklist

```text
evidence-ch22/
  change-ticket-and-owner-approval.md
  platform-baseline.txt
  kraft-baseline.txt
  topic-cr.yaml
  topic-partitions.txt
  effective-config.txt
  consumed-baseline.txt
  consumer-offsets.txt
  segment-observation.md
  retention-change-before-after.md
  replay-horizon-risk.md
  storage-forecast.md
  governance-policy-review.md
  acceptance.txt
  security-review.md
  assessor-signoff.md
```

- [ ] Lab context and data-owner approval captured.
- [ ] Kafka KRaft, broker/PVC and topic health verified.
- [ ] Time and size retention semantics documented correctly.
- [ ] Topic creation and effective configuration verified.
- [ ] Deterministic records produced/consumed and offsets captured.
- [ ] Segment roll evidence collected or explicitly marked Pending.
- [ ] Lab-only retention change and restoration verified.
- [ ] Replay horizon and capacity forecast reviewed.
- [ ] GitOps governance, RBAC and security controls assessed.
- [ ] Automated preflight executed and evidence preserved.
- [ ] Independent technical and security review completed.

## 26. Assessment — 100 points

| Domain | Points |
|---|---:|
| Explain retention, segment rolling and cleanup timing | 10 |
| Explain size limits and replay horizon | 10 |
| Inventory Kubernetes/Strimzi storage health | 10 |
| Provision governed KafkaTopic safely | 10 |
| Validate effective broker topic config | 10 |
| Produce/consume and inspect offsets | 10 |
| Demonstrate segment behavior and change governance | 10 |
| Capacity and replay-window calculations | 10 |
| Execute preflight and analyze evidence | 10 |
| Incident runbooks, security and operational handoff | 10 |
| **Total** | **100** |

**Pass:** at least 85/100, no critical safety violations, and independent evidence for executed labs. Unperformed tests remain Pending; publication alone never means acceptance.

## 27. Cleanup and next chapter

After retaining sanitized evidence and confirming the topic is disposable:

```bash
kubectl -n kafka-lab delete kafkatopic sre-retention-ch22 --ignore-not-found
```

This permanently removes the test topic and its records. Do not delete Kafka broker/controller PVCs, KafkaNodePools or the cluster.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Kubernetes StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/).

**Next:** Chapter 023 — Kafka Log Compaction, Tombstones, Keyed State Recovery and Kubernetes Reliability.

---

**Verification boundary:** GitHub publication verifies the document exists; it does not prove live retention cleanup, storage measurements, policy enforcement, security approval or production readiness.
