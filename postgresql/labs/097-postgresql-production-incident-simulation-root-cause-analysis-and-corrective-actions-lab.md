# Chapter 097 — Production Incident Simulation, RCA and Corrective Actions Lab

**PostgreSQL 18 · Disposable test database only · Runtime pending**

## 1. Preflight and safety

Start an isolated PostgreSQL 18 instance and three separate `psql` sessions. Ensure all connections target the disposable environment. Do not run lock-injection SQL on production. Assign incident commander, DBRE lead, application owner and scribe. Define synthetic SLO, alert threshold and abort conditions.

## 2. Prepare test workload

Run the Chapter 097 setup SQL in the disposable database. Record a baseline successful read and update, p95/p99 (if available), connection count and UTC timestamp.

## 3. Inject blocking fault

Session A:
```sql
BEGIN;
UPDATE incident097.accounts SET balance=balance+1 WHERE id=1;
```

Session B:
```sql
SET lock_timeout='10s';
UPDATE incident097.accounts SET balance=balance+2 WHERE id=1;
```

While B is waiting, Session C runs [097 diagnostic SQL](../labs/sql/097-incident-rca-inspect.sql). Record `pg_blocking_pids`, wait event, transaction age and timestamp. Do not extend the fault beyond the approved test duration.

## 4. Incident command and mitigation

Declare the synthetic incident, capture application impact, assign one mitigation owner and issue a factual update. Roll back Session A to release the lock. Record whether B succeeded or timed out. Verify a fresh test transaction completes normally.

## 5. Investigate and document

Populate [097 incident timeline](../labs/incident/097-incident-simulation-timeline.csv). Use [blameless RCA template](../labs/incident/097-blameless-rca-template.md) to distinguish observed blocker, contributing factors and detection gaps.

## 6. Corrective actions

Populate [097 COA tracker](../labs/incident/097-corrective-action-tracker.csv). Example improvements: application transaction scope, bounded timeouts, pooler retry behavior, blocker alerts and runbook ownership. Define before/after tests and evidence.

## 7. Repeat and accept

Repeat the same bounded scenario after approved corrective changes in the disposable environment. Confirm improved detection and bounded application impact. Complete [097 acceptance scorecard](../labs/acceptance/097-incident-rca-scorecard.csv). Mark unexecuted work NOT VERIFIED.

## 8. Cleanup

In Session A issue `ROLLBACK` if still open. In disposable database only, `DROP SCHEMA incident097 CASCADE;` after evidence capture and explicit lab cleanup approval.

**Runtime:** pending.
