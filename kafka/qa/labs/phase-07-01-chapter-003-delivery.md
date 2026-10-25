# Phase 7.1 — Chapter 003 Producer, Consumer and Delivery Semantics

**Curriculum:** [003 — Kafka Producers, Consumers and Message Delivery Semantics](../../01-fundamentals-architecture/003-kafka-producers-consumers-and-message-delivery-semantics.md)

**Status:** Published; runtime acceptance pending.

## Purpose
Exercise producer `acks=all`, idempotence configuration, successful delivery of five uniquely identified records, partition-local ordering, synchronous offset commits, and committed-offset visibility after consumer restart.

## Kubernetes setup
A disposable GitHub-hosted kind cluster, Strimzi 0.47.0, Kafka 4.0.0 KRaft, three dedicated controllers and three dedicated brokers. The test topic has three partitions, replication factor 3, and min ISR 2.

## Acceptance
1. Enforce `kind-kafka-qa` context and wait for Kafka and topic Ready.
2. Publish five records to partition 0 with `acks=all` and idempotence enabled; verify broker acknowledgements.
3. Consume from the acknowledged first offset and assert five values and order.
4. Explicitly commit the next offset with `commitSync()` and verify it.
5. Restart the consumer with the same group and confirm its committed offset.
6. Upload JSON PASS/FAIL evidence.

## Scope and safety
This test validates **successful acknowledged delivery**, not exactly-once processing. It does not inject lost acknowledgements, retry ambiguity, transaction aborts, broker failure, or concurrent producers. Those are separate follow-up labs. All infrastructure is disposable and no production offsets are touched.

[GitHub Actions workflow](../../../.github/workflows/kafka-chapter-003-delivery.yml)
