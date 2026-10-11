# Lab 017 — Isolation Levels and Application Failure Patterns

**Audience:** DBRE/SRE. **Baseline:** Chapter 004 PostgreSQL 18 Linux lab.
**Duration:** 90–120 minutes. **Concurrency execution:** Pending.

[Chapter](../chapters/017-isolation-levels-and-application-failure-patterns.md) · [Setup](004-reproducible-postgresql-operations-lab.md) · [Provisioning](../scripts/017-provision-isolation-lab.sql) · [Reset](../scripts/017-reset-isolation-lab.sql) · [Observer](../scripts/017-isolation-inspection.sql) · [Retry pattern](../scripts/017-transaction-retry-pattern.py)

Use actor terminals A/B and administrator/observer C. All connect to the same disposable primary. Only c017_iso fixtures change. Do not wrap all phases in one script: the ordering between sessions is the trigger.

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
  PGAPPNAME=chapter017-control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
actor_a() {
  PGAPPNAME=chapter017-A psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
actor_b() {
  PGAPPNAME=chapter017-B psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
observe_017() {
  PGAPPNAME=chapter017-observer psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
    -f scripts/017-isolation-inspection.sql
}
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
~~~

Terminal C provisions once:

~~~bash
bash scripts/004-operations-lab.sh verify
lab_sql -f scripts/017-provision-isolation-lab.sql
observe_017
~~~

Expected units 100 and two on-call rows. Occupied schema is refused.

A starts actor_a, B starts actor_b. At both psql prompts:

~~~text
\set VERBOSITY verbose
SET statement_timeout='5s';
SET lock_timeout='1s';
~~~

Expected errors remain at the interactive prompt. Capture their SQLSTATE. Before each reset, COMMIT successful phases or ROLLBACK failed/open transactions in both actors.

## 2. Read Committed cached-value overwrite

A:

~~~sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT units FROM c017_iso.counter WHERE id=1;
~~~

B, before A writes:

~~~sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT units FROM c017_iso.counter WHERE id=1;
~~~

Both read 100. Simulate application arithmetic cached outside SQL.

A writes its planned decrement of 10:

~~~sql
UPDATE c017_iso.counter SET units=90 WHERE id=1;
COMMIT;
~~~

B writes its already computed value for a decrement of 20:

~~~sql
UPDATE c017_iso.counter SET units=80 WHERE id=1;
COMMIT;
~~~

C observes: final units 80, not the intended 70. Both transactions succeeded; there was no dirty read. B could have reread but did not.

Reset from C after both actors finish:

~~~bash
lab_sql -f scripts/017-reset-isolation-lab.sql
~~~

Repeat the two Read Committed transactions, but use these updates instead of absolute cached values:

A:

~~~sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT units FROM c017_iso.counter WHERE id=1;
~~~

B:

~~~sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT units FROM c017_iso.counter WHERE id=1;
~~~

A, then commit before B updates:

~~~sql
UPDATE c017_iso.counter SET units=units-10 WHERE id=1 AND units>=10 RETURNING units;
COMMIT;
~~~

B:

~~~sql
UPDATE c017_iso.counter SET units=units-20 WHERE id=1 AND units>=20 RETURNING units;
COMMIT;
~~~

C requires final units 70. This single-row pattern incorporates the current row and a capacity guard; it is not a universal multi-row invariant solution.

## 3. Repeatable Read concurrent-update failure

C resets. A:

~~~sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT units FROM c017_iso.counter WHERE id=1;
~~~

Expected 100. B:

~~~sql
BEGIN ISOLATION LEVEL READ COMMITTED;
UPDATE c017_iso.counter SET units=units-10 WHERE id=1;
COMMIT;
~~~

A now attempts its stale decision:

~~~sql
UPDATE c017_iso.counter SET units=80 WHERE id=1;
~~~

Require 40001. Before rollback, A tries:

~~~sql
SELECT 1;
~~~

Require 25P02: this is the secondary aborted-transaction error, not the original cause.

A starts a full retry after rollback:

~~~sql
ROLLBACK;
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT units FROM c017_iso.counter WHERE id=1;
UPDATE c017_iso.counter SET units=units-20 WHERE id=1 AND units>=20 RETURNING units;
COMMIT;
~~~

Require fresh input 90 and final units 70. The retry reread the decision data rather than replaying an old absolute value.

## 4. Repeatable Read write skew

C resets. The invariant is at least one on-call worker.

A:

~~~sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM c017_iso.roster WHERE on_call;
~~~

B, before either updates:

~~~sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM c017_iso.roster WHERE on_call;
~~~

Both see 2. A then B update different rows:

A:

~~~sql
UPDATE c017_iso.roster SET on_call=false WHERE id=1;
~~~

B:

~~~sql
UPDATE c017_iso.roster SET on_call=false WHERE id=2;
~~~

COMMIT in A and B. C runs observe_017 and requires on_call_count 0 / invariant false. Both decisions used stable snapshots, but the combined committed result violated the cross-row rule.

No other actor may write these fixtures. If a different error occurs, investigate the schedule rather than claiming the anomaly.

## 5. Serializable detects the incompatible schedule

C resets. A:

~~~sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM c017_iso.roster WHERE on_call;
~~~

B:

~~~sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM c017_iso.roster WHERE on_call;
~~~

Both must read 2 before either writes. C can observe SIReadLock metadata and backend state; these predicate-read locks are not ordinary blockers.

A attempts:

~~~sql
UPDATE c017_iso.roster SET on_call=false WHERE id=1;
~~~

B attempts:

~~~sql
UPDATE c017_iso.roster SET on_call=false WHERE id=2;
~~~

Then attempt COMMIT in each actor that has not already failed. At least one must receive 40001 before both incompatible changes can commit. The victim and failure point can vary; do not require a particular actor or message.

If UPDATE or COMMIT fails, explicitly ROLLBACK in that actor and defer its business retry until the other actor finishes. Do not continue issuing business statements in an aborted block.

C runs observe_017. Require the invariant true. Record which worker remains on call and which actor was rejected.

Retry the rejected operation in a **new Serializable transaction** using its own worker ID. Replace the example ID 1 below with 2 if B was rejected:

~~~sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) AS fresh_on_call_count FROM c017_iso.roster WHERE on_call;
UPDATE c017_iso.roster SET on_call=false
WHERE id=1 AND (SELECT count(*) FROM c017_iso.roster WHERE on_call)>1;
COMMIT;
~~~

Expected fresh count 1, UPDATE 0 and invariant still true. The correct business result is declining the last worker's request, not forcing the first attempt's decision through.

If both initial writes unexpectedly fail, roll both back, inspect other writers/schedule, and rerun from reset. Do not invent a successful concurrent outcome.

## 6. Retry-helper boundary review

The Python helper is an importable teaching function, not an executable database client. Its factory must open a fresh compatible non-autocommit connection; the callback must rerun all decision reads and transactional SQL.

Review that failure on COMMIT is inside the retry boundary; only 40001/40P01 retry, rollback/close occur before jitter, and success returns after commit. Do not place external side effects or callback-owned commits inside it.

Fixture tests of its orchestration do not verify real PostgreSQL conflicts, pool integration or application idempotency. Production testing must include all three.

## 7. Acceptance and cleanup

| Evidence | Required observation |
|---|---|
| Cached overwrite | Two RC successes leave 80 |
| Atomic change | Both decrements preserved; final 70 |
| RR same-row conflict | 40001, then 25P02 before rollback |
| RR retry | Fresh 90 becomes 70 |
| RR write skew | Both commit; on-call invariant false |
| Serializable schedule | At least one 40001; incompatible result cannot commit |
| Business retry | Fresh decision declines last-worker removal |
| Observer | Actual session/lock metadata; no inference from missing blockers alone |
| Restoration | Fixture schema absent; original topology/probe healthy |

Retain ordered session actions, isolation levels, actual SQLSTATEs, commit outcomes and invariant checks. Keep statement timing/labels so another operator can reproduce the schedule.

In A/B, ROLLBACK any remaining transaction and exit with \q. C resets to verify no active actor transactions, then drops only the exercise objects:

~~~bash
lab_sql -f scripts/017-reset-isolation-lab.sql
lab_sql <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DROP TABLE c017_iso.counter;
DROP TABLE c017_iso.roster;
DROP SCHEMA c017_iso;
COMMIT;
SELECT count(*) AS remaining_exercise_schemas FROM pg_namespace WHERE nspname='c017_iso';
SQL
bash scripts/004-operations-lab.sh verify
~~~

Require zero schemas and original primary/two-standby/probe success. Lock timeouts are a reason to inspect sessions, not add CASCADE or kill unrelated clients.

No global/default isolation setting, role attribute, password or HBA policy changed. Real lab execution remains pending.
