# Phase 6.3 — Chapter 002 Consumer Restart, Partition Assignment and Rebalancing

**Status:** Published; live GitHub Actions PASS/FAIL pending.

## Objective
Test **consumer-group partition reassignment**, not Kafka broker replica reassignment. A single consumer initially owns all three partitions; when a second joins, partitions split between them. After that consumer exits, the survivor takes all three. A replacement member then joins and causes another rebalance.

## Environment
GitHub-hosted Ubuntu runner, disposable kind cluster, Strimzi 0.47.0, Kafka 4.0.0 KRaft, three controller-only and three broker-only Pods, three-partition KafkaTopic `qa-ch002-ordering`. No local Kafka or Kubernetes required.

## Automated acceptance
1. Enforce `kind-kafka-qa` context; wait for Kafka and topic Ready.
2. Verify three topic partitions.
3. Run two independent Java KafkaConsumer threads in one ephemeral Kafka Pod, with a common group ID and CooperativeStickyAssignor.
4. Assert one member owns all three partitions, then two members have disjoint nonempty assignments covering all three.
5. Stop one member and assert the survivor owns all three.
6. Start a replacement member; assert another disjoint, complete assignment.
7. Save JSON evidence with assignment snapshots and PASS/FAIL.

The consumer Java source uses Kafka's runtime libraries in the Strimzi container and has bounded waits. This lab is not a test of message delivery, lag, broker failures, persistent storage or multiple Kubernetes consumer Pods. Those require separate acceptance tests.

## Execution
[GitHub Actions — Kafka Chapter 002 Consumer Rebalance Lab](../../../.github/workflows/kafka-chapter-002-rebalance.yml). Trigger manually or push a relevant file to `main`; inspect the artifact and failed-step diagnostics before certifying.
