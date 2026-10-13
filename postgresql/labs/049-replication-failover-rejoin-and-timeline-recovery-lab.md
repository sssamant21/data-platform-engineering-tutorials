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

On disposable instances only, have the operator confirm fencing and candidate readiness, then manually promote the selected standby according to the documented PostgreSQL procedure. The lab intentionally provides **no automatic promotion script**. Verify `pg_is_in_recovery() = false` on the new primary and confirm application routing targets only one writable instance.

## 4. pg_rewind assessment

For the **stopped, fenced** former primary, confirm common ancestry, compatible PostgreSQL major version, `wal_log_hints` or data checksums, `full_page_writes`, and required WAL availability. Record dry-run output:

```bash
pg_rewind --dry-run --target-pgdata=/isolated/old-primary-pgdata \
  --source-server="host=new-primary port=5432 user=rewind_user dbname=postgres"
```

Do not run actual rewind without approved target backup, target ownership checks, credentials, and documented rejoin plan. If prerequisites fail, use a fresh verified base backup.

## 5. Rejoin verification

Reconfigure the former primary as a standby only after successful rewind/rebuild and approval. Check streaming connection, replay catch-up, slot status, timeline continuity and application read routing. Never restart the old primary in writable mode after a new primary has been promoted.

## 6. Acceptance

**Pass:** single-writer fencing demonstrated, candidate selection evidence recorded, promotion verified, timeline divergence explained, rejoin approach justified, and RPO/RTO measured. **Runtime:** pending.
