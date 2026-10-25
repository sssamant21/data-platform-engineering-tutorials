# Chapter 018 acceptance scope

Publication and execution are separate. The manuscript is published; this implementation
has not yet passed GitHub Actions. Enterprise certification is NOT_CERTIFIED.

Run independently from the checkout root:

```bash
python kafka/qa/run_chapter_018.py
```

Prerequisites: the disposable `kind-kafka-qa` cluster, namespace `kafka-qa`, Strimzi
0.47.0 and the existing `runtime/strimzi-three-node-ch004.yaml` fixture (Kafka
4.0.0/KRaft, three brokers, RF=3, min ISR=2). The chapter workflow provisions these.
No changes to the existing fixture or Chapters 001–017 workflows are required.

| Manuscript objectives/labs | Automated measurable assertion |
|---|---|
| A: topic durability | Three partitions, valid leaders, three replicas and full ISR, independently read via Admin API at each scaling stage |
| B: baseline | Six acknowledged unique event IDs reconciled by a separate audit consumer |
| C–F: actual group participation | Deployment scales 1 → 2 → 4; stable Kafka membership equals desired count, assignments cover all partitions without overlap |
| E: partition ceiling | Exactly one idle member at four replicas; neither member idle at two replicas |
| F/H: recovery and lag | Scale back to one, recover ownership, committed offsets equal log end on all partitions, total six records |

Two consecutive successful Admin observations are required at each stage. Every
kubectl operation, convergence loop and CI job has a timeout. Generated topic,
Deployment and group names carry a unique run suffix. Cleanup addresses only the
created Deployment and KafkaTopic; the workflow destroys its isolated kind cluster.
The client image is inherited from the ready Kafka broker image (Kafka 4.0.0),
without adding an unreviewed third-party application image.

Evidence: `kafka/qa/evidence/chapter-018-runtime.json` records commit/run provenance,
versions, resource IDs, passed checks, assignment snapshots, offsets, errors and
limitations. Deployment/Pod/consumer diagnostics are captured before cleanup.
Workflow failure diagnostics also include operator logs and Kubernetes events.
The `kafka-chapter-018-RUN_ID` Actions artifact is retained for seven days.

Offline verification:

```bash
python -m py_compile kafka/qa/run_chapter_018.py kafka/qa/select_changed_chapters.py
python -m unittest discover -s kafka/qa -p test_chapter_018.py -v
python kafka/qa/run_qa.py --stage static --no-shell
```

Limitations: console consumers demonstrate assignment and committed lag, not
application side effects or a reviewed graceful-shutdown implementation. No timing
SLO, HPA/KEDA, newer consumer protocol, static membership, TLS/SASL/ACL, multi-zone
failure or independent security review is certified. The Kafka listener is the
existing disposable plaintext lab listener. No production security settings change.
The audit consumer validates IDs independently of the scaling group; the scaling
group's commits do not establish business-effect deduplication.

The per-chapter pull-request workflow runs only when its runner, observer, tests or
workflow change. The existing main-branch orchestrator still runs at most two
chapters concurrently and now selects 018 with the three-broker fixture. A shared
runtime change selects all supported chapters, preserving existing behavior.
