# Lab 008 — Configuration Precedence, Reload and Restart

[Chapter 008](../chapters/008-configuration-precedence-reloads-and-restarts.md) · [Evidence SQL](../scripts/008-configuration-inspection.sql)

## Objective and boundaries

Use the disposable Chapter 004 lab to demonstrate a login default, session/local overrides, a reloadable persistent setting and a restart-only setting. Restore the original baseline afterward.

Reference PostgreSQL 18. Use lab_admin for persistent changes and lab_app for session tests. Only the manual primary on port 55432 is changed/restarted. Standbys remain running; they reconnect after a brief primary interruption.

Do not run this procedure on production, a provider instance or an operator-managed server. Close application exercise sessions before restarts.

## 1. Establish identity and preserve evidence

~~~bash
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter008-control
unset PGOPTIONS
mkdir -p evidence/chapter008

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -f postgresql/scripts/008-configuration-inspection.sql \
  > evidence/chapter008/before.txt
echo $?
~~~

Expected: exit 0, intended primary and Chapter 004 shared_buffers baseline of 64MB (8192 with unit 8kB). The evidence script's collection timeouts are local and restored at transaction end.

Save any prior PGOPTIONS before clearing it. This ensures hidden client options do not contaminate the exercise.

## 2. Check ownership of the intended changes

Connect as lab_admin:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab
~~~

Run:

~~~sql
SELECT current_database(), current_user, inet_server_port(), pg_is_in_recovery();
SHOW shared_buffers;
SHOW log_min_duration_statement;

SELECT name,setting,sourcefile
FROM pg_catalog.pg_file_settings
WHERE name IN ('shared_buffers','log_min_duration_statement')
  AND sourcefile=current_setting('data_directory') || '/postgresql.auto.conf';

SELECT s.setdatabase,s.setrole,cfg.item
FROM pg_catalog.pg_db_role_setting AS s
CROSS JOIN LATERAL unnest(s.setconfig) AS cfg(item)
WHERE s.setdatabase IN (0,(SELECT oid FROM pg_catalog.pg_database WHERE datname='ops_lab'))
  AND s.setrole IN (0,(SELECT oid FROM pg_catalog.pg_roles WHERE rolname='lab_app'))
  AND cfg.item LIKE 'statement_timeout=%';

SELECT sourcefile,sourceline,error
FROM pg_catalog.pg_file_settings WHERE error IS NOT NULL;
~~~

Proceed only if this is the intended disposable primary, shared_buffers is 64MB, log_min_duration_statement is -1, no existing auto.conf overrides for these names, no matching statement_timeout login/database defaults and no file errors.

If the baseline differs, stop and reconcile it; the cleanup below is designed for this known baseline and must not erase someone else's overrides.

Close the administrative session before shell steps.

## 3. Demonstrate new-login and session precedence

In Terminal A, connect as lab_app **before** adding its default:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
~~~

Run SHOW statement_timeout and record the old value, normally 0.

In Terminal B:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER ROLE lab_app IN DATABASE ops_lab SET statement_timeout='9s';"
~~~

In Terminal A, SHOW statement_timeout should still show the old startup default. Close Terminal A and reconnect as lab_app using the same command.

Now:

~~~sql
SHOW statement_timeout;
SET statement_timeout='7s';
BEGIN;
SET LOCAL statement_timeout='2s';
SHOW statement_timeout;
ROLLBACK;
SHOW statement_timeout;
RESET statement_timeout;
SHOW statement_timeout;
~~~

Expected: initial 9s, transaction-local 2s, restored session value 7s and RESET value 9s. Close Terminal A.

Explain why SET ROLE or a pool checkout on an old backend is not equivalent to a fresh login.

## 4. Apply a reloadable persistent value

Use separate standalone SQL commands:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER SYSTEM SET log_min_duration_statement='1000ms';"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT pg_reload_conf();"
~~~

Expected: persistent override written and reload signal result true. Allow reload processing to occur, then check a fresh connection:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT name,setting,unit,source,sourcefile,pending_restart
      FROM pg_catalog.pg_settings WHERE name='log_min_duration_statement';"
~~~

Expected after reload: setting 1000, unit ms, auto.conf file source and pending_restart false. If not, inspect file errors and logs; do not infer success from the signal result alone.

The change can increase logging of slow statements on this primary. Use only synthetic, nonsecret lab work and restore it later.

## 5. Apply a restart-only value

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER SYSTEM SET shared_buffers='80MB';"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT pg_reload_conf();"
~~~

After reload processing, inspect:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT name,setting,unit,context,pending_restart
      FROM pg_catalog.pg_settings WHERE name='shared_buffers';"
~~~

Expected: current value still 64MB/8192 blocks, context postmaster and pending_restart true. Check pg_file_settings for the requested 80MB and absence of errors.

Close lab sessions and restart only the primary as its owning OS account:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -m fast -w -t 30 restart

bash postgresql/scripts/004-operations-lab.sh verify
~~~

Expected after successful start: shared_buffers 80MB/10240 blocks and pending_restart false; verifier confirms both standbys stream and receive the probe.

If restart fails, retain logs and stop. Do not remove the data directory or postmaster.pid to force startup.

## 6. Restore persistent and login layers

As lab_admin, execute each command independently:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER SYSTEM RESET log_min_duration_statement;"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER SYSTEM RESET shared_buffers;"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "ALTER ROLE lab_app IN DATABASE ops_lab RESET statement_timeout;"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT pg_reload_conf();"
~~~

The reload should restore log_min_duration_statement to -1; shared_buffers restoration still needs restart.

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -m fast -w -t 30 restart

bash postgresql/scripts/004-operations-lab.sh verify

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -f postgresql/scripts/008-configuration-inspection.sql \
  > evidence/chapter008/after-rollback.txt
~~~

Verify baseline 64MB, log threshold -1, no pending restart, no named auto.conf overrides and no role-in-database timeout override.

A **fresh** lab_app connection should again show its baseline statement_timeout, normally 0. Old application connections can retain startup defaults until reconnected.

Do not use ALTER SYSTEM RESET ALL or restore the entire auto.conf file indiscriminately.

## 7. Evidence, interruptions and acceptance

Record before/change/rollback values, winning sources, pending_restart, server start times and replication verification in acceptance.md. Logs and source paths can contain sensitive metadata; review before sharing.

If interrupted mid-lab, use the change record to remove only overrides created here. If the server cannot start, inspect the exact file/log error and restore valid named configuration through the supported offline process; do not guess or overwrite unrelated settings.

| Check | Pass condition |
|---|---|
| Preflight | Known baseline and no preexisting conflicting overrides |
| Login defaults | Old/new connections demonstrate different startup defaults |
| Local scope | 2s → 7s → 9s sequence explained |
| Reload | Log threshold changes without a restart requirement |
| Restart | shared_buffers stays old until restart and then changes |
| Topology | Both standbys verified after primary restart |
| Rollback | Named overrides removed and original values reactivated |
| Cleanup | No open transaction or new login default remains |
| Evidence | Actual values, versions, timings and limitations retained |

Static review does not establish actual configuration activation. Mark lab verified only after executing these checks successfully.
