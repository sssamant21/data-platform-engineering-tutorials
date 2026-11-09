# SQL Tutorials — Status Tracker

> **Scope:** 120 planned chapters in 12 parts. Source of truth for titles and chapter order: [MASTER-TOC.md](MASTER-TOC.md).
> **Updated:** 2026-11-09. Content publication and runtime validation are distinct milestones.

| Metric | Count |
|---|---:|
| Planned chapters | 120 |
| Authored and published chapters | 23 |
| Remaining to draft | 97 |
| Independently reviewed chapters | 0 |
| PostgreSQL 18 runtime-validated chapters | 0 |

## Part-level progress

| Part | Chapters | Published | Remaining |
|---|---|---:|---:|
| 01 — Fundamentals | 001–010 | 10 | 0 |
| 02 — Filtering and sorting | 011–020 | 10 | 0 |
| 03 — Modeling, DDL, constraints | 021–030 | 3 | 7 |
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
| [007](part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md) | SELECT fundamentals — retrieve rows and columns | Published | Pending | Pending |
| [008](part-01-fundamentals/008-aliases-expressions-literals-and-calculated-columns.md) | Aliases, expressions, literals, and calculated columns | Published | Pending | Pending |
| [009](part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md) | Data types, NULL, and explicit type conversion | Published | Pending | Pending |
| [010](part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md) | Lab 01 — explore the sample database and write first queries | Published | Pending | Pending |
| [011](part-02-filtering/011-where-and-comparison-operators.md) | WHERE and comparison operators | Published | Pending | Pending |
| [012](part-02-filtering/012-and-or-not-and-boolean-precedence.md) | AND, OR, NOT, and Boolean precedence | Published | Pending | Pending |
| [013](part-02-filtering/013-null-handling-and-sql-three-valued-logic.md) | NULL handling and SQL three-valued logic | Published | Pending | Pending |
| [014](part-02-filtering/014-in-between-and-range-predicates.md) | IN, BETWEEN, and range predicates | Published | Pending | Pending |
| [015](part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md) | LIKE, wildcard matching, and dialect-specific ILIKE | Published | Pending | Pending |
| [016](part-02-filtering/016-distinct-and-duplicate-handling.md) | DISTINCT and duplicate handling | Published | Pending | Pending |
| [017](part-02-filtering/017-order-by-and-deterministic-sorting.md) | ORDER BY and deterministic sorting | Published | Pending | Pending |
| [018](part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md) | LIMIT, OFFSET, FETCH, and TOP across dialects | Published | Pending | Pending |
| [019](part-02-filtering/019-case-coalesce-and-nullif.md) | CASE, COALESCE, and NULLIF | Published | Pending | Pending |
| [020](part-02-filtering/020-lab-02-filter-and-rank-operational-records.md) | Lab 02 — filter and rank operational records | Published | Pending | Pending |
| [021](part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md) | Entity relationships and conceptual data modeling | Published | Pending | Pending |
| [022](part-03-modeling/022-create-database-create-schema-and-create-table.md) | CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE | Published | Pending | Pending |
| [023](part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md) | Choosing numeric, character, Boolean, and temporal types | Published | Pending | Pending |
| 024–120 | See Master TOC | Planned | — | — |

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

## Chapter 007 publication evidence

- Chapter: [007](part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md); commit `fdb84ad882d409c3465b2a11eda2d08f9bca07d6`.
- Lab: [007 SQL](labs/007-select-fundamentals.sql); commit `224e32e508fa0db6fb8f87d08e3cda581b919f6d`.
- Both files re-fetched and verified on `main`. Read-only transaction, synthetic CTE data, environment assertion, and expected-results acceptance checks reviewed statically. **Independent editorial review and PostgreSQL 18 runtime execution remain pending.**

## Chapter 008 publication evidence

- Chapter: [008](part-01-fundamentals/008-aliases-expressions-literals-and-calculated-columns.md); commit `cc4f9d272ff6fc0e7fd64fc88a6a5b07b77c8e83`.
- Lab: [008 SQL](labs/008-aliases-expressions-calculated-columns.sql); commit `f73a41bc9f39408bf6cd4a9c756d35b89832ed15`.
- Both files were re-fetched from `main`; basic static inspection confirmed the lab contains no persistent write/DDL commands. Expected arithmetic and results were reviewed manually. **Independent editorial review and PostgreSQL 18 runtime execution remain pending**.

## Chapter 009 publication evidence

- Chapter: [009](part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md); commit `04db4722ca526560a32997d4ebb2f9810a5ea9b5`.
- Lab: [009 SQL](labs/009-data-types-null-explicit-conversion.sql); commit `550f2eca4b3e453608bfecada7b50d6b287dd2f2`.
- README navigation: commit `4f57cbb884c6e77197d4add7f3523dcb402ebccc`.
- Both chapter and lab re-fetched from GitHub `main`. Targeted static inspection confirmed the SQL lab's PostgreSQL 18/database guard, read-only transaction, synthetic data, deterministic checks, and rollback. Expected results reviewed against literal inputs; full independent editorial review and automated SQL syntax verification remain pending.
- **No isolated PostgreSQL 18 runtime execution or reproducible runtime evidence was obtained; runtime validation remains pending.**

## Chapter 010 publication evidence

- Chapter: [010](part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md); commit `0d19c77c02a777aca3a030486247ed58603e31af`.
- Lab: [010 SQL](labs/010-lab-01-explore-sample-database.sql); commit `1231f6269e01c8313ca7168064db6afe06e4a6fe`.
- Both files were re-fetched and verified on GitHub main. Static inspection checked synthetic CTE datasets, read-only transaction, PostgreSQL 18/database assertion, deterministic expected counts/totals and rollback. Independent editorial review and actual isolated PostgreSQL 18 execution with retained evidence are **pending**.
- Part 01 authored/published: **10/10**. This is not a runtime certification.

## Chapter 011 publication evidence

- Chapter: [011](part-02-filtering/011-where-and-comparison-operators.md); commit `a408496b1310e033d91a28b04685d2b2ed07165d`.
- Lab: [011 SQL](labs/011-where-comparison-operators.sql); commit `e1c0c0398966635f2bc1f763f8fac0da448dcebb`.
- README navigation: commit `a25de1adde8c6f7acd7cf83192b223c21aca333e`.
- Chapter and lab re-fetched from GitHub main. Targeted static review: lab uses synthetic VALUES, read-only transaction, PostgreSQL 18/database guard, six expected ID-set checks, fail-closed assertion and ROLLBACK. Link paths inspected. **Independent editorial review, comprehensive SQL syntax validation, and actual isolated PostgreSQL 18 execution are pending**; no runtime evidence obtained.

## Chapter 012 publication evidence

- Chapter: [012](part-02-filtering/012-and-or-not-and-boolean-precedence.md); commit `3dfcdc4fd9522cde1cc5d8ce978dec9d8b30cb6b`.
- Lab: [012 SQL](labs/012-and-or-not-boolean-precedence.sql); commit `ef90ac64ac1753691731c97f1836d2e92e89482a`.
- README navigation commit `bd1febc26a6b54a0658db0f2bbfd44d7bb981fa3`.
- Both chapter and lab were re-fetched from GitHub `main`. Targeted static inspection confirmed synthetic `VALUES`, read-only transaction, version/database guard, six exact ID-set acceptance checks, and rollback. Expected ID sets reviewed from literal data. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 execution remain pending**; no runtime evidence was collected.

## Chapter 013 publication evidence

- Chapter: [013](part-02-filtering/013-null-handling-and-sql-three-valued-logic.md); commit `1f2f5332773e478e99e8b6995dc24a50ab4a1acd`.
- Lab: [013 SQL](labs/013-null-three-valued-logic.sql); commit `bdb0622d5cebb91cd42d5fc1b52e25aa75f2713a`.
- README navigation: commit `38b64b43aea7d1482a0aa29fe187cfe34cd5b6a1`.
- Chapter and lab fetched and verified on GitHub main. Targeted static inspection: synthetic VALUES, read-only transaction, PostgreSQL version/database assertion, exact-result acceptance checks, and ROLLBACK. Expected outputs manually reasoned from literal inputs. **Independent editorial review, full SQL syntax checks, and isolated PostgreSQL 18 runtime execution remain pending.** No runtime evidence obtained.

## Chapter 014 publication evidence

- Chapter: [014](part-02-filtering/014-in-between-and-range-predicates.md); commit `0f45320d52f9b5e61e63749c5d5afa14e562e78d`.
- Lab: [014 SQL](labs/014-in-between-range-predicates.sql); commit `2344290efa45eccac7bbbe777a2cb794c97e6f32`.
- README navigation: commit `f1ac6cc4b5808e3f4abb13345665a4c9f6c96c64`.
- Both new files were re-fetched from GitHub `main`. Targeted static inspection confirmed synthetic inline data, a read-only transaction, PostgreSQL 18/database guard, expected-result assertions, and rollback. Relative navigation paths inspected; expected ID sets reasoned from literal rows. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 execution remain pending.** No runtime evidence was collected.

## Chapter 015 publication evidence

- Chapter: [015](part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md); commit `5a244acc78427699052f44ecbab3f58aa62169ea`.
- Lab: [015 SQL](labs/015-like-wildcards-ilike.sql); commit `0e627742f0657fafc21a4aa085ea9b8021d6c14c`.
- Both files re-fetched from GitHub `main`. Targeted static inspection: synthetic inline VALUES, read-only transaction, PostgreSQL 18/database guard, explicit C collation for case-sensitive examples, expected ID-set assertions, and rollback. Expected outputs manually reasoned; Markdown relative paths inspected. **Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 runtime execution remain pending.** No runtime evidence collected.

## Chapter 016 publication evidence

- Chapter: [016](part-02-filtering/016-distinct-and-duplicate-handling.md); commit `da2b5aeadb8a9949eb5e087adfba2367aed3b3a4`.
- Lab: [016 SQL](labs/016-distinct-duplicate-handling.sql); commit `3e0adfb603108b5660bbd3fb1e8f4c86fd4518f3`.
- README navigation: commit `cf355ae9131e1abcfd2c55bb6ff17c70c0d2f387`.
- Chapter and lab fetched from GitHub `main` after creation. Targeted static checks: read-only transaction, inline synthetic data, PostgreSQL 18/database guard, deterministic expected counts, exact acceptance checks, rollback and relative navigation. **No independent editorial review, comprehensive SQL syntax verification, or actual isolated PostgreSQL 18 runtime execution was completed.** Runtime acceptance remains pending.

## Chapter 017 publication evidence

- Chapter: [017](part-02-filtering/017-order-by-and-deterministic-sorting.md); commit `96480970b248d7aa3ab7a5d30cf43a29cecc912d`.
- Lab: [017 SQL](labs/017-order-by-deterministic-sorting.sql); commit `0e1a0edfc0fb7e1cba0871a7e15d01d0773e69c6`.
- README navigation: commit `e1997e73b068214d730d0feb8a8808f353725ad0`.
- Both files were fetched from GitHub `main` after publication. Targeted static inspection checked synthetic inline values, read-only transaction, database/version assertion, deterministic expected ID arrays, rollback, and chapter-relative paths. Expected arrays were manually reasoned, **not executed**. Independent editorial review, comprehensive syntax checks and actual isolated PostgreSQL 18 runtime acceptance remain **pending**; no runtime evidence collected.

## Next work item

**023 — Choosing numeric, character, Boolean, and temporal types.** Continue Part 03 with type-selection examples and isolated PostgreSQL 18 lab. PostgreSQL 18 runtime acceptance for existing chapters remains pending.

## Quality gates

1. Before authoring, read current `main`, Master TOC, this tracker, and existing chapter files.
2. Do not overwrite existing chapters automatically or duplicate chapter numbers.
3. Review SQL syntax, expected outputs, Markdown paths, and safety instructions before publication.
4. Run PostgreSQL 18 examples in an isolated environment when available; retain command output/evidence and label validation correctly. When unavailable, record **runtime pending**, not **passed**.
5. Update this tracker after each confirmed GitHub publication; report exact commit and next unfinished chapter.
6. Continue through all 120 chapters without a manual `NEXT`. Stop advancing when the curriculum is complete or if a real safety, access, or correctness blocker prevents progress.

## Chapter 018 publication evidence

- Chapter: [018](part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md); published with commit `615cd870769c64c10170c621306c58571e4352cc`.
- Lab: [018 SQL](labs/018-limit-offset-fetch-top.sql); same commit `615cd870769c64c10170c621306c58571e4352cc`.
- README navigation updated in the same commit. GitHub `main` fetch verified the three files.
- Targeted static inspection: inline synthetic data, read-only transaction, timeout, rollback, environment assertion, expected result arrays, deterministic ordering and links. This is **not** comprehensive SQL syntax verification or independent editorial review.
- **Actual PostgreSQL 18 runtime execution: pending.** No isolated instance was run and no runtime evidence is claimed.
- **Next unfinished chapter:** 019 — CASE, COALESCE, and NULLIF.

## Chapter 019 publication evidence

- Chapter: [019](part-02-filtering/019-case-coalesce-and-nullif.md); commit `b81971eadd78bde98cd94129207787f2fca9940b`.
- Lab: [019 SQL](labs/019-case-coalesce-nullif.sql); commit `bf1ddd9f51ffe28fb699df654758b303726b1f6a`.
- README navigation: commit `f11057c7c3d2d3889bc1fbd3e2d4730cb1c9c0dc`.
- Chapter, lab, and README re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked six synthetic events, NULL rate semantics, read-only transaction, version/database guard, timeout, exact assertions, and rollback. **Independent editorial review and comprehensive SQL syntax checks pending.**
- **Actual isolated PostgreSQL 18 runtime validation pending; no execution evidence was collected.**
- **Next unfinished chapter:** 020 — Lab 02: filter and rank operational records.

## Chapter 020 publication evidence

- Chapter: [020](part-02-filtering/020-lab-02-filter-and-rank-operational-records.md), commit `945e3c0db2f6684ad54505d731c476081e96d094`.
- Lab: [020 SQL](labs/020-lab-02-filter-and-rank-operational-records.sql), commit `e8fd8a331ca0da25f907c9d9353207da2f0f4b80`.
- README navigation commit `85768b25fb6ba58c873ab0fe61627f919aa8f1ce`.
- Chapter and lab were re-fetched from GitHub `main`. Targeted static reasoning reviewed six selected synthetic events, deterministic ranking, expected pagination arrays, service counts, read-only transaction, environment assertion, timeout and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **PostgreSQL 18 runtime validation pending:** no isolated PostgreSQL 18 instance was executed and no reproducible runtime evidence was collected.
- Part 02 authored/published: 10/10. Next unfinished chapter: **021 — Entity relationships and conceptual data modeling**.

## Chapter 021 publication evidence

- Chapter: [021](part-03-modeling/021-entity-relationships-and-conceptual-data-modeling.md), commit `243a8fac8b11a6524585166532562638aeabdc45`.
- Lab: [021 SQL](labs/021-entity-relationships-conceptual-modeling.sql), commit `e1b94742c7d93acbb9c3f1ac20c146d05344ffb8`.
- README navigation commit `c6d7263cd5741e6299dca93ef335fd43ba891836`.
- Chapter and lab fetched from GitHub `main` after creation. Targeted static inspection confirmed synthetic inline datasets, PostgreSQL 18/database guard, read-only transaction, expected results and fail-closed assertions. This is not comprehensive SQL syntax verification or independent editorial review.
- **Actual isolated PostgreSQL 18 runtime validation pending**; no execution evidence obtained.
- **Next unfinished chapter:** 022 — CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE.

## Chapter 022 publication evidence

- Chapter: [022](part-03-modeling/022-create-database-create-schema-and-create-table.md), commit `2739a5fb188f772b35d2146e9ceebe4d7542f491`.
- Lab: [022 SQL](labs/022-create-schema-and-tables-isolated.sql), commit `570c5080dff38feb9442b42d9d2ee04c3e72fe21`.
- README navigation commit `9b05fd209200a2697ead671e281f7032368a26f9`.
- Chapter and lab fetched from GitHub `main` after creation; README link verified before tracker update. Targeted static inspection reviewed version/database guard, pre-existing-schema refusal, transaction-scoped DDL, synthetic rows, count/amount assertions, foreign key metadata, ROLLBACK and post-rollback schema absence check. This is **not** independent editorial review or comprehensive syntax validation.
- **Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution or reproducible runtime evidence was obtained.
- **Next unfinished chapter: 023 — Choosing numeric, character, Boolean, and temporal types.**

## Chapter 023 publication evidence

- Chapter: [023](part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md); commit `dcafd32dfac87953ed8ae711784664feea70c2ff`.
- Lab: [023 SQL](labs/023-choosing-sql-data-types.sql); commit `2315ef338e922a7117728c812e0b230847bc0912`.
- README navigation commit `d418f895a1b95949241b25301be5e0b0b7600e9b`.
- All three files re-fetched from GitHub `main` before tracker update. Targeted static reasoning reviewed six synthetic records, exact amount total 91.45, NULL count 2, read-only transaction, PostgreSQL 18/database checks, timeout and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **Actual isolated PostgreSQL 18 runtime validation: pending**; no execution evidence was collected.
- **Next unfinished chapter: 024 — Primary keys, natural keys, surrogate keys, and UNIQUE.**
