# Chapter 01 Lab — Deploy, Query, Inspect and Restore PostgreSQL

**Safety:** Disposable local lab ONLY. Do not run the destructive cleanup command against an existing container or volume.  
**Runtime:** Docker Desktop (Windows PowerShell) or Docker Engine with PostgreSQL 17 container.  
**Status:** Lab instructions authored; runtime execution not yet completed.

[Chapter 01](../../chapters/01-postgresql-fundamentals-and-architecture.md)

## Step 0 — Prerequisites

Run in PowerShell:

```powershell
docker version
docker info --format '{{.OSType}}'
```

Expected: Docker client/server available and `linux` container mode. **Stop unless the Docker context is an explicitly approved disposable local engine.** A remote or shared engine is not suitable. Run this read-only preflight before creating anything:

```powershell
$ErrorActionPreference = 'Stop'
$context = docker context show
if ($LASTEXITCODE -ne 0) { throw 'Cannot determine Docker context' }
Write-Host "Docker context: $context (verify this is your approved disposable local engine)"
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Requires a running Linux Docker engine' }
$existingContainer = @(docker ps -a --filter 'name=^/pg-fleet-lab This exercise includes a plain-text demo password appropriate only for a disposable local training container.

## Step 1 — Start PostgreSQL

```powershell
docker run -d `
  --name pg-fleet-lab `
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe_123 `
  -e POSTGRES_DB=appdb `
  -p 127.0.0.1:55432:5432 `
  -v pg_fleet_data:/var/lib/postgresql/data `
  postgres:17
if ($LASTEXITCODE -ne 0) { throw 'Docker run failed; do not continue to docker exec' }
```

```powershell
docker ps --filter "name=pg-fleet-lab"
docker exec pg-fleet-lab pg_isready -U postgres
docker logs --tail 20 pg-fleet-lab
```

Expected: container running and PostgreSQL accepting connections.

**Security note:** The example uses the `postgres` superuser only to simplify isolated training. Production applications should use least-privilege roles, secret management, and encrypted connections.

## Step 2 — Connect and verify

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d appdb
```

In the `psql` session:

```sql
SELECT version();
SELECT current_database();
SELECT current_user;
SELECT pg_is_in_recovery();
```

Expected: PostgreSQL 17, `appdb`, `postgres`, and `false` for a writable primary.

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
docker exec pg-fleet-lab sh -c 'pg_dump -U postgres -Fc appdb > /tmp/appdb.dump'
docker cp pg-fleet-lab:/tmp/appdb.dump .\appdb.dump
docker exec pg-fleet-lab createdb -U postgres appdb_restore
docker exec pg-fleet-lab pg_restore --exit-on-error -U postgres -d appdb_restore /tmp/appdb.dump
if ($LASTEXITCODE -ne 0) { throw 'Restore failed; do not report success' }
docker exec pg-fleet-lab psql -U postgres -d appdb_restore -c "SELECT count(*) FROM orders;"
```

Expected: 50,000 restored orders. For a repeated run, choose a new restore database name or deliberately remove the previous disposable restore database first. This test demonstrates logical restore, not WAL archiving, PITR or an independent-node disaster recovery scenario.

## Step 8 — Collect evidence

Record PostgreSQL version, image tag, check outputs, plan comparisons, rollback test, health query results, and restore row count. Redact secrets before committing logs to GitHub.

## Step 9 — Optional cleanup (destructive to this lab only)

**Only after independently verifying the active Docker context, exact container ID, container mounts, volume identity, and that both resources were created by this exercise.** If identity is uncertain, retain the resources and stop. The commands below are deliberately commented out to prevent accidental copy/paste deletion:

```powershell
# docker stop pg-fleet-lab
# docker rm pg-fleet-lab
# This irreversibly removes all lab data if the volume is not in use:
# docker volume rm pg_fleet_data
```

Do not automate this cleanup as part of routine production housekeeping.
 --format '{{.Names}}')
if ($LASTEXITCODE -ne 0 -or $existingContainer.Count -ne 0) { throw 'Container name is occupied or cannot be checked; stop' }
$existingVolume = @(docker volume ls --filter 'name=^pg_fleet_data This exercise includes a plain-text demo password appropriate only for a disposable local training container.

## Step 1 — Start PostgreSQL

```powershell
docker run -d `
  --name pg-fleet-lab `
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe_123 `
  -e POSTGRES_DB=appdb `
  -p 127.0.0.1:55432:5432 `
  -v pg_fleet_data:/var/lib/postgresql/data `
  postgres:17
```

```powershell
docker ps --filter "name=pg-fleet-lab"
docker exec pg-fleet-lab pg_isready -U postgres
docker logs --tail 20 pg-fleet-lab
```

Expected: container running and PostgreSQL accepting connections.

**Security note:** The example uses the `postgres` superuser only to simplify isolated training. Production applications should use least-privilege roles, secret management, and encrypted connections.

## Step 2 — Connect and verify

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d appdb
```

In the `psql` session:

```sql
SELECT version();
SELECT current_database();
SELECT current_user;
SELECT pg_is_in_recovery();
```

Expected: PostgreSQL 17, `appdb`, `postgres`, and `false` for a writable primary.

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
docker exec pg-fleet-lab sh -c 'pg_dump -U postgres -Fc appdb > /tmp/appdb.dump'
docker cp pg-fleet-lab:/tmp/appdb.dump .\appdb.dump
docker exec pg-fleet-lab createdb -U postgres appdb_restore
docker exec pg-fleet-lab pg_restore -U postgres -d appdb_restore /tmp/appdb.dump
docker exec pg-fleet-lab psql -U postgres -d appdb_restore -c "SELECT count(*) FROM orders;"
```

Expected: 50,000 restored orders. For a repeated run, choose a new restore database name or deliberately remove the previous disposable restore database first. This test demonstrates logical restore, not WAL archiving, PITR or an independent-node disaster recovery scenario.

## Step 8 — Collect evidence

Record PostgreSQL version, image tag, check outputs, plan comparisons, rollback test, health query results, and restore row count. Redact secrets before committing logs to GitHub.

## Step 9 — Optional cleanup (destructive to this lab only)

**Only after manually confirming the exact names identify disposable lab resources:**

```powershell
docker stop pg-fleet-lab
docker rm pg-fleet-lab
# This irreversibly removes all lab data if the volume is not in use:
docker volume rm pg_fleet_data
```

Do not automate this cleanup as part of routine production housekeeping.
 --format '{{.Name}}')
if ($LASTEXITCODE -ne 0 -or $existingVolume.Count -ne 0) { throw 'Volume name is occupied or cannot be checked; stop' }
$portListener = Get-NetTCPConnection -LocalPort 55432 -State Listen -ErrorAction SilentlyContinue
if ($portListener) { throw 'Port 55432 is already listening; stop' }
```

The absence checks do not prove that the selected Docker engine is disposable; confirm its endpoint and ownership independently. Do not delete or reuse unknown resources. A plain-text demo password is appropriate only for this disposable local training container. This exercise includes a plain-text demo password appropriate only for a disposable local training container.

## Step 1 — Start PostgreSQL

```powershell
docker run -d `
  --name pg-fleet-lab `
  -e POSTGRES_PASSWORD=TrainingOnly_ChangeMe_123 `
  -e POSTGRES_DB=appdb `
  -p 127.0.0.1:55432:5432 `
  -v pg_fleet_data:/var/lib/postgresql/data `
  postgres:17
```

```powershell
docker ps --filter "name=pg-fleet-lab"
docker exec pg-fleet-lab pg_isready -U postgres
docker logs --tail 20 pg-fleet-lab
```

Expected: container running and PostgreSQL accepting connections.

**Security note:** The example uses the `postgres` superuser only to simplify isolated training. Production applications should use least-privilege roles, secret management, and encrypted connections.

## Step 2 — Connect and verify

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d appdb
```

In the `psql` session:

```sql
SELECT version();
SELECT current_database();
SELECT current_user;
SELECT pg_is_in_recovery();
```

Expected: PostgreSQL 17, `appdb`, `postgres`, and `false` for a writable primary.

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
docker exec pg-fleet-lab sh -c 'pg_dump -U postgres -Fc appdb > /tmp/appdb.dump'
docker cp pg-fleet-lab:/tmp/appdb.dump .\appdb.dump
docker exec pg-fleet-lab createdb -U postgres appdb_restore
docker exec pg-fleet-lab pg_restore -U postgres -d appdb_restore /tmp/appdb.dump
docker exec pg-fleet-lab psql -U postgres -d appdb_restore -c "SELECT count(*) FROM orders;"
```

Expected: 50,000 restored orders. For a repeated run, choose a new restore database name or deliberately remove the previous disposable restore database first. This test demonstrates logical restore, not WAL archiving, PITR or an independent-node disaster recovery scenario.

## Step 8 — Collect evidence

Record PostgreSQL version, image tag, check outputs, plan comparisons, rollback test, health query results, and restore row count. Redact secrets before committing logs to GitHub.

## Step 9 — Optional cleanup (destructive to this lab only)

**Only after manually confirming the exact names identify disposable lab resources:**

```powershell
docker stop pg-fleet-lab
docker rm pg-fleet-lab
# This irreversibly removes all lab data if the volume is not in use:
docker volume rm pg_fleet_data
```

Do not automate this cleanup as part of routine production housekeeping.
