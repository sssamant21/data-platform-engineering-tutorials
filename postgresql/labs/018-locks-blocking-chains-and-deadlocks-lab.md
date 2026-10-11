# Lab 018 — Lock Chains, Queued Strong Locks and Deadlocks

**Audience:** DBRE/SRE. **Baseline:** Chapter 004 PostgreSQL 18 Linux lab.
**Duration:** 90–120 minutes; four terminals.
**Runtime execution:** Pending.

[Chapter](../chapters/018-locks-blocking-chains-and-deadlocks.md) · [Setup](004-reproducible-postgresql-operations-lab.md) · [Provisioning](../scripts/018-provision-lock-lab.sql) · [Reset](../scripts/018-reset-lock-lab.sql) · [Inspector](../scripts/018-lock-chain-inspection.sql)

Actors A/B/C use lab_app; D uses the observer/admin. All target the same primary and only c018_locks fixtures. Prepare the observer terminal before starting waits. Complete each live wait observation/release within its 90-second lock budget; otherwise roll actors back and rerun the phase.

## 1. Guard and functions in every terminal

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
  PGAPPNAME=chapter018-control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
actor_018() {
  local actor="$1"; shift
  case "$actor" in A|B|C) ;; *) return 2;; esac
  PGAPPNAME="chapter018-$actor" psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
observe_018() {
  PGAPPNAME=chapter018-observer psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
    -f scripts/018-lock-chain-inspection.sql
}
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(lab_sql -Atc "SELECT setting FROM pg_settings WHERE name='deadlock_timeout'")" == 1000 ]] || exit 2
~~~

The last guard requires the lab's default one-second deadlock check, expressed as 1000ms. If different, inspect previous changes; do not alter the production-like global setting to force the test.

D provisions once:

~~~bash
bash scripts/004-operations-lab.sh verify
lab_sql -f scripts/018-provision-lock-lab.sql
lab_sql -c 'SELECT id,quantity FROM c018_locks.probe ORDER BY id;'
observe_018
~~~

Expected rows (1,100),(2,200). Occupied schema is refused.

A/B/C open actor_018 A, actor_018 B, actor_018 C respectively. At each prompt:

~~~text
\set VERBOSITY verbose
SET statement_timeout='120s';
SET lock_timeout='90s';
~~~

These larger actor budgets allow manual observation, not unlimited waiting. Observer/admin commands remain short. Do not issue another command in a terminal while its query is waiting.

## 2. Row chain: C waits for B, B waits for A

A:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+10 WHERE id=1;
~~~

Leave A idle in transaction.

B:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+20 WHERE id=2;
UPDATE c018_locks.probe SET quantity=quantity+20 WHERE id=1;
~~~

The last statement waits for A; B already holds row 2.

C:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+30 WHERE id=2;
~~~

C waits for B. D immediately runs observe_018. Require blocking edges C→B and B→A, with A a root candidate. Inspect Lock waits, transaction-ID locks, held relation modes and actor transaction state. Exact raw lock rows can vary.

Release only the root in A:

~~~sql
ROLLBACK;
~~~

B's pending UPDATE should complete. C remains blocked because B still holds row 2. D observes again: B is now C's root candidate.

B:

~~~sql
ROLLBACK;
~~~

C's UPDATE completes. C:

~~~sql
ROLLBACK;
~~~

D runs the following only after all three rollbacks, and requires quantities 100/200 and no actor waits:

~~~bash
lab_sql -c 'SELECT id,quantity FROM c018_locks.probe ORDER BY id;'
observe_018
~~~

Releasing A alone did not resolve every dependency.

## 3. NOWAIT and SKIP LOCKED

A:

~~~sql
BEGIN;
SELECT id FROM c018_locks.probe WHERE id=1 FOR UPDATE;
~~~

C:

~~~sql
BEGIN;
SELECT id FROM c018_locks.probe WHERE id=1 FOR UPDATE NOWAIT;
~~~

Require immediate 55P03. C rolls back the failed transaction, then:

~~~sql
ROLLBACK;
BEGIN;
SELECT id FROM c018_locks.probe ORDER BY id FOR UPDATE SKIP LOCKED;
ROLLBACK;
~~~

Expected only ID 2. This is an intentionally incomplete view, not a corrected report. A rolls back.

## 4. Queued strong lock blocks a later reader

D resets after all actors finish. A:

~~~sql
BEGIN;
SELECT * FROM c018_locks.probe;
~~~

A holds AccessShareLock through its open transaction.

B:

~~~sql
BEGIN;
LOCK TABLE c018_locks.probe IN ACCESS EXCLUSIVE MODE;
~~~

B waits. The lab's scoped UPDATE grant permits this explicit mode; no owner-level DDL is executed.

Only after B is waiting, C runs a plain SELECT outside an explicit transaction:

~~~sql
SELECT * FROM c018_locks.probe;
~~~

C can queue behind B's strong request. D runs observe_018 and records C→B→A, B's ungranted AccessExclusiveLock and C's read request. B is a soft blocker before holding the lock.

A ROLLBACK lets B acquire the lock, but C stays blocked. B ROLLBACK releases it; C returns both rows. This simulates a strong-lock migration convoy without schema changes.

If C ran before B queued, it may complete normally. That is a different schedule; rerun the phase rather than claiming the convoy.

## 5. Controlled opposite-order deadlock

D resets. A:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=1;
~~~

B:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=2;
~~~

A requests B's row and waits:

~~~sql
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=2;
~~~

B now requests A's row:

~~~sql
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=1;
~~~

Require 40P01 in one participant after deadlock detection. Do not assume A or B is the victim. The error can resolve the cycle before D captures a live graph; record client verbose detail and the protected primary log.

Victim: explicitly ROLLBACK. Survivor: after its pending UPDATE completes, COMMIT. D:

~~~bash
lab_sql -c 'SELECT id,quantity FROM c018_locks.probe ORDER BY id;'
observe_018
tail -n 80 "$PG_LAB_ROOT/logs/primary.log"
~~~

Require final quantities 101/201: one full two-row increment committed, the victim's work did not. Record the database deadlock counter and stats_reset as supporting evidence; publication timing/counter history is not an exact standalone pass criterion.

55P03/57014 instead of 40P01 means a budget or schedule failure, not a passing deadlock. Roll actors back, inspect settings and rerun safely.

## 6. Consistent row order prevents this cycle

D resets. A:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=1;
~~~

B:

~~~sql
BEGIN;
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=1;
~~~

B waits on row 1. A continues in the agreed order:

~~~sql
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=2;
COMMIT;
~~~

B's first UPDATE completes, then B:

~~~sql
UPDATE c018_locks.probe SET quantity=quantity+1 WHERE id=2;
COMMIT;
~~~

D reads the fixture after both commits:

~~~bash
lab_sql -c 'SELECT id,quantity FROM c018_locks.probe ORDER BY id;'
observe_018
~~~

Require final quantities 102/202 and both transactions committed without a deadlock. This prevents the fixture's opposite-order cycle; other tables/triggers/advisory resources need their own complete ordering review.

## 7. Acceptance and cleanup

| Evidence | Required observation |
|---|---|
| Row chain | C→B→A; idle root and resource evidence |
| Root release | B continues while C remains blocked |
| Intermediate release | C continues; all phase writes rolled back |
| NOWAIT | Correct immediate 55P03 |
| SKIP LOCKED | Only unlocked row returned |
| Queued strong lock | Later reader waits behind B; original reader is root |
| Deadlock | One 40P01 victim; survivor commits; rows 101/201 |
| Consistent order | Both complete; rows 102/202 |
| Restoration | Exercise objects absent; original topology/probe healthy |

The inspector is bounded to three actor labels, depth eight and 20 prepared-transaction rows. It is metadata-only and samples changing state. Reading the fixture itself during a queued/held AccessExclusive lock would also block an observer; run data checks only after release. Do not use an out-of-scope root candidate as automatic termination authorization.

A/B/C roll back any remaining transaction and exit with \q. D:

~~~bash
lab_sql -f scripts/018-reset-lock-lab.sql
lab_sql <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DROP TABLE c018_locks.probe;
DROP SCHEMA c018_locks;
COMMIT;
SELECT count(*) AS remaining_exercise_schemas FROM pg_namespace WHERE nspname='c018_locks';
SQL
bash scripts/004-operations-lab.sh verify
~~~

Require zero schemas and original primary/two-standby/probe success. No global timeout, password, HBA policy or listener changed. Preserve sanitized schedules, PIDs/backend starts, lock edges, SQLSTATEs and final row outcomes. Runtime execution remains pending.

If interrupted or a timeout fires, stop issuing business commands, explicitly roll all actors back and inspect before resetting. Do not add CASCADE or terminate unrelated sessions to force cleanup.
