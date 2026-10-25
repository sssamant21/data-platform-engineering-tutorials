# Chapter 024 local compatibility preflight and explicit integration no-go gate

`python kafka/qa/run_chapter_024.py` executes only the unconditional local baseline
and compatibility inventory from manuscript Labs A/B/L. It uses the persistent
three-node Kafka 4.0.0/KRaft/Strimzi 0.47.0 fixture. No RemoteStorageManager artifact,
cloud sandbox or reviewed bucket/identity inputs have been supplied.

## Live preflight checks

- Verify exact broker CR version, broker image IDs/digests, operator image, Kafka
  CLI version, served KafkaTopic APIs and the actual PVC/PV/StorageClass mapping.
- Query each broker's effective remote-log enable/manager/metadata-manager settings
  using Kafka Admin; require the remote feature to remain disabled for this lab.
- Create a uniquely owned local-only RF3/minISR2 topic; verify remote storage is
  disabled and reconcile six deterministic local records. These reads are never
  reported as remote-read proof.
- Capture KRaft, filesystem headroom, immutable storage identity and diagnostics.
- Evaluate a fail-closed integration prerequisite checklist and the manuscript's
  illustrative 8 MiB/s/30-day capacity model. Neither reviewed-input presence nor a
  calculated footprint is runtime integration/security/billing evidence.

The runtime JSON labels its scope `LOCAL_BASELINE_AND_COMPATIBILITY_GATE_ONLY`.
Labs G (bucket/identity), H (offload), I (remote reads/recovery), IAM denial and DR
RPO/RTO are explicitly NOT_EXECUTED/NOT_TESTED. No plugin is installed, remote flag
toggled, cloud resource provisioned or bucket object touched. Production admission,
identity, encryption/KMS, request pricing and legal/assessor review remain pending.

Plugin/provider compatibility is NOT_ESTABLISHED. The operator supports a custom
remote manager mechanism, but support for the interface is not evidence that an
unprovided artifact/provider combination is compatible. These requirements follow
[Strimzi 0.47.0 deploying](https://strimzi.io/docs/operators/0.47.0/deploying) and
[Kafka 4.0 broker configuration](https://kafka.apache.org/40/generated/kafka_config.html).

## CI cost and regression controls

Selector changes no longer trigger every older storage workflow on every new
chapter registration. Fast offline chapter/selector guards now run in static CI.
Actual runner/client/fixture/workflow edits still trigger the affected standalone
workflows, and the changed-chapter orchestrator retains its dependency-scoped
matrix and max-parallel=2. A selector-only merge retains full runtime selection.
Chapters 021–023 get a one-time workflow regression run for this trigger adjustment;
the actual runtime steps and assertions are unchanged.

A successful Actions preflight is not tiered-storage integration, disaster recovery,
production readiness, a manuscript assessment score or enterprise certification.
Certification remains NOT_CERTIFIED. The conditional integration artifacts and
sandbox must be reviewed before those execution gates can receive credit.
