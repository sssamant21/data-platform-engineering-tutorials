# PostgreSQL V03 — Chapters 061–066 Physical Backup and PITR Acceptance

**Validation environment:** disposable PostgreSQL 18 GitHub Actions Docker instance, network mode `none`, no published ports.  
**Enterprise certification:** NOT_CERTIFIED. **Actual staging rehearsal:** NOT_EXECUTED.

## Goal and test scope

The [isolated PITR runner](v03_ch061_066_pitr_disposable.sh) performs a real physical base backup, `pg_verifybackup` manifest check and a separate restored PostgreSQL server started from a fresh PGDATA. The source and restore have separate ports, separate data directories and operate exclusively within a disposable, network-isolated CI container. No external database credentials or operational endpoints are available.

The workflow tests a genuine PostgreSQL recovery boundary, not just a static SQL example: it creates Chapter 064 and 066 one-time fixtures on the temporary server, completes a base backup **before** any incident markers, commits “before-target” records, captures a timezone-aware target timestamp, then commits “after-target” records and deletes an existing reference row. It archives WAL and starts a cloned server with the explicitly recorded recovery target, configured to **pause**, not promote, at that point.

## Acceptance conditions

| Gate | Expected result | Scope |
|---|---|---|
| Network and cluster isolation | Docker network=none, no published ports, PostgreSQL major 18 and distinct PGDATA | Disposable only |
| Source preparation | Guarded one-time Chapter 064 and 066 fixtures execute with actual observed cluster system identifier | Disposable only |
| Physical backup | `pg_basebackup -Fp -X stream` succeeds and backup manifest is verified | Disposable only |
| Corruption refusal | A separate, deliberately corrupted backup COPY fails `pg_verifybackup` | Disposable only |
| Archive health | Source archive mode is ON; real archived WAL entries recorded | Local archive only |
| Recovery target | Timestamp with UTC offset strictly after base backup and first commit, before second commit | Historical PITR |
| Paused recovery | Restored server accepts read-only queries, is in recovery and paused at target | Separate PGDATA/port |
| Before/after validation | Before-target events present; after-target events absent in both databases | Actual WAL replay |
| Deleted reference recovery | Chapter 066 reference row remains present in PITR clone, absent from original source | Actual data |
| Cleanup | Restored server is stopped; disposable Docker server destroyed | No persistent changes |

The workflow writes **only a short, sanitized outcome report**, containing the number of assertions and general lab context. It does not upload database contents, client records, connection strings, source backups or WAL into GitHub artifacts.

## Operational limitations

This is one small Docker instance with two PostgreSQL server processes and a local WAL archive. It does **not** prove off-host archive durability, independent failure domains, cloud/object-storage retention, app-level recovery, production security or DR site cutover. It does not measure actual business RPO/RTO and cannot establish enterprise DR acceptance. Failed or missing tests must result in NO_GO; the result must never be inferred from the template alone.

- Chapters 061, 062 and 065 still need **separate** logical dump/restore runtime tests and real retention simulation acceptance.
- Chapter 063 physical-backup steps are partly represented by this shared physical base backup and verification lab but still require independent Windows/service-account and application validation.
- Chapter 064/066 historical PITR correctness is distinct from the **latest recoverable point** needed to establish real RPO.
- Chapters 067–070 multi-node replication, synchronous-commit behavior, quorum-backed fencing, failover and application routing are not tested here.
- Chapter 050 staging certification remains **BLOCKED** on [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45), with [draft PR #44](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/44) unchanged.

## Evidence and next step

Run [V03 Chapters 061–066 PITR workflow](../../.github/workflows/postgresql-v03-ch061-066-backup-pitr.yml). **Mark successful only after GitHub Actions reports a green job and its evidence validates actual PostgreSQL 18 execution.** The script remains fail-closed on nonzero commands, archive failure, unreachable restore target or unexpected data-state results.

After this isolated drill, move to Chapter 061/062/065 logical restore and retention, then Chapters 067–070 multi-node HA. Keep this PR in draft until the relevant technical acceptance is reviewed.
