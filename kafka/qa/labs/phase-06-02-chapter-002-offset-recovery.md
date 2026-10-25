# Phase 6.2 — Chapter 002 Consumer Offsets, Restart and Replay

**Status:** Draft automated lab published; runtime result pending.

## Goal
Verify Kafka consumer-group committed offsets, resume behavior after restarting a consumer, and replay with a fresh group. This is a *Chapter 002 extension*, not a replacement for Chapter 017/018's detailed consumer-group coverage.

## Kubernetes execution
Use the existing disposable six-Pod Strimzi/KRaft fixture, topic `qa-ch002-ordering`, and GitHub Actions. The script produces uniquely tagged records, consumes with a fresh group, inspects group offsets, publishes another record, resumes with the same group, and replays from the beginning with a different group.

## Acceptance
- Kafka and topic Ready.
- Baseline events produced and consumed.
- Committed consumer offsets visible in `kafka-consumer-groups.sh --describe`.
- Same consumer group resumes and consumes newly published event.
- Fresh group replays historical records.
- JSON PASS/FAIL evidence uploaded on success or failure.

## Caveat
The console consumer's auto-commit timing can make this lab fail nondeterministically; a robust follow-up should use an explicit synchronous commit consumer client. A failed offset assertion must not be treated as a Kafka outage. The lab does not test concurrent group members, rebalances or production recovery.
