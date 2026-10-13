# Chapter 067 — Streaming Replication and HA Architecture Lab

**PostgreSQL 18 · Isolated lab only · Runtime pending**

## 1. Safety and prerequisites

Provision two **disposable** PostgreSQL 18 instances on different ports/hosts: primary and standby. Confirm standby PGDATA is unused/empty, and both instances have separate storage, unique ports and credentials. Never run pg_basebackup into an active PGDATA. Keep production network endpoints out of the lab.

## 2. Primary preflight

On the primary, inspect wal_level, max_wal_senders, max_replication_slots, hot_standby and wal_keep_size using [067-replication-inspect.sql](../labs/sql/067-replication-inspect.sql). Configure wal_level=replica, sufficient sender capacity, a dedicated REPLICATION role and a narrowly scoped pg_hba.conf rule. Prefer TLS and protected password files; do not commit secrets.

## 3. Initialize standby

With the **standby stopped** and its target directory empty, run from the standby host:

```bash
pg_basebackup -h PRIMARY_LAB_HOST -p 5432 -U repl_lab -D /var/lib/postgresql/standby067 -Fp -X stream -P -R
```

Replace PRIMARY_LAB_HOST with a verified lab-only address. The -R option writes standby.signal and primary_conninfo into the backup; inspect those values and secure any generated credentials. Start the standby on its own lab port after reviewing config and filesystem ownership.

## 4. Verify streaming

On the primary:

```sql
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
```

On the standby:

```sql
SELECT pg_is_in_recovery(),pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn();
SELECT status,receive_start_lsn,latest_end_lsn FROM pg_stat_wal_receiver;
```

Expected: standby in recovery, streaming sender visible on primary, receiver active on standby.

## 5. Data propagation test

Create a disposable database/table on the primary, insert a known unique marker and commit. Query the marker on standby after replay catches up. Record source commit time, standby visibility time and relevant LSNs. Do not infer lag solely from last_xact_replay_timestamp on an idle system.

## 6. Controlled lag observation

Apply a bounded burst of inserts in the lab and observe receive/replay LSN movement and lag. Stop if WAL retention, disk, CPU or memory thresholds are exceeded. Do not artificially block replay on production.

## 7. HA safety exercise

Document the required DCS/quorum, fencing, promotion, routing, old-primary rejoin and rollback process. **Do not promote** a standby while the primary is accepting writes. If failover is tested, first isolate/fence the primary in the lab and use a verified orchestration runbook.

## 8. Acceptance

| Gate | Expected | Status |
|---|---|---|
| Primary and standby isolated | Unique PGDATA and endpoints | Pending |
| Streaming sender/receiver | Connected and healthy | Pending |
| Standby read-only | pg_is_in_recovery() true | Pending |
| Test marker replicated | Verified after commit | Pending |
| Lag measurement | LSN and timing recorded | Pending |
| WAL retention budget | Documented | Pending |
| HA fencing plan | Documented and reviewed | Pending |
| Backup/PITR independence | Verified policy | Pending |

**Runtime:** pending.
