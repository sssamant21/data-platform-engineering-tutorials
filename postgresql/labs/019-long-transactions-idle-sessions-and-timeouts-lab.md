# Lab 019 — Transaction Age and Timeout Recovery

PostgreSQL 18; disposable Chapter 004 primary only. Runtime verification pending.
[Chapter](../chapters/019-long-transactions-idle-sessions-and-transaction-timeouts.md)

## Guard, provision and connect

Use the non-root owner and PG_LAB_ROOT exported by Chapter 004. Finish earlier concurrency labs first. Use terminals A, B and O; run this shell block in each:

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
  PGAPPNAME=c019_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
actor() {
  PGAPPNAME="$1" PGOPTIONS='-c statement_timeout=30s -c lock_timeout=2s -c transaction_timeout=120s -c idle_in_transaction_session_timeout=60s -c idle_session_timeout=0' \
    psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
~~~

Do not print the private passfile. In O, provision:

~~~bash
admin <<'SQL'
BEGIN;
CREATE SCHEMA c019_timeouts AUTHORIZATION lab_admin;
CREATE TABLE c019_timeouts.probe (id integer PRIMARY KEY, value integer NOT NULL);
INSERT INTO c019_timeouts.probe VALUES (1, 100);
GRANT USAGE ON SCHEMA c019_timeouts TO lab_app, lab_observer;
GRANT SELECT, UPDATE ON c019_timeouts.probe TO lab_app;
GRANT SELECT ON c019_timeouts.probe TO lab_observer;
COMMIT;
SQL
~~~

Existing schema means investigate a previous attempt; do not blindly drop it.
Open A using actor c019_A and B using actor c019_B. Each interactive psql:

~~~sql
\set VERBOSITY verbose
\set ON_ERROR_STOP off
\set ON_ERROR_ROLLBACK off
\pset pager off
SELECT pg_backend_pid(), backend_start
FROM pg_stat_activity WHERE pid = pg_backend_pid();
SHOW statement_timeout;
SHOW lock_timeout;
SHOW transaction_timeout;
SHOW idle_in_transaction_session_timeout;
SHOW idle_session_timeout;
~~~

Expected errors are intentional. ON_ERROR_ROLLBACK must be off to prevent psql savepoints from hiding failed transaction behavior. Setup/cleanup retain ON_ERROR_STOP. Record PID and backend_start for every original connection.

From repository root, O collects metadata with:

~~~bash
PGAPPNAME=c019_observer PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
  -U lab_observer -d ops_lab -f postgresql/scripts/019-transaction-age-inspection.sql
~~~

Adjust only the script path if your working directory differs. This observer never reads fixture rows or exports query text. Its settings are its own, not remote actor values.

## 1. Active work, idle transaction and retained locks

In A:

~~~sql
BEGIN;
UPDATE c019_timeouts.probe SET value = 101 WHERE id = 1;
SELECT pg_sleep(8);
~~~

Collect in O during sleep: expect active, transaction_age and active_statement_age. Once A returns to its prompt, wait a few seconds and collect again without issuing SQL in A. Expect idle in transaction with growing idle_age. Server-side sleep is an active statement; client inactivity is a different state.

In B:

~~~sql
BEGIN;
UPDATE c019_timeouts.probe SET value = 102 WHERE id = 1;
SELECT 1;
ROLLBACK;
~~~

Expect UPDATE to fail with 55P03 after its two-second lock budget; SELECT then returns 25P02. Rollback recovers B. Roll back A, then B reads the fixture: value must be 100. While A holds locks, O uses metadata only.

## 2. Statement cancellation and explicit recovery

A, outside a transaction:

~~~sql
SET statement_timeout = '2s';
BEGIN;
UPDATE c019_timeouts.probe SET value = 103 WHERE id = 1;
SELECT pg_sleep(6);
SELECT 1;
ROLLBACK;
SELECT pg_backend_pid(), value FROM c019_timeouts.probe WHERE id = 1;
SET statement_timeout = '30s';
~~~

Expect 57014, then 25P02, then successful rollback. The original backend survives and value is 100. Optionally collect after the error before rollback; stay within the baseline 60-second inactivity and 120-second total guards. Do not infer retained resources from an aborted-state label alone.

For an autocommit comparison, run the long SELECT outside BEGIN with the two-second statement setting: after 57014, SELECT 1 succeeds without explicit rollback. Restore 30s afterwards.

## 3. SET LOCAL restoration

In A:

~~~sql
SHOW statement_timeout;
BEGIN;
SET LOCAL statement_timeout = '1s';
SHOW statement_timeout;
SELECT pg_sleep(3);
ROLLBACK;
SHOW statement_timeout;
~~~

Expected values: 30s, 1s, then 30s after rollback. Also try a fast SELECT and COMMIT with SET LOCAL to demonstrate restoration after success. Session SET inside a transaction has different rollback semantics; no login defaults are changed here.

## 4. Idle-in-transaction session termination

Quit A using \q. Open a fresh actor c019_idle_tx and run:

~~~sql
\set VERBOSITY verbose
\set ON_ERROR_STOP off
SET statement_timeout = '30s';
SET transaction_timeout = '120s';
SET idle_in_transaction_session_timeout = '5s';
SET idle_session_timeout = '0';
SELECT pg_backend_pid(), backend_start
FROM pg_stat_activity WHERE pid = pg_backend_pid();
BEGIN;
UPDATE c019_timeouts.probe SET value = 104 WHERE id = 1;
\! sleep 8
SELECT 1;
~~~

The shell sleep is client-side; the server waits for client input. Expect FATAL 25P03 and termination of the original backend. psql may discover this on the next command and reconnect automatically. Compare the original PID/start pair with O's metadata, not just application_name. A replacement connection does not preserve the original session overrides.

In B, outside a transaction, read the fixture: expect 100, proving the uncommitted update disappeared. Quit A, including any replacement connection.

## 5. Idle session outside a transaction

Open actor c019_idle_plain:

~~~sql
\set VERBOSITY verbose
SET idle_in_transaction_session_timeout = '60s';
SET idle_session_timeout = '5s';
SELECT pg_backend_pid(), backend_start
FROM pg_stat_activity WHERE pid = pg_backend_pid();
\! sleep 8
SELECT 1;
~~~

Expect FATAL 57P05 and disappearance of the original backend. No explicit transaction was open. Compare with a fresh baseline actor: idle_session_timeout is zero, so the same client wait should preserve its backend. Quit both trials.

Unexpected socket closure needs a separate real driver/pool integration test. psql's reconnect does not establish correct connection checkout handling.

## 6. Total transaction budget during active work

Open actor c019_total; configure before BEGIN:

~~~sql
\set VERBOSITY verbose
SET statement_timeout = '0';
SET lock_timeout = '1s';
SET idle_in_transaction_session_timeout = '0';
SET idle_session_timeout = '0';
SET transaction_timeout = '5s';
SHOW transaction_timeout;
SELECT pg_backend_pid(), backend_start
FROM pg_stat_activity WHERE pid = pg_backend_pid();
BEGIN;
UPDATE c019_timeouts.probe SET value = 105 WHERE id = 1;
SELECT pg_sleep(8);
~~~

Expect FATAL 25P04 around the transaction budget while active. Other competing timeouts were disabled only in this isolated session. O confirms original backend disappearance; B confirms value 100. Quit any replacement connection.

For cumulative duration, use another fresh actor. Set statement_timeout to 3s, transaction_timeout to 5s, then BEGIN and execute three separate SELECT pg_sleep(2) commands. Each statement fits its own budget, but total elapsed transaction time triggers termination. Human typing counts toward that total. A control with transaction_timeout zero and the same statement budget should complete all three; immediately ROLLBACK and quit. Prepared transactions are outside this exercise.

## Cleanup and evidence

ROLLBACK and \q in surviving original actors. Quit replacement connections too. O checks:

~~~bash
admin -c "SELECT pid, backend_start, application_name, state FROM pg_stat_activity WHERE datname='ops_lab' AND application_name LIKE 'c019_%' AND pid <> pg_backend_pid();"
~~~

Investigate any remaining actor and close it through its own terminal. Do not broadly terminate sessions. Once actors are absent:

~~~bash
admin <<'SQL'
BEGIN;
DROP TABLE c019_timeouts.probe;
DROP SCHEMA c019_timeouts;
COMMIT;
SELECT to_regnamespace('c019_timeouts') IS NULL AS fixture_removed;
SQL
~~~

Cleanup is bounded; an incompatible remaining lock causes an error. Resolve the owner before retrying. Session timeout changes disappear with connection closure; no global changes, reloads or ALTER ROLE resets were made.

| Trial | Required evidence |
|---|---|
| Active and idle | Same backend identity, different state and clock fields |
| Lock timeout | 55P03 then 25P02 then rollback |
| Statement timeout | 57014; original backend survives; value 100 |
| SET LOCAL | 30s restored after transaction completion |
| Idle transaction | 25P03; original backend absent; value 100 |
| Idle plain | 57P05; original backend absent |
| Total budget | 25P04 during active work; value 100 |
| Cleanup | No actors; fixture_removed true |

Record server version, effective actor settings, original SQLSTATE and sanitized metadata. Timing is approximate under scheduling/load. If another error wins, diagnose effective settings and repeat with a fresh connection. Do not mark verified without real execution evidence.
