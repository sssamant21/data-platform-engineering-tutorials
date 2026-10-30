# Chapter 044 — WAL Archiving, Restore Commands and PITR Lab

**PostgreSQL 18 · Isolated lab cluster only · Runtime validation pending.**

## 1. Preflight: read-only inspection

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/044-preflight.sql
```

Capture server version, archive settings, archiver counters, WAL LSN, replication slots, disk headroom and last successful base backup. The SQL script changes no configuration.

## 2. Archive design worksheet

| Check | Evidence / expected outcome |
|---|---|
| wal_level and archive_mode | Appropriate for continuous archiving |
| Archive command | Returns success only after durable storage |
| Existing destination file | Identical content accepted, mismatch rejected |
| Interrupted transfer | No partial file acknowledged |
| WAL continuity | All required segments from base backup available |
| Archive failure | Alert and retry without deleting source WAL |
| Retention | Base backups, WAL and timeline history retained together |
| Access control | Separate credentials and encrypted storage |

For a disposable self-managed cluster, configure a **tested** archive tool or safe local lab archive command under a reviewed change. Do not copy illustrative configuration into production.

## 3. Generate a known recovery marker

Run this only in a dedicated disposable lab database after archive configuration is confirmed:

```bash
psql -X -w -v ON_ERROR_STOP=1 -d postgres \
  -v expected_system_id=REPLACE_WITH_OBSERVED_DISPOSABLE_SOURCE_SYSTEM_ID \
  -v expected_data_directory=/absolute/path/to/disposable/source/PGDATA \
  -v expected_operator=AUTHORIZED_SOURCE_ROLE \
  -v confirm_stage=044-MARKER \
  -f postgresql/labs/sql/044-marker.sql
```

This one-time marker requires a verified, disposable PostgreSQL 18 source cluster, an exact operator role, its independently inspected absolute data-directory path, cluster system identifier and `044-MARKER` token. Replace every placeholder manually and use an appropriately privileged connection. The script refuses existing `ch044` objects and creates its fixture transactionally; never re-run against an occupied schema. Record the marker timestamp and its transaction context. A wall-clock marker is illustrative; confirm actual commit boundaries and WAL availability before selecting a PITR target. Do not intentionally damage production data.

## 4. Isolated PITR rehearsal

1. Take a verified physical base backup with a continuous WAL archive available.
2. Create a separate empty PostgreSQL 18 recovery data directory on an isolated instance; never overwrite a running PGDATA.
3. Restore files and tablespaces; configure `restore_command` for the verified archive.
4. Set an approved recovery target and create `recovery.signal` in the **isolated** restored data directory.
5. Start recovery and inspect logs for WAL requests, replay progress and target reached.
6. Pause and verify data against the marker; only promote if the drill requires it and the target is correct.
7. Record actual RPO, RTO, timeline and archive completeness.

## 5. Failure drills

- Archive destination unavailable: demonstrate alerting and WAL retention risk.
- Missing segment: verify recovery cannot safely reach the requested point.
- Incorrect timezone target: compare UTC-normalized times.
- Divergent timeline: inspect history and choose the intended branch.
- Failed restore_command: examine exit status and requested filename.

## 6. Acceptance

| Requirement | Evidence |
|---|---|
| Configuration understood | Preflight SQL output |
| Archive continuity checked | WAL inventory and timeline history |
| Recovery target defined | Timestamp/LSN and approval |
| Isolated restore completes | Startup and replay logs |
| Marker verified | Row-level application validation |
| Recovery measured | Achieved RPO/RTO |
| No production changes | Lab isolation documented |

**Runtime status:** pending. This is a guided exercise; it does not claim an executed PITR restore.
