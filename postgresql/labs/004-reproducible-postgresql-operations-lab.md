# Lab 004 — Reproducible PostgreSQL Operations Environment

[Chapter 004](../chapters/004-build-a-reproducible-postgresql-operations-lab.md) · [Control script](../scripts/004-operations-lab.sh)

## Objective and prerequisites

Create a primary and two physical streaming standbys on an isolated Linux host. Use Bash, Python 3 and PostgreSQL 18 initdb, pg_ctl, psql and pg_basebackup binaries. Record the exact versions. Run as a non-root lab OS user.

The script uses loopback ports 55432–55434 and a unique private directory under /tmp. Existing system PostgreSQL services are not altered. Do not run this script against production or expose its listeners remotely.

## 1. Verify prerequisites

From the repository root:

~~~bash
id
initdb --version
pg_ctl --version
psql --version
pg_basebackup --version
python3 --version
bash -n postgresql/scripts/004-operations-lab.sh
~~~

Expected: non-root identity, all PostgreSQL tools on major 18, Python 3 and no Bash syntax errors.

Record CPU/memory/free disk using Chapter 003. The small starting resource budget is for a low-volume lab only. Close unrelated workloads on the disposable host if resources are tight.

## 2. Build the environment

Ensure PG_LAB_ROOT is unset for a new setup. Do not clear it if you intend to operate an existing lab.

~~~bash
bash postgresql/scripts/004-operations-lab.sh setup
~~~

Expected sequence: primary initialized and started, lab roles/database created, two base backups, both standbys started, two streaming rows, then:

~~~text
export PG_LAB_ROOT=/tmp/postgresql-dbre-lab.<unique-id>
PASS: primary, two recovering standbys, two streaming senders and replicated probe.
~~~

Copy the exact printed export statement into your shell. Do not use the placeholder above.

If setup fails, do not mark acceptance passed. Keep its root and logs and use the chapter's failure procedure. Re-running setup creates a different lab rather than repairing the failed one.

## 3. Configure a client session

With the exact lab root exported:

~~~bash
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGHOST=127.0.0.1
export PGPORT=55432
export PGDATABASE=ops_lab
export PGUSER=lab_observer
export PGCONNECT_TIMEOUT=5
export PGSSLMODE=disable
export PGAPPNAME=chapter004-observer
~~~

These credentials and TLS settings belong only to the private loopback lab. Save prior shell connection values if needed so they can be restored.

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -c "SELECT current_user, current_database(), pg_is_in_recovery();"
~~~

Expected: lab_observer, ops_lab, false.

## 4. Verify the topology

On the primary as the observer:

~~~sql
SELECT application_name, state, sync_state, client_addr
FROM pg_stat_replication
ORDER BY application_name;
~~~

Expected: standby1 and standby2, state streaming, sync_state async and loopback client addresses.

Check each standby explicitly:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -p 55433 \
  -c "SELECT inet_server_port(), pg_is_in_recovery(), current_setting('transaction_read_only');"
psql -X -w -v ON_ERROR_STOP=1 -p 55434 \
  -c "SELECT inet_server_port(), pg_is_in_recovery(), current_setting('transaction_read_only');"
~~~

Expected: respective ports, true and on.

As a lab administrator, verify checksums and primary settings:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -U lab_admin -p 55432 \
  -c "SELECT name, setting FROM pg_settings
      WHERE name IN ('data_checksums','fsync','wal_level','synchronous_standby_names')
      ORDER BY name;"
~~~

Expected: checksums on, fsync on, wal_level replica and no synchronous standby names. Empty synchronous_standby_names is intentional.

## 5. Demonstrate application writes and reader visibility

Connect to the primary as lab_app:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -U lab_app -p 55432
~~~

In that psql session:

~~~sql
SET statement_timeout = '5s';
SET lock_timeout = '1s';
INSERT INTO public.lab_probe(id,payload) VALUES (2,'chapter004-application')
ON CONFLICT(id) DO UPDATE SET payload=EXCLUDED.payload;
SELECT id,payload FROM public.lab_probe ORDER BY id;
~~~

Close this session with backslash-q.

Query both standbys as lab_app:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -U lab_app -p 55433 \
  -c "SELECT id,payload FROM public.lab_probe WHERE id=2;"
psql -X -w -v ON_ERROR_STOP=1 -U lab_app -p 55434 \
  -c "SELECT id,payload FROM public.lab_probe WHERE id=2;"
~~~

Expected after replay catches up: id 2 and chapter004-application. If immediately absent, repeat bounded checks and investigate receiver/replay state rather than assuming data loss.

The observer has monitoring privileges, not application-table SELECT. Use lab_app for probe reads.

## 6. Demonstrate a standby write rejection

On a standby, attempt the same bounded write as lab_app:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -U lab_app -p 55433 \
  -c "INSERT INTO public.lab_probe VALUES (3,'should-not-commit');"
echo $?
~~~

Expected: read-only error and nonzero exit status. This is an intentional failed lab operation. Do not promote the standby or disable read-only protections.

Verify the primary still serves SQL and that id 3 is absent:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -U lab_app -p 55432 \
  -c "SELECT count(*) FROM public.lab_probe WHERE id=3;"
~~~

Expected: 0.

## 7. Stop and restart the complete lab

Close all interactive sessions. Then:

~~~bash
bash postgresql/scripts/004-operations-lab.sh stop
bash postgresql/scripts/004-operations-lab.sh start
bash postgresql/scripts/004-operations-lab.sh verify
~~~

Expected: clean stop, subsequent start and verification PASS. The fixture row at id 2 should still exist on all three instances.

The verifier refreshes id 1 with a new token. It only writes the designated fixture; do not interpret it as read-only monitoring.

Brief shutdown should normally retain required WAL for this small lab, but the retention allowance is finite. A long interruption can require rebuilding a standby.

## 8. Evidence and diagnostic files

Record in evidence/chapter004/acceptance.md:

- Exact OS, server/client versions and resource budget.
- Lab root identifier, topology and owner; omit credential contents.
- Role/recovery-state checks.
- Two streaming sender rows.
- Application row visible on both standbys.
- Expected read-only failure and absence of rejected row.
- Stop/start/verification result.
- Any gaps, errors and corrective actions.

Logs are in PG_LAB_ROOT/logs. Configuration copies and credentials exist under the lab root. Do not upload raw credentials, include the lab root in Git or publish sensitive error text.

## 9. Keep or destroy the lab

For later chapters, normally stop and retain it:

~~~bash
bash postgresql/scripts/004-operations-lab.sh stop
~~~

To remove this disposable lab irreversibly:

~~~bash
PG_LAB_CONFIRM_DESTROY=yes \
  bash postgresql/scripts/004-operations-lab.sh destroy
~~~

The script validates the path/owner/marker, stops instances and rejects nested mounts before deletion. Never replace it with an unreviewed rm command or point PG_LAB_ROOT at existing PostgreSQL data.

After destruction, restore prior client variables or unset those introduced only for this exercise. /tmp storage is transient even when you retain it.

## 10. Acceptance checklist

| Check | Pass condition |
|---|---|
| Prerequisites | Exact PostgreSQL 18 binaries and non-root identity |
| Isolation | Three separate directories, loopback ports and logs |
| Security | SCRAM, private password file and no published secrets |
| Topology | Primary false / both standbys true for recovery |
| Replication | Two named streaming senders |
| Data | Application probe visible on both readers |
| Read-only behavior | Standby write rejected; no primary row created |
| Lifecycle | Clean stop/start and subsequent verifier PASS |
| Handover | Versioned evidence and limitations recorded |
| Cleanup | Lab retained stopped or destroyed using guarded procedure |

If a check fails, the lab is not verified. Static code checks are recorded separately from runtime execution.
