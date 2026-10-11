# Lab 009 — Service Lifecycle and Crash Recovery

**Audience:** DBRE/SRE. **Environment:** disposable Chapter 004 PostgreSQL 18 primary and two standbys. **Runtime verification:** pending.

[Chapter](../chapters/009-systemd-startup-shutdown-and-crash-recovery.md) · [Lab setup](004-reproducible-postgresql-operations-lab.md) · [Inspection SQL](../scripts/009-lifecycle-inspection.sql)

The interruption commands target only the manual primary. Do not run them against a packaged service or production cluster. Keep standbys running; never promote them during this exercise. Use three terminals under the same non-root lab OS user. Run commands from the repository's postgresql directory.

## 1. Guard and baseline in each terminal

Export the existing PG_LAB_ROOT printed by Chapter 004 setup. If its directory disappeared, recreate the lab using that chapter. In **every terminal**, run this guard before any lifecycle command:

~~~bash
: "${PG_LAB_ROOT:?Export the disposable Chapter 004 lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ -d "$PG_LAB_ROOT/primary" && ! -L "$PG_LAB_ROOT/primary" \
   && -O "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/primary/PG_VERSION")" == 18 ]] || exit 2
[[ "$(pg_ctl --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGAPPNAME=chapter009-lab
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_admin -d ops_lab "$@"
}
app_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_app -d ops_lab "$@"
}
~~~

In Terminal B verify identity, durability and fixture availability:

~~~bash
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW fsync')" == on ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW full_page_writes')" == on ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT count(*) FROM public.lab_probe WHERE id IN (9001,9002,9003)')" == 0 ]] || exit 2
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
  -U lab_observer -d ops_lab -f scripts/009-lifecycle-inspection.sql
~~~

If fixture IDs are occupied, stop and investigate. Do not overwrite them. Record baseline start time, instance role, primary process status and two streaming senders. Recheck instance identity if anything changes during the exercise.

Optionally perform the chapter's **read-only** systemd inspection on a separate packaged host. Record “not applicable” if no systemd or PostgreSQL unit exists. A systemd service lifecycle test is outside this manual-lab exercise; never assign these data directories to another supervisor.

## 2. Smart shutdown: a wait timeout does not cancel shutdown

Terminal A: open an idle application session and leave it connected:

~~~bash
app_sql
~~~

Terminal B: request smart shutdown with a deliberately short caller wait:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" -m smart -w -t 5 stop
~~~

Expected: the command times out/nonzero because Terminal A remains connected. This is an expected experimental result, not a passing shell check. The shutdown request remains active. Terminal A should still be usable for existing-session operations; new connections should be rejected.

In Terminal A, type:

~~~text
\q
~~~

In Terminal B, poll status manually:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" status
tail -n 40 "$PG_LAB_ROOT/logs/primary.log"
~~~

Expected after the idle session exits: status reports no server running and the log records clean shutdown. If it remains running, identify other sessions and release them deliberately. Do not issue a start while shutdown continues. Then:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start
bash scripts/004-operations-lab.sh verify
~~~

Record caller timeout, actual shutdown completion and subsequent SQL readiness separately.

## 3. Fast shutdown: abort an active transaction cleanly

Terminal A opens a **new** app session:

~~~bash
app_sql
~~~

Type the following SQL, leaving the transaction open:

~~~sql
SET statement_timeout = '5s';
SET lock_timeout = '1s';
BEGIN;
INSERT INTO public.lab_probe(id,payload) VALUES (9003,'chapter009-fast-uncommitted');
~~~

Terminal B:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" -m fast -w -t 30 stop
tail -n 40 "$PG_LAB_ROOT/logs/primary.log"
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start
app_sql -c 'SELECT count(*) AS fast_uncommitted_rows FROM public.lab_probe WHERE id=9003;'
~~~

Expected: clean shutdown and count 0. The old application session has lost its connection; depending on the terminal it may display the disconnect only when it next sends a command. Close it rather than attempting to reuse the unfinished transaction. Do not send COMMIT before the shutdown.

If stop or start times out, inspect status and logs. Do not blindly continue this sequence.

## 4. Immediate shutdown: prove transaction visibility after recovery

Terminal B commits the durable fixture through the application role:

~~~bash
app_sql <<'SQL'
SET statement_timeout = '5s';
SET lock_timeout = '1s';
BEGIN;
SET LOCAL synchronous_commit = on;
INSERT INTO public.lab_probe(id,payload) VALUES (9001,'chapter009-committed');
COMMIT;
SELECT id,payload FROM public.lab_probe WHERE id=9001;
SQL
~~~

Expected: COMMIT acknowledgment and the exact fixture payload. Retain this output before interrupting the process.

Terminal A opens another **new** session with app_sql, then leaves this insert uncommitted:

~~~sql
SET statement_timeout = '5s';
SET lock_timeout = '1s';
BEGIN;
INSERT INTO public.lab_probe(id,payload) VALUES (9002,'chapter009-crash-uncommitted');
~~~

Terminal B can confirm the transaction is idle in transaction using pg_stat_activity. Observe the session application name and transaction start; do not query or terminate arbitrary sessions.

Terminal C: after confirming both fixture steps occurred, run:

~~~bash
date -u +'%Y-%m-%dT%H:%M:%SZ'
pg_ctl -D "$PG_LAB_ROOT/primary" -m immediate -w -t 30 stop
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start
date -u +'%Y-%m-%dT%H:%M:%SZ'
tail -n 80 "$PG_LAB_ROOT/logs/primary.log"
~~~

Expected: an unclean shutdown followed by startup recovery and eventual readiness. Preserve timestamps and actual log messages. Immediate shutdown uses PostgreSQL's intended signal path; it does not emulate a kernel crash or storage loss.

If startup wait expires, pg_ctl may have returned while PostgreSQL continues recovering. Inspect status and the log, wait for progress, then test SQL. Do not remove PID/WAL files, launch a competing server or issue repeated restarts. Stop the exercise and preserve evidence if recovery reports missing WAL, storage errors or repeated termination.

Terminal B, only after readiness:

~~~bash
app_sql <<'SQL'
SET statement_timeout = '5s';
SET lock_timeout = '1s';
SELECT id,payload FROM public.lab_probe WHERE id IN (9001,9002,9003) ORDER BY id;
SELECT count(*) = 1 AS committed_retained
FROM public.lab_probe WHERE id=9001 AND payload='chapter009-committed';
SELECT count(*) = 0 AS unfinished_absent
FROM public.lab_probe WHERE id IN (9002,9003);
SQL
bash scripts/004-operations-lab.sh verify
~~~

Expected: exactly row 9001; both boolean checks true; primary writable and both standbys recovering and streaming. The verify helper also updates its owned ID 1 replication probe. This establishes reconnection through a new session, not recovery of the disconnected session.

## 5. Evidence and acceptance

Retain a small report:

| Evidence | Required result |
|---|---|
| Runtime versions and topology | PG18; one primary; two standbys |
| Smart shutdown | Caller timeout with live session; clean stop after it exits |
| Fast shutdown | Clean stop; ID 9003 absent after start |
| Commit acknowledgment | ID 9001 committed before immediate stop |
| Recovery log | Observed unclean shutdown/recovery and readiness |
| Post-recovery SQL | ID 9001 payload retained; IDs 9002/9003 absent |
| Replication verification | Two streaming senders and probe visible on both standbys |
| Timing | Interruption, readiness and probe success timestamps |
| Restoration | Test fixtures removed; original topology healthy |

Report observed elapsed recovery time as a lab result. Do not present it as production RTO or infer host-loss RPO. Service unit inspection alone does not verify systemd startup/shutdown behavior.

## 6. Cleanup and restore

Close all experimental sessions. Only after verifying the retained row is this exercise's exact fixture, delete that owned row with the administrative role:

~~~bash
lab_sql <<'SQL'
BEGIN;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
DELETE FROM public.lab_probe
WHERE id=9001 AND payload='chapter009-committed';
COMMIT;
SELECT id,payload FROM public.lab_probe WHERE id IN (9001,9002,9003);
SQL
bash scripts/004-operations-lab.sh verify
~~~

Expected: DELETE 1 and no rows for the three fixture IDs. If IDs 9002/9003 unexpectedly exist, record a failed test and investigate before deleting anything.

If the lab is stopped following a failed step, inspect logs and process status before using the Chapter 004 start action. If finite WAL retention prevents a standby reconnecting, retain the failure evidence and rebuild the disposable lab through Chapter 004; do not improvise a promotion.

Keep the lab for Chapter 010 or use Chapter 004's guarded stop/destroy procedure. No service units or durability settings were changed by this exercise.
