# Lab 020 — Safe Intervention in a Concurrency Incident

Audience: DBRE/SRE. PostgreSQL 18; Chapter 004 disposable primary.
Status: authored/static reviewed; runtime verification pending.

[Chapter](../chapters/020-safe-cancellation-termination-and-concurrency-incident-lab.md) · [Snapshot](../scripts/020-concurrency-incident-snapshot.sql) · [Signal helper](../scripts/020-reviewed-session-signal.sql)

## Scenario and bounds

A holds row 1. B holds row 2 and waits on row 1. C waits on row 2. You will inspect the chain, cancel B, verify A remains, reject stale targeting, then terminate the specifically reviewed idle holder A in a second phase.

Expected final values are row 1 = 100 and row 2 = 200. Every fixture mutation is rolled back. Use four terminals A, B, C and O. O acts as operator; actors use lab_app. No service restart, OS kill, prepared transaction or global configuration change is part of this lab.

The 90-second lock budget, 120-second statement budget and 180-second transaction/inactivity budgets are guardrails, not production recommendations. Prepare O's helper before creating waits. If a budget expires while you are reading, recover actors and recreate the phase. Never signal a previously captured target without reviewing fresh evidence.

## 1. Guard the disposable cluster

Start the Chapter 004 lab as its non-root owner. Finish earlier fixture cleanup. In each terminal run:

~~~bash
set -euo pipefail
test -n "$PG_LAB_ROOT"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c020_control PGOPTIONS='-c statement_timeout=8s -c lock_timeout=1s -c timezone=UTC' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
actor() {
  PGAPPNAME="$1" PGOPTIONS='-c statement_timeout=120s -c lock_timeout=90s -c transaction_timeout=180s -c idle_in_transaction_session_timeout=180s -c idle_session_timeout=0 -c timezone=UTC' \
    psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
}
snapshot() {
  PGAPPNAME=c020_observer PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_observer -d ops_lab -f postgresql/scripts/020-concurrency-incident-snapshot.sql
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
~~~

Run from repository root or adjust the two script paths. Do not expose passfile contents. The SQL signal helper cannot validate a filesystem marker by itself; always use this guarded connection path.

In O, provision:

~~~bash
admin <<'SQL'
BEGIN;
CREATE SCHEMA c020_incident AUTHORIZATION lab_admin;
CREATE TABLE c020_incident.balance (id integer PRIMARY KEY, value integer NOT NULL);
INSERT INTO c020_incident.balance VALUES (1,100),(2,200);
GRANT USAGE ON SCHEMA c020_incident TO lab_app, lab_observer;
GRANT SELECT, UPDATE ON c020_incident.balance TO lab_app;
GRANT SELECT ON c020_incident.balance TO lab_observer;
COMMIT;
SQL
~~~

Existing schema is a failed precondition: investigate rather than overwrite it.

## 2. Prepare reviewed actuation

In O define this helper. It accepts only cancel or terminate and prompts for the exact fields from the latest snapshot. Do not enter arbitrary PIDs.

~~~bash
reviewed_signal() {
  local requested_action="$1"
  local reviewed_pid reviewed_start reviewed_state reviewed_query_start reviewed_app
  case "$requested_action" in cancel|terminate) ;; *) return 2 ;; esac
  read -r -p "Reviewed PID: " reviewed_pid
  read -r -p "Reviewed backend_start, including UTC offset: " reviewed_start
  read -r -p "Reviewed state: " reviewed_state
  read -r -p "Reviewed query_start, including UTC offset: " reviewed_query_start
  read -r -p "Reviewed application_name: " reviewed_app
  admin -v action="$requested_action" -v confirm=yes \
    -v target_pid="$reviewed_pid" -v target_start="$reviewed_start" \
    -v target_state="$reviewed_state" -v target_query_start="$reviewed_query_start" \
    -v target_app="$reviewed_app" \
    -f postgresql/scripts/020-reviewed-session-signal.sql
}
~~~

Calling this helper represents your explicit decision for that one reviewed lab actor. There is no automatic selection or escalation. Bad input, state changes or identity mismatches do not broaden its filters. Zero rows means no matching signal call; a permission error is not permission to grant yourself broader privileges.

A returned signal_result true still needs follow-up observation. A false result, warning or administrative timeout requires inspection before another action. Signals cannot be undone by rolling back the administrative connection.

## 3. Build the three-session chain

Open A with actor c020_A, B with actor c020_B and C with actor c020_C. In each:

~~~sql
\set VERBOSITY verbose
\set ON_ERROR_STOP off
\set ON_ERROR_ROLLBACK off
\pset pager off
SELECT pg_backend_pid(), backend_start
FROM pg_stat_activity WHERE pid=pg_backend_pid();
SHOW statement_timeout;
SHOW lock_timeout;
SHOW transaction_timeout;
SHOW idle_in_transaction_session_timeout;
~~~

Keep each original PID/start-time pair. Interactive expected errors must not be hidden by automatic savepoint recovery. Setup and operator scripts retain ON_ERROR_STOP.

In A:

~~~sql
BEGIN;
UPDATE c020_incident.balance SET value=101 WHERE id=1;
~~~

Leave A at its prompt. In B:

~~~sql
BEGIN;
UPDATE c020_incident.balance SET value=201 WHERE id=2;
UPDATE c020_incident.balance SET value=102 WHERE id=1;
~~~

B's second UPDATE waits. In C:

~~~sql
BEGIN;
UPDATE c020_incident.balance SET value=202 WHERE id=2;
~~~

C waits. Run snapshot in O. Required evidence: A idle in transaction, B active with Lock wait and direct blocker A, C active with Lock wait and direct blocker B. Labels alone are insufficient; correlate recorded backend identities.

Do not run SELECT on the fixture from O. Metadata inspection must remain available even when application relations are locked.

If you see a zero blocker or an edge outside these three actors, stop actuation and investigate. The lab contains no prepared transaction and no legitimate external blocker.

## 4. Cancel the middle waiter

In O, review B's latest row and run reviewed_signal cancel, entering B's identity, active state and query_start. Record result and timestamp.

Expected: B reports 57014. Its failed transaction abort releases the row-2 lock, allowing C's UPDATE to complete; C can now be idle in its own transaction. Do not expect C's uncommitted value to be durable.

In B:

~~~sql
SELECT 1;
ROLLBACK;
~~~

Expect 25P02 then successful rollback. In C issue ROLLBACK.

Run snapshot again. A should still be idle in transaction holding its row-1 change. B and C are no longer waiting. Canceling B did not close A's transaction.

For a deliberate stale-target test, invoke reviewed_signal cancel with B's original captured fields from its canceled UPDATE. Expect zero rows because B's state/query_start changed. Capture that refusal. Never relax the filters to make stale targeting succeed.

Have A ROLLBACK. O can now safely check:

~~~bash
admin -c 'SELECT id,value FROM c020_incident.balance ORDER BY id;'
~~~

Expect 100 and 200. If another timeout fired first, retain its SQLSTATE and rebuild this phase in fresh transactions.

## 5. Idle cancellation is not transaction closure

In A start a fresh transaction:

~~~sql
BEGIN;
UPDATE c020_incident.balance SET value=111 WHERE id=1;
~~~

Run snapshot. A is idle in transaction. reviewed_signal cancel with its fresh idle identity refuses to act because cancellation in this helper requires active state.

For this one controlled demonstration, run admin in O's shell to open the guarded interactive admin connection. Copy A's exact PID/start/query timestamps from the fresh snapshot into the following psql variables. Replace each placeholder; do not leave angle-bracket text:

~~~sql
\set a_pid '<reviewed A PID>'
\set a_start '<reviewed A backend_start with offset>'
\set a_query_start '<reviewed A query_start with offset>'
SELECT pg_cancel_backend(a.pid) AS idle_cancel_signal_sent
FROM pg_stat_activity a
WHERE a.pid=:'a_pid'::integer
  AND a.backend_start=:'a_start'::timestamptz
  AND a.query_start=:'a_query_start'::timestamptz
  AND a.datname='ops_lab' AND a.usename='lab_app'
  AND a.application_name='c020_A'
  AND a.backend_type='client backend'
  AND a.state='idle in transaction'
  AND a.pid<>pg_backend_pid();
~~~

This exception demonstrates server behavior only; it is not the production procedure. True reports signal delivery. Quit O's interactive connection with \q to return to its shell. Collect again without commands in A: its transaction should remain open. Do not use idle cancellation as a rollback substitute.

In B:

~~~sql
BEGIN;
UPDATE c020_incident.balance SET value=112 WHERE id=1;
~~~

B waits, proving A still retains the conflicting lock. Prepare the next action promptly within the phase budgets.

## 6. Terminate the specifically reviewed holder

Review a fresh snapshot of A and B. Select A based on its ownership and impact; record why owner rollback is deliberately unavailable in this exercise.

In O call reviewed_signal terminate using A's fresh idle state and exact identity. The SQL helper uses a three-second termination wait, under its eight-second administrative statement budget.

Expected: A's original backend exits; B's UPDATE completes after A's uncommitted change rolls back. A may only discover FATAL 57P01 on its next command and interactive psql may reconnect. A connection labeled c020_A with a different PID/start is a replacement. Quit it.

B issues ROLLBACK. O verifies A's original PID/start pair is absent using snapshot, then checks fixture values: 100 and 200.

Do not retry a production request merely because its session was lost. This controlled fixture did not COMMIT; a real disconnect during COMMIT has an uncertain client-visible outcome.

## 7. Cleanup and acceptance

ROLLBACK and \q in B and C; quit all surviving or reconnected A sessions. In O:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c020_A','c020_B','c020_C');"
~~~

Required: zero actors. Resolve any remaining actor through its terminal. Then:

~~~bash
admin <<'SQL'
BEGIN;
DROP TABLE c020_incident.balance;
DROP SCHEMA c020_incident;
COMMIT;
SELECT to_regnamespace('c020_incident') IS NULL AS fixture_removed;
SQL
~~~

A remaining lock can cause bounded cleanup failure. Resolve its owner and retry; never add broad termination to cleanup.

| Evidence | Acceptance |
|---|---|
| Initial graph | B waits on A; C waits on B; matching PID/start pairs |
| Cancel B | 57014; B needs rollback; C progresses; A remains |
| Stale identity | No signal row; no unintended backend affected |
| Idle cancel | A remains idle in transaction; B subsequently blocks |
| Terminate A | Original backend absent; B progresses; replacement distinguished |
| Correctness | Both final fixture values unchanged |
| Cleanup | No actors; fixture_removed true |

Add an incident note with impact, target, decision, operator, action result, verification and preventive change. Retain sanitized metadata and SQLSTATEs. Static review alone does not mark this lab verified; production acceptance also requires real driver/pool recovery evidence.
