# Chapter 020 automated capstone acceptance

Execute `python kafka/qa/run_chapter_020.py` in the disposable kind/Strimzi fixture,
or run its dedicated Actions workflow. Chapters 019/020 share the bounded
`runtime_acceptance.py` harness and `TransactionAcceptance.java` test client.
No pre-existing Chapter 001–018 workflow is modified.

| Manuscript lab/objective | Executed assertion |
|---|---|
| A/B baseline | Version/durability preflight, full RF=3/ISR=3/minISR=2, unique acknowledged IDs and exact input/output reconciliation |
| C/I offsets | Auto commit disabled, synchronous transactional output and consumed next offsets; abort-and-seek recovery, restart resumes committed progress |
| D–F membership/scaling | Real Java consumer Deployment scales 1 → 2 → 3 → 1, stable exclusive ownership covers three partitions, progress reconciled after each transition |
| E/G rollout and recovery | Readiness requires group join; rolling replacement logs three graceful closes; replacement Pod has a new UID after one owned application Pod deletion |
| G pre-commit failure point | Six new acknowledged inputs are held before processing; committed offsets and read-committed output remain at the prior batch; replacement recovers all six |
| H/I transactions | Independent client Job validates commit/abort visibility, LSO blocking/release, old-epoch fencing, output/offset atomicity and exact output IDs |
| K/L observability | Resource/events/operator/client/application logs, actions with command/time/expected/observed/reviewer/status and measured recovery interval |

The worker is reviewed repository Java test code, source-launched using the same
version-matched image as the broker. No package installation, registry publishing,
broker/controller fault, PVC deletion or production mutation occurs. The worker
commits Kafka output and offsets in one transaction and wakes its poll loop on
SIGTERM, aborting unfinished work and closing within bounded termination grace.
The temporary pre-commit hold exists only inside the selected test Pod; replacement
Pods do not inherit it. The deletion guard verifies Pod → ReplicaSet → Deployment
controller UIDs, not just a mutable app label.

The workflow pins Strimzi 0.47.0 and Kafka 4.0.0/KRaft using the existing
three-broker fixture. Jobs have retries disabled and operation/workflow timeouts
are bounded. Cleanup targets unique test resources, then destroys the kind cluster.
Existing orchestrator concurrency remains at two chapters.

Evidence is uploaded as `kafka-chapter-020-RUN_ID` for seven days and includes
`chapter-020-runtime.json`, Java transaction log, per-action observations, rollout
shutdown stream, application logs and diagnostics. JSON records immutable head and
checkout SHAs, run ID, resource names, check results and recovery UIDs/timing.
The recorded recovery interval includes observation overhead; there is no invented
business RTO target. `NOT_CERTIFIED` is retained even when supported checks pass.

Pending independent assessment: TLS/SASL/ACL/RBAC/NetworkPolicy security review,
production image approval, external database/API effects, HPA/KEDA and real
business throughput/latency/event-age SLOs. One-host ephemeral kind cannot certify
multi-zone availability. Automated results do not award the manuscript's 85/100
score or replace application-owner/security/assessor signoff.

This PR is stacked on Chapter 019, itself stacked on Chapter 018. Merge in that
order and retarget to main after prerequisite review; do not merge automatically.
