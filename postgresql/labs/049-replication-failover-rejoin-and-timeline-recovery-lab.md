# Chapter 049 — Replication Failover, Rejoin and Timeline Recovery Lab

**PostgreSQL 18 · Isolated primary/standby topology · Runtime validation pending.**

## 1. Read-only topology preflight

```bash
psql -X -v ON_ERROR_STOP=1 -h PRIMARY_HOST -d postgres -f postgresql/labs/sql/049-primary.sql
psql -X -v ON_ERROR_STOP=1 -h STANDBY_HOST -d postgres -f postgresql/labs/sql/049-standby.sql
```

Use secure credentials and replace placeholders with disposable lab endpoints. Capture primary and standby roles, WAL positions, replication slots, receiver state, relevant configuration and PostgreSQL versions.

## 2. Failover decision tabletop

| Gate | Required evidence |
|---|---|
| Primary failure confirmed | Host, database and application health |
| Old primary fenced | Independent proof it cannot accept writes |
| Candidate selected | Replay position, health, expected data loss |
| Business approval | RPO/RTO and loss acceptance |
| Backup recovery path | Last verified base backup and WAL continuity |
| Promotion method | HA manager or controlled manual command |
| Post-promotion checks | Single writable primary, new timeline, application health |
| Rollback/rejoin plan | Preserve former-primary state; choose rewind or rebuild |

**Stop condition:** if old-primary fencing cannot be proven, do not promote.

## 3. Isolated promotion exercise

On disposable instances only, have the operator confirm fencing and candidate readiness, then manually promote the selected standby according to the documented PostgreSQL procedure. The operator-run lab intentionally provides **no general-purpose automatic promotion script**. A **separate CI-only script** is provided below, hard-bound to an isolated, network-disabled Chapter 004 PostgreSQL 18 topology and two explicit tokens; it is not an HA manager. Verify `pg_is_in_recovery() = false` on the new primary and confirm application routing targets only one writable instance.

## 4. pg_rewind assessment

For the **cleanly stopped, independently fenced** former primary, confirm common ancestry, compatible PostgreSQL major version, `wal_log_hints` or data checksums, `full_page_writes`, and required WAL availability. A stopped server is not necessarily fenced from all clients or automated restarts. Record dry-run output:

```bash
pg_rewind --dry-run --target-pgdata=/isolated/old-primary-pgdata \
  --source-server="host=new-primary port=5432 user=rewind_user dbname=postgres"
```

Do not run actual rewind without approved target backup, target ownership checks, credentials, and documented rejoin plan. **After a successful rewind, configure standby recovery (standby.signal and correct connection/WAL settings) before starting the former primary.** Rewind may copy configuration from the source; starting it as writable risks a second divergence. A failed rewind can leave the target PGDATA unusable, in which case rebuild from a verified base backup. If prerequisites fail, use a fresh verified base backup.

## 5. Rejoin verification

Reconfigure the former primary as a standby only after successful rewind/rebuild and approval. Check streaming connection, replay catch-up, slot status, timeline continuity and application read routing. Never restart the old primary in writable mode after a new primary has been promoted.

## CI-only disposable switchover rehearsal (V03)

[Controlled switchover harness](../validation/v03_ha_disposable.py) and [GitHub Actions workflow](../../.github/workflows/postgresql-v03-ha-disposable.yml) perform **only** these isolated operations after exact cluster and marker checks:

1. Commit a unique marker on Chapter 004 primary A (127.0.0.1:55432) and prove it is visible on both standbys.
2. **Planned local fence only:** use `pg_ctl stop` on A, stop unused standby 2, independently check their process states and refusal of A's TCP endpoint. This is *not* network-level fencing or proof that an external HA manager cannot restart A.
3. Only after these gates, promote standby 1 (127.0.0.1:55433), verify new WAL timeline and one reachable writer, and recheck the acknowledged marker.
4. Measure **local smoke-test** RTO from simulated shutdown to query readiness; record marker RPO as zero **only for that specific acknowledged test transaction** (not an asynchronous business-loss guarantee).
5. Run `pg_rewind --dry-run` against the preserved, stopped original A; do **not** run actual rewind. Create a **separate empty directory** using `pg_basebackup -R`, confirm `standby.signal` and `primary_conninfo`, then start that rebuilt standby on the freed lab port and verify catch-up. The original A directory is never overwritten.

**Use only the CI workflow or an equally isolated approved lab.** Do not copy its stop/promote actions into a shared, staging or production system. Failed fencing or inconsistent identity blocks promotion; all live enterprise fencing, actual rewind, application routing, PITR and business RPO/RTO acceptance remain mandatory, independent gates.

## 6. Acceptance

**Pass:** single-writer fencing demonstrated, candidate selection evidence recorded, promotion verified, timeline divergence explained, rejoin approach justified, and RPO/RTO measured. **Runtime:** pending.
