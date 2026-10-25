# Phase 6.4 — Chapter 002 Consumer Lag, Offset Reset and Recovery Acceptance

**Status:** Published; runtime PASS/FAIL pending.

## Learning objective
Measure Kafka consumer lag as `log-end offset - committed offset`, verify that consuming and explicitly committing removes lag, and demonstrate replay via `seek()` without modifying the committed group offset.

## Kubernetes execution
GitHub-hosted Ubuntu runner, disposable `kind-kafka-qa`, Strimzi 0.47.0, Kafka 4.0.0, three controllers and three brokers. Uses topic `qa-ch002-ordering` and an isolated test-only consumer group. No local setup.

## Automated acceptance
1. Verify safe context, Kafka and topic readiness.
2. Record partition 0's starting end offset; publish five records directly to partition 0 with `acks=all`.
3. Commit the starting offset and inspect it using the Kafka Admin API.
4. Assert initial lag = 5.
5. Consume five records in order and commit the ending offset; assert lag = 0.
6. Recreate consumer using the same group; assert committed offset equals the log end.
7. Seek backward five offsets, replay the records and assert the committed offset is unchanged.
8. Upload JSON PASS/FAIL evidence and failure diagnostics.

## Safety
No production consumer-group offsets are changed. `seek()` affects only the test consumer's current position. This lab does not call `kafka-consumer-groups.sh --reset-offsets` and does not test retention-expired offsets, lag under high throughput, or consumer rebalances.

[GitHub Actions workflow](../../../.github/workflows/kafka-chapter-002-lag.yml)
