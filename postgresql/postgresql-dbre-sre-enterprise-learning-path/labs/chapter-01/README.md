# Chapter 01 Lab — Deploy, Query, Inspect and Restore PostgreSQL

**Safety:** Disposable local lab ONLY. Do not run destructive cleanup against an existing container or volume.
**Runtime:** Windows PowerShell with Docker Desktop using an approved local Linux-container engine and PostgreSQL 18. **Migration authored, not runtime validated.** The PowerShell preflight uses Windows-only `Get-NetTCPConnection`; Linux-host execution requires a separately reviewed equivalent port-ownership check and is not supported by this exact command sequence.
**Status:** Instructions authored; runtime execution not yet completed.

[Chapter 01](../../chapters/01-postgresql-fundamentals-and-architecture.md)

## Step 0 — Prerequisites and identity guardrails

**PostgreSQL 18 migration note:** This is a source-level migration only. The new `pg18_fleet_data` volume must be empty and distinct from any PostgreSQL 17 training volume. The official PostgreSQL 18 image defaults to `PGDATA=/var/lib/postgresql/18/docker` and persists the parent `/var/lib/postgresql`. Never attach an existing PostgreSQL 17 data volume or claim successful execution before collecting evidence.

Run in PowerShell on an **approved disposable local Docker engine**. Never use a remote or shared context. Stop on any failed identity check; do not delete pre-existing resources to make this lab run.

```powershell
$ErrorActionPreference = 'Stop'
docker version
if ($LASTEXITCODE -ne 0) { throw 'Docker client/server unavailable' }
$context = docker context show
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine Docker context' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Docker context' }
Write-Host "Verify Docker endpoint and ownership manually: $context"
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Requires Linux Docker engine' }
$existingContainer = @(docker ps -a --filter 'name=^/pg18-fleet-lab$' --format '{{.Names}}')
if ($LASTEXITCODE -ne 0 -or $existingContainer.Count -ne 0) { throw 'Container name occupied or cannot be checked' }
$existingVolume = @(docker volume ls --filter 'name=^pg18_fleet_data$' --format '{{.Name}}')
if ($LASTEXITCODE -ne 0 -or $existingVolume.Count -ne 0) { throw 'Volume name occupied or cannot be checked' }
$portListener = Get-NetTCPConnection -LocalPort 55432 -State Listen -ErrorAction SilentlyContinue
if ($portListener) { throw 'Port 55432 already listening' }
```

The name/port checks are not proof of a disposable Docker engine. Verify the context endpoint and local ownership independently. The example password is training-only and must never be reused outside this isolated environment.

## Step 1 — Start PostgreSQL

```powershell
docker run -d `
  --name pg18-fleet-lab `
  --label dbre.training=postgresql-enterprise-ch01 `
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe_123 `
  -e POSTGRES_DB=appdb `
  -p 127.0.0.1:55432:5432 `
  -v pg18_fleet_data:/var/lib/postgresql `
  postgres:18
if ($LASTEXITCODE -ne 0) { throw 'Docker run failed; do not continue to docker exec' }
$labContext = docker context show
if ($LASTEXITCODE -ne 0 -or $labContext -ne $context) { throw 'Docker context changed after preflight' }
$labId = docker inspect --format '{{.Id}}' pg18-fleet-lab
if ($LASTEXITCODE -ne 0 -or $labId -notmatch '^[a-f0-9]{64}$') { throw 'Cannot verify full lab container ID' }
$labImage = docker inspect --format '{{.Config.Image}}' $labId
if ($LASTEXITCODE -ne 0 -or $labImage -ne 'postgres:18') { throw 'Unexpected lab container image' }
$labLabel = docker inspect --format '{{index .Config.Labels "dbre.training"}}' $labId
if ($LASTEXITCODE -ne 0 -or $labLabel -ne 'postgresql-enterprise-ch01') { throw 'Unexpected lab ownership label' }
$labVolume = docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql"}}{{.Name}}{{end}}{{end}}' $labId
if ($LASTEXITCODE -ne 0 -or $labVolume -ne 'pg18_fleet_data') { throw 'Unexpected lab data mount' }
$labPgdata = docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $labId
if ($LASTEXITCODE -ne 0 -or @($labPgdata | Where-Object { $_ -eq 'PGDATA=/var/lib/postgresql/18/docker' }).Count -ne 1) { throw 'Unexpected PostgreSQL 18 PGDATA configuration' }
$labImageId = docker inspect --format '{{.Image}}' $labId
if ($LASTEXITCODE -ne 0 -or $labImageId -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Cannot verify immutable image identity' }
Write-Host "Retain for cleanup verification: context=$labContext container_id=$labId volume=$labVolume image_id=$labImageId"
```

```powershell
docker ps --filter "name=^/pg18-fleet-lab$"
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect lab container state' }
# PostgreSQL initialization can take time; bounded readiness is not a substitute for identity checks.
$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
  docker exec $labId pg_isready -U postgres
  $probeExit = $LASTEXITCODE
  if ($probeExit -eq 0) { $ready = $true; break }
  if ($probeExit -ne 1 -and $probeExit -ne 2) {
    throw "Unexpected pg_isready/Docker exit code $probeExit; stop and inspect"
  }
  Start-Sleep -Seconds 2
}
if (-not $ready) { throw 'PostgreSQL not ready after 30 probes; stop and inspect logs' }
docker logs --tail 20 $labId
if ($LASTEXITCODE -ne 0) { throw 'Cannot read lab logs' }
```

Expected: container running and PostgreSQL accepting connections.

**Security note:** The example uses the `postgres` superuser only to simplify isolated training. Production applications should use least-privilege roles, secret management, and encrypted connections.

## Step 2 — Connect and verify

```powershell
docker exec -it $labId psql -X -v ON_ERROR_STOP=1 -U postgres -d appdb
if ($LASTEXITCODE -ne 0) { throw 'Interactive psql session failed; do not proceed to backup or report lab success' }
```

In the interactive `psql` session (startup files disabled): **`ON_ERROR_STOP` does not automatically terminate an interactive session after every SQL error.** If any command fails, stop the exercise, record the error, and do not report success. The PowerShell exit-code check above only confirms the eventual `psql` process exit status; it is not proof that every interactively entered SQL statement succeeded. Verify the expected outputs and counts explicitly before proceeding:

```sql
SELECT version();
SHOW data_directory;
SELECT current_database();
SELECT current_user;
SELECT pg_is_in_recovery();
```

Expected: PostgreSQL 18, data directory `/var/lib/postgresql/18/docker`, `appdb`, `postgres`, and `false` for a writable primary. Record the exact server minor version and image digest; stop if the data directory differs.

## Step 3 — Create schema and generate workload

```sql
CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO customers (email)
SELECT 'customer' || n || '@example.com'
FROM generate_series(1,100) AS n;
INSERT INTO orders (customer_id, status, amount, created_at)
SELECT ((n - 1) % 100) + 1,
       'paid',
       (n % 1000)::numeric / 10,
       now() - n * interval '1 minute'
FROM generate_series(1,50000) AS n;
SELECT count(*) AS customers FROM customers;
SELECT count(*) AS orders FROM orders;
```

Expected: 100 customers and 50,000 orders. Use a fresh lab or recreate empty tables if repeating.

## Step 4 — Query planning and indexing

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;

CREATE INDEX idx_orders_customer_created
    ON orders (customer_id, created_at DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

Capture both plans and compare scan choice, sorting, execution time and buffers. A query optimizer may still prefer a sequential scan depending on measurements and statistics. Never claim a guaranteed speedup.

## Step 5 — Transaction behavior

```sql
BEGIN;
UPDATE orders SET status = 'shipped' WHERE order_id = 1;
SELECT order_id, status FROM orders WHERE order_id = 1;
ROLLBACK;
SELECT order_id, status FROM orders WHERE order_id = 1;

BEGIN;
UPDATE orders SET status = 'shipped' WHERE order_id = 1;
COMMIT;
SELECT order_id, status FROM orders WHERE order_id = 1;
```

Expected: rollback preserves the old status; commit makes the update visible afterwards.

## Step 6 — DBRE health checks

```sql
SELECT pid, usename, state, wait_event_type FROM pg_stat_activity;
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
SHOW max_connections;
SHOW shared_buffers;
SHOW work_mem;
SHOW wal_level;
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables ORDER BY relname;
```

These are starting points, not a complete health certification. Statistics may lag current activity.

## Step 7 — Logical backup and independent restore

Exit `psql` using `\q`. Run in PowerShell:

```powershell
# Prevent shell redirection from truncating an existing container-side backup.
# POSIX shell noclobber (set -C) also rejects a pre-existing destination at redirection time.
# Exit 0 means the destination does not exist; any other result stops this run.
docker exec $labId test ! -e /tmp/appdb.dump
if ($LASTEXITCODE -ne 0) { throw 'Container /tmp/appdb.dump exists or cannot be checked; stop without overwriting it' }
docker exec $labId sh -c 'set -C; pg_dump -U postgres -Fc appdb > /tmp/appdb.dump'
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; stop before restore' }
docker exec $labId sh -c 'test -s /tmp/appdb.dump'
if ($LASTEXITCODE -ne 0) { throw 'Backup file is absent or empty' }
# Never overwrite an existing local backup, including one from another exercise.
$backupPath = Join-Path (Get-Location) 'appdb.dump'
if (Test-Path -LiteralPath $backupPath) { throw 'Local appdb.dump already exists; choose a clean directory before continuing' }
docker cp "${labId}:/tmp/appdb.dump" $backupPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $backupPath -PathType Leaf)) { throw 'Backup copy failed' }
if ((Get-Item -LiteralPath $backupPath).Length -le 0) { throw 'Copied backup is empty; do not restore' }
# Use a new, empty restore database. Stop if it already exists; never drop it automatically.
$restoreExists = docker exec $labId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='appdb_restore';"
if ($LASTEXITCODE -ne 0 -or $restoreExists.Trim() -ne '') { throw 'Cannot verify a fresh appdb_restore database' }
docker exec $labId createdb -U postgres appdb_restore
if ($LASTEXITCODE -ne 0) { throw 'Restore database creation failed' }
docker exec $labId pg_restore --exit-on-error -U postgres -d appdb_restore /tmp/appdb.dump
if ($LASTEXITCODE -ne 0) { throw 'Restore failed; do not report success' }
$restoredCount = docker exec $labId psql -X -v ON_ERROR_STOP=1 -U postgres -d appdb_restore -tAc 'SELECT count(*) FROM orders;'
if ($LASTEXITCODE -ne 0 -or $restoredCount.Trim() -ne '50000') { throw 'Restore row-count acceptance failed' }
Write-Host "Restore verified: $restoredCount orders"
```

Expected: 50,000 restored orders. For a repeated run, choose a new restore database name or deliberately remove the previous disposable restore database first. This test demonstrates logical restore, not WAL archiving, PITR or an independent-node disaster recovery scenario. The local `appdb.dump` and container `/tmp/appdb.dump` contain actual lab data: keep them out of source control, redact evidence, and remove them only after confirming their exact identity and that they are no longer required. The lab does not automatically delete backup artifacts.

## Step 8 — Collect evidence

Record PostgreSQL server/client versions, image tag and immutable image ID/digest, actual PGDATA and volume mount, check outputs, plan comparisons, rollback test, health query results, and restore row count. Redact secrets before committing logs to GitHub.

## Step 9 — Optional cleanup (destructive to this lab only)

**Only after independently verifying the active Docker context matches the recorded `$labContext`, the full container ID matches `$labId`, the container has label `dbre.training=postgresql-enterprise-ch01`, its data mount is `pg18_fleet_data`, and the volume has no other consumers.** Inspect with `docker inspect pg18-fleet-lab`, `docker volume inspect pg18_fleet_data`, and `docker ps -a --filter volume=pg18_fleet_data`. If identity is uncertain, stop and retain resources. The commands below are deliberately commented out to prevent accidental copy/paste deletion:

```powershell
# docker stop pg18-fleet-lab
# docker rm pg18-fleet-lab
# This irreversibly removes all lab data if the volume is not in use:
# docker volume rm pg18_fleet_data
```

Do not automate this cleanup as part of routine production housekeeping.