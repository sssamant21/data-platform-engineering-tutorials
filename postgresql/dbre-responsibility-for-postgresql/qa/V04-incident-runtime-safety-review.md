# PostgreSQL DBRE V04 — Incident & Runtime Safety Source Review

**Date:** 2026-11-01 UTC
**Status:** STATIC SOURCE REVIEW COMPLETE; STAGING / PRODUCTION RUNTIME VALIDATION PENDING
**Owner:** PostgreSQL DBRE
**Reviewed scope:** PostgreSQL DBRE Page 04 PG-INC-001–013; companion monitoring, operations and HA/DR guides; PostgreSQL 14–18 official catalog/runtime semantics.

## 1. Summary and assurance

The source review identified **five operational safety gaps and one observability enhancement** in the existing incident runbook. The guide has been updated with exact read-only SQL and independently authorized mitigation gates.

This milestone does NOT execute load testing, hold locks, fill WAL, advance transaction IDs, change configuration, cancel/terminate sessions, modify replication slots, perform failover, or validate database RPO/RTO. No staging/production PostgreSQL connection or provider metrics were available. **Static review is not production certification.**

## 2. Findings and corrections

| ID | Severity | Finding | Correction |
|---|---|---|---|
| V04-F01 | Medium | Connection triage grouped pg_stat_activity without isolating client backends and omitted PG16+ reserved_connections. | Filter backend_type=client backend; add reserved_connections-if-supported alongside max_connections and superuser reserve; clarify real headroom includes more consumers. |
| V04-F02 | High | Replication slot inspection showed LSN distance without wal_status, safe_wal_size, xmin or catalog_xmin. | Add state, remaining WAL budget and tuple-retention horizon; clarify NULL safe_wal_size semantics and lost/unreserved hazards. |
| V04-F03 | High | Wraparound SQL covered XID but not multixact age. | Add mxid_age(datminmxid) and mxid_age(relminmxid), and include TOAST relation inspection. |
| V04-F04 | High | Blocking mitigation text did not insist on fresh PID/transaction identity or prevent inadvertent targeting of anti-wraparound processes. | Add APP/business confirmation, PID-reuse caution, independent approval and no termination snippets. |
| V04-F05 | High | Runbook listed hazardous actions but lacked uniform stop/no-go matrix for slot, vacuum, failover, storage, and backend changes. | Add seven-line fail-closed mitigation decision table and restricted emergency authorization. |
| V04-E01 | Medium | Vacuum guidance did not connect feedback/slot catalog_xmin to potential cleanup obstruction or distinguish emergency anti-wraparound behavior. | Add long snapshot/slot xmin, worker, IO, lock and forced-vacuum safety notes. |

**Review limitation:** SQL and functions were compared with official documentation, not executed against all targeted PostgreSQL majors/providers.

## 3. Incident coverage / staging test plan

| Test ID | Runbook | Isolated staging experiment or tabletop | Gate / evidence |
|---|---|---|---|
| V04-T01 | PG-INC-001 | Synthetic database-unavailable signal, provider endpoint false-positive test | Confirm role/region, application probe, on-call route; no blind promotion |
| V04-T02 | PG-INC-002 | Bounded simulated connection pool saturation, preserve administrative reserve | Pool/rejection metrics, client-only count, PG16+ reserved pool, APP SLO |
| V04-T03 | PG-INC-003 | Representative slow query and plan regression without unsafe EXPLAIN ANALYZE on production | Query class, wait, IO, APP p95/p99, owner and tested rollback |
| V04-T04 | PG-INC-004 | Controlled locks/deadlock with disposable test tables and reviewed transaction owner | Blocker identification, cancel/terminate decision **tabletop**; no uncontrolled backend kill |
| V04-T05 | PG-INC-005 | Replica behind primary / standby replay pause with explicit staging authority | Distinguish receive/replay LSN, NULL lag, idle last-replay timestamp |
| V04-T06 | PG-INC-006 | Synthetic slot backpressure design/tabletop; no WAL exhaustion on a shared environment | wal_status, safe_wal_size, slot consumer, xmin/catalog_xmin and free disk |
| V04-T07 | PG-INC-007 | Archiver storage/network failure drill in isolated self-managed test only | Alert vs proven PITR chain and provider differences |
| V04-T08 | PG-INC-008 | Heavy DML/vacuum pressure on throwaway table at bounded workload | Dead tuples estimate, progress, long snapshots, IO and app impact |
| V04-T09 | PG-INC-009 | Low-risk threshold simulation / query-based XID and multixact age assessment | No dangerous wraparound acceleration; incident/tabletop escalation |
| V04-T10 | PG-INC-010 | Injected simulated low-space monitoring alert, **no full disk** | Physical disk and WAL, cautious mitigation, provider alert route |
| V04-T11 | PG-INC-011 | Restore/PITR failure tabletop, not production restore | Last recoverable point, missing WAL, app acceptance and incident |
| V04-T12 | PG-INC-012 | Fencing/failover design and independent single-writer test rehearsal in isolated topology | Abort on fencing failure; no promotion until authorization; link V06 |
| V04-T13 | PG-INC-013 | Expired test credential/TLS change and migration-lock tabletop | Security review, no bypass of authentication, safe rollback |

**Not executed:** all V04-T01–T13 remain Pending. Negative tests must be constrained to an isolated, approved lab; resource exhaustion and wraparound are represented by synthetic signals or small bounded exercises rather than deliberate production damage.

## 4. Read-only staging diagnostic pack

File: [V04-readonly-staging-triage.sql](V04-readonly-staging-triage.sql).

Includes:
- Identity, actual PostgreSQL version and standby role.
- Count of client backends by state and connection-reserve configuration.
- Current lock waiters and blocker PID mapping.
- Long transactions and deadlock counter reset.
- Primary-style replication sender view, slot state and archive counters.
- Vacuum progress (database-local relation OID) and XID/MXID ages.

The pack uses a READ ONLY transaction and local 5-second statement timeout. It includes **no cancellation, terminate, CREATE/DROP, VACUUM, promotion or replication-slot mutation**. Even read-only monitoring requires approved credentials and can consume resources. For a production incident with exhausted connections, rely on approved provider and Prometheus metrics first.

### Proposed execution process — not executed

1. Select an isolated PostgreSQL 14–18 staging deployment whose owner has granted testing.
2. Provide an approved role with least-privilege stats visibility; no superuser or mutation permissions.
3. Check target identity with a separate safe connection; schedule during a bounded maintenance window.
4. Run only the read-only pack, with psql -X -v ON_ERROR_STOP=1 and statement timeout; capture sanitized results.
5. Confirm source views return expected columns and role-specific visibility; log permission denials rather than escalating privileges without approval.
6. Record PG version, role, primary/replica, provider, UTC time, success/fail for each statement, and estimated load.
7. Compare results against exporter/app/provider telemetry; do not equate query output with independent recovery proof.
8. Submit DBRE and APP/DATA peer review of mitigation stop gates, then file results in VALIDATION.md.

## 5. Primary/standby and cloud provider distinctions

| Platform | What SQL can show | What additional evidence is required |
|---|---|---|
| Self-managed PostgreSQL | Client sessions, lock waiters, WAL slots and XID/MXID ages, archiver counters | Host disk, WAL directory, HA orchestrator, independent fencing, base backups |
| AWS RDS PostgreSQL | Supported catalog/replication views under restricted admin | CloudWatch, RDS events, latest restorable time, Multi-AZ state, provider support |
| Amazon Aurora PostgreSQL | Compatible SQL, Aurora-specific role/replication semantics | Writer/reader endpoints, cluster storage/lag, engine-specific standby behavior |
| Azure Flexible Server | Catalog stats where privilege permits | Azure Monitor, server HA, control-plane backup and storage |
| Cloud SQL PostgreSQL | Catalog stats where privilege permits | Cloud Monitoring, HA/PITR control-plane status and restricted privileges |

**Important:** No single SQL pack can certify managed-provider backup, disk, failover or split-brain safety. Check each actual release, role and provider engine behavior.

## 6. Operational safety gates (must not be bypassed)

- Do not cancel/terminate sessions based on stale PIDs or uncertain APP transaction correctness.
- Do not drop replication slots to reclaim WAL without downstream DATA/APP owners and rebuild/sync plan.
- Do not disable WAL archiving, fsync or autovacuum to relieve pressure.
- Do not run VACUUM FULL in anti-wraparound emergency; obtain qualified peer review for targeted safer recovery.
- Do not promote a standby or repoint application endpoints without **independently verified primary fencing and single-writer acceptance**.
- Do not assume idle replay_lag or last_xact_replay_timestamp is direct RPO evidence.
- Do not treat a successful physical base backup as proven PITR without WAL continuity and restore exercises.
- Do not remove locks, slots, jobs, WAL files, security or retention without formal incident/change authority.

## 7. Evidence register template

| Field | Value |
|---|---|
| Test ID / incident case / ticket | |
| DB provider / cluster / region / node role | |
| PostgreSQL major/minor version / settings | |
| Monitoring role/permissions | |
| APP/Data Owner/DBRE reviewer | |
| UTC test time and rollback/stop scope | |
| Collected SQL and exporter/cloud signal IDs | |
| Expected outcome / actual outcome | |
| Data loss or application risk | |
| PASS/FAIL / blocked / remediation ticket | |
| Links to sanitized evidence and approvals | |

## 8. V04 acceptance status

- [x] Source review of PG-INC-001–013 completed.
- [x] Connection, replication slot, autovacuum, XID/MXID and mitigation decision gaps documented.
- [x] Read-only staging SQL and guardrail matrix added.
- [ ] Exact SQL pack run under intended monitoring role/engine versions in staging.
- [ ] V04-T01–T13 scenarios exercised and sanitized evidence retained.
- [ ] Provider-specific cloud behavior and APP/pooler integration independently verified.
- [ ] DBRE/APP/DATA/PLT/SEC peer reviews obtained.
- [ ] Incident recovery and performance SLO checks validated end to end.

**V04 disposition:** STATIC DOCUMENTATION/SOURCE REVIEW COMPLETE; STAGING VALIDATION AND APPROVAL PENDING.

## 9. Source references

- [PostgreSQL 18 Monitoring Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 14 Slot Metadata](https://www.postgresql.org/docs/14/view-pg-replication-slots.html)
- [PostgreSQL 18 Replication Slots](https://www.postgresql.org/docs/18/view-pg-replication-slots.html)
- [PostgreSQL 16 Connection Reserves](https://www.postgresql.org/docs/16/runtime-config-connection.html)
- [PostgreSQL 18 Vacuum/Anti-Wraparound](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [PostgreSQL 18 Vacuum Freeze Configuration](https://www.postgresql.org/docs/18/runtime-config-vacuum.html)
