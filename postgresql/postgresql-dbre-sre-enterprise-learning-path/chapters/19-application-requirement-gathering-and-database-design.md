# Chapter 19 — Application Requirement Gathering and Database Design

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Audience:** application engineers, DBRE/SRE, architects, security and product owners  
**Duration:** 60 minutes | **Status:** authored, not runtime-validated or independently reviewed

## Outcomes and prerequisites

Learners can translate stakeholder statements into measurable database requirements, produce a logical/physical design, evaluate transaction boundaries and indexes, and write an architecture decision record (ADR) with operational acceptance gates. Prerequisites: Chapters 02–05, 09–12, 16 and 18; basic SQL and Docker CLI. Lab assumes PostgreSQL **17** official container image, Docker Engine/Desktop with Linux containers, ~1 GiB free RAM and no cloud account. SQL uses standard PostgreSQL 17 features; test on other versions before use.

## 60-minute teaching outline

| Time | Activity |
|---|---|
| 0–10 min | Interview stakeholders and separate facts, assumptions and unknowns |
| 10–20 min | Define workload, data classification, retention, SLO, RPO/RTO and ownership |
| 20–30 min | Logical model, keys, normalization, transactions and lifecycle |
| 30–40 min | Physical schema, access patterns, indexing and migration planning |
| 40–55 min | Execute the isolated design lab and inspect evidence |
| 55–60 min | Review ADR, risk register and acceptance checklist |

## 1. Requirements discovery

Interview the application owner, product owner, privacy/security, analytics, platform and on-call DBRE. Record **source, decision owner, date, confidence and acceptance test** for each requirement.

| Category | Questions | Evidence / output |
|---|---|---|
| Business | What user journeys must work? Which are critical? | Top three journeys, owner, priority |
| Access patterns | Point lookup, filtered search, joins, batch, reporting? | Sample SQL, expected rows, query frequency |
| Volume | Initial rows, bytes/row, peak writes, 12–24 month growth? | Sizing assumptions and uncertainty |
| Latency | p95/p99 response budgets, concurrency and burst? | Application SLO, measured baseline plan |
| Consistency | Can reads lag? Which writes must be atomic? | Transaction invariants, stale-read tolerance |
| Availability | Outage budget, maintenance, regions? | SLO, failover dependencies |
| Recovery | Maximum tolerable data loss and restoration time? | Approved RPO and RTO, recovery test plan |
| Security | PII/PHI, tenant isolation, audit and encryption? | Data classification and controls owner |
| Lifecycle | Updates to old records, retention, legal holds, erasure? | Deletion/archive rules, exceptions |
| Operations | Who patches, backs up, monitors, pages, pays? | RACI and escalation paths |

**Do not choose PostgreSQL merely because the data is relational.** Validate transaction semantics, access paths, data sovereignty, write amplification, scale limits and operational fit against alternatives. Keep OLTP source-of-truth data separate from search/reporting projections where appropriate.

### Example workload contract (fictional appointment system)

- Create patient records and appointments; a patient can have many appointments.
- Prevent duplicate external patient IDs; every appointment references an existing patient.
- Patient lookup by external ID; upcoming appointments by patient and scheduled time.
- Appointment status changes are transactional; no cross-system distributed transaction is assumed.
- Sample design targets for **discussion only**: 100 requests/second peak, p95 database query under 50 ms, 99.9% service availability, RPO 15 minutes, RTO 60 minutes. These are *not approved or tested SLOs*.
- Treat patient-like data as sensitive; lab uses invented identifiers only. No real PHI or customer data.

## 2. Architecture and design

~~~
Application/API → connection pool → PostgreSQL primary → WAL/backup archive
                                      ↘ optional standby for HA/read scaling
                                      ↘ CDC/ETL → analytical/search store
~~~

A connection pool limits backend connection churn; it does not create capacity. Replication improves availability only with tested promotion, fencing and client routing. A backup is not a recovery guarantee until restore/PITR is measured.

**Logical model:** Patient (1) → Appointment (many). Stable surrogate primary keys simplify joins; unique business keys prevent duplicates. Use NOT NULL, CHECK, FOREIGN KEY and UNIQUE constraints as close to data as possible. Use UTC-aware `timestamptz` for instants. Define ownership for schema changes and sensitive fields.

**Physical design:** Begin with B-tree indexes for equality/range predicates; avoid speculative indexing, which increases write and storage cost. Test query plans with `EXPLAIN (ANALYZE, BUFFERS)` only on disposable data or approved read-only workloads: ANALYZE executes statements. Consider partial indexes for sparse status filters after collecting actual distributions. Plan migration compatibility, backfill, feature flags and rollback before changing live schemas.

**Privacy:** This teaching schema intentionally excludes clinical notes, names and DOB. In production, agree classification, access controls, encryption, logging redaction, retention and lawful deletion with security/compliance owners. Row-level security, if used, needs explicit policy tests and bypass-role review; tenant separation is not automatically assured by a tenant_id column.

## 3. Runnable lab

Follow [Chapter 19 lab](../labs/chapter-19/README.md). It creates disposable tables, loads synthetic data, checks referential integrity, and compares a filtered query plan before/after a targeted index. Collect `SELECT version()`, row counts, constraint errors, plan output and the completed ADR. No runtime execution is claimed in this document.

## 4. ADR template and decision gates

**ADR-019:** context and stakeholders; options (PostgreSQL OLTP, alternate store, split OLTP/analytics); workload assumptions; selected architecture and rejected alternatives; transaction and consistency invariants; privacy classification; SLO/RPO/RTO approvals; backup/restore test; HA and failover fencing; schema ownership; migration/rollback; capacity and cost; open risks; sign-offs.

| Gate | Required evidence |
|---|---|
| Functional | Constraints, read/write paths and negative tests demonstrated |
| Performance | Representative volume, query plans, p95/p99 and load-test method |
| Reliability | Approved RPO/RTO and *measured* restore/failover rehearsal |
| Security | Threat review, privileges, retention, logging and classification |
| Operations | Monitoring, alerts, on-call, runbooks, owner and change procedure |

## 5. Guardrails, rollback and troubleshooting

Use disposable local containers and fake data only. Never apply this schema, migrations or cleanup to shared databases. If constraints fail, inspect foreign-key parent existence and unique external IDs. If plans use sequential scans, inspect table size and selectivity before assuming an index is needed; small tables often prefer scans. If Docker cannot start, check daemon, port collision and memory. If transactions fail, inspect SQLSTATE and rollback explicitly. For lab cleanup, remove only the uniquely named Chapter 19 container and its anonymous data volume as documented in the lab. For a production schema migration, rollback may require a forward-fix and data reconciliation rather than DROP TABLE.

## Acceptance checklist

- [ ] Stakeholder requirements and unknowns captured with owners
- [ ] Workload, consistency, privacy and lifecycle decisions documented
- [ ] Schema constraints and query patterns explained
- [ ] Local lab evidence recorded, or explicitly marked not executed
- [ ] ADR includes options, SLO/RPO/RTO, operations and approval gaps
- [ ] Cleanup scoped to isolated lab resources
- [ ] Independent reviewer identified (not yet completed)

## Official references

- [PostgreSQL 18 — Data Definition](https://www.postgresql.org/docs/18/ddl.html)
- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Indexes](https://www.postgresql.org/docs/18/indexes.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 — Backup and Restore](https://www.postgresql.org/docs/18/backup.html)
- [PostgreSQL 18 — Client Authentication](https://www.postgresql.org/docs/18/client-authentication.html)
