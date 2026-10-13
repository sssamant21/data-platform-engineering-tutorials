# Chapter 070 — Planned Switchover, Failover and Split-Brain Prevention Lab

**PostgreSQL 18 · Isolated HA lab · Runtime pending**

## 1. Environment and stop conditions

Provision at least two disposable PostgreSQL 18 nodes, a tested HA manager with quorum-backed leader selection and a lab-only writer endpoint. Use independent storage and a dedicated application test database. The lab **must not** touch production endpoints, PGDATA, DCS or cloud fencing controls.

**STOP if:** old-primary fencing is not proven, the leader identity is ambiguous, the standby is behind beyond the approved RPO, or two nodes are writable.

## 2. Preflight

Run [070-ha-preflight.sql](../labs/sql/070-ha-preflight.sql) against both nodes, labeling each result with node identity. Capture HA manager leader state, DCS quorum, replication LSNs, timeline, backup health, WAL archiving, replication slots, writer routing, and client sessions.

Create a lab-only database and a marker table on the current primary:

```sql
CREATE TABLE IF NOT EXISTS public.ch070_marker (
  id text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO public.ch070_marker(id) VALUES ('before-switchover')
ON CONFLICT DO NOTHING;
```

Verify marker replication to standby before proceeding.

## 3. Planned switchover

1. Announce lab maintenance and pause application writes/background jobs.
2. Confirm no active write transactions and that standby replay has caught up to the agreed primary LSN.
3. Invoke the HA manager's **documented switchover API**, not an ad-hoc promotion. Record its exact command for the installed HA manager.
4. Prove the old primary is demoted/fenced before enabling writes on the new primary.
5. Verify exactly one node returns `pg_is_in_recovery()=false`; the other is stopped or in recovery.
6. Confirm writer endpoint resolves to the new primary and a new marker is committed.
7. Verify the former primary rejoined as a standby and catches up.

## 4. Unplanned failover simulation

1. Start from a healthy two-node lab and verify backups.
2. Simulate primary failure through the HA manager's supported **lab-only** failure injection.
3. Verify the fencing mechanism's result from an independent control plane.
4. Wait for orchestrated promotion of the eligible standby; record decision time and new timeline.
5. Validate writer routing, test marker and transaction idempotency; record RPO/RTO.
6. Restore the old node **only after fencing and reconciliation**. Use pg_rewind or fresh base backup as required by the documented HA workflow.

**If no quorum/fencing implementation is available:** perform a tabletop exercise only, mark failover/fencing NOT VERIFIED, and do not claim runtime acceptance.

## 5. Split-brain prevention exercise

Simulate a network partition only in an isolated lab that supports fencing. Confirm the minority/old leader cannot accept writes and that quorum elects at most one writable leader. Never simulate a partition in production to test fencing.

## 6. Rollback and rejoin

Restore lab writer routing, confirm old/new roles, WAL archiving, replication slots and standby catch-up. Test a new transaction through the application endpoint. Document whether pg_rewind prerequisites are met; do not execute pg_rewind on a running primary.

## 7. Acceptance

Complete [070-ha-failover-scorecard.csv](../labs/acceptance/070-ha-failover-scorecard.csv). Mandatory gates include old-primary fencing, single writer, healthy promotion, application endpoint switch, commit reconciliation, measured RPO/RTO, rejoin and backup continuity.

**Runtime:** pending.
