# SQL Tutorials — Status Tracker

> **Scope:** 120 planned chapters in 12 parts. Source of truth for titles and chapter order: [MASTER-TOC.md](MASTER-TOC.md).
> **Updated:** 2026-11-08. Content publication and runtime validation are distinct milestones.

| Metric | Count |
|---|---:|
| Planned chapters | 120 |
| Authored and published chapters | 6 |
| Remaining to draft | 114 |
| Independently reviewed chapters | 0 |
| PostgreSQL 18 runtime-validated chapters | 0 |

## Part-level progress

| Part | Chapters | Published | Remaining |
|---|---|---:|---:|
| 01 — Fundamentals | 001–010 | 6 | 4 |
| 02 — Filtering and sorting | 011–020 | 0 | 10 |
| 03 — Modeling, DDL, constraints | 021–030 | 0 | 10 |
| 04 — Transactions and DML | 031–040 | 0 | 10 |
| 05 — Joins | 041–050 | 0 | 10 |
| 06 — Aggregation and reporting | 051–060 | 0 | 10 |
| 07 — Subqueries and CTEs | 061–070 | 0 | 10 |
| 08 — Window functions | 071–080 | 0 | 10 |
| 09 — Functions, views, JSON | 081–090 | 0 | 10 |
| 10 — Performance | 091–100 | 0 | 10 |
| 11 — Security and DBRE/SRE | 101–110 | 0 | 10 |
| 12 — Data engineering and dialects | 111–120 | 0 | 10 |

## Chapter status

| Chapter | Title | Content | Review | Runtime |
|---|---|---|---|---|
| [001](part-01-fundamentals/001-introduction-to-sql.md) | Introduction to SQL — purpose, use cases, and stakeholder roles | Published | Pending | Pending |
| [002](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md) | Relational databases and DBMS architecture | Published | Pending | Pending |
| [003](part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md) | Set up the SQL lab — PostgreSQL 18, Docker, and SQL clients | Published | Pending | Pending |
| [004](part-01-fundamentals/004-databases-schemas-tables-rows-columns.md) | Databases, schemas, tables, rows, and columns | Published | Pending | Pending |
| [005](part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md) | Records, relationships, keys, and relational terminology | Published | Pending | Pending |
| [006](part-01-fundamentals/006-anatomy-of-sql-statement-and-logical-query-processing.md) | Anatomy of a SQL statement and logical query processing | Published | Pending | Pending |
| 007–120 | See Master TOC | Planned | — | — |

## Chapter 002 publication evidence

- Chapter: [002](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md); commit `bb9c5761befd5ef469e0fdc10f12968c49dddd2f`.
- Lab: [002 SQL](labs/002-relational-architecture.sql); commit `3381fbee46c8199797ecd0a8c029749e00afc893`.
- GitHub fetch verified both files on `main`; read-only static check completed. Independent review and PostgreSQL 18 runtime execution remain pending.

## Chapter 003 publication evidence

- Chapter: [003](part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md); commit `1efd2d4da9fc7809d7a58895d6863f4d6f5b3e5d`.
- Docker Compose: [compose.yaml](labs/docker/compose.yaml); commit `b1c1324798a19400e6e42aca1e33a07127f9a9d5`.
- SQL: [003-lab-smoke-test.sql](labs/003-lab-smoke-test.sql); commit `618cb38e25eef5ee43cd22aa6f2834534819347f`.
- Lab guide: [Docker README](labs/docker/README.md); commit `79be3378d1dc564deec58e9673ab40756bceb94b`.
- GitHub fetch confirmed all four artifacts on `main`. Static checks: read-only SQL, version assertion, loopback port, PostgreSQL 18 volume path. **No PostgreSQL 18 container was run**; independent review and runtime evidence remain pending.

## Chapter 004 publication evidence

- Chapter: [004](part-01-fundamentals/004-databases-schemas-tables-rows-columns.md); commit `d688a90b294b0cc5de10b58be5ce2eac7d5d49f5`.
- Lab: [004 SQL](labs/004-databases-schemas-tables-rows-columns.sql); commit `75d0d135f93f88e34e8baf79a8a6b25ba1194ef8`.
- GitHub fetch verified both files on `main`. Lab uses `BEGIN READ ONLY` and synthetic in-query rows. Expected counts and sums reviewed. **No PostgreSQL 18 execution evidence**; independent review and runtime acceptance remain pending.

## Chapter 005 publication evidence

- Chapter: [005](part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md); commit `3c136e65ae133fa5c53a806e559dcae17d8cfe10`.
- Lab: [005 SQL](labs/005-records-relationships-keys.sql); commit `d4b165fb857fc714207bf238df3fd94227b48673`.
- GitHub fetch verified both files on `main`. Static review found a read-only transaction, environment checks, synthetic data and expected-output assertions. **Independent editorial review and actual PostgreSQL 18 execution are pending**.

## Chapter 006 publication evidence

- Chapter: [006](part-01-fundamentals/006-anatomy-of-sql-statement-and-logical-query-processing.md); commit `565e76ee88ea194bc13438f9224341a62af69ffc`.
- Lab: [006 SQL](labs/006-statement-anatomy-logical-processing.sql); commit `ce6d2247b8c6db8d23d8185e39a26c4fd5c204cf`.
- Both artifacts fetched and verified on `main`; read-only transaction, synthetic dataset, environment guards and deterministic expected-result assertions checked statically. **Independent editorial review and PostgreSQL 18 runtime execution remain pending.**

## Next work item

**007 — SELECT fundamentals: retrieve rows and columns.** Continue using synthetic, read-only examples in the Chapter 003 isolated PostgreSQL 18 lab. Avoid duplicating other established PostgreSQL DBRE/SRE learning paths; this track focuses on SQL literacy and application.

## Quality gates

1. Before authoring, read current `main`, Master TOC, this tracker, and existing chapter files.
2. Do not overwrite existing chapters automatically or duplicate chapter numbers.
3. Review SQL syntax, expected outputs, Markdown paths, and safety instructions before publication.
4. Run PostgreSQL 18 examples in an isolated environment when available; retain command output/evidence and label validation correctly. When unavailable, record **runtime pending**, not **passed**.
5. Update this tracker after each confirmed GitHub publication; report exact commit and next unfinished chapter.
6. Continue through all 120 chapters without a manual `NEXT`. Stop advancing when the curriculum is complete or if a real safety, access, or correctness blocker prevents progress.
