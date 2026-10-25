# Chapter 019 automated acceptance

Run `python kafka/qa/run_chapter_019.py` against the disposable kind fixture,
or use the Chapter 019 GitHub Actions workflow. It creates its own three-partition
input/output topics and Kubernetes client Job. Java source is mounted read-only in
a ConfigMap and compiled/executed by the version-matched Strimzi Kafka image's
source launcher. It does not install tools or execute test code in broker Pods.

| Manuscript objectives/labs | Measurable acceptance |
|---|---|
| A / metadata | Input/output each have three partitions, RF=3, ISR=3, valid leaders and effective min ISR=2 |
| C–G / commit and abort | Client Job completes; committed event visible and aborted event absent in read_committed; aborted event present in read_uncommitted |
| LSO semantics | A later nontransactional write remains hidden behind an open transaction, then becomes visible after abort |
| H / fencing | Replacement epoch fences old producer on a disposable transactional ID; only replacement output commits |
| B/I / atomic processing | Six acknowledged input IDs; aborted output and offsets remain invisible/unchanged; retry after seek commits output and next offsets atomically |
| Recovery | New consumer resumes at committed offsets with no already-committed input; exact output IDs reconciled |
| Final health | Full ISR remains intact after all application-level tests |

The harness fails promptly for a failed Job, requires every expected client
assertion, captures logs and Kubernetes events before scoped cleanup, and uses
bounded operation/Job/workflow timeouts. Job retries are disabled to prevent
unexamined business resubmission. The selector includes 019 on the existing
three-broker Kafka 4.0.0/KRaft fixture and retains orchestrator max-parallel=2.

Evidence: `chapter-019-runtime.json`, `chapter-019-client.log`, resource/event,
client and operator diagnostics under `kafka/qa/evidence/`. The JSON identifies the
PR head, checkout merge commit, Actions run, resources, assertions and limitations.
Actions uploads an artifact with seven-day retention even when execution fails.

No external database/API effect, production SLO, broker/zone failure, TLS/ACL
configuration, independent security review or enterprise certification is implied.
Publication, implementation and executed results must be assessed separately.
The fencing test uses only a unique test ID; it never targets a shared writer.

The Chapter 019 PR is based on the Chapter 018 branch so reviewers can inspect
only this chapter's changes; merge Chapter 018 first, then retarget to main.
