# PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path

**A separate, role-aligned PostgreSQL learning track** for Database Reliability Engineers, Site Reliability Engineers, Database Engineers, and Platform Engineers.

> Inspired by publicly described responsibilities for an enterprise Postgres Database Team working across bare metal, AWS, and Kubernetes. This is an independent educational project, not Apple internal documentation or an official Apple course.

## What makes this track different?

The existing [PostgreSQL DBRE/SRE curriculum](../README.md) is an extensive 100-chapter operational reference. **This track is a focused 20-chapter onboarding journey** specifically structured around application consulting, multi-platform PostgreSQL architecture, database fleet operations, and reliability ownership. It does not replace or rename the existing curriculum.

- **Audience:** beginner-to-intermediate engineers advancing to enterprise DBRE/SRE responsibilities
- **Format:** 20 guided chapters, approximately 60 minutes each, with practical labs
- **Platforms:** self-managed/bare metal, AWS RDS, and Kubernetes-operated PostgreSQL
- **Deliverables:** safe labs, platform comparisons, design reviews, operational evidence, and a capstone
- **Safety:** labs run only in disposable/non-production environments; production changes require review and approval

## Start here

1. [Master table of contents](MASTER-TOC.md)
2. [Progress and validation tracker](STATUS-TRACKER.md)
3. [Chapter 01 — PostgreSQL Fundamentals and Architecture](chapters/01-postgresql-fundamentals-and-architecture.md)
4. [Chapter 01 lab](labs/chapter-01/README.md)
5. [Chapter 02 — Databases, Schemas, Tables and Relationships](chapters/02-databases-schemas-tables-and-relationships.md)
6. [Chapter 02 lab](labs/chapter-02/README.md)
7. [Chapter 03 — SQL Transactions, ACID and MVCC](chapters/03-sql-transactions-acid-and-mvcc.md)
8. [Chapter 03 lab](labs/chapter-03/README.md)
9. [Chapter 04 — PostgreSQL Internals: WAL, Buffers and Checkpoints](chapters/04-postgresql-internals-wal-buffers-and-checkpoints.md)
10. [Chapter 04 lab](labs/chapter-04/README.md)
11. [Chapter 05 — Indexes, Query Plans and Performance](chapters/05-indexes-query-plans-and-performance.md)
12. [Chapter 05 lab](labs/chapter-05/README.md)
13. [Chapter 06 — PostgreSQL on Bare Metal](chapters/06-postgresql-on-bare-metal.md)
14. [Chapter 06 lab](labs/chapter-06/README.md)
15. [Chapter 07 — PostgreSQL on AWS RDS](chapters/07-postgresql-on-aws-rds.md)
16. [Chapter 07 lab](labs/chapter-07/README.md)
17. [Chapter 08 — PostgreSQL on Kubernetes](chapters/08-postgresql-on-kubernetes.md)
18. [Chapter 08 lab](labs/chapter-08/README.md)
19. [Chapter 09 — Selecting the Right Enterprise PostgreSQL Architecture](chapters/09-selecting-the-right-enterprise-postgresql-architecture.md)
20. [Chapter 09 lab](labs/chapter-09/README.md)
21. [Chapter 10 — Streaming Replication and High Availability](chapters/10-streaming-replication-and-high-availability.md)
22. [Chapter 10 lab](labs/chapter-10/README.md)
23. [Chapter 11 — Backup, Restore, PITR and Disaster Recovery](chapters/11-backup-restore-pitr-and-disaster-recovery.md)
24. [Chapter 11 lab](labs/chapter-11/README.md)

## Learning goals

By completion, the learner will be able to:
- collect application workload requirements and justify PostgreSQL as a database choice;
- explain database, schema, table, relation, index, transactions, MVCC, WAL, and core PostgreSQL processes;
- distinguish operational ownership on bare metal, AWS RDS, and Kubernetes;
- implement and test backup, observability, high availability, performance, security, and lifecycle workflows;
- manage fleet inventory, configuration, patching, capacity, cost, ownership, and operational change;
- produce a reviewable database solution design and evidence-based reliability assessment.

## Chapter requirements

Each chapter includes learning outcomes, 60-minute outline, prerequisite/version assumptions, reproducible lab steps, expected observations, safety/rollback notes, troubleshooting, and acceptance checks. **Authored is not lab-verified**: no chapter is certified until actual runtime evidence is collected and reviewed.

## Separation from existing content

The enterprise learning path lives entirely under `postgresql/postgresql-dbre-sre-enterprise-learning-path/`. Existing 100-chapter lessons and DBRE ownership/runbooks remain untouched and serve as optional deeper references.

## Official references

- [PostgreSQL documentation](https://www.postgresql.org/docs/)
- [Amazon RDS for PostgreSQL documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
