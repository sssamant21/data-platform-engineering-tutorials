# Chapter 021 persistent storage acceptance

Run independently with `python kafka/qa/run_chapter_021.py` after applying
`runtime/strimzi-three-node-persistent-ch021.yaml` in the disposable `kind-kafka-qa`
cluster / `kafka-qa` namespace. Its dedicated workflow provisions kind, the pinned
Strimzi 0.47.0 operator, and Kafka 4.0.0/KRaft with three persistent-claim dual-role
nodes. Existing ephemeral fixtures and Chapters 001–020 workflows are unchanged.

## Acceptance mapping

| Manuscript lab/objective | Automated measurable evidence |
|---|---|
| A/B: persistent storage chain | Verify KafkaNodePool persistent-claim/1Gi/standard/deleteClaim=false; map actual broker Pod volume and container mount to Bound PVC, PV claim UID, capacity, StorageClass and local-path backend |
| C/D: retention and segments | A uniquely named three-partition RF3/minISR2 topic; effective Admin API and kafka-configs.sh settings match cleanup.policy=delete, retention.ms=3600000, retention.bytes=16777216, segment.bytes=1048576, segment.ms=60000 |
| E: deterministic delivery | Source-launched Java Job produces 96 unique records with 64 KiB deterministic payloads, explicit partition placement, idempotence/acks=all/no compression; verifies exact payloads, IDs, per-partition offsets/order and retained offset window |
| F: physical segment rolling | Bounded ~6 MiB logical data forces size-based rolls, without sleep-based deletion assumptions; kafka-log-dirs.sh must report nine unique healthy partition replicas across three brokers; read-only find metadata requires at least two nonempty .log segments and matching .index/.timeindex files on every replica |
| H: storage pressure metadata | Read-only df block/inode snapshots at the discovered PVC mounts, PV node affinity, actual Pod placement and node Ready/DiskPressure conditions; requested capacity is never reported as free space |
| L: quorum/final health | Valid KRaft leader; full RF3/ISR3, effective settings and PVC/PV UIDs/mount mappings unchanged after the bounded workload |

All data paths come from Kafka log-directory metadata and actual Pod PVC mounts,
not guessed Strimzi filesystem layouts. A path guard restricts inspection to the
unique test topic under the verified mount. The runner executes no filesystem
write command in a broker Pod, never edits/deletes segments/indexes, and never
issues delete/patch operations on PVCs/PVs. It performs no broker restart, storage
resize, deliberate disk fill, corruption or storage fault injection.

The shared Chapters 019/020 harness supplies context/version/durability checks,
bounded Job lifecycle, JSON evidence, diagnostics and cleanup of the owned topic,
client Job and ConfigMap. The cluster lifecycle belongs to the workflow: only the
newly created disposable kind cluster is destroyed at job completion. Persistent
claims here survive application client execution, not destruction of the kind
node container or runner. `deleteClaim: false` does not provide host-loss durability.

## Evidence and safety boundaries

`chapter-021-runtime.json` records immutable head/checkout SHAs, run ID, check
statuses, before/after Pod→PVC→PV/StorageClass inventory, nine replica log directories,
physical file metadata and limitations. Per-observation evidence records timestamp,
actual command, expected/observed outcome, evidence path and automated reviewer
identity. Java logs, read-only Kafka tools, df snapshots, node/resource/events,
PVC/PV/StorageClass and broker/operator diagnostics accompany it. The dedicated
workflow uploads `kafka-chapter-021-RUN_ID` for seven days, including failures.

The changed-chapter selector registers 021 with its persistent fixture. The existing
orchestrator applies that fixture directly, retains max-parallel=2 and executes the
same independently runnable script. No extra provisioner installation is required:
the fixture explicitly requests kind's existing `standard` StorageClass and the
runner verifies the actual `rancher.io/local-path` provisioner and
`WaitForFirstConsumer` binding mode.

## Not validated / not certified

- Single-node kind local-path volumes share one host and failure domain. They
  cannot establish independent replica durability, node/zone loss recovery,
  production CSI attach/detach behavior, encryption or storage-backend resilience.
- Local-path PVC capacity is allocation metadata, not an enforced disk quota;
  df reports shared host filesystem capacity, not an isolated 1 GiB filesystem.
- PVC expansion/shrink, disk pressure, power-loss/fsync guarantees, corruption,
  backups and broker restart durability are not tested. The manuscript keeps
  expansion and disk-pressure exercises as tabletop work.
- Retention eligibility configuration and record preservation during this short
  run are tested. Asynchronous expiration/deletion timing, consumer replay loss
  after expiration and compaction are not tested. No deletion SLA is inferred.
- IOPS, throughput, p99 latency, measured ingest forecasting, production headroom
  thresholds, business SLOs and Prometheus/CSI metric availability are not certified.
- Broker/controller roles share a PVC per node; separate controller-storage
  recovery and production security/application-owner/assessor review remain pending.

Publication, implementation, successful Actions runtime validation and enterprise
certification are distinct. A passing run retains `certification=NOT_CERTIFIED` and
covers only the supported checks above; it does not award the manuscript's 85/100
assessment or substitute for independent review.

## Local checks

```bash
python -m unittest discover -s kafka/qa -p 'test_chapter_0*.py' -v
python -m py_compile kafka/qa/run_chapter_021.py kafka/qa/select_changed_chapters.py
python kafka/qa/run_qa.py --stage static --no-shell
```

Version-specific reference: [Strimzi 0.47.0 deploying and managing](https://strimzi.io/docs/operators/0.47.0/deploying).
