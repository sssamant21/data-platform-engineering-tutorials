# Chapter 050 — High Availability and Disaster Recovery Acceptance Lab

**PostgreSQL 18 · Runtime: V03 disposable lab PASS · independent staging and enterprise acceptance PENDING.**

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

## V03 isolated PITR evidence (requires successful CI)

[Chapter 045 PITR runner](../validation/v03_pitr_disposable.py) and [CI workflow](../../.github/workflows/postgresql-v03-pitr-disposable.yml) demonstrate a **separate** PostgreSQL 18 source and recovery endpoint in a network-disabled disposable container. The runner executes the existing guarded Chapter 045 fixture, creates a verified physical backup, writes the good marker, creates a *named WAL restore point*, performs the isolated bad update, confirms WAL archival and restores the base backup into an **empty new** PGDATA. Recovery pauses at the named restore point; Chapter 045's real verification SQL must exit zero for 1,000 valid rows, the known-good marker and zero corrupted rows. Incorrect recovered-PGDATA verification must exit nonzero.

This proves only lab data invariants and that one WAL replay target can be reached. It does **not** certify archive retention, multi-host durability, application cutover, independent fencing, business RPO/RTO or production readiness.

## V03 lab-only HA evidence (not enterprise acceptance)

The [isolated switchover test](../validation/v03_ha_disposable.py) uses the exact Chapter 004 three-node topology and records a local shutdown fence, witnessed marker replay, controlled promotion, timeline change, one reachable writer, local SQL-service recovery time, `pg_rewind --dry-run`, and **fresh-base-backup** standby rejoin. The source old-primary PGDATA is preserved, and no actual rewind or production fencing is attempted.

A green CI run is **not** evidence of independent old-primary fencing, real application cutover, verified archived WAL or PITR, a complete HA/DR operational runbook, business RPO/RTO compliance, or authorized production deployment. Mark those mandatory acceptance rows **PENDING** until separate live exercises and independent sign-off.

## Separate actual-rewind acceptance gate

The [V03 actual-rewind runner](../validation/v03_rewind_disposable.py) is a *new disposable-only* acceptance scenario. It takes a preserved backup of the stopped former-primary data directory, proves a successful rewind dry-run, attempts an actual `pg_rewind --no-ensure-shutdown`, and permits restart **only after** the former primary has been configured as a standby. It then checks replay of a post-promotion marker and one writable primary. This is distinct from the already successful [fresh-directory rebuild](../validation/v03_ha_disposable.py).

The disposable actual-rewind gate passed on [run #41171155567](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41171155567): in-place PGDATA rewind, safe read-only rejoin and post-promotion marker replay. Independent production-like fencing, application traffic and business RPO/RTO gates remain **PENDING**.

## V04-D final independent acceptance: certification not granted

The [V04-D Chapter 050 acceptance register](../validation/V04D-FINAL-CH050-ACCEPTANCE.md) and [offline checker](../validation/v04d_ch050_acceptance.py) require exact binding to approved V04-A/B/C evidence, an actual operator-authorized staging rehearsal, independent old-primary restart/write fencing, client-level service recovery, all eleven mandatory rows below, five failure-mode checks, and four measured HA/PITR business objectives within approved limits. Four independent post-exercise sign-offs are also required.

**Current result: NO_GO / NOT_CERTIFIED**: no authenticated independent staging evidence or authorized live rehearsal has been provided. A green disposable CI workflow or completed metadata worksheet cannot authorize staging failover or certify an enterprise system. Keep PR #44 draft until source records and independent approvals are reviewed.

## V04-E private evidence integrity intake

Use the [V04-E private evidence intake guide](../validation/V04E-EVIDENCE-INTEGRITY-INTAKE.md) after the independently authorized staging test to verify that retained local redacted copies of the eleven Chapter 050 acceptance artifacts, five negative scenarios and four HA/PITR measurements match the recorded SHA-256 values. The offline checker is **not** an evidence-authentication service or certification authority. No real staging evidence has been provided; status remains NO_GO / NOT_CERTIFIED.

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

**Acceptance:** every mandatory staging gate passes with independently authenticated evidence and observed objectives meet the approved business thresholds. **Actual staging runtime:** NOT_EXECUTED; enterprise NOT_CERTIFIED.
