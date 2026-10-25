# Phase 7.3 — Targeted Kafka Leader Failover and Producer Retry Metrics

**Status:** Published; GitHub Actions runtime verification pending.

## Objective
Identify partition 0's current leader for `qa-ch003-delivery`, start producer traffic, delete the **leader** broker Pod, verify election of a different leader, and validate 100 acknowledged records with no missing, duplicate or out-of-order values in the test offset window.

## Runtime
Disposable GitHub-hosted kind cluster with Strimzi 0.47.0 and Kafka 4.0.0 KRaft, three dedicated controllers and three brokers. Topic replication factor 3 and `min.insync.replicas=2`.

## Acceptance checks
- Partition 0 leader identified from Kafka topic metadata.
- Producer has sent at least 10 acknowledged records before fault injection.
- The leader broker Pod is deleted.
- Partition 0 elects a different leader.
- All 100 records are acknowledged and read in order, with no duplicates in the test offset window.
- Producer `retry-total` metric is recorded in JSON.
- Deleted broker is recreated with a new Pod UID and Kafka returns to Ready.

## Interpretation
The result separately records `producer_retry_total` and `retry_observed`. **PASS does not require a nonzero retry count**, because Kafka may elect a new leader before an in-flight request requires retry. A nonzero retry count is evidence of client retries, not proof of exactly-once end-to-end processing. The test does not validate transaction semantics or all failure timing scenarios.

[GitHub Actions workflow](../../../.github/workflows/kafka-chapter-003-leader-failover.yml)
