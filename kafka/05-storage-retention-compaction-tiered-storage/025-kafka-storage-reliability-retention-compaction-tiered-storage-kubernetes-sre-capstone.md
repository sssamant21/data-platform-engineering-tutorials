# Chapter 025 — Kafka Storage Reliability, Retention, Compaction and Tiered Storage Kubernetes SRE Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 05 — Storage, Retention, Compaction and Tiered Storage (5/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–024; especially storage, retention, compaction and tiered-storage Chapters 021–024  
**Audience:** Kafka administrators, SREs, DBREs, Kubernetes platform engineers, data owners and security reviewers  
**Publication status:** Published · **Live lab status:** Pending · **Security review:** Pending

> **Safety and change authority:** This is an **isolated-lab acceptance capstone**, not authorization to test production fault tolerance. Never manually delete Kafka segments, broker/controller PVCs, KRaft metadata, or remote-storage objects. Never weaken min ISR, disable TLS/authentication, shorten business retention, force unclean leader election or run disk-fill experiments in production. Any disruptive game day requires written approval, a disposable cluster, recovery owner, abort criteria and captured baseline.

## 1. Capstone mission

Prove that a Kubernetes-first Kafka platform can:

1. Preserve replicated writes while broker and storage components operate within defined failure budgets.
2. Enforce a governed delete-retention policy with measurable consumer replay headroom.
3. Reconstruct keyed application state correctly from a compacted topic, including real null-value tombstones.
4. Detect storage exhaustion trends, replica lag, log-cleaner backlog and KafkaTopic drift before business impact.
5. Recover a disposable consumer workload and verify event IDs, offsets and state checksums.
6. Evaluate tiered-storage compatibility, IAM, remote reads and DR without claiming support where no tested plugin exists.
7. Produce a repeatable evidence bundle and a 100-point independent reliability assessment.

**Acceptance boundary:** Publishing the capstone does not establish a passed lab. Remote-storage integration is an optional conditional gate; **production tiered-storage readiness cannot be claimed without executing it**.

## 2. Architecture and failure domains

```text
   Synthetic producer Job / approved client image
                     |
        Kafka bootstrap Service (TLS if configured)
                     |
     Strimzi-managed KRaft Kafka cluster
        |             |             |
    broker A       broker B       broker C
      PVC A          PVC B          PVC C
        |             |             |
        +-- replicated topic partitions --+
                     |
       +-------------+-------------+
       |                           |
  delete-retention topic     compacted state topic
       |                           |
  replay consumer              state consumer
       |                           |
  offset/age evidence         keyed-state checksum
       |                           |
       +------ SRE metrics --------+
                     |
        alerting / incident command
                     |
     optional supported remote-log plugin
                     |
       isolated encrypted object storage
```

KRaft controller quorum, broker replication, PVC placement and remote object-store availability are distinct failure domains. Remote log storage is not a substitute for controller metadata recovery or an independent DR strategy.

## 3. Reliability acceptance contract

| Gate | Target | Evidence |
|---|---|---|
| Kafka control plane | Kafka Ready, KRaft quorum healthy | Kafka CR + quorum status |
| Topic durability | RF3, min ISR2, all ISR present at baseline | Topic config and partition describe |
| Event integrity | Zero unaccounted missing synthetic event IDs | Producer manifest and consumer reconciliation |
| Consumer replay | Committed offsets within retained log window | Per-partition earliest/end/committed offsets |
| Retention policy | Approved effective topic config | GitOps YAML, KafkaTopic status and broker config |
| Compacted state | Expected final key/value map, deletion applied | Verified real tombstone + state checksum |
| Storage headroom | Positive forecasted headroom through recovery window | Filesystem metrics and capacity model |
| Alerting | Actionable disk/ISR/lag/cleaner alerts | Rules, dashboard screenshots and alert tests |
| Operational recovery | RTO/RPO measured against locally agreed objectives | Timed game-day evidence |
| Tiered storage | Compatible plugin + offload/read checksums if in scope | Plugin provenance and integration evidence |
| Security | Approved identity, TLS, RBAC, object-store controls | Security review and audit |
| Governance | Data owner and change approver signoff | Tickets, rollback and evidence manifest |

**No invented SLOs:** define concrete local thresholds before the test. A baseline cannot pass simply because a script exits zero.

## 4. Required lab environment

Shared foundation:

- Kubernetes namespace: `kafka-lab`.
- Kafka CR: `sre-kafka`.
- Kafka CLI Pod: `kafka-cli`.
- Bootstrap Service: `sre-kafka-kafka-bootstrap:9092` for the isolated foundation; production-like clusters must use their configured TLS/authentication listeners.
- Three healthy brokers and three-replica topics.
- Supported Strimzi KafkaTopic API version, commonly `kafka.strimzi.io/v1` when served.
- StorageClass with healthy PVCs, storage metrics and enough free capacity for bounded tests.
- Approved image for any real Java producer/consumer used in advanced gates.

Before starting, confirm the current context is a **disposable** cluster and record the approver. Namespace isolation alone does not make destructive tests safe on a shared cluster.

## 5. Lab 01 — Establish the change, scope and rollback plan

Create `evidence-ch25/change-approval.md` containing:

```text
Change ticket:
Cluster/context:
Namespace:
Data owner:
Incident commander:
Recovery operator:
Allowed synthetic topics:
Allowed operations:
Forbidden operations:
RPO objective:
RTO objective:
Maximum event age:
Minimum free disk / forecast headroom:
Stop/abort criteria:
Rollback decision owner:
Approvals:
```

**Acceptance:** all fields populated, scope approved, no production/shared cluster dependencies.

## 6. Lab 02 — Kubernetes/KRaft baseline

```bash
mkdir -p evidence-ch25
kubectl config current-context | tee evidence-ch25/context.txt
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide \
  | tee evidence-ch25/platform-baseline.txt
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch25/kraft-quorum.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch25/kubernetes-events.txt
```

**Acceptance:** no controller quorum incident, Kafka Ready, broker and PVC inventory captured. Collect actual filesystem free bytes from monitoring; PVC requested capacity is not free space.

## 7. Lab 03 — Provision both acceptance topics

Save `topics-ch25.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-retention-ch25
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
  annotations:
    sre.example.com/owner: "kafka-lab"
    sre.example.com/change-ticket: "LAB-CH25"
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
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-compaction-ch25
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
  annotations:
    sre.example.com/owner: "kafka-lab"
    sre.example.com/change-ticket: "LAB-CH25"
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: compact
    min.cleanable.dirty.ratio: 0.1
    delete.retention.ms: 86400000
    segment.bytes: 1048576
    segment.ms: 60000
```

Small segment settings are **lab-only**. Never copy these into production topic defaults.

```bash
kubectl apply --dry-run=server -f topics-ch25.yaml
kubectl apply -f topics-ch25.yaml
kubectl -n kafka-lab get kafkatopic \
  sre-retention-ch25 sre-compaction-ch25 -o yaml \
  > evidence-ch25/topic-crs.yaml
```

**Acceptance:** both KafkaTopic CRs reconciled; effective broker settings verified in Lab 04.

## 8. Lab 04 — Validate RF, ISR and effective policies

```bash
for topic in sre-retention-ch25 sre-compaction-ch25; do
  kubectl -n kafka-lab exec kafka-cli -- \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
    --describe --topic "$topic" \
    | tee "evidence-ch25/${topic}-partitions.txt"
  kubectl -n kafka-lab exec kafka-cli -- \
    /opt/kafka/bin/kafka-configs.sh \
    --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
    --entity-type topics --entity-name "$topic" --describe \
    | tee "evidence-ch25/${topic}-config.txt"
done
```

**Acceptance:** exactly three partitions/topic, RF3, ISR3, min ISR2, delete retention on first topic and compaction on second. Do not interpret KafkaTopic YAML alone as effective configuration.

## 9. Lab 05 — Produce a bounded synthetic event ledger

Save a manifest of expected IDs:

```bash
printf '%s\n' event-2501 event-2502 event-2503 event-2504 \
  event-2505 event-2506 event-2507 event-2508 \
  | tee evidence-ch25/expected-event-ids.txt
```

Produce deterministic keys and values:

```bash
printf '%s\n' \
  'tenant-A:event-2501' 'tenant-B:event-2502' \
  'tenant-C:event-2503' 'tenant-A:event-2504' \
  'tenant-B:event-2505' 'tenant-C:event-2506' \
  'tenant-A:event-2507' 'tenant-B:event-2508' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch25 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

A successful CLI exit alone does not prove every event was durably acknowledged. Use an approved application producer with callback/future results and a signed ledger for rigorous loss accounting.

**Acceptance:** eight expected IDs in producer ledger; Kafka acknowledgments independently verified when available.

## 10. Lab 06 — Consume and reconcile the ledger

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch25 --from-beginning \
  --group sre-retention-ch25-reconcile \
  --max-messages 8 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch25/consumed-ledger.txt
```

**Reconciliation procedure:** parse the actual value field using the confirmed CLI output format, compare its event IDs as a **multiset** against the expected ledger, fail on missing or unexpected IDs, and record duplicates separately. Partition interleaving is nondeterministic. Never use simple line count as proof of exactly-once effects.

**Acceptance:** zero missing IDs and no unexpected IDs, with raw output and parser version preserved.

## 11. Lab 07 — Observe retention and segment lifecycle

```bash
sleep 70
printf '%s\n' 'tenant-C:event-2509' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-retention-ch25 \
  --producer-property acks=all \
  --property parse.key=true --property key.separator=:
```

Capture segment metrics, topic offsets and broker disk use. The one-hour `retention.ms` means this lab **does not** prove expiration/deletion after 70 seconds. Active segments, cleanup cadence and timestamp semantics affect physical cleanup.

**Acceptance:** segment rolling observed via permitted read-only metrics or filesystem listing; otherwise Pending. Never force cleanup with filesystem deletion.

## 12. Lab 08 — Verify consumer replay horizon

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-retention-ch25-reconcile \
  | tee evidence-ch25/consumer-offsets.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-get-offsets.sh --help \
  | tee evidence-ch25/get-offsets-help.txt
```

Use the installed CLI's supported earliest/latest offset options or AdminClient `ListOffsets` to record per-partition log start/end. Compare with committed group offsets and event-age monitoring. A committed offset below log start means the old records are no longer replayable from that log.

**Acceptance:** documented per-partition replay margin and owner-approved alert thresholds.

## 13. Lab 09 — Compacted-topic keyed updates

```bash
printf '%s\n' \
  'customer-A:status=bronze' \
  'customer-B:status=silver' \
  'customer-A:status=gold' \
  'customer-C:status=active' \
  'customer-B:status=platinum' \
  'customer-A:status=diamond' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-compaction-ch25 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

**Acceptance:** updates use stable non-null keys; expected latest state is A=diamond, B=platinum, C=active before tombstone.

## 14. Lab 10 — Real tombstone and state reconstruction

A tombstone is a Kafka record with **non-null key and actual null value**, not a text string `"null"`. Reuse the reviewed Java `TombstoneProducer` from [Chapter 023](023-kafka-log-compaction-tombstones-keyed-state-recovery-and-kubernetes-reliability.md), built with pinned Kafka client dependencies in an approved Kubernetes Job image.

Send a tombstone for `customer-B`. Then consume from earliest retained offsets using an approved client that:

1. Reads all partitions until a captured end-offset snapshot.
2. Applies keyed records in partition offset order.
3. Removes keys on actual null values.
4. Builds state from an **empty** state store.
5. Persists state/checkpoints consistently and reconciles to the expected map.

Expected final state:

```text
customer-A = status=diamond
customer-B = absent
customer-C = status=active
```

**Acceptance:** a verified null-value record, state checksum and no stale B entry. If no approved build/runtime exists, mark this gate **Pending**, not Passed. Kafka console producer output is not proof of a null-value tombstone.

## 15. Lab 11 — Log cleaner and storage observability

Collect actual installed metrics for:

- Log cleaner backlog/dirty ratio and cleaning throughput.
- Segment counts and local log size.
- Per-broker PVC filesystem available bytes, IOPS, latency and projected days-to-full.
- Under-replicated/offline partitions and ISR transitions.
- Consumer offset lag, event age and replay-window exhaustion.
- Strimzi reconciliation failures and topic config drift.

**Acceptance:** dashboards and alert rules mapped to concrete metric sources, thresholds, owners and paging routes. Do not invent Prometheus metric names or claim an alert fired without evidence.

## 16. Lab 12 — Capacity and retention forecast

Assume 12 MiB/s sustained ingest, RF3 and 24-hour delete retention:

```text
logical bytes ≈ 12 MiB/s × 86400 = 1,036,800 MiB ≈ 1012.5 GiB
replicated bytes ≈ 3037.5 GiB ≈ 2.97 TiB
```

This excludes indexes, hot partitions, burst traffic, segment boundaries, filesystem overhead, replication recovery headroom and compaction dirty-data amplification.

For compacted topics also forecast distinct-key cardinality, update churn, cleaner I/O, tombstones and state bootstrap duration. For tiered storage add object-store request charges, remote-read egress, KMS and metadata overhead.

**Acceptance:** per-broker capacity model and growth forecast; no global percentage-only conclusion.

## 17. Lab 13 — Controlled consumer Pod restart game day

**Prerequisite:** an approved consumer Deployment with verified image, Kafka credentials, graceful SIGTERM and recovery semantics. Do not invent or deploy a placeholder consumer image.

1. Capture consumer group assignments, committed offsets and state checksum.
2. Confirm readiness and recovery gates.
3. Restart **only the disposable consumer Deployment** through an approved rollout.
4. Observe rebalances, offset recovery, Pod readiness and processing.
5. Reconcile event IDs and keyed state after recovery.
6. Record actual RTO and compare with the pre-agreed objective.

```bash
# Replace only after validating that the Deployment is lab-owned.
kubectl -n kafka-lab rollout restart deployment/<VERIFIED_LAB_CONSUMER_DEPLOYMENT>
kubectl -n kafka-lab rollout status deployment/<VERIFIED_LAB_CONSUMER_DEPLOYMENT> --timeout=300s
```

**Acceptance:** no unaccounted loss, correct final state, measured recovery and no restart loop. Without a real lab consumer Deployment, this remains Pending.

## 18. Lab 14 — Disk-pressure and broker PVC failure tabletop

Simulate **on paper only**:

- One broker's data PVC reaches critical headroom.
- CSI latency increases and replica lag rises.
- A zonal volume cannot attach to a replacement node.
- A storage expansion request remains Pending.

Prepare a decision tree for broker health, ISR, free-space forecast, storage expansion and application backpressure. Explicitly prohibit manual segment deletion, blind PVC replacement, disabling min ISR and unapproved topic retention reduction.

**Acceptance:** an incident commander can identify no-go criteria and safe recovery owners.

## 19. Lab 15 — Retention governance and GitOps drift drill

1. Compare GitOps `KafkaTopic` desired settings, Kubernetes CR and effective Kafka config.
2. Propose a **non-destructive** extension of retention for the disposable delete topic.
3. Require data-owner and platform approval in the test change record.
4. Validate the proposed YAML with server-side dry run.
5. Apply through the lab's authoritative GitOps workflow; avoid competing controllers.
6. Confirm reconciliation, monitor storage impact and restore the approved baseline.

**Acceptance:** before/after effective config, approvals, rollback caveats and audit evidence. Restoring a shorter policy may make old records eligible for deletion; never imply rollback resurrects deleted data.

## 20. Lab 16 — Tiered-storage compatibility and conditional integration

Use [Chapter 024](024-kafka-tiered-storage-remote-log-lifecycle-object-storage-security-and-kubernetes-disaster-recovery.md) to establish the exact Kafka/Strimzi/remote-manager compatibility matrix.

**Required tabletop:** plugin provenance, object-store IAM, workload identity, KMS, private endpoint, cost forecast, remote metadata, RPO/RTO and cross-region recovery limitations.

**Conditional live integration:** only with a supported plugin, approved bucket and disposable cluster:

1. Offload eligible closed segments.
2. Verify remote object and metadata integrity.
3. Wait for supported local cleanup, without manually deleting files.
4. Read retained older offsets from remote storage.
5. Compare checksums and p95/p99 read latency.
6. Test authorized IAM-denial recovery in the isolated cloud sandbox.

**Acceptance:** record compatibility and either real remote-read evidence or **Not Executed**. A design review alone cannot certify tiered storage.

## 21. Lab 17 — Automated baseline acceptance

Save `verify-ch25.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/7] Cluster readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s

echo '[2/7] KRaft metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[3/7] Broker/PVC inventory'
kubectl -n "$NS" get kafkanodepool
kubectl -n "$NS" get pvc -o wide

echo '[4/7] Topic CRs'
kubectl -n "$NS" get kafkatopic sre-retention-ch25 sre-compaction-ch25

check_topic() {
  local topic="$1" policy="$2" extra="$3"
  local desc config
  desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
    --bootstrap-server "$BS" --describe --topic "$topic")"
  printf '%s\n' "$desc"
  printf '%s\n' "$desc" | awk '
    /Partition:/ && /Replicas:/ && /Isr:/ {
      split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
      split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
      seen++; if(rf!=3 || isr!=3) bad++
    }
    END {if(seen!=3 || bad){print "FAIL: RF/ISR/partitions";exit 1}
         print "PASS: 3 partitions, RF3 ISR3"}'
  config="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
    --bootstrap-server "$BS" --entity-type topics \
    --entity-name "$topic" --describe)"
  printf '%s\n' "$config"
  for expected in "cleanup.policy=$policy" "$extra" 'min.insync.replicas=2'; do
    if ! grep -Fq "$expected" <<<"$config"; then
      echo "FAIL: $topic missing $expected" >&2
      return 1
    fi
  done
}

echo '[5/7] Delete-retention topic health and config'
check_topic sre-retention-ch25 delete 'retention.ms=3600000'

echo '[6/7] Compaction topic health and config'
check_topic sre-compaction-ch25 compact 'delete.retention.ms=86400000'

echo '[7/7] Final topic health'
kubectl -n "$NS" get kafkatopic sre-retention-ch25 sre-compaction-ch25

echo 'PASS: metadata baseline only.'
echo 'NOT PROVEN: event reconciliation, real tombstones, cleaner progress, filesystem headroom, Pod recovery, remote reads, security or RPO/RTO.'
```

```bash
chmod +x verify-ch25.sh
./verify-ch25.sh | tee evidence-ch25/baseline-acceptance.txt
```

**Validation limitations:** this script is intentionally read-only. It assumes three brokers with RF3/ISR3. It cannot replace event reconciliation, state reconstruction, disk metrics, IAM validation or recovery testing. CLI output formatting must be checked against the installed Kafka version.

## 22. Lab 18 — Evidence reconciliation and independent review

Produce a signed evidence manifest:

```text
evidence-ch25/
  change-approval.md
  context.txt
  platform-baseline.txt
  kraft-quorum.txt
  topic-crs.yaml
  sre-retention-ch25-partitions.txt
  sre-retention-ch25-config.txt
  sre-compaction-ch25-partitions.txt
  sre-compaction-ch25-config.txt
  expected-event-ids.txt
  consumed-ledger.txt
  event-reconciliation.json
  consumer-offsets.txt
  segment-observation.md
  tombstone-verification.md
  reconstructed-state.json
  cleaner-storage-metrics.md
  capacity-forecast.md
  consumer-restart-rto.md
  disk-pressure-tabletop.md
  retention-gitops-review.md
  tiered-storage-compatibility.md
  remote-read-evidence.md
  baseline-acceptance.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

For each gate include timestamp, Kafka/Strimzi versions, command, expected result, actual result, evidence path, reviewer, Pass/Fail/Pending and corrective-action owner.

## 23. Twelve production failure scenarios

### 23.1 Broker PVC fills

**Signals:** write failures, disk free bytes critical, ISR shrink.  
**Action:** preserve data, coordinate approved expansion or ingest control; no filesystem deletion.

### 23.2 Storage I/O throttling causes replica lag

**Signals:** producer p99 rises, under-replicated partitions.  
**Action:** correlate CSI metrics and Kafka replication; restore throughput before disruptive operations.

### 23.3 Retention removes data before consumer replay

**Signals:** OffsetOutOfRange, committed offset behind log start.  
**Action:** recover from independent upstream/backups; offset reset cannot restore deleted records.

### 23.4 Retention fails to free space promptly

**Signals:** high disk use after config update.  
**Action:** inspect active segment, segment rolling, cleanup cycle and effective config.

### 23.5 Compaction backlog grows

**Signals:** dirty ratio and segment count increase.  
**Action:** examine cleaner I/O, segment eligibility and capacity.

### 23.6 Tombstone is literal text

**Signals:** deleted key remains with value `"null"`.  
**Action:** verify serialized null and repair state through approved replay.

### 23.7 State consumer restarts with stale checkpoint

**Signals:** divergence after Pod rollout.  
**Action:** rebuild from empty state/consistent snapshot and reconcile.

### 23.8 Partitioning change breaks keyed ordering

**Signals:** one key's updates across partitions.  
**Action:** stop unsafe rollout and design migration with stable routing.

### 23.9 Strimzi reconciliation conflict

**Signals:** KafkaTopic desired state differs from effective broker config.  
**Action:** restore single GitOps source of truth and audit manual changes.

### 23.10 Remote object-store access denied

**Signals:** remote-copy/read errors, IAM denials.  
**Action:** restore least-privilege identity and validate KMS/network; never expose bucket publicly.

### 23.11 Remote history missing after bucket lifecycle deletion

**Signals:** remote metadata references absent objects.  
**Action:** stop unmanaged lifecycle deletion; assess independent backup and recovery.

### 23.12 Regional outage with incomplete metadata recovery

**Signals:** remote segments exist but Kafka cluster cannot recover.  
**Action:** execute supported DR workflow with metadata, identity and consumer-state recovery.

## 24. Troubleshooting matrix

| Symptom | Kafka check | Kubernetes/cloud check | Avoid |
|---|---|---|---|
| Disk pressure | Log size, segment roll, ISR | PVC free bytes, CSI | Manual segment rm |
| Replay gap | Earliest/committed offsets | Consumer Pod history | Blind offset reset |
| Cleaner lag | Dirty ratio, cleaner metrics | Broker IOPS | Delete .log files |
| Stale keyed state | Real tombstone, key routing | Consumer checkpoint/PVC | Ignore null semantics |
| Replica degradation | Under-replicated partitions | Node/CSI latency | Lower min ISR |
| Config drift | Effective topic config | Strimzi events/GitOps | Competing CLI changes |
| Remote read errors | Remote metadata, copy status | IAM/KMS/object-store logs | Public bucket access |
| Slow recovery | Consumer replay rate | Pod scheduling and storage | Bypass readiness |

## 25. Eight production runbooks

### Runbook A — Kafka disk pressure

1. Declare severity, owner and affected broker/PVC.
2. Capture filesystem free bytes, growth rate, ISR and producer errors.
3. Stop unsafe retention or filesystem changes.
4. Coordinate approved storage expansion, traffic control or balancing.
5. Verify write recovery, ISR and projected headroom.
6. Publish incident timeline and prevention actions.

### Runbook B — Retention and replay loss

1. Identify affected topics/groups and earliest available offsets.
2. Determine missing records and business impact.
3. Preserve audit and effective configuration evidence.
4. Recover from upstream/backups through approved reconciliation.
5. Verify event IDs and downstream state.
6. Fix alerting and retention governance.

### Runbook C — Log cleaner backlog

1. Capture cleaner metrics, segment count and disk pressure.
2. Validate cleanup policy and dirty ratio.
3. Identify broker I/O contention and key churn.
4. Restore cleaner capacity through supported changes.
5. Verify progress without promising fixed completion time.
6. Update capacity forecast and alerts.

### Runbook D — Tombstone correctness

1. Inspect actual record nullability and key serialization.
2. Verify stable partition routing and producer acknowledgments.
3. Capture consumer state/checkpoint evidence.
4. Rebuild/reconcile deleted keys from authoritative source.
5. Validate no stale keys remain.
6. Add automated tombstone regression tests.

### Runbook E — Consumer state rebuild

1. Quiesce or isolate affected state consumer.
2. Preserve offsets, state-store checksums and incident evidence.
3. Rebuild from earliest available compacted log or approved snapshot.
4. Apply actual null tombstones and all partition updates.
5. Reconcile against authoritative state.
6. Restore service only after readiness and RTO verification.

### Runbook F — PVC provisioning and recovery

1. Identify broker Pod/PVC/PV and StorageClass.
2. Inspect CSI errors, zone affinity and node placement.
3. Preserve PVC identity and replica durability.
4. Apply supported Strimzi/Kubernetes recovery.
5. Verify broker readiness, ISR and storage headroom.
6. Record root cause and remediation.

### Runbook G — Remote-log storage incident

1. Verify plugin version, remote metadata and Kafka ISR.
2. Inspect object-store IAM/KMS, throttling and connectivity.
3. Protect local retention while offload is impaired.
4. Restore supported remote manager functionality.
5. Verify remote-read checksums and latency.
6. Review cloud cost and security alerts.

### Runbook H — DR exercise and acceptance

1. Agree scenario, RPO/RTO and isolation boundaries.
2. Verify metadata, topic config, identities and backup dependencies.
3. Execute supported recovery in isolated infrastructure.
4. Reconcile synthetic event ledger and state.
5. Measure actual recovery duration and data gap.
6. Publish signed acceptance or remediation plan.

## 26. SLOs, alerts and error-budget policy

Use measured workload and business objectives, not universal magic thresholds. Suggested SLIs:

- Producer acknowledged-event reconciliation rate.
- Kafka partition unavailability and ISR health.
- Consumer oldest-event age / remaining retention horizon.
- Broker filesystem days-to-full and storage latency.
- Log cleaner backlog age and dirty-segment pressure.
- State bootstrap duration and checksum divergence.
- Remote-copy lag and remote-read success/p99 when enabled.
- Recovery time and unrecoverable data gap per game day.

**Example policy:** page before projected consumer catch-up time exceeds remaining replay horizon, and halt change rollout if ISR degrades or any unexpected data-integrity mismatch occurs.

## 27. Acceptance assessment — 100 points

| Domain | Points | Evidence gate |
|---|---:|---|
| Change approval, safety and rollback | 10 | Signed change record |
| KRaft, Strimzi, broker/PVC health | 10 | Live metadata/metrics |
| RF3/minISR2 and topic policy validation | 10 | Effective Kafka config |
| Producer/consumer event reconciliation | 10 | Actual ID multiset |
| Retention, segment and replay-horizon validation | 10 | Offsets + metrics |
| Real tombstone and keyed-state rebuild | 10 | Live client evidence |
| Cleaner and storage capacity/alerting | 10 | Metrics + forecast |
| Consumer recovery and measured RTO | 10 | Live Pod restart |
| Tiered storage/DR design and conditional testing | 10 | Compatibility + execution status |
| Runbooks, security and independent signoff | 10 | Assessor record |
| **Total** | **100** | |

**Part 05 capstone pass:** ≥85/100, no critical safety or data-integrity failures, and live evidence for the event-reconciliation, tombstone/state-rebuild and consumer-recovery gates. If tiered storage is in production scope, remote offload/read and recovery must be executed and passed; a tabletop alone is insufficient. If any critical gate is Pending, the capstone is **Not Yet Accepted** regardless of score.

## 28. Cleanup, operational handoff and next part

After approval and evidence preservation:

```bash
kubectl -n kafka-lab delete kafkatopic \
  sre-retention-ch25 sre-compaction-ch25 --ignore-not-found
```

Topic deletion is destructive and must only target the approved disposable topics. Do **not** delete Kafka broker/controller PVCs, PVs, KafkaNodePools, KRaft metadata or remote object-store data manually.

**Handoff package:** change approval, version matrix, KafkaTopic manifests, event ledger, offset/replay evidence, state checksums, capacity forecast, alert inventory, runbooks, RPO/RTO results, security signoff and unresolved risks.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Apache Kafka KIP-405](https://cwiki.apache.org/confluence/display/KAFKA/KIP-405%3A+Kafka+Tiered+Storage).

**Next:** Chapter 026 — Kafka Networking Architecture, Kubernetes Services, Listeners and Broker Connectivity Troubleshooting. This begins **Part 06 — Networking, Security, TLS, SASL and ACLs**.

---

**Verification boundary:** Chapter publication is complete; live labs, game-day results, tiered-storage integration and independent security review remain Pending until evidence is captured and signed off.
