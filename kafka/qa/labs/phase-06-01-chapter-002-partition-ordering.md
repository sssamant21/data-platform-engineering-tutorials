# Phase 6.1 — Chapter 002: Topics, Partitions, Offsets and Ordering

**Curriculum chapter:** [002 — Kafka Topics, Partitions, Offsets and Ordering](../../01-fundamentals-architecture/002-kafka-topics-partitions-offsets-and-ordering.md)

**Status:** Published, runtime PASS/FAIL pending.

## Goal
Demonstrate Kafka's ordering guarantee **within a partition**. Do not assume global ordering across partitions.

## Kubernetes architecture
Use disposable `kind-kafka-qa` and namespace `kafka-qa`, Strimzi 0.47.0, Kafka 4.0.0 KRaft, three controller-only Pods and three broker-only Pods. A three-partition topic uses replication factor 3 and min ISR 2. All storage is ephemeral and all Pods run on one kind host; this is not a production availability test.

## Automated exercises
1. Verify the exact disposable Kubernetes context.
2. Wait for Kafka and the topic to report Ready.
3. Inspect topic metadata for three partitions and three replicas.
4. Produce five uniquely identified records with the same key and `acks=all`.
5. Consume five records with printed partition and offset metadata.
6. Assert the same key maps to the same partition, the five values remain in order, and offsets strictly increase.
7. Write `kafka/qa/evidence/chapter-002-certification.json` with checks, selected partition, offsets and PASS/FAIL.

## Run
Go to [Kafka Chapter 002 Partition Ordering Certification](../../../.github/workflows/kafka-chapter-002-certification.yml) in GitHub Actions and choose **Run workflow**. The workflow also runs on relevant pushes to `main`.

## Limitations
This test covers one key and a single producer session. It does not certify ordering under multiple concurrent producers, changes to partition count, retries with non-idempotent settings, cross-partition order, or production resilience. Treat those as separate acceptance tests. No local laptop installation is required.
