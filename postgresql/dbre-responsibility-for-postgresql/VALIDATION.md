# PostgreSQL DBRE Responsibility — Validation & Certification Register

**Status:** Seven documentation milestones drafted and published; V01 static structural audit PASSED — **NOT CERTIFIED FOR PRODUCTION**  
**Last documentation update:** 2026-10-31  
**Owner:** PostgreSQL DBRE  
**Scope:** Self-managed PostgreSQL, AWS RDS/Aurora PostgreSQL, Azure Flexible Server and Google Cloud SQL

GitHub publication and Markdown structure validation are not proof that SQL functions, privileges, managed provider capabilities, staging exercises or recovery objectives have passed.

## Milestone tracking

| Milestone | Documentation | Staging/runtime evidence | Stakeholder approval |
|---|---|---|---|
| 01 Ownership and RACI | Drafted | Cluster/provider/owner register pending | Pending |
| 02 Daily/weekly/monthly operations | Drafted | Role-based read-only SQL and cadence pilot pending | Pending |
| 03 Monitoring, alerts and SLO | Drafted | Exporter labels, Prometheus, APP instrumentation and routing pending | Pending |
| 04 Incident runbooks | Drafted | All 13 scenario assessments, prioritized staged exercises pending | Pending |
| 05 Capacity and FinOps | Drafted | Growth history, IO/CPU baseline, forecasts and bill reconciliation pending | Pending |
| 06 Backup, HA and DR | Drafted | Base/WAL or cloud PITR restore, independent fencing and failover tests pending | Pending |
| 07 Data lifecycle / maintenance | Drafted | Read-only discovery, owner controls and 15 safety tests pending | Pending |

## Workstreams

| ID | Workstream | Evidence requirement | State |
|---|---|---|---|
| V01 | Structure and source links | 9 files, 28 fences, 13 local links, headings and table columns checked | **PASS (static only)** — [V01 report](qa/V01-structure-link-safety-audit.md) |
| V02 | SQL and version compatibility | [V02 catalog/version/provider review](qa/V02-sql-version-provider-compatibility.md), 3 guide corrections | **Static review completed; staging execution PENDING** |
| V03 | Monitoring and security | [V03 source/metric/security report](qa/V03-monitoring-alerting-security-review.md) and [sample alerts](qa/V03-prometheus-alerts.example.yml) | **Source review complete; live validation pending** |
| V04 | Incident and vacuum/replication | [V04 source review](qa/V04-incident-runtime-safety-review.md), [read-only staging pack](qa/V04-readonly-staging-triage.sql) and mitigation gates | **Static review complete; staging tests PENDING** |
| V05 | Capacity/growth/FinOps | [V05 review incl. offline synthetic tests](qa/V05-capacity-growth-finops-review.md), [read-only SQL](qa/V05-readonly-capacity-inventory.sql), [offline model](qa/V05-capacity-forecast.py) | **Static QA and local synthetic Python tests PASS; real telemetry/billing PENDING** |
| V06 | Backup/PITR/HA/DR | Timed isolated restore, fencing, one writer, failback and RPO/RTO | Pending |

## Document QA evidence

- [x] V01 static structure, internal links, code fences, tables and limited destructive command pattern audit — [report](qa/V01-structure-link-safety-audit.md).
- [ ] External documentation links (37) checked for reachability/version relevance.
- [ ] V02 SQL/API syntax, privileges, engine versions and managed provider restrictions independently validated.
- [x] V03 exporter source/role/alert design review and sample rules published.
- [ ] V03 live series, monitoring role, promtool rules, on-call routing and Security approval pending.
- [x] V04 incident runbook source audit covers 13 scenarios, connection reserve, blocking, WAL/slots, replica lag, XID/MXID age and mitigation gates.
- [ ] V04 isolated staging exercises V04-T01–T13, evidence collection and DBRE/APP/DATA peer review pending.
- [x] V05 source-reviewed capacity model: no table/index/TOAST double counts, physical used/free separation, WAL counter reset awareness and provider-specific monitoring.
- [x] V05 locally executed offline forecast: Python compilation, built-in synthetic self-test, CSV acceptance and negative-data rejection PASS (Git blob SHA verified).
- [ ] V05 staging capacity SQL, physical-disk time series, peak forecasts and FIN invoice reconciliation pending.
- [ ] V06 real environment, staging and business recovery acceptance pending.

## Technical validation checklist

- [ ] Inventory every production primary/standby provider, major/minor version, extension list and service owner.
- [x] V02 source-based review documented for 20 SQL blocks; corrected index-view columns, UTC time label and database-scoped vacuum OID. [Details](qa/V02-sql-version-provider-compatibility.md).
- [ ] Execute all SQL and verify function/view columns across supported deployed PostgreSQL versions and managed-provider monitoring roles.
- [ ] Validate psql monitoring session and read-only privileges; do not use SUPERUSER unnecessarily.
- [ ] Confirm pg_stat_statements presence, correct preload/extension and queryid behavior where used.
- [ ] Check version-gated pg_stat_io (PG16+), pg_stat_checkpointer (PG17+) and any other feature differences.
- [ ] Verify PgBouncer/connection pool, APP p95/p99 and DB synthetic availability SLIs.
- [ ] Verify actual postgres_exporter metric names/labels, target disappearance, counter reset and no-data behavior.
- [ ] Monitor replication lag, slots/retained WAL, archive failures, restore point and disk headroom.
- [ ] Test XID and multixact freeze warning and emergency response with SAFE staging/tabletop scenario; do not manufacture critical wraparound on production.
- [ ] Validate locks/deadlocks and session cancellation/termination decision gates.
- [ ] Collect primary/replica or Aurora shared-volume physical metrics separately from logical database/table/index bytes; prevent table/index/TOAST double counting and validate WAL/backup storage.
- [ ] Persist daily measurements for weekly/monthly/quarterly/semiannual/yearly growth reports.
- [ ] Test 30/60/90-day forecasts, peak load and recovery capacity before instance right-sizing.
- [ ] Verify self-managed physical backup, WAL archive chain, pg_verifybackup and an isolated PITR restore.
- [ ] Verify cloud PITR creates expected new instance/server and restore-related HA/network/credential limitations.
- [ ] Perform controlled promotion/fencing/single-writer, app endpoint and pg_rewind/rebuild tabletop/staging test.
- [ ] Validate DATA/APP reconciliation and measured RPO/RTO under agreed service objectives.
- [ ] Test read-only unused-object detection with required owner/retention/telemetry and no DDL privilege.
- [ ] Run 15 data lifecycle safety cases; check OID re-creation, constraints, dependencies, holds and slots.
- [ ] Verify no unsafe delete/WAL file removal/disable fsync or failover commands are executable through guide examples.
- [ ] Review PHI, SQL text, credentials, privacy controls, audit and least-privilege DB access with SEC.
- [ ] Collect DBRE, APP, DATA, PLT, SEC, FIN and SM sign-off and publish approved evidence.

## Evidence register

| Validation item | Instance/provider/version | Date UTC | Owner | Evidence URL | Outcome |
|---|---|---|---|---|---|
| SQL and extension compatibility | TBD | TBD | TBD | TBD | Pending |
| Monitoring/exporter and APP SLO | TBD | TBD | TBD | TBD | Pending |
| Blocking, autovacuum, WAL and slot exercise | TBD | TBD | TBD | [V04 static report](qa/V04-incident-runtime-safety-review.md) | **Staging exercise pending** |
| Capacity and bill review | TBD | TBD | TBD | [V05 static report](qa/V05-capacity-growth-finops-review.md) | **Staging metrics and billing pending** |
| Isolated backup/PITR restore | TBD | TBD | TBD | TBD | Pending |
| Independent fencing / HA drill | TBD | TBD | TBD | TBD | Pending |
| Lifecycle safety tests | TBD | TBD | TBD | TBD | Pending |
| Stakeholder sign-offs | TBD | TBD | TBD | TBD | Pending |

## Certification rule

All production high-risk procedures need version/provider-specific evidence, independent change approval, demonstrated stop/rollback and application/data correctness checks. A successful GitHub commit is **not** certification, and these guides do not authorize destructive maintenance or incident failover.
