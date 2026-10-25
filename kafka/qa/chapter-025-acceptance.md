# Chapter 025 live local-storage capstone acceptance

`python kafka/qa/run_chapter_025.py` runs the supported local storage and application
recovery gates in the persistent Kafka 4.0.0/KRaft/Strimzi 0.47.0 kind fixture.
Existing inventory, retention policy, bounded clients, real tombstone/state logic
and ownership guards are reused with their prior defaults preserved.

## Executed gates

1. Record synthetic-lab authorization and test-only bounds before work: minimum
   observed shared-filesystem free space 64 MiB, rolling rebuild budget 180 seconds,
   no broker/PVC/file or cloud-object faults. These are harness limits, not business
   SLOs, signed independent change approval or a production capacity forecast.
2. Provision concurrent delete-retention and compacted RF3/minISR2 topics; verify
   effective settings and full ISR using real Java/Kafka APIs and metadata.
3. Produce a deterministic 96-record/64 KiB event ledger with acks=all/idempotence,
   exact expected value hashes and per-partition IDs/offsets. Reconcile before and
   after recovery, commit audit next offsets, and compare earliest/latest bounds.
4. Execute guarded server-dry-run/Strimzi 1h -> 2h -> 1h retention reconciliation;
   restoring the shorter policy is permitted only for safely young synthetic data.
5. Produce 108 keyed updates including genuine null-value deletion, literal string
   null and bounded history; rebuild exact state from empty maps to captured end
   offsets, allowing compaction gaps. Record cleaner progress without a deadline SLA.
6. Observe real retention-topic segment rolls/index metadata on all nine replicas
   through verified PVC mounts. No segment is edited or removed manually.
7. Start a real Java state-bootstrap consumer Deployment. Readiness appears only
   after empty-state reconstruction and full metadata checks. Verify its actual
   state SHA-256, Pod -> ReplicaSet -> Deployment controller UIDs and source image.
8. Stream the original Pod's shutdown log, roll only this disposable Deployment,
   require a new Pod UID with the identical rebuilt state checksum, capture graceful
   process exit and enforce the predeclared 180-second test completion budget.
9. Reconcile all 96 acknowledged retention events and committed offsets again;
   verify unchanged PVC/PV identities, remaining filesystem headroom and KRaft leader.

The consumer serves a frozen synthetic bootstrap snapshot, not a continuous-update
production state service. It deliberately reconstructs an empty in-memory store;
it does not certify state-PVC checkpoints or streaming group rebalance behavior.
Measured recovery is rolling replacement/bootstrap completion including observation,
not an outage-duration measurement or a production RTO/RPO claim.

## Conditional and independent gates

Tiered plugin/bucket compatibility, offload, remote reads, IAM-denial recovery and
DR remain NOT_EXECUTED/NOT_TESTED. The manuscript explicitly allows a conditional
remote gate but forbids a production tiered-readiness claim without execution.
Installed Prometheus/alert tests, production storage forecasts, security, signed
change records and assessor signoff are PENDING. No dashboard or legal approval is
invented. The 12 MiB/s/RF3/24h forecast is labeled an illustrative byte calculation.

Runtime status covers only the live local checks above. The manuscript's full
85/100 independent capstone acceptance is NOT_YET_ACCEPTED, and enterprise
certification stays NOT_CERTIFIED. No automated score substitutes for review.

## Evidence and CI

JSON records test bounds, expected ledger, stage Jobs, effective policy/offset
observations, state checksum and replacement UIDs/timing, physical segment files,
headroom, pending gates and limits. Per-stage logs and streamed shutdown evidence
are uploaded with Kubernetes diagnostics for seven days. Only owned synthetic
topics, Jobs, ConfigMaps and the consumer Deployment are cleaned up; PVCs/PVs and
broker/controller resources are not mutated by the runner.

Shared storage path and synthetic retention guards now accept the capstone's
chapter namespace while retaining owned-name/PVC boundaries. The compaction client
adds checksum and long-running bootstrap/readiness modes; previous seed/rebuild
modes retain their assertions. Dependency tests ensure importing chapters rerun.
Old selector tests now permit additional legitimate dependent chapters rather than
incorrectly capping their lists. Existing runtime assertions are not relaxed.
