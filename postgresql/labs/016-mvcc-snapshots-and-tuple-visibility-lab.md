# Lab 016 — MVCC, Snapshots and Tuple Visibility

**Audience:** DBRE/SRE. **Baseline:** disposable Chapter 004 PostgreSQL 18 primary.
**Duration:** 75–100 minutes; three terminals.
**Runtime verification:** Pending.

[Chapter](../chapters/016-mvcc-snapshots-and-tuple-visibility.md) · [Existing setup](004-reproducible-postgresql-operations-lab.md) · [Provisioning](../scripts/016-provision-mvcc-lab.sql) · [Inspection](../scripts/016-mvcc-inspection.sql)

Terminal A is the reader, B the writer, C the observer/administrator. All connect to the same primary, so replica lag is not part of the experiment. The isolated c016_mvcc schema is the only data scope changed.

## 1. Guard and functions in every terminal

Export the existing PG_LAB_ROOT printed by Chapter 004. Run from the repository's postgresql directory:

~~~bash
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable
lab_sql() {
  PGAPPNAME=chapter016-control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
mvcc_reader() {
  PGAPPNAME=chapter016-reader psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
mvcc_writer() {
  PGAPPNAME=chapter016-writer psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
mvcc_observe() {
  PGAPPNAME=chapter016-observer psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
    -f scripts/016-mvcc-inspection.sql
}
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
~~~

Terminal C only:

~~~bash
bash scripts/004-operations-lab.sh verify
lab_sql -f scripts/016-provision-mvcc-lab.sql
mvcc_observe
~~~

Expected rows (1,100) and (2,200). Provisioning rejects an occupied schema. lab_app receives DML only on this new fixture; its existing public.lab_probe grants are unchanged.

## 2. Read Committed: uncommitted writer stays hidden

Terminal A starts mvcc_reader; at its psql prompt:

~~~sql
SET statement_timeout='5s';
SET lock_timeout='1s';
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT pg_backend_pid(),pg_current_snapshot()::text;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe ORDER BY id;
~~~

Expected ID 1 value 100. Leave the transaction open.

Terminal B starts mvcc_writer:

~~~sql
SET statement_timeout='5s';
SET lock_timeout='1s';
BEGIN;
UPDATE c016_mvcc.probe SET value=110 WHERE id=1;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe WHERE id=1;
~~~

Expected writer sees 110 before commit. Leave it open.

Terminal A:

~~~sql
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe WHERE id=1;
~~~

Expected 100 promptly: no dirty read and no row-update wait for this plain SELECT. Do not add FOR UPDATE.

Terminal C runs mvcc_observe. Record writer backend_xid/state and reader state. Read Committed may release its statement horizon while idle; do not require its backend_xmin to remain populated.

As a separate bounded writer-conflict check in C:

~~~bash
if lab_sql -v VERBOSITY=verbose \
  -c "SET statement_timeout='5s'; SET lock_timeout='1s'; UPDATE c016_mvcc.probe SET value=value+1 WHERE id=1;"; then
  echo 'FAIL: second writer unexpectedly completed; check the intended open writer transaction.'
else
  echo 'Require SQLSTATE 55P03 from lock_timeout, not a connection/syntax error.'
fi
~~~

Expected lock timeout while B holds the row update. This command's failed implicit transaction commits no change. Other error codes are not a pass.

Terminal B:

~~~sql
COMMIT;
~~~

Terminal A, in the same open Read Committed transaction:

~~~sql
SELECT pg_current_snapshot()::text;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe WHERE id=1;
COMMIT;
~~~

Expected 110. Compare actual metadata with the earlier version; do not assume exact XIDs or tuple locations. A new statement can observe the commit without reconnecting or beginning another transaction.

## 3. Rollback preserves the prior visible value

Terminal B:

~~~sql
BEGIN;
UPDATE c016_mvcc.probe SET value=999 WHERE id=1;
SELECT id,value FROM c016_mvcc.probe WHERE id=1;
~~~

Expected own-write 999. Terminal A, outside a transaction, still sees 110:

~~~sql
SELECT id,value FROM c016_mvcc.probe WHERE id=1;
~~~

Terminal B:

~~~sql
ROLLBACK;
SELECT id,value FROM c016_mvcc.probe WHERE id=1;
~~~

Expected 110 after rollback. A physical aborted version may remain until pruning/vacuum; logical rollback does not promise instant file shrink.

## 4. Repeatable Read retains updated and deleted versions

Terminal A:

~~~sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT pg_current_snapshot()::text AS held_snapshot;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe ORDER BY id;
~~~

This explicitly establishes a data snapshot. Expected (1,110) and (2,200). Leave it open.

Terminal B:

~~~sql
BEGIN;
UPDATE c016_mvcc.probe SET value=140 WHERE id=1;
DELETE FROM c016_mvcc.probe WHERE id=2;
COMMIT;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe ORDER BY id;
~~~

Expected fresh view: only (1,140).

Terminal A:

~~~sql
SELECT pg_current_snapshot()::text AS held_snapshot;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe ORDER BY id;
~~~

Expected stable snapshot and both old rows (1,110),(2,200). Tuple xmax may now be nonzero even though the old version remains visible to A. Interpret it with snapshot/transaction state, not as an unconditional deletion flag.

Terminal C:

~~~bash
mvcc_observe
lab_sql -c 'VACUUM (VERBOSE,ANALYZE) c016_mvcc.probe;'
mvcc_observe
~~~

Record A's backend_xmin and transaction age, and the actual verbose vacuum output. Run VACUUM outside a transaction block. Ordinary VACUUM can run alongside this plain reader, but cannot remove versions still needed by the retained snapshot.

Exact removed/dead-tuple counters may vary due to pruning/statistics; they are not hard-coded acceptance numbers. Other horizon sources also exist, so inspect the reported slots/prepared transactions instead of attributing every retained tuple to one session blindly.

Terminal A queries again:

~~~sql
SELECT id,value FROM c016_mvcc.probe ORDER BY id;
~~~

Expected the same two old rows after VACUUM. This is direct visibility evidence that the snapshot's required data was preserved.

## 5. Release the horizon and observe fresh visibility

Terminal A:

~~~sql
COMMIT;
SELECT id,value,xmin::text,xmax::text,ctid FROM c016_mvcc.probe ORDER BY id;
~~~

Expected only (1,140). Ending the reader did not undo B's committed update/delete.

Terminal C:

~~~bash
lab_sql -c 'VACUUM (VERBOSE,ANALYZE) c016_mvcc.probe;'
mvcc_observe
~~~

Record released reader horizon and new vacuum output. Old versions are now eligible for reclamation if no other relevant horizon retains them. Do not require relation file size to shrink or n_dead_tup to become exactly zero immediately.

## 6. Evidence and troubleshooting

| Evidence | Required observation |
|---|---|
| Baseline | Correct primary; two expected fixtures |
| Uncommitted update | Writer sees 110; reader sees 100 |
| Writer conflict | Second writer receives 55P03 within bounded wait |
| Read Committed refresh | Same reader transaction sees 110 after writer commit |
| Rollback | Own 999 disappears; committed 110 remains |
| Held snapshot | Repeatable Read retains old updated/deleted rows |
| Horizon | Retained reader backend_xmin and transaction-age evidence |
| Vacuum | Actual output; old data still visible to A afterward |
| Release | Fresh reader sees only (1,140); horizon released |
| Restoration | Exercise objects/sessions removed; original topology healthy |

If the reader sees a new value too early, check that its first snapshot preceded B's commit and that it really used Repeatable Read. If a plain reader blocks, inspect DDL/explicit lock behavior and verify the statement was not changed to a locking read.

If VACUUM cannot run, confirm Terminal C used its standalone command and the correct administrative role. An empty pg_stat_progress_vacuum view after a tiny vacuum is not proof it did not run.

The inspector samples only the three named exercise sessions, limits slot/prepared listings and reports counts. It is not a complete production incident inventory. Query text is omitted.

## 7. Cleanup

In A and B, finish any open transaction with ROLLBACK and exit with \q. Before cleanup, inspect whether any exercise sessions remain in a transaction:

~~~bash
lab_sql -c "SELECT pid,application_name,state,xact_start FROM pg_stat_activity
WHERE application_name IN ('chapter016-reader','chapter016-writer')
AND xact_start IS NOT NULL;"
~~~

Require no remaining exercise transaction. Drop only the isolated fixture:

~~~bash
lab_sql <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DROP TABLE c016_mvcc.probe;
DROP SCHEMA c016_mvcc;
COMMIT;
SELECT count(*) AS remaining_exercise_schemas FROM pg_namespace WHERE nspname='c016_mvcc';
SQL
bash scripts/004-operations-lab.sh verify
~~~

Expected zero schemas and original primary/two-standby/probe success. A lock timeout during cleanup is a reason to inspect the remaining session, not add CASCADE or terminate unrelated clients.

Keep sanitized evidence of actual row/snapshot/horizon behavior. Execution remains pending until the multi-session sequence is run.
