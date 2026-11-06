# Chapter 03 Lab — ACID Transactions and Two-Session MVCC

**Level:** Beginner-to-intermediate · **Duration:** ~23 minutes guided lab · **PostgreSQL:** 17  
**Status:** Authored; not runtime verified. Run on a disposable local database only.

[Chapter 03](../../chapters/03-sql-transactions-acid-and-mvcc.md) · [Previous Chapter 02 lab](../chapter-02/README.md)

## 0. Preflight and lab safety

Use Docker Desktop with the `pg-fleet-lab` container from Chapter 01. This exercise does not require a production environment and must not use one.

Open **two separate PowerShell terminals**, named **Session A** and **Session B**. Leave both open for the concurrency experiments. In this lab, do **not** enter Session B commands in Session A.

Before opening either SQL session, use **Session A PowerShell** to verify that the name still resolves to the exact disposable Chapter 01 container. Retrieve the original full container ID, Docker context and data-volume name from the Chapter 01 creation record; do **not** substitute values obtained from the current container for that independent record.

```powershell
$ErrorActionPreference = 'Stop'
$expectedContext = Read-Host 'Recorded Chapter 01 Docker context'
$expectedId = Read-Host 'Recorded Chapter 01 full container ID'
$expectedVolume = Read-Host 'Recorded Chapter 01 data volume (pg_fleet_data)'
if (-not $expectedContext -or $expectedId -notmatch '^[a-f0-9]{64}

Check the database name:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname='training_ch03';"
```

Expected for first use: no row. If a database named `training_ch03` already exists, inspect it first; **do not drop or overwrite it automatically**.

If it does not exist:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch03
```

## 1. Connect Session A and create test data

In **Session A PowerShell**, connect:

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d training_ch03
```

In **Session A psql**, run once on an empty chapter database:

```sql
SELECT current_database(), current_user;

CREATE TABLE public.accounts (
    account_id INTEGER PRIMARY KEY,
    balance NUMERIC(12,2) NOT NULL CHECK (balance >= 0)
);

INSERT INTO public.accounts (account_id, balance)
VALUES (1, 100.00), (2, 100.00);

SELECT * FROM public.accounts ORDER BY account_id;
```

Expected:

```text
 account_id | balance
------------+---------
          1 |  100.00
          2 |  100.00
```

The table is deliberately simple. It demonstrates database transactions but is **not** a complete finance or payments design.

## 2. Atomic commit

In **Session A psql**:

```sql
BEGIN;
UPDATE public.accounts
SET balance = balance - 25.00 WHERE account_id = 1;
UPDATE public.accounts
SET balance = balance + 25.00 WHERE account_id = 2;
COMMIT;

SELECT account_id, balance FROM public.accounts ORDER BY account_id;
SELECT SUM(balance) AS total_balance FROM public.accounts;
```

Expected: account 1 = 75.00, account 2 = 125.00, total = 200.00.

**Explanation:** both writes were grouped into one committed transaction. The database's CHECK constraint prevents a negative balance, but the transaction structure and application design must still preserve the conservation invariant.

## 3. Explicit rollback

In **Session A**:

```sql
BEGIN;
UPDATE public.accounts
SET balance = balance - 10.00 WHERE account_id = 1;
SELECT balance FROM public.accounts WHERE account_id = 1;
ROLLBACK;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: within the uncommitted transaction, account 1 shows 65.00; after rollback it shows 75.00.

## 4. Savepoint rollback without discarding all work

In **Session A**:

```sql
BEGIN;
SAVEPOINT before_change;
UPDATE public.accounts
SET balance = balance - 5.00 WHERE account_id = 1;
SELECT balance FROM public.accounts WHERE account_id = 1;
ROLLBACK TO SAVEPOINT before_change;
COMMIT;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: intermediate value 70.00; after savepoint rollback and commit, final value 75.00.

## 5. CHECK violation with controlled recovery

**Intentional SQL error** in this disposable lab. In **Session A**:

```sql
BEGIN;
SAVEPOINT before_invalid_balance;
UPDATE public.accounts
SET balance = -1
WHERE account_id = 1;
-- Expected ERROR: new row violates check constraint
ROLLBACK TO SAVEPOINT before_invalid_balance;
COMMIT;

SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: rejected UPDATE; after rollback-to-savepoint, final value 75.00. If you forget the savepoint rollback, the failed transaction cannot continue normally: issue `ROLLBACK;` before starting a new one.

## 6. Start Session B

Open **Session B PowerShell** (do not close A):

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d training_ch03
```

In **both sessions**, verify:

```sql
SELECT pg_backend_pid(), current_database(), current_user;
```

Expected: same database, different backend PIDs. Do not assume the numeric PIDs match the examples below.

## 7. Compare READ COMMITTED visibility

Run steps **in the exact sequence** shown. Leave Session A's transaction open only for the duration of the exercise, then commit immediately.

**Session A — start a READ COMMITTED transaction:**

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: 75.00. Leave A's transaction open.

**Session B — change and commit the row (autocommit statement):**

```sql
UPDATE public.accounts
SET balance = balance - 5.00
WHERE account_id = 1
RETURNING account_id, balance;
```

Expected: 70.00. In default `psql` autocommit mode, the statement commits on successful completion.

**Session A — repeat the SELECT and finish the transaction:**

```sql
SELECT balance FROM public.accounts WHERE account_id = 1;
COMMIT;
```

Expected: **70.00** on the second SELECT, even though the explicit transaction began before Session B's update. In READ COMMITTED, each statement uses a fresh snapshot of committed data.

## 8. Compare REPEATABLE READ visibility

**Session A — start a transaction and establish its snapshot:**

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: 70.00. Keep A open.

**Session B — update the same row:**

```sql
UPDATE public.accounts
SET balance = balance + 3.00
WHERE account_id = 1
RETURNING account_id, balance;
```

Expected: 73.00. The update can commit because A only read the row and did not take an explicit conflicting lock.

**Session A — read before and after ending the transaction:**

```sql
SELECT balance FROM public.accounts WHERE account_id = 1;
COMMIT;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: first SELECT **70.00**, next SELECT after COMMIT **73.00**. The snapshot remains stable within the REPEATABLE READ transaction.

**Caution:** This demonstration performs read-only queries in A during the concurrent updates. A transaction that tries to update a row changed since its REPEATABLE READ snapshot could instead fail with a concurrent-update serialization error.

## 9. Observe session state safely

Begin a short, read-only transaction in **Session A**:

```sql
BEGIN;
SELECT current_database();
```

Before A commits, run in **Session B**:

```sql
SELECT pid, usename, state, wait_event_type,
       now() - xact_start AS transaction_age
FROM pg_stat_activity
WHERE datname = 'training_ch03'
ORDER BY pid;
```

Expected: Session A may appear as `idle in transaction` while it is waiting at its `psql` prompt. Session B may appear as `active`. Actual values and timing vary.

**Immediately finish Session A**:

```sql
COMMIT;
```

Never leave an instructional session idle in transaction after the exercise.

## 10. Record results and cleanly disconnect

In either session:

```sql
SELECT account_id, balance FROM public.accounts ORDER BY account_id;
```

Expected final balances: account 1 = 73.00, account 2 = 125.00. The later Session B updates were intentionally not paired with offsetting account changes; the resulting sum is 198.00, which illustrates why business invariants need an application transaction and design.

Exit **both** PostgreSQL sessions with:

```text
\q
```

Do not delete the database as part of ordinary lab cleanup.

## Evidence and pass conditions

- [ ] Version and target database identity recorded.
- [ ] Two distinct backend PIDs observed.
- [ ] Atomic commit produced 75.00 and 125.00.
- [ ] Rollback restored 75.00.
- [ ] Savepoint recovered without retaining its invalid change.
- [ ] CHECK failure rejected an invalid negative balance.
- [ ] READ COMMITTED repeated query observed a newer committed value.
- [ ] REPEATABLE READ preserved its snapshot until commit.
- [ ] `pg_stat_activity` queried, and both sessions closed.
- [ ] Evidence sanitized; no real passwords or personal data captured.

**Expected outcomes are not runtime evidence.** This chapter has not been executed or independently reviewed by publication automation.

## If a step fails

| Problem | Cause | Recovery |
|---|---|---|
| Table already exists | A prior lab run is present | Inspect existing data; start a separately named disposable database if needed |
| `current transaction is aborted` | Statement failed before rollback | Issue `ROLLBACK;` or `ROLLBACK TO SAVEPOINT`, as appropriate |
| Session B seems blocked | Session A may hold a conflicting write lock | Check and end Session A transaction after reviewing which action is in progress |
| Session A sees a surprising value | Wrong order, wrong database, or isolation level | Confirm backend and `SHOW transaction_isolation;` inside the transaction |
| Background connection gone | Client/container restarted | Reconnect, inspect state, rerun in a fresh disposable lab |

## Official documentation

- [PostgreSQL 17: Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html)
- [PostgreSQL 17: MVCC Introduction](https://www.postgresql.org/docs/17/mvcc-intro.html)
- [PostgreSQL 17: SAVEPOINT](https://www.postgresql.org/docs/17/sql-savepoint.html)
- [PostgreSQL 17: Statistics Views](https://www.postgresql.org/docs/17/monitoring-stats.html)
 -or $expectedVolume -ne 'pg_fleet_data') {
    throw 'Missing or invalid independent Chapter 01 identity record'
}
$context = docker context show
if ($LASTEXITCODE -ne 0 -or $context -ne $expectedContext) { throw 'Docker context mismatch' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Docker context inspection failed' }
# Inspect the endpoint above and independently confirm it is the approved local, disposable engine.
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Requires Linux Docker engine' }
$id = docker inspect --format '{{.Id}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or $id -ne $expectedId) { throw 'Container identity mismatch' }
$label = docker inspect --format '{{index .Config.Labels "dbre.training"}}' $id
if ($LASTEXITCODE -ne 0 -or $label -ne 'postgresql-enterprise-ch01') { throw 'Training ownership label mismatch' }
$image = docker inspect --format '{{.Config.Image}}' $id
if ($LASTEXITCODE -ne 0 -or $image -ne 'postgres:17') { throw 'Unexpected image' }
$volume = docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' $id
if ($LASTEXITCODE -ne 0 -or $volume -ne $expectedVolume) { throw 'Data volume mismatch' }
$running = docker inspect --format '{{.State.Running}}' $id
if ($LASTEXITCODE -ne 0 -or $running -ne 'true') { throw 'Training container not running' }
docker exec $id pg_isready -U postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL not ready' }
docker exec $id psql -U postgres -d postgres -v ON_ERROR_STOP=1 -tAc "SELECT current_setting('server_version_num')::int / 10000, pg_is_in_recovery();"
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL identity query failed' }
```

Expected: version major **17** and `pg_is_in_recovery() = false`. Verify these values explicitly before continuing; successful command exit alone does not establish the expected version or primary role. If the context endpoint, recorded identity, mount, version or role cannot be verified, **stop**. Repeat this preflight in Session B before opening its `psql` connection. Subsequent commands use the container name only after this verification; re-check identity if the container or context changes.

Check the database name:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname='training_ch03';"
```

Expected for first use: no row. If a database named `training_ch03` already exists, inspect it first; **do not drop or overwrite it automatically**.

If it does not exist:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch03
```

## 1. Connect Session A and create test data

In **Session A PowerShell**, connect:

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d training_ch03
```

In **Session A psql**, run once on an empty chapter database:

```sql
SELECT current_database(), current_user;

CREATE TABLE public.accounts (
    account_id INTEGER PRIMARY KEY,
    balance NUMERIC(12,2) NOT NULL CHECK (balance >= 0)
);

INSERT INTO public.accounts (account_id, balance)
VALUES (1, 100.00), (2, 100.00);

SELECT * FROM public.accounts ORDER BY account_id;
```

Expected:

```text
 account_id | balance
------------+---------
          1 |  100.00
          2 |  100.00
```

The table is deliberately simple. It demonstrates database transactions but is **not** a complete finance or payments design.

## 2. Atomic commit

In **Session A psql**:

```sql
BEGIN;
UPDATE public.accounts
SET balance = balance - 25.00 WHERE account_id = 1;
UPDATE public.accounts
SET balance = balance + 25.00 WHERE account_id = 2;
COMMIT;

SELECT account_id, balance FROM public.accounts ORDER BY account_id;
SELECT SUM(balance) AS total_balance FROM public.accounts;
```

Expected: account 1 = 75.00, account 2 = 125.00, total = 200.00.

**Explanation:** both writes were grouped into one committed transaction. The database's CHECK constraint prevents a negative balance, but the transaction structure and application design must still preserve the conservation invariant.

## 3. Explicit rollback

In **Session A**:

```sql
BEGIN;
UPDATE public.accounts
SET balance = balance - 10.00 WHERE account_id = 1;
SELECT balance FROM public.accounts WHERE account_id = 1;
ROLLBACK;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: within the uncommitted transaction, account 1 shows 65.00; after rollback it shows 75.00.

## 4. Savepoint rollback without discarding all work

In **Session A**:

```sql
BEGIN;
SAVEPOINT before_change;
UPDATE public.accounts
SET balance = balance - 5.00 WHERE account_id = 1;
SELECT balance FROM public.accounts WHERE account_id = 1;
ROLLBACK TO SAVEPOINT before_change;
COMMIT;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: intermediate value 70.00; after savepoint rollback and commit, final value 75.00.

## 5. CHECK violation with controlled recovery

**Intentional SQL error** in this disposable lab. In **Session A**:

```sql
BEGIN;
SAVEPOINT before_invalid_balance;
UPDATE public.accounts
SET balance = -1
WHERE account_id = 1;
-- Expected ERROR: new row violates check constraint
ROLLBACK TO SAVEPOINT before_invalid_balance;
COMMIT;

SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: rejected UPDATE; after rollback-to-savepoint, final value 75.00. If you forget the savepoint rollback, the failed transaction cannot continue normally: issue `ROLLBACK;` before starting a new one.

## 6. Start Session B

Open **Session B PowerShell** (do not close A):

```powershell
docker exec -it pg-fleet-lab psql -U postgres -d training_ch03
```

In **both sessions**, verify:

```sql
SELECT pg_backend_pid(), current_database(), current_user;
```

Expected: same database, different backend PIDs. Do not assume the numeric PIDs match the examples below.

## 7. Compare READ COMMITTED visibility

Run steps **in the exact sequence** shown. Leave Session A's transaction open only for the duration of the exercise, then commit immediately.

**Session A — start a READ COMMITTED transaction:**

```sql
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: 75.00. Leave A's transaction open.

**Session B — change and commit the row (autocommit statement):**

```sql
UPDATE public.accounts
SET balance = balance - 5.00
WHERE account_id = 1
RETURNING account_id, balance;
```

Expected: 70.00. In default `psql` autocommit mode, the statement commits on successful completion.

**Session A — repeat the SELECT and finish the transaction:**

```sql
SELECT balance FROM public.accounts WHERE account_id = 1;
COMMIT;
```

Expected: **70.00** on the second SELECT, even though the explicit transaction began before Session B's update. In READ COMMITTED, each statement uses a fresh snapshot of committed data.

## 8. Compare REPEATABLE READ visibility

**Session A — start a transaction and establish its snapshot:**

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: 70.00. Keep A open.

**Session B — update the same row:**

```sql
UPDATE public.accounts
SET balance = balance + 3.00
WHERE account_id = 1
RETURNING account_id, balance;
```

Expected: 73.00. The update can commit because A only read the row and did not take an explicit conflicting lock.

**Session A — read before and after ending the transaction:**

```sql
SELECT balance FROM public.accounts WHERE account_id = 1;
COMMIT;
SELECT balance FROM public.accounts WHERE account_id = 1;
```

Expected: first SELECT **70.00**, next SELECT after COMMIT **73.00**. The snapshot remains stable within the REPEATABLE READ transaction.

**Caution:** This demonstration performs read-only queries in A during the concurrent updates. A transaction that tries to update a row changed since its REPEATABLE READ snapshot could instead fail with a concurrent-update serialization error.

## 9. Observe session state safely

Begin a short, read-only transaction in **Session A**:

```sql
BEGIN;
SELECT current_database();
```

Before A commits, run in **Session B**:

```sql
SELECT pid, usename, state, wait_event_type,
       now() - xact_start AS transaction_age
FROM pg_stat_activity
WHERE datname = 'training_ch03'
ORDER BY pid;
```

Expected: Session A may appear as `idle in transaction` while it is waiting at its `psql` prompt. Session B may appear as `active`. Actual values and timing vary.

**Immediately finish Session A**:

```sql
COMMIT;
```

Never leave an instructional session idle in transaction after the exercise.

## 10. Record results and cleanly disconnect

In either session:

```sql
SELECT account_id, balance FROM public.accounts ORDER BY account_id;
```

Expected final balances: account 1 = 73.00, account 2 = 125.00. The later Session B updates were intentionally not paired with offsetting account changes; the resulting sum is 198.00, which illustrates why business invariants need an application transaction and design.

Exit **both** PostgreSQL sessions with:

```text
\q
```

Do not delete the database as part of ordinary lab cleanup.

## Evidence and pass conditions

- [ ] Version and target database identity recorded.
- [ ] Two distinct backend PIDs observed.
- [ ] Atomic commit produced 75.00 and 125.00.
- [ ] Rollback restored 75.00.
- [ ] Savepoint recovered without retaining its invalid change.
- [ ] CHECK failure rejected an invalid negative balance.
- [ ] READ COMMITTED repeated query observed a newer committed value.
- [ ] REPEATABLE READ preserved its snapshot until commit.
- [ ] `pg_stat_activity` queried, and both sessions closed.
- [ ] Evidence sanitized; no real passwords or personal data captured.

**Expected outcomes are not runtime evidence.** This chapter has not been executed or independently reviewed by publication automation.

## If a step fails

| Problem | Cause | Recovery |
|---|---|---|
| Table already exists | A prior lab run is present | Inspect existing data; start a separately named disposable database if needed |
| `current transaction is aborted` | Statement failed before rollback | Issue `ROLLBACK;` or `ROLLBACK TO SAVEPOINT`, as appropriate |
| Session B seems blocked | Session A may hold a conflicting write lock | Check and end Session A transaction after reviewing which action is in progress |
| Session A sees a surprising value | Wrong order, wrong database, or isolation level | Confirm backend and `SHOW transaction_isolation;` inside the transaction |
| Background connection gone | Client/container restarted | Reconnect, inspect state, rerun in a fresh disposable lab |

## Official documentation

- [PostgreSQL 17: Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html)
- [PostgreSQL 17: MVCC Introduction](https://www.postgresql.org/docs/17/mvcc-intro.html)
- [PostgreSQL 17: SAVEPOINT](https://www.postgresql.org/docs/17/sql-savepoint.html)
- [PostgreSQL 17: Statistics Views](https://www.postgresql.org/docs/17/monitoring-stats.html)
