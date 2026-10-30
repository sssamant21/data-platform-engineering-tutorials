# Chapter 050 — High Availability and Disaster Recovery Acceptance Lab

**PostgreSQL 18 · Disposable primary/standby + isolated restore target · Runtime validation pending.**

## 1. Preconditions

A dedicated lab primary A, streaming standby B, protected base backup/WAL archive and separate restore target C are required. Configure secure connections and use unique lab credentials. No command in this lab should be executed against production.

## 2. Baseline collection

```bash
psql -X -v ON_ERROR_STOP=1 -h PRIMARY_HOST -d postgres -f postgresql/labs/sql/050-primary-preflight.sql
psql -X -v ON_ERROR_STOP=1 -h STANDBY_HOST -d postgres -f postgresql/labs/sql/050-standby-preflight.sql
```

Collect cluster identity, roles, replication LSNs, slot health, archiver status, WAL settings and standby conflict counts. Repeat samples after the exercise.

## 3. PITR acceptance

1. Run the Chapter 045 fixture in the dedicated lab and capture a verified physical backup.
2. Commit the known-good marker, then simulate the unwanted update.
3. Recover C from base backup plus WAL to an approved target before the unwanted commit.
4. Execute Chapter 045 verification SQL against **C**, not A.
5. Record backup/restore logs, timeline, recovered marker and achieved PITR RPO/RTO.

## 4. HA acceptance

1. Capture a committed business marker and its visibility on B.
2. Isolate A from all write clients; verify independent fencing.
3. Record candidate B's WAL replay position and expected data loss.
4. Manually promote B only after operator approval.
5. Verify B is writable, routing targets only B and application checks pass.
6. Record failure detection, fencing, promotion, routing and application readiness timestamps.

**Stop immediately** if fencing cannot be demonstrated.

## 5. Rejoin acceptance

1. Keep former A stopped and fenced.
2. Preserve its original data and logs.
3. Validate `pg_rewind` prerequisites, clean target shutdown, known WAL divergence, checksums/`wal_log_hints` and run an approved dry-run, or choose full rebuild. A failed actual rewind can leave target PGDATA unusable.
4. Before restart, verify rejoined A has `standby.signal` and correct `primary_conninfo`/archive settings; rewind can copy source configuration. Rejoin A as standby of B and verify receiver state and catch-up.
5. Confirm no dual-writer state and check backup/archive configuration on B.

## 6. Acceptance worksheet

| Gate | Pass/Fail | Evidence reference | Operator |
|---|---|---|---|
| Base backup verified | | | |
| WAL archive continuous | | | |
| Isolated PITR passes row checks | | | |
| Old primary fenced | | | |
| Candidate freshness approved | | | |
| Exactly one writable primary | | | |
| Application smoke tests pass | | | |
| Former primary safely rejoins | | | |
| HA RPO/RTO measured | | | |
| PITR RPO/RTO measured | | | |
| Alerts and runbooks reviewed | | | |

**Mandatory gates cannot be waived by a numeric score.**

## 7. RPO/RTO worksheet

- HA RPO: compare last acknowledged business transaction on A with latest verified transaction on B; document lost or unconfirmed writes.
- HA RTO: detection timestamp through validated application service restoration.
- PITR RPO: last legitimate committed transaction recovered versus approved incident boundary.
- PITR RTO: detection timestamp through validated recovery readiness, including authorization and restore.
- Record all timestamps in UTC and distinguish observed from inferred values.

## 8. Failure-injection review

Discuss archive gap, stale standby, orphaned slot, replication conflict, failed fencing and rewind failure. For each, state the signal, stop condition, business impact, recovery path and owner.

**Acceptance:** every mandatory gate passes with reproducible evidence and actual objectives meet approved thresholds. **Runtime:** pending.
