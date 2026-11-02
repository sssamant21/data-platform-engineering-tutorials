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
