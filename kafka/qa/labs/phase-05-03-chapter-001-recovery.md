# Phase 5.3 — Chapter 001 Broker Failure and Recovery Lab

**Platform:** disposable GitHub Actions kind + Strimzi 0.47.0 + Kafka 4.0.0 KRaft. **Status:** published, awaiting runtime execution.

## Goal

Measure recovery after deleting a single broker Pod in an **isolated single-broker lab**. Verify pre-failure and post-recovery messaging and capture the recovery time. This is a *service recovery* test, **not** a high-availability or persistence/durability test: the fixture uses ephemeral storage and has one broker.

## Execute

1. Open [Kafka Chapter 001 Recovery Lab](../../../.github/workflows/kafka-chapter-001-recovery.yml) in GitHub Actions.
2. Select **Run workflow**, branch `main`.
3. Inspect job logs and download `chapter-001-recovery-<run-id>` artifact.
4. Review `chapter-001-recovery-result.json` and its `recovery_seconds` metric.

## Automated acceptance

- Verify context is exactly `kind-kafka-qa`; refuse all other contexts.
- Wait for Strimzi Kafka and KafkaTopic readiness.
- Produce and consume a baseline record.
- Delete **only** the disposable lab broker Pod, wait for replacement UID and Ready condition.
- Wait for Kafka reconciliation and verify fresh topic messaging after restart.
- Save PASS/FAIL evidence; upload diagnostics on failure.

**Passing this test does not certify the Chapter 001 HA six-pod exercise.** That requires a separate multi-broker, multi-controller scenario with replication and controlled failure.

## Troubleshooting

Review namespace events, Strimzi operator logs, and broker Pod status in the evidence artifact. If Kafka does not recover, investigate controller metadata, operator reconciliation and ephemeral storage behavior. Do not use this procedure on shared or production clusters.
