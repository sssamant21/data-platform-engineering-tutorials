# Chapter 058 — Connection Pool Saturation, Timeouts and Recovery Lab

**PostgreSQL 18 · Disposable lab database · Runtime validation pending**

## 1. Safety and preflight

Use a dedicated PostgreSQL 18 instance with PgBouncer in a lab network. Maintain an independent administrator connection and confirm the lab database is isolated. Do not run connection storms, unbounded load tests or blanket backend termination.

## 2. Baseline

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/058-diagnostics.sql
```

Record max/reserved connections, session states, transaction ages and wait events.

## 3. Controlled blocking experiment

Create a disposable database `ch058_lab` and table:

```sql
CREATE TABLE public.ch058_lock_test(id integer PRIMARY KEY, note text);
INSERT INTO public.ch058_lock_test VALUES (1,'initial');
```

In **session A**:

```sql
BEGIN;
UPDATE public.ch058_lock_test SET note='held' WHERE id=1;
SELECT pg_backend_pid() AS blocking_pid;
-- Keep this transaction open for a short, supervised interval.
```

In **session B**, use a bounded wait:

```sql
SET lock_timeout='3s';
UPDATE public.ch058_lock_test SET note='waiting' WHERE id=1;
-- Expect SQLSTATE 55P03 (lock_not_available) after timeout.
```

Session A should promptly `ROLLBACK;` and session B should `RESET lock_timeout;`. Never leave idle transactions open after the exercise.

## 4. PgBouncer queue observation

From an authorized PgBouncer admin connection:

```powershell
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW STATS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW CLIENTS;"
```

Using a **small, fixed** number of lab clients, create short transactions and observe `cl_waiting`, server utilization and query waiting. Stop if queueing persists beyond the lab's agreed threshold. Capture the PgBouncer version and any field-name differences.

## 5. Cancellation vs termination decision

Review `pg_cancel_backend(pid)` versus `pg_terminate_backend(pid)` using an identified **lab-only** backend. First try a bounded query timeout and cooperative rollback. Termination is an optional, separately approved experiment; verify PID ownership and avoid admin, replication or other users' sessions.

## 6. Recovery acceptance

| Gate | Expected | Evidence |
|---|---|---|
| Blocking identified | PID and lock wait recorded | |
| Lock timeout | Bounded failure | |
| Session A cleanup | Transaction rolled back | |
| PgBouncer queue | Returns to baseline | |
| PostgreSQL slots | Admin headroom preserved | |
| Application errors | Return to baseline | |
| Recovery notes | Root cause and rollback documented | |

Drop `ch058_lab` only after confirming no shared objects or active sessions remain.

**Runtime:** pending.
