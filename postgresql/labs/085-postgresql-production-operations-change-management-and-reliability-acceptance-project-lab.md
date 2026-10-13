# Chapter 085 — Production Operations, Change Management and Reliability Acceptance Lab

**PostgreSQL 18 · Disposable cluster only · Runtime pending**

## 1. Prerequisites

Provision a disposable PostgreSQL 18 cluster, application smoke-test client, approved lab identity, monitoring and isolated backup/restore target. Assign change commander, executor, independent verifier and application owner. Never use production customer data or execute a real destructive change as a demonstration.

## 2. Baseline and readiness

Run [085 preflight SQL](../labs/sql/085-production-change-preflight.sql). Record version, recovery role, extension inventory, settings source, pending restarts, replication/archiving, XID age, active sessions and lock waits. Independently verify backup recovery, disk headroom, app latency and change approvals.

## 3. Change plan

Create a ticket describing the disposable lab database, intended config change, targeted table maintenance, risk, start/end UTC, abort criteria, rollback owner and application smoke tests. Complete [085 change evidence template](../labs/acceptance/085-change-evidence-template.md).

## 4. Disposable fixture

```sql
CREATE TABLE public.ch085_orders (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  status text NOT NULL DEFAULT 'new',
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.ch085_orders(status)
SELECT CASE WHEN g % 2 = 0 THEN 'new' ELSE 'done' END
FROM generate_series(1,1000) AS g;
```

Record count and representative application reads/writes.

## 5. Controlled change

In the disposable lab only, capture original value **and source** of `log_min_duration_statement`. Apply a reviewed temporary logging change with `ALTER SYSTEM SET log_min_duration_statement='500ms'`, request `SELECT pg_reload_conf();`, and verify effective value, `source`, `pending_restart` and logs. If the setting is owned by a provider/operator, do not use ALTER SYSTEM; use its supported controller.

Then perform targeted `VACUUM (ANALYZE) public.ch085_orders;` as a **separate top-level command** outside a transaction block. Verify table statistics, row count, read/write behavior and latency.

## 6. Simulated failure and rollback

Introduce an intentionally unacceptable *lab-only* logging threshold in a separate approved rehearsal, detect drift and revert through the same configuration owner. If the original setting was set through `ALTER SYSTEM`, restore its original value; otherwise reset the lab override and reload. Confirm application connectivity and no pending restart. Do not run uncontrolled restarts or delete any data.

## 7. Independent verification

Have a second reviewer compare the before/after SQL, app SLO, backup restore evidence, alert delivery and config source. Validate there are no lingering changes or failed maintenance steps.

## 8. Acceptance and closure

Complete [085 scorecard](../labs/acceptance/085-production-operations-scorecard.csv), record any NOT VERIFIED items, change timeline, rollback decision, owners and follow-up actions. Do not mark production readiness PASS based only on a single-node disposable lab.

**Runtime:** pending.
