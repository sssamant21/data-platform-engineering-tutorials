# Phase 6.5 — Chapter 002 Final Certification and Evidence Gate

**Status:** Gate published; certification result pending.

## Purpose
Require the latest `main` GitHub Actions run of each Chapter 002 lab to have a successful conclusion and its expected JSON PASS evidence. A successful workflow without the expected evidence is insufficient. Missing, failed or still-running latest results block certification.

## Required labs
- Phase 6.1 — Partition Ordering: `kafka-chapter-002-certification.yml`
- Phase 6.2 — Offset Recovery: `kafka-chapter-002-offset-recovery.yml`
- Phase 6.3 — Consumer Rebalance: `kafka-chapter-002-rebalance.yml`
- Phase 6.4 — Consumer Lag and Replay: `kafka-chapter-002-lag.yml`

## Execution
Run [Kafka Chapter 002 Final Certification Gate](../../../.github/workflows/kafka-chapter-002-final-certification.yml) from GitHub Actions. It uses the GitHub API to inspect each latest run, downloads the attached evidence, checks all required PASS fields, and uploads `chapter-002-final-certification.json`. It never modifies Kafka or requires a laptop cluster.

## Important limitations
- The gate verifies workflow conclusions and artifact content; it does not itself rerun Kafka.
- Each lab may have run at a different repository commit. The gate records the run IDs and commit hashes to make this visible. It does not establish that all four labs passed on an identical source revision.
- A workflow with stale passing evidence is not enough if its latest run has failed.
- Certification only covers the explicitly tested Chapter 002 lab scope, not every possible Kafka failure scenario.
