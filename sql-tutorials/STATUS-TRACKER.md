# SQL Tutorials — Status Tracker

> **Scope:** 120 planned chapters in 12 parts. Source of truth for titles and chapter order: [MASTER-TOC.md](MASTER-TOC.md).
> **Updated:** 2026-11-08. Content publication and runtime validation are distinct milestones.

| Metric | Count |
|---|---:|
| Planned chapters | 120 |
| Authored and published chapters | 2 |
| Remaining to draft | 118 |
| Independently reviewed chapters | 0 |
| PostgreSQL 18 runtime-validated chapters | 0 |

## Part-level progress

| Part | Chapters | Published | Remaining |
|---|---|---:|---:|
| 01 — Fundamentals | 001–010 | 2 | 8 |
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
| 003–120 | See Master TOC | Planned | — | — |

## Chapter 002 publication evidence

- Chapter: [002](part-01-fundamentals/002-relational-databases-and-dbms-architecture.md); commit `bb9c5761befd5ef469e0fdc10f12968c49dddd2f`.
- Lab: [002 SQL](labs/002-relational-architecture.sql); commit `3381fbee46c8199797ecd0a8c029749e00afc893`.
- GitHub fetch verified both files on `main`; read-only static check completed. Independent review and PostgreSQL 18 runtime execution remain pending.

## Next work item

**003 — Set up the SQL lab: PostgreSQL 18, Docker, and SQL clients.** Preserve consistent 60-minute lessons and use read-only examples when no isolated lab is required. Chapter 003 establishes reproducible PostgreSQL 18 lab setup. Avoid duplicating other established PostgreSQL DBRE/SRE learning paths; this track focuses on SQL literacy and application.

## Quality gates

1. Before authoring, read current `main`, Master TOC, this tracker, and existing chapter files.
2. Do not overwrite existing chapters automatically or duplicate chapter numbers.
3. Review SQL syntax, expected outputs, Markdown paths, and safety instructions before publication.
4. Run PostgreSQL 18 examples in an isolated environment when available; retain command output/evidence and label validation correctly. When unavailable, record **runtime pending**, not **passed**.
5. Update this tracker after each confirmed GitHub publication; report exact commit and next unfinished chapter.
6. Continue through all 120 chapters without a manual `NEXT`. Stop advancing when the curriculum is complete or if a real safety, access, or correctness blocker prevents progress.
