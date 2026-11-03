# Chapter 20 — Enterprise PostgreSQL DBRE/SRE Capstone

**Status:** Authored; runtime not executed; independent review pending. **Audience:** DBRE/SRE and application engineers. **Duration:** 60 minutes.

## Prerequisites and assumptions
Complete Chapters 01–19. Use Docker Desktop or Docker Engine, PostgreSQL **17** official image, 2 GB free RAM, and a terminal with Docker CLI. Commands use POSIX shell; Windows users can run them in Git Bash/WSL. The exercise uses synthetic data, an isolated container and no cloud account. Confirm Docker is running before starting. Do not use production credentials, workloads, or volumes.

## Learning outcomes
Design and defend a PostgreSQL service against application, security, reliability, observability, capacity, and governance requirements; collect reproducible evidence; distinguish design review from actual recovery/failover certification.

## 60-minute teaching plan
| Minutes | Activity |
|---|---|
| 0–10 | Requirements, architecture and ownership |
| 10–20 | Security, data model, transactions and indexing |
| 20–35 | Execute local lab, inspect configuration and workload |
| 35–45 | Observe query plan, capacity and operational signals |
| 45–55 | DR/HA tabletop, risk register, RPO/RTO and change plan |
| 55–60 | Evidence checklist and peer-review handoff |

## Scenario and architecture
A fictional appointment service needs 99.9% monthly availability, a **proposed** RPO of 15 minutes and RTO of 60 minutes (targets for review, not demonstrated results), peak 100 requests/second, 30-day operational logs and defined retention/privacy rules. The architecture is application → connection pool → PostgreSQL primary → optional standby; monitoring/exporter and backups are separate trust and failure domains. A single Docker container in this lab demonstrates SQL and operational inspection **only**: it cannot validate HA, restore success, or SLO compliance.

**Decision record:** Compare self-managed PostgreSQL, RDS PostgreSQL and Kubernetes operator deployments by ownership, recovery capability, team maturity, operational cost, secrets and maintenance windows. No provider resources are provisioned. For AWS/Kubernetes exercises, use a separately approved sandbox and estimate cost before provisioning.

## Fundamentals and governance
- ACID transactions protect appointment consistency; MVCC enables concurrent readers, but long transactions may retain dead tuples.
- Primary keys, foreign keys and check constraints protect data integrity; indexes improve targeted reads at a write/storage cost.
- WAL supports crash recovery and replication, but replication alone is not a backup. Recovery objectives require timed, independently reviewed restore evidence.
- Separate application roles, use least privilege and SCRAM/TLS in actual deployments. The lab uses local container trust boundaries and no externally exposed port.
- Assign an application owner, database owner, security reviewer and incident commander; capture on-call routing and approved change/rollback criteria.

## Hands-on exercise
Follow [Chapter 20 lab](../labs/chapter-20/README.md) for copy/paste commands and expected observations. Collect server version, configuration, table constraints, transaction result, EXPLAIN plan, database size, session statistics, and a written design decision.

## Capstone deliverables
1. Workload and data-classification sheet with owner and retention.
2. Architecture decision record with platform responsibility matrix and failure domains.
3. Security matrix: identities, permissions, TLS/secrets, audit and access review.
4. Capacity model: baseline size, projected growth, headroom and cost assumptions.
5. SLO and alert proposal: availability, p95 latency, connection utilization, replication lag and disk headroom.
6. Recovery plan: backup inventory, isolated restore rehearsal, measured RPO/RTO and fencing/single-writer evidence **to be performed separately**.
7. Risk register and change plan with approvals, rollback triggers and evidence links.

## Acceptance rubric (100 points)
| Area | Points | Required evidence |
|---|---:|---|
| Requirements and design | 20 | workload, ADR, RACI |
| SQL/data correctness | 20 | constraints, transaction and plan |
| Security | 15 | least privilege and secret controls documented |
| Observability/capacity | 15 | baseline measurements and alert rationale |
| HA/DR safety | 20 | proposed procedure, explicit untested status, review gates |
| Operations and communication | 10 | incident/change/rollback checklist |

**Pass for educational completion:** 80+ with no unsafe production commands and no unsupported claims of recovery or certification. Independent reviewer must record reviewer, date, findings and disposition. Runtime execution is tracked separately.

## Guardrails, rollback and troubleshooting
All SQL writes are confined to a named lab schema in a disposable container. No failover, promotion, restore, network exposure, role escalation or production configuration changes. Rollback means dropping the lab container/volume after confirming its name; see lab cleanup. If Docker fails, inspect `docker info`; if SQL fails, check `docker logs pg-dbre-capstone20` and the expected database. A failed exercise is evidence of a failed exercise, not proof of PostgreSQL product failure.

## Official references
- [PostgreSQL 17 documentation](https://www.postgresql.org/docs/17/)
- [Transactions](https://www.postgresql.org/docs/17/tutorial-transactions.html)
- [Indexes and EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)
- [Monitoring statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [Backup and restore](https://www.postgresql.org/docs/17/backup.html)
- [High availability](https://www.postgresql.org/docs/17/high-availability.html)
- [Client authentication](https://www.postgresql.org/docs/17/client-authentication.html)
- [Amazon RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
