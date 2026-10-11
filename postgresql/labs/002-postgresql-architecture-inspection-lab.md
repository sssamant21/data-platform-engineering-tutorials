# Lab 002 — PostgreSQL Architecture Inspection

[Chapter 002](../chapters/002-architecture-processes-memory-storage-and-wal.md)

## Objective and prerequisites

Inspect processes, memory configuration and storage metadata, then observe WAL movement after a small logged write.

Use a disposable **PostgreSQL 18 primary** with psql, an authorized observer and a separate lab writer allowed to create objects in an approved lab schema. Record exact versions. Managed-service restrictions can make some observations unavailable; document them rather than requesting superuser reflexively.

The read-only snapshot can be reviewed for production use. The write exercise must run only in your lab. An existing instance is required; provisioning is covered in Chapter 004.

## 1. Collect a baseline

Use Chapter 001 connection settings and credential handling. From the repository root:

~~~bash
mkdir -p evidence/chapter002
psql -X -v ON_ERROR_STOP=1 \
  -f postgresql/scripts/002-architecture-snapshot.sql \
  > evidence/chapter002/baseline.txt
echo $?
~~~

Expected exit status: 0. Stop on errors. Identify the server version, recovery state, observer PID, process types, shared_buffers, work_mem, fsync and synchronous_commit.

Settings may have implicit units: shared_buffers can be in blocks, while work_mem can be in kB. Read the unit column.

## 2. Observe a backend

In Terminal A, connect to the lab:

~~~bash
PGAPPNAME=chapter002-client psql -X
~~~

Leave the connection idle. In Terminal B:

~~~sql
SELECT pid, backend_type, application_name, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE application_name = 'chapter002-client';
~~~

Expected: a client backend, normally idle while awaiting another command.

In Terminal A:

~~~sql
SELECT pg_sleep(20);
~~~

Repeat the query in Terminal B while it runs. Expected: active with Timeout/PgSleep. Observe the same backend PID. Close Terminal A with backslash-q, then confirm its row disappears.

Explain why idle, active and CPU-consuming are different descriptions.

## 3. Inspect logical storage

~~~sql
SELECT pg_relation_filepath('pg_catalog.pg_class'::regclass) AS path,
       pg_relation_size('pg_catalog.pg_class'::regclass) AS main_bytes,
       pg_total_relation_size('pg_catalog.pg_class'::regclass) AS total_bytes;
~~~

Expected: a path relative to the instance data directory and sizes in bytes. Total includes more components than the main relation.

On a self-managed lab host only, an authorized operator can inspect existing data and WAL mount capacity with df. Use the actual configured paths, not assumed installation defaults. Do not list sensitive file content or remove files. Managed-service learners should record the provider's capacity metric instead.

## 4. Observe a bounded logged write

Connect with your **lab writer** to an empty, approved lab schema. The following example uses public; substitute your approved schema if public creation is restricted. First verify that this dedicated exercise name does not already exist:

~~~sql
SELECT pg_is_in_recovery(), current_setting('transaction_read_only');
SELECT to_regclass('public.chapter002_wal_demo');
~~~

Proceed only on a disposable primary with read-write access and a null relation result. Do not drop an existing object to make the exercise run.

Execute these lines in one psql session, using autocommit:

~~~sql
\set ON_ERROR_STOP on
SET statement_timeout = '10s';
SET lock_timeout = '1s';
SELECT pg_current_wal_insert_lsn() AS before_lsn \gset
CREATE TABLE public.chapter002_wal_demo (
  id integer PRIMARY KEY,
  payload text NOT NULL
);
INSERT INTO public.chapter002_wal_demo
SELECT n, repeat('x',100)
FROM generate_series(1,1000) AS n;
SELECT count(*) AS rows_loaded FROM public.chapter002_wal_demo;
SELECT pg_current_wal_insert_lsn() AS after_lsn,
       pg_wal_lsn_diff(pg_current_wal_insert_lsn(), :'before_lsn'::pg_lsn)
       AS instance_wal_position_delta_bytes;
SELECT pg_relation_filepath('public.chapter002_wal_demo'::regclass),
       pg_size_pretty(pg_total_relation_size('public.chapter002_wal_demo'::regclass));
~~~

Expected: 1,000 rows and a positive WAL insertion-position delta. The exact delta varies. It measures instance-wide WAL movement between observations, including other sessions and background activity, not just these rows. It is not the on-disk size of retained WAL and does not establish replica replay progress.

No CHECKPOINT, WAL switch, stats reset or durability-setting changes are needed.

## 5. Cleanup and interpretation

In the same disposable lab, using the owning writer:

~~~sql
DROP TABLE public.chapter002_wal_demo;
~~~

This removes only the named exercise object. If interrupted, confirm the object belongs to this exercise before cleanup. Dropping it generates additional WAL; normal recycling follows PostgreSQL's retention rules.

Close sessions and restore prior shell connection settings. Retain baseline.txt and a short architecture-observations.md report.

## 6. Acceptance checks

| Check | Pass condition |
|---|---|
| Processes | Backend identified while idle, waiting and disconnected |
| Memory | Shared versus per-operation demand explained with actual settings |
| Storage | Relative relation path and heap/total distinction recorded |
| WAL | Logged write produces 1,000 rows and positive insertion-position movement |
| Interpretation | WAL movement distinguished from flush, replay and retained disk bytes |
| Checkpoints | Counters recorded without forcing or resetting a checkpoint |
| Cleanup | Exercise table removed and sessions closed |
| Evidence | Exact versions, observations and privilege limitations documented |

**Troubleshooting:** read-only errors → confirm primary and role; permission errors → approved schema/observer review; missing process → verify same endpoint and timing; zero or unexpected WAL delta → confirm completed logged writes and same instance; snapshot error → record the exact view/privilege mismatch and match documentation to the deployed version.

Authorship alone is not successful lab execution.
