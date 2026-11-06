# Chapter 04 Lab — Observe WAL, Shared Buffers, Checkpoints and I/O

**Lab mode:** local, disposable PostgreSQL 17 container · **Guided time:** ~22 minutes  
**Runtime status:** Instructions authored, **not executed** · **Risk:** low, small synthetic write workload  
[Chapter 04 lesson](../../chapters/04-postgresql-internals-wal-buffers-and-checkpoints.md) · [Chapter 01 setup](../chapter-01/README.md)

## Objectives and safeguards

Use a **separate database** (`training_ch04`) to observe a controlled write workload. Capture an LSN delta and PostgreSQL 17 monitoring views without forcing a checkpoint or changing durability settings.

**Do not** run this against production or an unidentified server. Do not change `fsync`, `full_page_writes`, `synchronous_commit`, `checkpoint_timeout`, `max_wal_size`, `archive_mode`, or replication slots. Do not delete files from `pg_wal` or reset shared statistics.

The Chapter 01 lab uses the container name `pg-fleet-lab`, PostgreSQL image `postgres:17`, host port `127.0.0.1:55432`, and disposable volume `pg_fleet_data`. These names must be checked against your actual environment before proceeding.

## Step 0 — Preflight (3 minutes)

In **Windows PowerShell** (Docker Desktop in Linux-container mode):

Before running any SQL, retrieve the **original Chapter 01 creation record** (Docker context, full container ID and volume). The values below are supplied from that record, not inferred from the current container name. Do not continue without them. Confirm the Docker endpoint is a locally owned, disposable engine; a matching context name alone is insufficient.

```powershell
$ErrorActionPreference = 'Stop'
$expectedContext = '<context-from-chapter-01-record>'
$expectedId = '<full-container-id-from-chapter-01-record>'
$expectedVolume = 'pg_fleet_data'
$context = docker context show
if ($LASTEXITCODE -ne 0 -or $context -ne $expectedContext) { throw 'Docker context mismatch' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Docker context inspection failed' }
# Independently verify the inspected endpoint is your approved local disposable engine.
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Expected Linux Docker engine' }
$id = docker inspect --format '{{.Id}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $id -ne $expectedId) { throw 'Container identity mismatch' }
$label = docker inspect --format '{{index .Config.Labels "dbre.training"}}' $id
if ($LASTEXITCODE -ne 0 -or $label -ne 'postgresql-enterprise-ch01') { throw 'Training ownership label mismatch' }
$image = docker inspect --format '{{.Config.Image}}' $id
if ($LASTEXITCODE -ne 0 -or $image -ne 'postgres:17') { throw 'Unexpected image' }
$mount = docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' $id
if ($LASTEXITCODE -ne 0 -or $mount -ne $expectedVolume) { throw 'Unexpected data mount' }
$running = docker inspect --format '{{.State.Running}}' $id
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') { throw 'Container is not running' }
docker exec $id pg_isready -U postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL is not ready' }
$version = docker exec $id psql -U postgres -d postgres -tAc 'SHOW server_version_num;'
if ($LASTEXITCODE -ne 0 -or $version.Trim() -notmatch '^17[0-9]{4}$') { throw 'Expected PostgreSQL 17' }
$recovery = docker exec $id psql -U postgres -d postgres -tAc 'SELECT pg_is_in_recovery();'
if ($LASTEXITCODE -ne 0 -or $recovery.Trim() -ne 'f') { throw 'Expected writable primary' }
```

**Expected:** approved local Linux Docker engine, original full container ID, matching training label/image/volume, PostgreSQL 17 and `f` (writable primary). Any mismatch is a **stop condition**. For subsequent steps, `pg-fleet-lab` refers only to this verified container; recheck identity if the context or container state changes.

## Step 1 — Create an isolated database (2 minutes)

Check whether the name is already in use:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname='training_ch04';"
```

**Expected for first run:** blank output. If `training_ch04` already exists, inspect its ownership and contents first; do **not** drop it or rerun CREATE statements blindly.

If absent, create:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch04
docker exec -it pg-fleet-lab psql -U postgres -d training_ch04
```

All commands from here through Step 8 run **inside the interactive `psql` session**, not PowerShell, unless explicitly noted.

Verify:

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SHOW server_version_num;
```

**Expected:** `training_ch04`, `postgres`, `f`, and a version number starting with `17`.

## Step 2 — Create a synthetic event table (2 minutes)

```sql
CREATE TABLE public.wal_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT count(*) AS initial_rows FROM public.wal_events;
```

**Expected:** `CREATE TABLE` and `initial_rows = 0`. The primary key creates an index, which also generates WAL during writes.

If the table already exists, inspect it rather than dropping or truncating it. This lab's row-count expectations assume a new, empty table.

## Step 3 — Baseline WAL and configuration (3 minutes)

Capture cluster-wide cumulative WAL statistics:

```sql
SELECT wal_records, wal_fpi, wal_bytes, wal_buffers_full, stats_reset
FROM pg_stat_wal;

SELECT pg_current_wal_lsn() AS start_lsn \gset
```

**Important:** `\gset` is a `psql` meta-command. Keep the line exactly as shown, **without a semicolon** before `\gset`. It stores `start_lsn` in the current `psql` client.

Check the variable:

```sql
\echo Baseline WAL LSN: :start_lsn
```

**Expected:** a non-empty hexadecimal-style LSN, for example `0/1A2B3C4`. The actual value will differ.

Read settings without changing them:

```sql
SHOW shared_buffers;
SHOW wal_buffers;
SHOW checkpoint_timeout;
SHOW max_wal_size;
SHOW checkpoint_completion_target;
SHOW full_page_writes;
SHOW fsync;
SHOW synchronous_commit;
SHOW track_io_timing;
SHOW track_wal_io_timing;
```

Record settings as observed. Do not interpret zero I/O timing as proof of zero I/O when tracking is disabled.

## Step 4 — Generate a modest WAL workload (3 minutes)

This single transaction inserts 2,000 **synthetic** rows; no real user data is involved.

```sql
BEGIN;

INSERT INTO public.wal_events (source, payload, created_at)
SELECT 'synthetic',
       repeat(md5(n::text), 4),
       clock_timestamp() - (n * interval '1 second')
FROM generate_series(1, 2000) AS g(n);

COMMIT;

SELECT count(*) AS event_rows FROM public.wal_events;
SELECT pg_current_wal_lsn() AS end_lsn \gset
```

**Expected:** `INSERT 0 2000`, `COMMIT`, `event_rows = 2000`. The `end_lsn` is captured after the commit.

Measure WAL byte-distance:

```sql
SELECT :'start_lsn'::pg_lsn AS start_lsn,
       :'end_lsn'::pg_lsn AS end_lsn,
       pg_wal_lsn_diff(
           :'end_lsn'::pg_lsn,
           :'start_lsn'::pg_lsn
       ) AS wal_bytes_between_lsns;
```

**Expected:** a **positive** WAL byte-distance. Its exact value is variable; it is not the table's on-disk size. If other databases write concurrently, their WAL is included in the delta.

**If a transaction fails:** issue `ROLLBACK;`, inspect the error, and avoid repeating the insert against partially populated data. Do not use automatic destructive reset scripts.

## Step 5 — Compare WAL counters and relation size (3 minutes)

```sql
SELECT wal_records, wal_fpi, wal_bytes, wal_buffers_full,
       wal_write, wal_sync, stats_reset
FROM pg_stat_wal;

SELECT
    pg_size_pretty(pg_relation_size('public.wal_events')) AS heap_size,
    pg_size_pretty(pg_indexes_size('public.wal_events')) AS index_size,
    pg_size_pretty(pg_total_relation_size('public.wal_events')) AS total_size;
```

Compare with the Step 3 WAL counters. The counters may update asynchronously and are **cluster-wide**. They may not exactly match the LSN delta. If the counters have not advanced yet, record that observation; do not reset stats or force a checkpoint to obtain a desired number.

**Interpretation:** WAL volume is not equal to table heap size or index size. WAL may contain metadata, full-page images and other concurrent activity.

## Step 6 — Observe checkpointer, background writer and I/O (4 minutes)

```sql
SELECT num_timed, num_requested, buffers_written,
       write_time, sync_time, stats_reset
FROM pg_stat_checkpointer;

SELECT buffers_clean, maxwritten_clean, buffers_alloc, stats_reset
FROM pg_stat_bgwriter;

SELECT backend_type, object, context, reads, writes, hits, evictions
FROM pg_stat_io
WHERE object = 'relation'
ORDER BY backend_type, context
LIMIT 20;

SELECT datname, blks_read, blks_hit,
       round(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2)
           AS postgres_buffer_hit_pct
FROM pg_stat_database
WHERE datname = current_database();
```

**Expected:** the queries return view rows (the exact counters vary). `pg_stat_io` may include NULLs for unsupported operation/backend combinations. `pg_stat_checkpointer` may show **no new checkpoints** during a short exercise; this is normal. Buffer-hit percentage can be NULL if no qualifying activity has been recorded, and it does not measure OS cache hits.

Do **not** issue a manual `CHECKPOINT` to make counters change.

## Step 7 — Inspect retention indicators without modification (2 minutes)

```sql
SHOW archive_mode;
SHOW wal_keep_size;

SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;
```

**Expected:** a standard standalone lab usually has no replication slots; `archive_mode` is commonly off in a default container. Do not assume those values in another environment.

If the slot view has rows, **do not drop them**. In real environments, slot retention may be required by physical replicas or logical consumers. Archiver configuration and backup validation are separate topics.

## Step 8 — Record evidence and exit (2 minutes)

Capture a sanitized note with:

| Evidence | Expected/required observation |
|---|---|
| Server version and identity | PostgreSQL 17, `training_ch04`, writable primary |
| `start_lsn` and `end_lsn` | Both recorded; positive byte-distance |
| Insert count | 2,000 rows in a fresh lab |
| `pg_stat_wal` before/after | Observed counters, reset timestamp and any lag |
| `pg_stat_checkpointer` | Actual counts/times; unchanged is acceptable |
| `pg_stat_bgwriter` | Actual buffer counters |
| `pg_stat_io` | Actual backend/context counts and NULLs |
| Buffer/configuration settings | Read-only settings captured |
| Retention indicators | Archive mode, WAL keep size, slot inventory |
| Review | Reviewer name/date **only after** independent review |

Exit the client:

```text
\q
```

**Cleanup:** leave `training_ch04` intact for later reference. Do not automatically drop the database, remove the Docker volume, or delete WAL. A separate, approved cleanup process may retire a confirmed disposable lab when no longer needed.

## Troubleshooting and recovery

| Observation | Possible reason | Safe next step |
|---|---|---|
| `pg_current_wal_lsn()` NULL | Connected to standby | Verify `pg_is_in_recovery()`; use the designated primary lab |
| `\gset` fails | Running in non-psql client or misplaced semicolon | Use interactive `psql` and the exact syntax shown |
| `:'start_lsn'` appears literally or variable missing | `\gset` did not execute | Repeat Step 3 baseline capture before a fresh workload |
| Table already exists | Lab previously run | Inspect and record existing state; don't drop automatically |
| Checkpoint counters unchanged | No checkpoint occurred in lab interval | Accept and document; do not force checkpoint |
| WAL counters lag LSN delta | Async stats collection or unrelated writes | Wait for natural stats update; explain measurement limits |
| `pg_stat_checkpointer` missing | PostgreSQL older than 17 | Check version and consult corresponding documentation |
| Permission denied | Connected as restricted role | Request approved monitoring privileges; do not bypass access controls |
| Unexpectedly high WAL volume | Concurrent activity or FPI | Confirm isolated environment and inspect workload before conclusions |

## Acceptance checklist

- [ ] Identity, version and primary status checked before writing.
- [ ] Separate disposable database created without overwriting existing data.
- [ ] Exactly 2,000 synthetic rows inserted in a fresh lab.
- [ ] Positive WAL LSN delta recorded and interpreted correctly.
- [ ] Cumulative WAL stats compared without resetting counters.
- [ ] Buffer, checkpoint, I/O and retention views read successfully.
- [ ] Explained why a WAL directory is not a backup.
- [ ] No durability, checkpoint, slot or archiving settings changed.
- [ ] No destructive cleanup performed.
- [ ] Actual execution evidence retained if performed; otherwise status stays **Not executed**.

## Official references

- [PostgreSQL 18 WAL introduction](https://www.postgresql.org/docs/18/wal-intro.html)
- [PostgreSQL 18 WAL configuration](https://www.postgresql.org/docs/18/wal-configuration.html)
- [PostgreSQL 18 monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 system administration functions](https://www.postgresql.org/docs/18/functions-admin.html)
- [PostgreSQL 18 archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
