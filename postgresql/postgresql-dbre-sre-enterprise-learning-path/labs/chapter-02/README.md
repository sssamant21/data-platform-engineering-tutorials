# Chapter 02 Lab — Relational Database Design and Safe Constraints

**Duration:** ~25 minutes within the 60-minute lesson · **Audience:** Beginner DBRE/SRE · **Runtime:** PostgreSQL 17  
**Status:** Instructions written; not executed. Do not treat expected results as observed results.

[Chapter 02](../../chapters/02-databases-schemas-tables-and-relationships.md) · [Course home](../../README.md)

## Safety and prerequisite checks

Run only against the explicitly disposable Docker container created in [Chapter 01](../chapter-01/README.md), named `pg-fleet-lab`. This lab creates a **separate** database, `training_ch02`; it does not modify the Chapter 01 `appdb` database.

**Version compatibility gate (PostgreSQL 18 migration):** Chapter 01 now provisions a PostgreSQL 18 container with a new volume mounted at `/var/lib/postgresql`, while this Chapter 02 procedure still checks for `postgres:17` and the legacy `/var/lib/postgresql/data` mount. **Do not run Chapter 02 against the source-migrated Chapter 01 container or weaken the identity checks to make it pass.** The shared-container prerequisite is currently unsatisfied. Keep this lab source-only/pending until its own commands, expected results, and version-specific mount checks are migrated and reviewed for PostgreSQL 18, then execute only in an approved disposable environment. The PostgreSQL 17 steps below are retained as historical instructions, not PG18 execution evidence.

Use PowerShell and Docker Desktop (Linux containers). No production credentials or customer data.

Before running any SQL, retrieve the **full container ID and Docker context recorded during Chapter 01 creation**. Do not infer ownership from the container name, a successful readiness check, or the training label alone. Replace the two placeholders below with the retained values; never copy an ID from the current lookup into the expected-ID variable.

```powershell
$ErrorActionPreference = 'Stop'
$expectedContext = '<recorded Chapter 01 Docker context>'
$expectedId = '<recorded Chapter 01 full container ID>'
if ($expectedContext -like '<*' -or $expectedId -like '<*') { throw 'Supply retained Chapter 01 creation evidence first' }
$context = docker context show
if ($LASTEXITCODE -ne 0 -or $context -ne $expectedContext) { throw 'Docker context differs from Chapter 01 evidence' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Docker endpoint' }
# Manually confirm this endpoint is the approved, local, disposable Docker engine.
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Linux Docker engine required' }
$id = docker inspect --type container --format '{{.Id}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $id -ne $expectedId) { throw 'Container identity mismatch' }
$label = docker inspect --type container --format '{{index .Config.Labels "dbre.training"}}' $id
if ($LASTEXITCODE -ne 0 -or $label -ne 'postgresql-enterprise-ch01') { throw 'Training label mismatch' }
$image = docker inspect --type container --format '{{.Config.Image}}' $id
if ($LASTEXITCODE -ne 0 -or $image -ne 'postgres:17') { throw 'Unexpected PostgreSQL image' }
$volume = docker inspect --type container --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' $id
if ($LASTEXITCODE -ne 0 -or $volume -ne 'pg_fleet_data') { throw 'Unexpected PostgreSQL data mount' }
$state = docker inspect --type container --format '{{.State.Running}}' $id
if ($LASTEXITCODE -ne 0 -or $state -ne 'true') { throw 'Lab container not running' }
docker exec $id pg_isready -U postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL is not ready' }
$identityResult = @(docker exec $id psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -tA -F '|' -c "SELECT current_setting('server_version_num')::int / 10000, pg_is_in_recovery();")
if ($LASTEXITCODE -ne 0 -or $identityResult.Count -ne 1 -or $identityResult[0].Trim() -ne '17|f') {
  throw 'PostgreSQL 17 primary identity check failed; do not execute this historical lab'
}
```

**Expected:** a verified Chapter 01 container, PostgreSQL major version `17`, and `f` for `pg_is_in_recovery()`. The PowerShell gate requires exactly one unaligned output row, `17|f`, and stops automatically on any other version or recovery role. If the container is absent, **stop**: the current Chapter 01 setup creates PostgreSQL 18 and cannot satisfy this historical PostgreSQL 17 prerequisite. Do not rerun Chapter 01 expecting a compatible PostgreSQL 17 container, and never adopt, replace, or delete an existing container to proceed. Wait for the scoped Chapter 02 PostgreSQL 18 migration and independent prerequisite review. Keep the recorded context/ID available for the rest of this lab. Keep the same PowerShell session and use `$expectedId` (the immutable ID retained from Chapter 01 creation) for every subsequent `docker exec`, not the mutable container name. If the container is recreated, the Docker context changes, or the retained identity cannot be reverified, stop; do not substitute a newly discovered ID.

## Step 1 — Check and create the chapter database

Check whether it already exists:

```powershell
$existingDb = @(docker exec $expectedId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -tA -c "SELECT datname FROM pg_database WHERE datname='training_ch02';")
if ($LASTEXITCODE -ne 0) { throw "Database-existence check failed; do not create anything" }
if ($existingDb.Count -gt 0) { throw "training_ch02 already exists or output was unexpected; inspect manually before proceeding" }
```

**Expected for first use:** no rows and a zero `psql` exit code. Any existing database, unexpected output, or query failure stops the procedure; inspect manually and never drop it automatically.

When no database exists:

```powershell
docker exec $expectedId createdb -U postgres training_ch02
```

Connect:

```powershell
docker exec -it $expectedId psql -U postgres -d training_ch02
```

Inside `psql`, verify:

```sql
SELECT current_database(), current_user;
```

Expected: `training_ch02` and `postgres`.

## Step 2 — Create a namespace and four tables

Paste the following into the `psql` session **once** for a clean `training_ch02` database.

```sql
CREATE SCHEMA retail_lab;

CREATE TABLE retail_lab.customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE retail_lab.products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE retail_lab.orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES retail_lab.customers(customer_id),
    status TEXT NOT NULL DEFAULT 'created'
        CHECK (status IN ('created','paid','cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE retail_lab.order_items (
    order_id BIGINT NOT NULL REFERENCES retail_lab.orders(order_id),
    line_no INTEGER NOT NULL CHECK (line_no > 0),
    product_id BIGINT NOT NULL REFERENCES retail_lab.products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, line_no)
);
```

**Expected:** four successful `CREATE TABLE` messages. The foreign keys use the default `NO ACTION` referential action and protect against orphan references.

Inspect:

```text
\dt retail_lab.*
\d retail_lab.orders
\d retail_lab.order_items
```

`\dt` and `\d` are `psql` meta-commands, not SQL statements.

## Step 3 — Add deterministic synthetic records

```sql
INSERT INTO retail_lab.customers (email)
VALUES ('ana@example.test'), ('ben@example.test');

INSERT INTO retail_lab.products (sku, product_name, unit_price)
VALUES
    ('SKU-001', 'Backpack', 49.99),
    ('SKU-002', 'Notebook', 9.50);

INSERT INTO retail_lab.orders (customer_id, status)
SELECT customer_id, 'paid'
FROM retail_lab.customers
WHERE email = 'ana@example.test';

INSERT INTO retail_lab.order_items
    (order_id, line_no, product_id, quantity, unit_price)
SELECT
    o.order_id, 1, p.product_id, 2, p.unit_price
FROM retail_lab.orders AS o
JOIN retail_lab.customers AS c
  ON c.customer_id = o.customer_id
JOIN retail_lab.products AS p
  ON p.sku = 'SKU-002'
WHERE c.email = 'ana@example.test';
```

**Expected:** 2 customers, 2 products, 1 order, and 1 order item. The order-item unit price is intentionally copied at purchase time.

Check counts:

```sql
SELECT
  (SELECT count(*) FROM retail_lab.customers) AS customers,
  (SELECT count(*) FROM retail_lab.products) AS products,
  (SELECT count(*) FROM retail_lab.orders) AS orders,
  (SELECT count(*) FROM retail_lab.order_items) AS order_items;
```

Expected result:

```text
 customers | products | orders | order_items
-----------+----------+--------+------------
         2 |        2 |      1 |          1
```

## Step 4 — Join tables and calculate an order total

```sql
SELECT c.email, o.order_id,
       SUM(i.quantity * i.unit_price) AS order_total
FROM retail_lab.customers AS c
JOIN retail_lab.orders AS o ON o.customer_id = c.customer_id
JOIN retail_lab.order_items AS i ON i.order_id = o.order_id
GROUP BY c.email, o.order_id
ORDER BY o.order_id;
```

**Expected:** one row for `ana@example.test`, with an order total of **19.00**. The generated order ID can vary; do not hard-code it.

### Question for the learner

What happens to old order totals if the catalog price of a Notebook increases tomorrow? Because `order_items.unit_price` captures the purchase-time price, existing order totals stay unchanged.

## Step 5 — Observe a CHECK constraint failure safely

These are **intentional errors** to demonstrate guardrails in a disposable environment. Run manually in `psql`, not as part of an automatic all-success deployment script.

```sql
BEGIN;
SAVEPOINT before_bad_row;

INSERT INTO retail_lab.order_items
    (order_id, line_no, product_id, quantity, unit_price)
SELECT o.order_id, 2, p.product_id, 0, p.unit_price
FROM retail_lab.orders AS o
JOIN retail_lab.products AS p ON p.sku = 'SKU-002'
LIMIT 1;

-- Expected ERROR: violates CHECK constraint for quantity > 0
ROLLBACK TO SAVEPOINT before_bad_row;
COMMIT;
```

**Expected:** insert rejected; the failed savepoint is rolled back; the transaction can commit without changes. Verify:

```sql
SELECT count(*) AS order_item_count FROM retail_lab.order_items;
```

Expected: `1`.

## Step 6 — Observe a foreign-key failure safely

```sql
BEGIN;
SAVEPOINT before_bad_customer;

INSERT INTO retail_lab.orders (customer_id, status)
VALUES (-999, 'created');

-- Expected ERROR: foreign key violation, no customer -999.
ROLLBACK TO SAVEPOINT before_bad_customer;
COMMIT;
```

**Expected:** insert rejected; no orphan order created. Do not disable foreign-key enforcement to make the example succeed.

## Step 7 — Explore indexes and statistics

Primary keys and `UNIQUE` constraints create indexes, but PostgreSQL does not automatically create an index on every referencing foreign-key column.

```sql
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'retail_lab'
ORDER BY tablename, indexname;

-- Illustrative workload index; inspect query workload before doing this in production.
CREATE INDEX idx_orders_customer_created
ON retail_lab.orders(customer_id, created_at DESC);

SELECT
    relname,
    n_live_tup,
    n_dead_tup
FROM pg_stat_user_tables
WHERE schemaname = 'retail_lab'
ORDER BY relname;

SELECT
    pg_size_pretty(pg_total_relation_size('retail_lab.orders')) AS orders_total_size,
    pg_size_pretty(pg_total_relation_size('retail_lab.order_items')) AS order_items_total_size;
```

Table-statistics counts may not be exact or immediately refreshed. Size output is environment-dependent. With a tiny sample the planner may not choose the added index.

## Step 8 — Explain database and operational design choices

Write a short design review:

1. Why does `orders.customer_id` require a valid customer record?
2. Which relationship would be affected by removing a product?
3. Where is the historical purchase price stored, and why?
4. Which two entities might grow at different rates?
5. How would you identify the owner of schema changes and approve DDL in a production environment?
6. If moving to RDS or Kubernetes, which operational responsibilities shift and which remain?

## Step 9 — Evidence and expected acceptance

Store *sanitized* evidence outside the repository until reviewed:

- version, database identity, and schema object listings;
- four table creation confirmations and row-count output;
- correct 19.00 order total;
- one CHECK failure and one FK failure, with saved transaction recovery;
- index inventory and table size queries;
- completed design-review notes.

**Not yet executed:** Evidence is still pending; this README records expected results, not successful runtime validation.

## Optional cleanup — not automatic

Do not drop tables or databases merely to repeat the tutorial. The disposable `training_ch02` database can be retained for later lessons. If decommissioning an isolated lab, use a separate approval/identity check before any destructive operation.

## Official references

- [PostgreSQL 18: Data Definition](https://www.postgresql.org/docs/18/ddl.html)
- [PostgreSQL 18: Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18: Information Schema](https://www.postgresql.org/docs/18/information-schema.html)
- [PostgreSQL 18: psql](https://www.postgresql.org/docs/18/app-psql.html)
