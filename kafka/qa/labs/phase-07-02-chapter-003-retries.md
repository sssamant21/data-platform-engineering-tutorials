# Phase 7.2 — Chapter 003 Producer Retries, Duplicate Prevention and Failure Injection

**Status:** Published; runtime verification pending.

## Goal
Run a Kafka producer configured with `acks=all`, idempotence, bounded delivery timeout and retries while restarting a Kafka broker Pod. Verify all 12 acknowledged records appear once and in order, and that the broker is recreated and Kafka becomes Ready.

## Environment
Disposable GitHub Actions kind cluster, Strimzi 0.47.0, Kafka 4.0.0 KRaft, three broker-only and three controller-only Pods. The topic has three partitions, replication factor 3, min ISR 2. The test runs the Java client in a survivor broker Pod and deletes a different broker Pod.

## Acceptance
- Safe `kind-kafka-qa` context.
- Kafka and topic Ready before injection.
- Broker deletion requested during the test.
- Twelve acknowledged messages, with no duplicates in the tested offset range.
- Partition-local order preserved.
- Replacement broker Pod has a new UID and a ready Kafka container.
- Kafka returns to Ready.
- JSON PASS/FAIL evidence uploaded.

## Limits
The broker restart is real, but this version does **not** prove the deleted broker was the partition leader or that an internal producer retry actually occurred. A green result demonstrates correctness under this specific injected broker restart, not general duplicate prevention, exactly-once processing or leader-failover recovery. A future lab should deliberately restart the topic partition leader and capture retry metrics.

[GitHub Actions workflow](../../../.github/workflows/kafka-chapter-003-retry.yml)
