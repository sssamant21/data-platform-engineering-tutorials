# Page 07 — PostgreSQL Data Lifecycle & Safe Maintenance Automation

**Document ID:** PG-DBRE-OPS-007 | **Owner:** PostgreSQL DBRE + Business Data Owner  
**Status:** DRAFT — NO DESTRUCTIVE AUTOMATION AUTHORIZED  
**Scope:** Tables, partitions, indexes, schemas, databases, replication slots and routine maintenance

> **Safety:** An idle or empty table/index/partition, or an inactive replication slot, is merely a **candidate** for investigation. No automated DROP, DELETE, TRUNCATE, detach partition, schema/database removal or slot deletion may run without approved scope, data retention, recovery safeguards and independent authorization.

## 1. Lifecycle modes

**A — Business-approved retention:** DATA defines required retention/hold rules and approved disposition; DBRE implements tested partition lifecycle or other exact-scoped automation. Retention expiry is a business authorization contract, not a query-statistics inference.

**B — Weekly read-only candidate discovery:** DBRE collects metadata/usage and produces tickets; DATA and APP assess whether business records and downstream workloads still need the object.

**C — Routine non-destructive maintenance:** PostgreSQL VACUUM/ANALYZE, index health, planner statistics, autovacuum, bloat, freeze ages and partition health require safe operational procedures; disruptive rewrites need formal change approval.

## 2. Ownership and change authority

| Activity | Accountable | Responsible/consulted |
|---|---|---|
| Business retention, legal hold and data class | DATA | DATA, SEC, APP |
| PostgreSQL technical maintenance and discovery | DBRE | DBRE |
| SQL/index dependency review | APP | APP, DBRE |
| Retention/recovery risk assessment | DATA | DATA, SEC, DBRE |
| Exact-object data deletion permission | DATA | DATA, APP, SEC |
| Formal production change authorization | SM | DBRE, APP, DATA |
| Technical executor and audit | DBRE | DBRE |
| Post-change correctness and APP functionality | APP/DATA | APP, DATA, DBRE |

One person should not independently request, approve and execute irreversible retirement.

## 3. Ownership/retention register

| Field | Required |
|---|---|
| Provider/cluster/database/schema | Exact environment |
| Object type/name/OID and owner | Tables, indexes, materialized views, partitions, slots |
| APP/DATA owner and source of truth | Names, backup contacts |
| Retention and legal/PHI classifications | Approved expiry and holds |
| Readers and writers | APP SQL, ORM, BI, functions, scheduled jobs |
| Replication, CDC, logical slots | Consumer and rebootstrap plan |
| FK, unique/PK constraints, triggers/views | Structural dependencies |
| Backup/PITR and last restore evidence | Recoverability gate |
| Observed activity, telemetry gaps and stats_reset | Data provenance |
| Size, benefit and candidate status | Evidence, not deletion authority |
| Approval ticket, exact object, expiry and reviewer | Independent record |

Unknown owner/retention, incomplete usage history, active migration/replay or no viable restore path = **HOLD**.

## 4. Heuristics are not deletion criteria

| Signal | Possible interpretation | Cannot prove |
|---|---|---|
| Zero live rows | May be empty | Never used in future load, migration or reconciliation |
| idx_scan=0 | No index scans counted since stats reset | Index does not enforce PK/UNIQUE or serve rare queries |
| No recent writes | Apparently quiet | Annual report, monthly batch or delayed ingestion irrelevant |
| Table older than period | Old data | Legally disposable or past hold expiry |
| Partition older than date | Candidate | Late arriving events, FK, legal hold or replay |
| WAL slot inactive | Current consumer disconnected | CDC/DR consumer can be dropped without loss |
| Large apparent bloat | Resource inefficiency | VACUUM FULL is safe or needed |
| No observed app reads | May be unused | View/function or externally scheduled consumer absent |

Historical pg_stat_* counters can reset after unclean restart/manual reset and reflect only visible collection windows. They do not provide a complete access audit. Indexes may be essential for constraints despite low scans. Prefer APP tracing/audit, query inventories, ETL schedules, business owner attestation and date/retention metadata.

## 5. Read-only inventory SQL (run per database)

~~~~sql
-- Database identities and logical sizes
SELECT oid, datname, pg_database_size(oid) AS database_bytes
FROM pg_database
WHERE datallowconn
ORDER BY database_bytes DESC;

-- Tables, partitions and materialized views with exact OID, size and activity
SELECT c.oid, n.nspname AS schema_name, c.relname, c.relkind,
       pg_total_relation_size(c.oid) AS total_bytes,
       s.n_live_tup, s.n_dead_tup,
       s.last_autovacuum, s.last_autoanalyze
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid=c.oid
WHERE c.relkind IN ('r','p','m')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY total_bytes DESC
LIMIT 100;

-- Index scan usage is only a review signal
SELECT schemaname, relname, indexrelname, relid AS table_oid,
       indexrelid AS index_oid, idx_scan,
       pg_relation_size(indexrelid) AS index_bytes
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC NULLS FIRST
LIMIT 100;

-- Partition parent/child lineage
SELECT inhparent::regclass AS parent, inhrelid::regclass AS child
FROM pg_inherits
ORDER BY parent, child;

-- Replication slot consumer metadata
SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;

SELECT datname, stats_reset FROM pg_stat_database
WHERE datname IS NOT NULL;
~~~~

**Limitations:** relation/database sizes do not represent actual WAL, cloud backup, free disk and filesystem overhead. Partition parent relation storage does not represent all child partitions. Catalog OIDs change when objects are dropped and recreated. Never expose complete SQL text or patient identifiers in cleanup reports.

## 6. Protected and blocked candidates

BLOCK or HOLD if any of the following applies:

1. Table, partition or index has unknown owner, retention or legal hold.
2. Index supports PK/UNIQUE/EXCLUDE constraint or critical access patterns.
3. Source-of-truth table has no verified independent recovery.
4. Table referenced by active APP, views, functions, triggers, reports or jobs.
5. Data is replicated through logical/physical CDC or business recovery workflows.
6. Partition accepts delayed writes or is under migration/backfill/DR.
7. Slot serves any replica/CDC/replay/consumer, even if currently inactive.
8. Candidate relies on missing stats or reset/recent restart observations.
9. Candidate name was recreated with a new OID after approval.
10. Change would cascade through table/schema dependencies or violate SLO.
11. Confirmed current backup, WAL chain, DR protection or owner approval missing.
12. Requested operation would alter security policy or enterprise retention.

**Explicit bans in general cleanup tooling:** DROP CASCADE, TRUNCATE CASCADE, wildcard generated DROP, unapproved slot removal, WAL file deletion and disabling anti-wraparound protection.

## 7. Safe weekly candidate automation

1. Read an allowlist of production clusters/databases and owners.
2. Connect through a restricted read-only monitoring role.
3. Collect object OIDs/schema/type, owners, partition lineage, index constraints and slot metadata.
4. Correlate 30/90/365-day retained telemetry (depending on approved workload), APP traces and scheduled jobs; include coverage and stats_reset flags.
5. Exclude/HOLD unknown owner, legal holds, critical constraints, replication and backup dependencies.
6. Emit candidate reason, size, exact object identity and observation window.
7. Open owner-review ticket to DATA and APP with no SQL execution path.
8. Track approved KEEP/HOLD/retire decisions and expiration timestamps.
9. Publish a weekly report and audit log. Do not mutate production as part of discovery.

### Classification pseudocode — not runnable DB integration

~~~~python
def classify_asset(asset, evidence):
    if evidence.legal_hold or evidence.security_block:
        return "BLOCKED"
    if evidence.app_pipeline_replication_dependency:
        return "BLOCKED"
    if asset.critical_constraint_or_partition:
        return "BLOCKED"
    if not evidence.owner_known or not evidence.retention_defined:
        return "HOLD"
    if not evidence.stats_complete or not evidence.app_review_complete:
        return "HOLD"
    if evidence.possibly_unused:
        return "CANDIDATE_REVIEW"
    return "KEEP_OR_UNKNOWN"

# Read-only report and tickets only; no PostgreSQL DDL.
~~~~

The production collector must adapt to actual catalogs, provider privileges and protected schema boundaries.

## 8. Routine maintenance decision table

| Operation | Potential benefit | Risk/control |
|---|---|---|
| VACUUM / ANALYZE | Reclaim reusable page space and refresh planner stats | I/O, long snapshots, workload impact, normal autovacuum coordination |
| Autovacuum tuning | Better cleanup, freeze and wraparound protection | XID/multixact rate, shared resource load; DBRE peer review |
| CREATE INDEX CONCURRENTLY | APP query improvements | Extra index disk/WAL; long transaction and invalid-index cleanup |
| REINDEX CONCURRENTLY | Rebuild problematic index | Storage, IO, version/provider compatibility and rollback |
| VACUUM FULL / CLUSTER | Physical table rewrite and reclaim disk | ACCESS EXCLUSIVE locking, extra disk, maintenance window |
| Partition lifecycle | Predictable pruning/retention | Late data, FK, locks, need DATA authorization for deletion |
| Drop redundant index | Reduce write/storage cost | APP dependency and constraints, index plan baseline |
| Drop replication slot | Eliminate retained WAL | CDC data loss and resynchronization risk |
| Reduce backup/retention | Lower cost | Legal/DR/RPO/RTO breach, requires DATA/SEC approval |

VACUUM FULL is not normal autovacuum and should not be part of a weekly no-approval job. Treat pg_repack/external extension availability as provider/version-specific and stage-test carefully.

## 9. Data retention and partition retirement process

1. DATA defines minimum/maximum age, exact retention start, legal holds, archive and privacy rules.
2. DBRE identifies exact object OID/schema/partition boundary and current write/read routing.
3. APP validates ORM, scheduled jobs, reports, FKs, materialized views and late-arrival data.
4. DBRE/PLT validates complete backup/PITR and isolated restore for required data.
5. DATA and APP authorize the exact disposition, SEC approves legal/compliance aspects.
6. SM issues a change with explicit object, executors, maintenance window, rollback and abort conditions.
7. DBRE rechecks OID/name, dependencies, active writers and policy holds immediately before the operation.
8. Approved restricted executor performs controlled exact-scope change; discovery job never calls it.
9. APP/DATA validate SQL and business correctness; DBRE monitors WAL, storage and query SLOs.
10. Report actual reclaimed storage, archive availability, incident risk and retained evidence.

A date suffix in a partition name is not legal permission to discard its rows.

## 10. Approval state model

| State | Owner | Gate |
|---|---|---|
| DISCOVERED | DBRE automation | Candidate facts |
| HOLD/BLOCKED | DBRE | Insufficient evidence, dependency or legal protection |
| UNDER_REVIEW | APP/DATA | Data purpose and query needs confirmed |
| KEEP/REJECTED | DATA | Retention or application obligation |
| APPROVED | DATA + APP | Exact object and data disposition signed |
| SECURITY_REVIEW | SEC | Holds, PHI and compliance |
| CHANGE_APPROVED | SM | Independent formal authorization and executor |
| PRECHECK | DBRE | Revalidate OID, scope, backup, holds, writers |
| EXECUTED | Restricted DBRE | Audit record and recovery plan |
| VERIFIED | APP + DATA | APP service, data reconciliation and DBRE health |

Approval expires on an agreed time limit or upon changed OID, scope, owner, retention, app dependencies, backup, or replication status.

## 11. Staging safety test suite

| Test | Scenario | Expected |
|---|---|---|
| T01 | Empty table needed by monthly job | HOLD |
| T02 | idx_scan=0 but UNIQUE index | BLOCK |
| T03 | Stats reset, no historical coverage | HOLD |
| T04 | Table read through view/function | BLOCK |
| T05 | Source-of-truth without restore | BLOCK |
| T06 | Legal-hold partition | BLOCK |
| T07 | Late-arriving historical writes | HOLD |
| T08 | CDC slot inactive but consumer required | BLOCK |
| T09 | DROP CASCADE request | FAIL CLOSED |
| T10 | Object recreated under same name | FAIL CLOSED |
| T11 | Expired/missing business approval | FAIL CLOSED |
| T12 | XID wraparound condition | Prioritize safe recovery; no cleanup |
| T13 | Missing WAL archive/backup chain | BLOCK |
| T14 | Exact approved staging retirement | Audited action, recovery and APP checks |
| T15 | New query plan regression post-change | Stop/rollback, RCA |

## 12. Weekly reporting template

| Field | Entry |
|---|---|
| Week/UTC source and environment | |
| Objects inventoried and owners found | |
| Candidates / HOLD / BLOCKED, reasons | |
| Vacuum/XID/index risks and tickets | |
| CDC/replication slot / WAL dependencies | |
| PITR/recovery evidence and approvals | |
| Approved maintenance changes | |
| Logical/physical savings and APP SLO impact | |
| Next owner, due date and status | |

**Suggested report wording:** Weekly PostgreSQL maintenance has identified possible unused objects for DATA/APP review only. No tables, partitions, indexes, slots or databases were deleted automatically. Unknown ownership, retention, recovery and dependency cases remain on HOLD.

## 13. Acceptance criteria

- [ ] Owners, app dependencies, retention and legal holds registered.
- [ ] 30/90/365-day monitoring coverage and stats reset handling validated.
- [ ] Read-only discovery role cannot execute destructive DDL.
- [ ] PK/UNIQUE, views/jobs, replication, backups and active partitions protected.
- [ ] DATA/APP/SEC/SM approvals separated from execution.
- [ ] Exact OID and object-dependency recheck enforced before change.
- [ ] WAL/PITR recovery route verified for destructive candidates.
- [ ] All 15 negative/positive staging tests passed; fail closed.
- [ ] VACUUM/index/partition operations test lock/IO and APP impact.
- [ ] Post-change service/data/cost review retained and signed.

**Completion:** Staging-tested governance and technical controls with stakeholder sign-off. No destructive production automation is authorized solely by this guide.

## References

- [PostgreSQL catalogs](https://www.postgresql.org/docs/current/catalog-pg-class.html)
- [Monitoring statistics](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [VACUUM and transaction wraparound](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [REINDEX](https://www.postgresql.org/docs/current/sql-reindex.html)

Related repository tutorials: [Vacuum](../chapters/035-vacuum-autovacuum-and-index-cleanup.md) · [Partition lifecycle](../chapters/040-partition-lifecycle-retention-and-recovery-project.md).
