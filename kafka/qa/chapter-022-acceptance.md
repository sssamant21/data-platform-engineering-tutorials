# Chapter 022 retention governance acceptance

`python kafka/qa/run_chapter_022.py` independently runs the Chapter 022 lifecycle in
the existing disposable kind/Strimzi 0.47.0/Kafka 4.0.0 KRaft persistent fixture.
Three local-path PVCs retain RF3/minISR2. Reusable storage inspection and Java client
code from Chapter 021 now accept a chapter identifier and expected retention policy;
Chapter 021 retains its default settings and receives a runtime regression check.

## Manuscript mapping

- Labs A/J: verify actual broker Pod→PVC→PV/StorageClass mapping, bound capacities,
  unchanged identities and read-only filesystem headroom. Single-host kind is not
  a production CSI or multi-zone storage test.
- Labs B/C/L: require synthetic owner/classification/ticket annotations; verify
  KafkaTopic observed generation and effective Kafka Admin/CLI configuration.
- Labs D/E: seed 96 deterministic 64 KiB records using explicit partitions,
  idempotence/acks=all, reconcile exact payloads and offsets, explicitly commit the
  isolated audit group's next offsets and compare them with earliest/latest bounds.
- Lab F: observe physical size-based segment rolls across all nine replicas via
  supported Kafka log-directory metadata and read-only file/index listings. No
  forced deletion, broker restart or file mutation occurs.
- Lab G: validate a synthetic-only change guard, server-dry-run then reconcile
  1h → 2h → 1h through KafkaTopic, verifying exact data and effective policy after
  every transition. Restoration is permitted only while the test data is safely
  younger than one hour. Increasing retention cannot recover deleted records.
- Labs H/K: compute the manuscript's illustrative 20 MiB/s, 48-hour, 12-partition,
  RF3 scenario; demonstrate that a 50 GiB-per-partition cap gives only 30,720 seconds
  of nominal replay at that rate. This is a reproducible calculation, not a measured
  production forecast or a legal approval.

Each client stage is a separate bounded, no-retry Kubernetes Job using the same
version-matched image. Logs are preserved under baseline/extended/restored, and
JSON includes policy generations, synthetic authorization, before/after values,
actual read commands, observations, identities and limitations. Only the owned
KafkaTopic, Jobs and ConfigMaps are cleaned up; no PVC/PV is edited or deleted.

## CI selection and cost

The selector registers 022 on the persistent Chapter 021 fixture. Known shared
storage files dispatch only 021/022; truly shared runtime infrastructure still
selects all supported chapters. A selector-only edit still runs the full selection,
while a registration edit accompanying identifiable changed runners runs those
runners. This avoids an expanding all-chapter runtime fanout for each new chapter.
The existing orchestrator remains capped at two concurrent chapter jobs. Existing
fixture mappings are preserved and dependency selection has regression tests.

## Limits and certification

Actual one-hour retention expiration/deletion, legal erasure, production admission
or GitOps controllers, business replay guarantees, CSI/zone recovery, expansion,
power-loss durability, production benchmarks and independent security/assessor
approval are NOT_VALIDATED. Annotations do not enforce an admission policy. Plaintext
is disposable-lab-only. Publication, implementation, runtime execution and enterprise
certification remain distinct; successful supported checks retain NOT_CERTIFIED.

Evidence: `chapter-022-runtime.json`, phase-specific Java logs, KafkaTopic/config,
segment, PV/PVC/StorageClass, df and Kubernetes diagnostics. The workflow uploads
its artifact for seven days, including failures. No Chapter 023 work begins until
these supported runtime checks pass.
