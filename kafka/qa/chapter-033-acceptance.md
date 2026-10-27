# Chapter 033 consumer fetch, scaling and pre-commit replay acceptance

`python kafka/qa/run_chapter_033.py` independently uses the persistent secure
Kafka 4.0.0/KRaft/Strimzi 0.47.0 kind fixture. The shared lifecycle retains the
accepted Chapter 031/032 defaults; their runtime workflows are regressed. A validated
Java source bundle reuses the existing security, Kafka health, native process and
payload-audit helpers while launching the consumer main class first.

## Native fetch evidence

Nine measured trials repeat three matched profiles with six partitions, RF3/minISR2,
1,200 x 1KiB deterministic records, offered producer cap 400 records/s, acks=all,
idempotence, immutable image and unchanged SASL_SSL/hostname verification:

| Profile | Fetch minimum bytes | Max wait ms | Per-partition fetch bytes | Max poll records |
|---|---:|---:|---:|---:|
| Baseline | 1 | 100 | 1048576 | 500 |
| Minimum | 65536 | 100 | 1048576 | 500 |
| Wait | 65536 | 500 | 1048576 | 500 |

The native consumer CLI overrides its per-partition fetch limit from `--fetch-size`;
the harness supplies it explicitly rather than assuming the config file wins.
Classic protocol, RangeAssignor, manual commits and protected client properties are
explicit. Producer/consumer counts, bytes, error metrics, payload multisets and
captured committed ends are reconciled. Native global consumer metrics are kept
separate from topic series, avoiding duplicate/summed metric attribution.

Native CSV measures fetch throughput including group-join effects; it supplies no
business-processing p99. The harness does not manufacture one. Raw fetch metrics,
medians and sample variation are observations, not production tuning recommendations.
Kafka's pinned [consumer settings](https://kafka.apache.org/40/configuration/consumer-configs/)
and [fetch metric definitions](https://github.com/apache/kafka/blob/4.0.0/clients/src/main/java/org/apache/kafka/clients/consumer/internals/FetchMetricsRegistry.java)
define the version-specific behavior.

## Actual group and application behavior

Separate fresh groups run 1, 3, 6 and 8 consumer members as threads in one bounded
Pod per trial. The coordinator must report stable classic/range membership and
exclusive coverage of six partitions, with at most six active members and two idle
members at count eight. Consumers pause until the observed membership is stable,
then a known round-robin backlog is released to a one-millisecond synthetic handler.
The test requires 120 unique validated IDs, commit-after-handler offsets at captured
ends, observed duplicates/rebalance callbacks and bounded shutdown. Handler and event
age percentiles come from real per-record samples with a stated nearest-rank rule;
event age uses Kafka CreateTime on the shared host clock. No linear capacity or
per-member CPU claim is inferred from shared-JVM measurements.

A separate real Kubernetes Deployment scales manually 1→3→6. Readiness follows
consumer assignment, credentials remain read-only, and the client ID uses the actual
Pod name from the downward API. The inspector verifies coordinator membership,
assignments, acknowledged stage canaries and committed catch-up. The harness maps
member client IDs/hosts to actual Pod UIDs/IPs and verifies the Deployment→ReplicaSet
→Pod owner chain, immutable image and zero unexpected restarts. Worker logs contain
synthetic handler/event-age observations and actual cgroup snapshots. Owned consumer
Pods are released before native fetch trials to avoid an idle-client confound.
HPA/KEDA is explicitly NOT_EXECUTED without a reviewed metrics/scaler integration.

## Real crash-before-commit and replay

A uniquely owned **non-broker** standard/RWO sink PVC is created for synthetic state.
It binds when the first consumer Pod mounts it. No Kafka PVC or segment file is
edited or deleted. The crash client forces twelve unique processed IDs to a private
single-writer ledger, captures consumer position versus processed and committed state,
then halts with exit 23 before committing. The expected negative requires the exact
checkpoint, owned failed Job/Pod relationship and exit 23; OOM, authentication failure,
a different exit or an absent checkpoint cannot count as successful fault injection.

A fresh client mounts the same verified PVC/PV claim UID/node binding, reloads the
twelve persisted IDs, replays uncommitted records, suppresses duplicates by event ID,
forces newly processed IDs and commits only after processing. It must reconcile all
120 known IDs, observe at least twelve replay attempts and reach the captured ends.
This proves process-level at-least-once replay with an idempotent synthetic file sink.
It proves neither external DB exactly-once semantics nor host/power/CSI/zone recovery.
No production offsets are reset; no offset-alteration CLI/API is used.

## Safety, evidence and open assessment

Clients are non-root with bounded resources, token-free ServiceAccounts and restricted
credential projections. Shared headroom/node-pressure checks, actual Admin ISR/quorum
polling, worker/Job/API deadlines, readiness/owner checks, and explicit data assertions
gate execution. Fault injection terminates only the owned synthetic client. PVC
protection/finalizers are never bypassed. Only owned resources are cleaned up before
kind teardown; local-path capacity metadata is not an enforced per-volume quota.

JSON and raw logs retain commands, public config/source hashes, actual assignments,
Pod/PVC identities, offsets, payload checks, expected-fault classification, real timing,
cgroup observations and unavailable metrics. Sanitization runs before upload. Native
fetch, synthetic processing, manual scaling and durable replay are reported separately.

Single-host kind is not production capacity. Broker/downstream CPU, network, IOPS,
distributed clock accuracy, cooperative/static membership, full fetch/poll/slow-handler
sweeps, HPA/KEDA and independent signoff remain pending. Full assessment is
NOT_YET_ACCEPTED; enterprise certification is NOT_CERTIFIED. Publication, implementation,
supported runtime execution and independent certification remain distinct.
