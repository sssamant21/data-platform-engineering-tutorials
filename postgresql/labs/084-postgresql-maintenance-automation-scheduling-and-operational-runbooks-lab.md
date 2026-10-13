# Chapter 084 — Maintenance Automation, Scheduling and Operational Runbooks Lab

**PostgreSQL 18 · Disposable database only · Runtime pending**

## 1. Prerequisites and safeguards

Use a disposable PostgreSQL 18 cluster and PowerShell 7 or Windows PowerShell with `psql` in PATH. Provision a restricted lab maintenance identity and a secure libpq passfile or approved secret provider. Do not place credentials in the script or Git.

Create fixture in a disposable database:

```sql
CREATE TABLE public.ch084_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  payload text NOT NULL
);
INSERT INTO public.ch084_events(payload)
SELECT repeat('x',200) FROM generate_series(1,10000);
UPDATE public.ch084_events SET payload=repeat('y',200) WHERE id % 3=0;
```

## 2. Read-only baseline

Run [084 preflight SQL](../labs/sql/084-maintenance-preflight.sql). Record database identity, `pg_is_in_recovery()`, XID age, table statistics, WAL/archiver health, locks, disk headroom and UTC time. Check application SLOs and active incidents outside SQL.

## 3. Controlled maintenance

Review [PowerShell template](../labs/scripts/084-maintenance-job.ps1). The template defaults to **dry run**, uses an OS-level exclusive file handle to serialize executions on one host, and targets only `public.ch084_events`. It is **not** a multi-host distributed lock. Do not deploy to multiple scheduler nodes without an external coordination mechanism.

Run:

```powershell
./postgresql/labs/scripts/084-maintenance-job.ps1 -Database ch084_lab -DryRun
```

After confirming the lab database, credentials, exclusive host ownership and backups:

```powershell
./postgresql/labs/scripts/084-maintenance-job.ps1 -Database ch084_lab -Execute
```

The script uses `psql -X -v ON_ERROR_STOP=1`, a bounded `lock_timeout`, and `statement_timeout`. Verify table statistics after completion.

## 4. Failure injection

- Run a second job concurrently on the **same host**: it must exit because the lock file is held.
- Simulate unavailable PostgreSQL: the job must return failure and retain logs.
- Simulate a lock blocker on the lab table: job must stop after the lock timeout.
- Run `-DryRun` again: no maintenance SQL should execute.

Do not use production tables for these tests.

## 5. Scheduler and recovery tabletop

Draft a cron/systemd/Kubernetes CronJob schedule with concurrency controls, missed-run handling, a maximum deadline, scoped identity and alerts. Explain how distributed scheduling changes the locking strategy. Document failure response, retry budget and manual override approval.

## 6. Acceptance

Complete [084 scorecard](../labs/acceptance/084-maintenance-automation-scorecard.csv). Record exit codes, UTC start/end, redacted logs, before/after metrics and application health. Mark unexecuted scheduler, distributed lock and HA tests NOT VERIFIED.

**Runtime:** pending.
