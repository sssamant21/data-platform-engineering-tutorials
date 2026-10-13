# Chapter 075 — High Availability and Disaster Recovery Acceptance Lab

**PostgreSQL 18 · Full HA/DR capstone · Runtime pending**

## 1. Lab safety

Use isolated PostgreSQL 18 nodes across a **simulated or genuine** three-AZ region, a separate DR environment, tested HA manager/DCS quorum, independent fencing, writer endpoint and isolated backup restore target. Do not inject failures, change DNS, or run destructive operations against production. Have an independent incident observer and a STOP/rollback owner.

## 2. Preparation

Record service RPO/RTO, lab boundaries, infrastructure and backup inventory, credentials/keys, fencing design, quorum, replication mode, WAN connectivity, recovery capacity and rollback procedure. Prepare an application transaction ledger with unique request IDs and confirmed outcomes.

Run [075 inspection SQL](../labs/sql/075-ha-dr-acceptance-inspect.sql) on every node; label each result with node, role and UTC time. Collect HA manager leader/term, DCS quorum, fencing, proxy writer backend, backup and WAL archive status separately.

## 3. Test matrix

| Phase | Injection | Evidence |
|---|---|---|
| A | No failure | Baseline app write success, latency, role, LSN and backups |
| B | Standby unavailable | SyncRep waits, WAL retention, write impact and restoration |
| C | Planned switchover | Write drain, old leader fenced, new leader and app success |
| D | Primary crash | Fencing, leader election, RPO/RTO and transaction reconciliation |
| E | AZ / DCS voter loss | Quorum, eligibility, zone resilience |
| E2 | DCS quorum loss / partition | Fail-closed behavior; no dual writer |
| F | Region A outage | Independently fenced source and Region B cutover |
| G | Controlled failback | Rebuild/rewind former leader and approved switchover |
| H | Backup/PITR restore | Independent restore with transaction marker verification |

Only perform partition/DR promotion exercises when independent fencing is implemented and verified. Otherwise use tabletop analysis and record NOT VERIFIED.

## 4. Transaction probe

Create a lab-only table with a unique transaction ID primary key and UTC timestamps. Write through the **application writer endpoint**, not directly to an arbitrary node. Record acknowledgment result, request ID and read-back status. When a COMMIT times out, query the authoritative writer before retrying.

Example fixture (lab-only database):

```sql
CREATE TABLE IF NOT EXISTS public.ch075_probe (
  request_id text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  note text NOT NULL
);
INSERT INTO public.ch075_probe(request_id,note)
VALUES ('baseline-001','before failover')
ON CONFLICT DO NOTHING;
```

## 5. Execution discipline

For each phase: capture preflight; obtain approval; start UTC timer; inject only the named lab failure; capture leader/fencing/DCS evidence; validate application writes; measure RPO/RTO; restore replicas and backup/archive health; record PASS/FAIL/NOT VERIFIED. Do not proceed if a mandatory safety gate fails.

## 6. Failback and cleanup

Keep former primary fenced until timeline-safe rewind/rebuild. Restore it as standby, verify replay catch-up, then perform approved controlled switchover. Return test DNS/proxy to baseline and confirm only one writer. Remove lab fixtures only after evidence is preserved.

## 7. Acceptance and signoff

Complete [scorecard](../labs/acceptance/075-ha-dr-acceptance-scorecard.csv) and [evidence template](../labs/acceptance/075-ha-dr-evidence-template.md). A simulated zone or region does not establish real failure-domain tolerance. Attach raw logs and timestamps, and record owner signoff only after execution.

**Runtime:** pending.
