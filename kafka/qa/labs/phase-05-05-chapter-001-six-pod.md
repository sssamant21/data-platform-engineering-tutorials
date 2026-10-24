# Phase 5.5 — Chapter 001 Dedicated Six-Pod Architecture Acceptance

**Status:** Published; GitHub Actions runtime evidence pending.

## Architecture

Deploy **three controller-only** and **three broker-only** Strimzi KafkaNodePool Pods, Kafka 4.0.0 KRaft, topic replication factor 3 and `min.insync.replicas=2` in disposable kind on a GitHub-hosted runner. This validates logical role separation but not production multi-host or multi-zone fault tolerance.

## Execution

Open [Kafka Chapter 001 Six-Pod Lab](../../../.github/workflows/kafka-chapter-001-six-pod.yml) in GitHub Actions and select **Run workflow**, or push a relevant lab file to `main`. No laptop setup is required.

## Automated acceptance

1. Enforce exact `kind-kafka-qa` context.
2. Wait for Kafka and KafkaTopic Ready.
3. Verify three ready controller Pods and three ready broker Pods.
4. Verify topic replication factor 3 and produce a baseline record with `acks=all`.
5. Delete exactly one disposable broker Pod; retry an `acks=all` write within 180 seconds.
6. Verify the operator replaces the Pod, Kafka becomes Ready, and both records remain consumable.
7. Record JSON PASS/FAIL and recovery seconds, with diagnostics uploaded on failure.

**Limitations:** Ephemeral storage and a single kind host cannot validate persistent data recovery, zone failure, security hardening, or production RPO/RTO. Do not mark Chapter 001 certified until this workflow and earlier chapter-specific labs pass, and the remaining assessment requirements are reviewed.
