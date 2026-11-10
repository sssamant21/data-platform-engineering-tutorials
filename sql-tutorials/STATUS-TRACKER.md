# SQL Tutorials — Status Tracker

> **Scope:** 120 planned chapters in 12 parts. Source of truth for titles and chapter order: [MASTER-TOC.md](MASTER-TOC.md).
> **Updated:** 2026-11-10. Content publication and runtime validation are distinct milestones.

| Metric | Count |
|---|---:|
| Planned chapters | 120 |
| Authored and published chapters | 47 |
| Remaining to draft | 73 |
| Independently reviewed chapters | 0 |
| PostgreSQL 18 runtime-validated chapters | 0 |

## Part-level progress

| Part | Chapters | Published | Remaining |
|---|---|---:|---:|
| 01 — Fundamentals | 001–010 | 10 | 0 |
| 02 — Filtering and sorting | 011–020 | 10 | 0 |
| 03 — Modeling, DDL, constraints | 021–030 | 10 | 0 |
| 04 — Transactions and DML | 031–040 | 10 | 0 |
| 05 — Joins | 041–050 | 7 | 3 |
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
| [024](part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md) | Primary keys, natural keys, surrogate keys, and UNIQUE | Published | Pending | Pending |
| [025](part-03-modeling/025-foreign-keys-and-referential-integrity.md) | Foreign keys and referential integrity | Published | Pending | Pending |
| [026](part-03-modeling/026-not-null-check-default-and-constraint-validation.md) | NOT NULL, CHECK, DEFAULT, and constraint validation | Published | Pending | Pending |
| [027](part-03-modeling/027-identity-columns-sequences-and-generated-values.md) | Identity columns, sequences, and generated values | Published | Pending | Pending |
| [028](part-03-modeling/028-alter-table-rename-operations-and-safe-schema-changes.md) | ALTER TABLE, rename operations, and safe schema changes | Published | Pending | Pending |
| [029](part-03-modeling/029-normalization-1nf-3nf-and-intentional-denormalization.md) | Normalization (1NF–3NF) and intentional denormalization | Published | Pending | Pending |
| [030](part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md) | Lab 03 — design and build a normalized operational schema | Published | Pending | Pending |
| [031](part-04-data-modification/031-insert-single-row-and-multi-row-records.md) | INSERT single-row and multi-row records | Published | Pending | Pending |
| [032](part-04-data-modification/032-insert-select-and-bulk-loading-fundamentals.md) | INSERT ... SELECT and bulk-loading fundamentals | Published | Pending | Pending |
| [033](part-04-data-modification/033-update-with-safe-predicates-and-preview-queries.md) | UPDATE with safe predicates and preview queries | Published | Pending | Pending |
| [034](part-04-data-modification/034-delete-with-safe-predicates-and-referential-implications.md) | DELETE with safe predicates and referential implications | Published | Pending | Pending |
| [035](part-04-data-modification/035-delete-versus-truncate-versus-drop.md) | DELETE versus TRUNCATE versus DROP | Published | Pending | Pending |
| [036](part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md) | UPSERT and MERGE patterns across SQL dialects | Published | Pending | Pending |
| [037](part-04-data-modification/037-returning-output-and-write-verification.md) | RETURNING, OUTPUT, and write verification | Published | Pending | Pending |
| [038](part-04-data-modification/038-begin-commit-rollback-and-savepoint.md) | BEGIN, COMMIT, ROLLBACK, and SAVEPOINT | Published | Pending | Pending |
| [039](part-04-data-modification/039-isolation-levels-and-common-transaction-anomalies.md) | Isolation levels and common transaction anomalies | Published | Pending | Pending |
| [040](part-04-data-modification/040-lab-04-complete-a-safe-auditable-transaction-workflow.md) | Lab 04 — complete a safe, auditable transaction workflow | Published | Pending | Pending |
| [041](part-05-joins/041-join-fundamentals-and-relationship-cardinality.md) | Join fundamentals and relationship cardinality | Published | Pending | Pending |
| [042](part-05-joins/042-inner-join-matched-records.md) | INNER JOIN — matched records | Published | Pending | Pending |
| [043](part-05-joins/043-left-outer-join-preserve-unmatched-left-rows.md) | LEFT OUTER JOIN — preserve unmatched left rows | Published | Pending | Pending |
| [044](part-05-joins/044-right-and-full-outer-join-applicability-and-portability.md) | RIGHT and FULL OUTER JOIN — applicability and portability | Published | Pending | Pending |
| [045](part-05-joins/045-cross-join-and-self-join.md) | CROSS JOIN and SELF JOIN | Published | Pending | Pending |
| [046](part-05-joins/046-multi-table-joins-and-join-condition-design.md) | Multi-table joins and join condition design | Published | Pending | Pending |
| [047](part-05-joins/047-one-to-many-and-many-to-many-relationships.md) | One-to-many and many-to-many relationships | Published | Pending | Pending |
| 048–120 | See Master TOC | Planned | — | — |

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

**035 — DELETE versus TRUNCATE versus DROP.** Continue Part 04 with isolated, rollback-only demonstrations. PostgreSQL 18 runtime acceptance for existing chapters remains pending.

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

## Chapter 024 publication evidence

- Chapter: [024](part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md); commit `8ad6c848298676027fbea05d7e64ab07ea57aac9`.
- Isolated rollback-only lab: [024 SQL](labs/024-primary-natural-surrogate-unique.sql); commit `3dccc07552297f83660be16bfeb5a0513f74e711`.
- README navigation commit `e84e14fdeb7da80bc978c657e1942580cad8ce2f`.
- Both authored files were fetched from GitHub `main`; targeted static inspection covers transaction rollback, temporary synthetic tables, version/database guard, expected values, and duplicate-key assertions. Independent editorial review, comprehensive SQL syntax verification, and actual isolated PostgreSQL 18 runtime execution **remain pending**. No runtime evidence claimed.
- **Next:** Chapter 025 — Foreign keys and referential integrity.

## Chapter 025 publication evidence

- Chapter: [025](part-03-modeling/025-foreign-keys-and-referential-integrity.md); commit `b5d872555cc8992f4b68715d91d47c072536190d`.
- Isolated rollback-only lab: [025 SQL](labs/025-foreign-keys-referential-integrity.sql); commit `1b9547f597293d1447ef4769d4c49af14cce3954`.
- README navigation: commit `c935e4a4e1350cd9356e7a3f2dce9d92e35a458f`.
- Both authored artifacts were fetched from GitHub `main` after publication. Targeted static inspection covered synthetic data, guardrails, rollback, expected counts and foreign-key rejection handling. **Independent editorial review, comprehensive SQL syntax checks and actual PostgreSQL 18 runtime validation are pending.** No isolated PostgreSQL 18 execution evidence was obtained.
- Part 03: **5/10**; total: **25/120**. Next: **026 — NOT NULL, CHECK, DEFAULT, and constraint validation**.

## Chapter 026 publication evidence

- Chapter: [026](part-03-modeling/026-not-null-check-default-and-constraint-validation.md); commit `646a93e76740415fffebc847bb0c94b79c9e863a`.
- Isolated rollback-only lab: [026 SQL](labs/026-not-null-check-default-validation.sql); commit `315e9643e6c7bf41016e5279714cf47d1c6b80d7`.
- README navigation: commit `d96176eb7dfaad03c8c61d708aee0eb903b42074`.
- Chapter, SQL lab and README were fetched from GitHub `main` after publication. Targeted static inspection reviewed chapter links, synthetic row counts (3), defaulted values, expected SQLSTATEs 23502/23514, five synthetic legacy rows (3 invalid), environment guards, timeouts and rollback. These are reasoned checks, **not executed SQL**.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No runtime evidence obtained.
- Part 03: **6/10**; total **26/120**; next unfinished chapter: **027 — Identity columns, sequences, and generated values**.

## Chapter 027 publication evidence

- Chapter: [027](part-03-modeling/027-identity-columns-sequences-and-generated-values.md); commit `bebac562009e524e6aae343c15d48fb511f77072`.
- Isolated rollback-only lab: [027 SQL](labs/027-identity-sequences-generated-values.sql); commit `5d67dade4b05f05ae7c66ff96286cef6b7bf0f47`.
- README navigation: commit `dc4847b52d4b9444e757ef06846465790ae18647`.
- Chapter, lab, and README fetched and verified from GitHub `main` before updating this tracker. Targeted static reasoning inspected identity ALWAYS/BY DEFAULT semantics, expected IDs (100,101,102,999 and 1,500), SQLSTATE 428C9, unique violation handling, generated total 46.75, temporary sequence values 10/15, version/database guard, transaction rollback and relative links. These are **not runtime test results**.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No execution evidence collected.
- Part 03: **7/10**; total **27/120**; next unfinished chapter **028 — ALTER TABLE, rename operations, and safe schema changes**.

## Chapter 028 publication evidence

- Chapter: [028](part-03-modeling/028-alter-table-rename-operations-and-safe-schema-changes.md); commit `16c4b5c8da7b6e9eec328fa5360935eab63f5b44`.
- Isolated rollback-only lab: [028 SQL](labs/028-alter-table-safe-schema-changes.sql); commit `0744a00e4817a9d7f0a90511e68e5e7f7031eead`.
- README navigation: commit `5b5b56013180e08ae85e652f98fff8bf781333bc`.
- Both new files and README were fetched and verified from GitHub `main` before updating this tracker. Targeted static inspection reviewed chapter/lab paths, synthetic values (3 records, 24.75 total), default/backfill distinction, SQLSTATE classes for CHECK/UNIQUE, version/database guard, temporary objects, timeouts, and rollback. This is **not** an independent editorial review or comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution evidence obtained.
- Part 03: **8/10**; total **28/120**; next unfinished chapter **029 — Normalization (1NF–3NF) and intentional denormalization**.

## Chapter 029 publication evidence

- Chapter: [029](part-03-modeling/029-normalization-1nf-3nf-and-intentional-denormalization.md); commit `8df8ca0cb595e2bd9b87533789cd77b0755f3d76`.
- Read-only lab: [029 SQL](labs/029-normalization-1nf-3nf-denormalization.sql); commit `ff4db34435d0d3a1a6f66a3be13064ac463f6aec`.
- README navigation: commit `bd2770f8cb45ded6d2026a167625c4dccca07610`.
- Chapter and lab fetched from GitHub `main` after creation; targeted static reasoning reviewed synthetic cardinalities (2 customers, 2 products, 2 orders, 3 lines), expected total 85.00, stale cache drift 5.00, PostgreSQL 18/database guards, read-only transaction, fail-closed assertions, and rollback. This is **not** independent editorial review or comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution or reproducible runtime evidence obtained.
- Part 03: **9/10**; total **29/120**; next unfinished chapter **030 — Lab 03: design and build a normalized operational schema**.

## Chapter 030 publication evidence

- Chapter: [030](part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md); commit `4d5f411bf827ee6cb1a728cb255b97f660a9d49d`.
- Lab: [030 SQL](labs/030-lab-03-normalized-operational-schema.sql); commit `08cfca4f45df1071e6b62c400e9807fab466dc2a`.
- README navigation: commit `4a05b6fcd0a80052924c1a33827f04ba23f3cb15`.
- Both new artifacts and README navigation re-fetched from GitHub `main`. Targeted static inspection: four synthetic temporary tables, PK/FK/UNIQUE/CHECK constraints, database/version/standby guard, timeouts, rollback, expected counts and revenue reconciliation (85.00). Relative paths reviewed. **Independent editorial review and comprehensive SQL syntax verification remain pending. No isolated PostgreSQL 18 instance was executed and no runtime evidence was collected.**
- Part 03 authored/published: **10/10**; not runtime certified.

## Chapter 031 publication evidence

- Chapter: [031](part-04-data-modification/031-insert-single-row-and-multi-row-records.md); commit `c7d2dbd5956ba8abcb838d655ec2464c648467bf`.
- Isolated rollback-only lab: [031 SQL](labs/031-insert-single-row-and-multi-row-records.sql); commit `2eb1b699fdbdbd4af8346a0b3e72f97b14b1a560`.
- README navigation commit `739fe267b72fbbefca124744736280dc5d2e8a79`.
- Both files and README navigation re-fetched from GitHub `main` after publication. Targeted static inspection covered version/database/standby guard, synthetic values, three expected constraint failures, transaction rollback, count 3 and sum 39.75, and relative links. **This is not comprehensive SQL syntax verification or independent editorial review.**
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 instance was executed or runtime evidence retained.
- Part 04: **1/10**; total **31/120**; next unfinished chapter **032 — INSERT ... SELECT and bulk-loading fundamentals**.

## Chapter 032 publication evidence

- Chapter: [032](part-04-data-modification/032-insert-select-and-bulk-loading-fundamentals.md); commit `0ce801a64c31b6310a0709e16f89eb3fc67ac32f`.
- Isolated rollback-only PostgreSQL 18 lab: [032 SQL](labs/032-insert-select-bulk-loading.sql); commit `fb26329adb4d58adac56ba0192d57c080d82ffd0`.
- README navigation commit `91d740252b2343aee32aef5053420cadcef7e704`.
- Chapter and lab re-fetched from GitHub main before tracker update. Targeted static reasoning checked five synthetic source events, accepted IDs EV-101/102/104, three accepted, two rejected, total 39.75, version/database/standby guard, timeouts and ROLLBACK. This does **not** constitute comprehensive SQL syntax verification.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 instance was executed and no runtime evidence collected.
- Part 04: **2/10**; total **32/120**; next unfinished chapter **033 — UPDATE with safe predicates and preview queries**.

## Chapter 033 publication evidence

- Chapter: [033](part-04-data-modification/033-update-with-safe-predicates-and-preview-queries.md); commit `6623c98265a31464fa420a3a04146b2b1e6e0d93`.
- Isolated rollback-only PostgreSQL 18 lab: [033 SQL](labs/033-update-safe-predicates-preview.sql); commit `a89a5d23f3b4e39c779c04309f8b9454cc8a0f14`.
- README navigation commit `20e08e70f57af6b76947d095b72b65712c8de482`.
- Chapter and lab were re-fetched from GitHub `main` after publication. Targeted static reasoning reviewed four synthetic events, exact candidate key EV-102, before/after row identities, 2 pending/2 reviewed, total 44.75, version/database/standby checks, temporary objects, timeouts and ROLLBACK. Relative link targets were checked against known repository paths. This is **not** comprehensive SQL syntax verification or independent editorial review.
- **Independent editorial review: pending. Comprehensive SQL syntax verification: pending. Actual isolated PostgreSQL 18 runtime validation: pending.** No PostgreSQL 18 execution evidence collected.
- Part 04: **3/10**; total **33/120**; next unfinished chapter **034 — DELETE with safe predicates and referential implications**.


## Chapter 034 publication evidence — 2026-11-09

- [Chapter 034 — DELETE with safe predicates and referential implications](part-04-data-modification/034-delete-with-safe-predicates-and-referential-implications.md), commit `845ccb5a0d41e457d657a62a7e3a66f070853867`.
- [PostgreSQL 18 rollback-only lab](labs/034-delete-safe-predicates-referential-implications.sql), commit `c5da8654414ceb2bec4e70a0d3d8a1a7e94ce82e`.
- README navigation commit `b31600f299bfe0a49a7145a05c1bf25d0e4b1b24`.
- Chapter and lab re-fetched from GitHub main. Targeted static inspection: synthetic temporary parent/child tables, guarded PostgreSQL 18 database/version, pre-delete exact ID assertion, DELETE RETURNING capture, expected foreign-key rejection, post-delete IDs/counts/orphan assertions, ROLLBACK. Relative paths checked against repository layout.
- **Authored/published: 34/120 (28.3%); remaining: 86. Part 04: 4/10.** Independent editorial review: **pending**. Comprehensive SQL syntax checks: **pending**. Actual isolated PostgreSQL 18 runtime execution and reproducible evidence: **pending**. No runtime certification claimed.
- **Next:** Chapter 035 — DELETE versus TRUNCATE versus DROP.

## Chapter 035 publication evidence — 2026-11-09

- [Chapter 035 — DELETE versus TRUNCATE versus DROP](part-04-data-modification/035-delete-versus-truncate-versus-drop.md), commit `9eda0adecbd64f1c4ad298905f0375bbb9ccf258`.
- [PostgreSQL 18 rollback-only synthetic lab](labs/035-delete-truncate-drop.sql), commit `1b7cd5f48df8f02665bf95a2595e98b07f208fe3`.
- README navigation commit `cb13819bb943e563e6a7ab250c0e262d1aef289f`.
- Both new files and README re-fetched from GitHub main. Targeted static inspection: database/version/standby guard, synthetic temporary data, exact DELETE candidate and affected-key checks, TRUNCATE row-count/table-presence checks, DROP absence assertion, conservative timeouts and ROLLBACK. Link paths checked against known chapter/lab locations. This does not establish comprehensive SQL syntax correctness or independent review.
- **Authored/published: 35/120 (29.2%); remaining: 85. Part 04: 5/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime validation and reproducible evidence: **pending**; no execution performed.
- **Next:** Chapter 036 — UPSERT and MERGE patterns across SQL dialects.

## Chapter 036 publication evidence — 2026-11-09

- [Chapter 036 — UPSERT and MERGE patterns across SQL dialects](part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), commit `e8e7c5a5e7a6ea694d034d2b4fe5f87dbb168db1`.
- [PostgreSQL 18 isolated rollback-only SQL lab](labs/036-upsert-merge-patterns.sql), commit `36dc923073b8a0152d70c8047fcd456d22ed2171`.
- README navigation commit `b682e36c9559f20267d9d84b6f24e968ac1dcdd4`.
- All three files re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked synthetic keys and version-guarded conflict updates, MERGE reconciliation (4 SKUs, quantity sum 31), repeatability, version/database/standby guard, timeouts, temp tables, and ROLLBACK. Relative links reviewed. This is **not** comprehensive SQL syntax validation or independent editorial review.
- **Authored/published: 36/120 (30.0%); remaining: 84; Part 04: 6/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime execution: **pending**; no runtime evidence collected.
- **Next:** Chapter 037 — RETURNING, OUTPUT, and write verification.

## Chapter 037 publication evidence — 2026-11-09

- [Chapter 037 — RETURNING, OUTPUT, and write verification](part-04-data-modification/037-returning-output-and-write-verification.md), commit `f15db09a1a2a7e7b5a2b2b6d00e23d6dd72190c0`.
- [PostgreSQL 18 rollback-only SQL lab](labs/037-returning-output-write-verification.sql), commit `cb8705f273ba302ff6a3d9bd8bb048bed65587d1`.
- README navigation commit `5c6ccd45e8006e5f54a6bff953dec3de7a1a23e4`.
- Chapter and lab re-fetched from GitHub main. Targeted static reasoning checked synthetic payments, expected UPDATE/INSERT/DELETE counts, reconciliation (3 rows; amount 41.75), PostgreSQL 18 guard, timeouts, temporary objects and ROLLBACK. **Not** an independent editorial review or comprehensive syntax check.
- **Authored/published: 37/120 (30.8%); remaining: 83; Part 04: 7/10.** Independent editorial review: **pending**. Comprehensive SQL syntax verification: **pending**. Actual isolated PostgreSQL 18 runtime validation: **pending**; no reproducible execution evidence collected.
- **Next:** Chapter 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT.

## Chapter 038 publication evidence — 2026-11-09

- [Chapter 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT](part-04-data-modification/038-begin-commit-rollback-and-savepoint.md), authored commit `045ec248340efd9c7b5bb16186914ed3be7bfa07`; link correction commit `bdf7c8356b5dc2ad8007388779e0ff9e78e98a5c`.
- [PostgreSQL 18 rollback-only SQL lab](labs/038-begin-commit-rollback-savepoint.sql), commit `e9aacdf8ed8f69b40f059b65a14d7d8381a46085`.
- README navigation commit `7bbdae9d71fdf047542eefd180862a3257e87254`.
- All three artifacts re-fetched from GitHub `main` before tracker update. Targeted static reasoning checked the two synthetic balances, conserved total (150.00), savepoint rollback, version/database/standby guard, temporary table, timeout settings, and outer rollback. No independent editorial review or comprehensive SQL syntax verification performed.
- **Authored/published: 38/120 (31.7%); remaining: 82; Part 04: 8/10.** Independent editorial review: **pending**. Actual isolated PostgreSQL 18 runtime execution: **pending**; no reproducible execution evidence collected.
- **Next:** Chapter 039 — Isolation levels and common transaction anomalies.

## Chapter 039 publication checkpoint

- [Chapter 039](part-04-data-modification/039-isolation-levels-and-common-transaction-anomalies.md) and [read-only lab](labs/039-isolation-levels-transaction-anomalies.sql) authored and published; targeted static reasoning only.
- Independent editorial review: pending. Comprehensive SQL syntax/static QA: pending. Actual PostgreSQL 18 runtime validation: pending (no isolated execution evidence).
- Next unfinished chapter: **040 — Lab 04: Complete a Safe, Auditable Transaction Workflow**.


## Latest milestone — Chapter 040

- Chapter and isolated rollback-only SQL lab published and re-fetched on GitHub main; Part 04 complete (40/120).
- Targeted static reasoning performed. **Independent editorial review: pending. Comprehensive static QA: pending. PostgreSQL 18 runtime execution: not performed; evidence pending.**
- Next unfinished chapter per Master TOC: **041 — Join fundamentals and relationship cardinality** (Part 05).

## Chapter 041 publication checkpoint — 2026-11-09

- [Chapter 041 — Join fundamentals and relationship cardinality](part-05-joins/041-join-fundamentals-and-relationship-cardinality.md): commit `3a0edc076e3690fe074d8503ea047e34ec038cd9`.
- [PostgreSQL 18 isolated rollback-only lab](labs/041-join-fundamentals-cardinality.sql): commit `76d86021c72e5a9a2676787cd30b6fab233797d6`.
- README navigation: commit `f5db77be55507d88f4cb9fd56fda799360b91c67`.
- All three artifacts re-fetched from GitHub main before this tracker update. Targeted static inspection reviewed join keys, synthetic counts (3 customers, 3 orders, 3 inner rows, 4 left rows, 4 line-item rows), revenue 65.00, temporary tables, database/version/standby guard and rollback. **Not independently editorially reviewed; comprehensive SQL syntax and link QA pending; no actual isolated PostgreSQL 18 execution or retained runtime evidence.**
- **Published 41/120 (34.2%), 79 remaining, Part 05 1/10. Next: 042 — INNER JOIN: matched records.**

## Chapter 042 publication checkpoint — 2026-11-09

- [Chapter 042 — INNER JOIN: matched records](part-05-joins/042-inner-join-matched-records.md): commit `ebf8fa8824a1e61c84af78415778d2ede2f01a5f`.
- [PostgreSQL 18 isolated rollback-only lab](labs/042-inner-join-matched-records.sql): commit `0a0418c12c4b529b9bef7b93592f5504be0a8127`.
- README navigation: commit `33e5a0506aab656c59e02cfcf96468aaab5174a7`.
- Chapter and lab re-fetched from GitHub main; targeted static reasoning checked synthetic join results, count/amount conservation, version/database guard, temporary tables and rollback. **Independent editorial review pending; comprehensive static syntax and link QA pending; actual PostgreSQL 18 runtime validation not performed and no execution evidence retained.**
- **Published 42/120 (35.0%), 78 remaining, Part 05 2/10. Next: 043 — LEFT OUTER JOIN: preserve unmatched left rows.**

## Chapter 043 publication checkpoint — 2026-11-10

- [Chapter 043 — LEFT OUTER JOIN](part-05-joins/043-left-outer-join-preserve-unmatched-left-rows.md): commit `9219c4e332bef04de436adac451e3070f613e5ec`.
- [Isolated PostgreSQL 18 SQL lab](labs/043-left-outer-join-unmatched-rows.sql): commit `7cd9ac88e1bd2379435d1a92e706dd70fd2427fa`.
- README navigation: commit `3d3dd3bd7d71213756c1305fa9728171ea3c3906`.
- Chapter and lab fetched from GitHub main after creation; README link fetched and confirmed. Targeted static reasoning reviewed source 4/74.00, left 4/74.00, matched 3/65.00, unmatched 1/9.00, ON vs WHERE 4 vs 2, customer-left 4, synthetic temporary tables, version/database guard, transaction timeouts, assertions, and rollback. This is **not** independent editorial review or comprehensive SQL syntax/link QA.
- **Actual PostgreSQL 18 execution: not performed; no reproducible runtime evidence.** Runtime acceptance pending.
- **Published 43/120 (35.8%), 77 remaining, Part 05 3/10. Next: 044 — RIGHT and FULL OUTER JOIN: applicability and portability.**

## Chapter 044 publication checkpoint — 2026-11-10

- [Chapter 044 — RIGHT and FULL OUTER JOIN](part-05-joins/044-right-and-full-outer-join-applicability-and-portability.md): commit `70cf14948c6de803aa1d0eb77b81e86266fce60f`.
- [Isolated PostgreSQL 18 SQL lab](labs/044-right-full-outer-join.sql): commit `5b92d218ccca49b25a7ccc0a0b89bece61938be9`.
- README navigation: commit `8bf387464b8c1fb4760c668e6a234c644a8fed26`.
- Chapter, lab, and README re-fetched from GitHub main. Targeted static reasoning checked fixture arithmetic (A 3/59.00, B 3/54.00, FULL 4, matched 2, A-only 1, B-only 1), RIGHT/LEFT equivalence, key uniqueness, PostgreSQL version/database/standby guard, timeouts, temporary tables and final rollback. **Not independently editorially reviewed; comprehensive syntax and link QA pending. Actual isolated PostgreSQL 18 runtime execution not performed; no retained runtime evidence.**
- **Published 44/120 (36.7%), 76 remaining, Part 05 4/10. Next: 045 — CROSS JOIN and SELF JOIN.**

## Chapter 045 publication evidence

- [Chapter 045](part-05-joins/045-cross-join-and-self-join.md): commit `51c2828cb610bd6f2a7e93f5c010c99c92bce64f`.
- [PostgreSQL 18 lab](labs/045-cross-join-self-join.sql): commit `ab6084efce7a98c9ce2b0cb7d4eb7a2069d9959a`.
- README navigation: commit `e66b24edbf1e9e38593be6237e68781d31171204`.
- Chapter, lab and README fetched from GitHub main; fixture/cardinality assertions reviewed by static reasoning. **Independent editorial review pending; comprehensive static SQL/link QA pending; PostgreSQL 18 runtime execution not performed, evidence pending.**
- **Published 45/120 (37.5%); 75 remaining; Part 05 5/10. Next: Chapter 046 — Multi-table joins and join condition design.**

## Chapter 046 publication evidence (2026-11-10)

- [Chapter 046](part-05-joins/046-multi-table-joins-and-join-condition-design.md): commit `f1d878b607ff05f3e04e0dd6afd51ce32f05e6a9`.
- [Lab 046](labs/046-multi-table-joins-condition-design.sql): commit `18abddd3cfe2e4a51e30d0f9e4d906f889c35bdf`.
- [README navigation](README.md): commit `5fa2c0b62903e5de69d7703a2e9e5dea8f0cb76d`.
- Both new files re-fetched from GitHub `main`. Targeted static reasoning inspected joins, fixture totals, assertions, temporary-table isolation and rollback. **No independent editorial review, comprehensive syntax/link QA, or actual PostgreSQL 18 runtime execution completed.** Runtime evidence pending.
- **Next:** Chapter 047 — One-to-many and many-to-many relationships.

## Chapter 047 publication evidence (2026-11-10)

- [Chapter 047](part-05-joins/047-one-to-many-and-many-to-many-relationships.md): commit `b850bafed28bc11a9a8dc390dfb6742affd43c10`.
- [PostgreSQL 18 lab](labs/047-one-to-many-many-to-many.sql): commit `c624143b6e0fbcd496ed189052584c0ea09b8d5b`.
- [README navigation](README.md): commit `70cb718a279e5b3a013373ded8120ad07ee5f470`.
- Chapter and lab fetched back from GitHub main; targeted static reasoning checked fixture counts, join cardinality, customer and tag totals, uniqueness assertions, transaction guard and rollback. **No independent editorial review, comprehensive automated syntax/link QA, or isolated PostgreSQL 18 runtime execution completed.** No runtime evidence retained.
- **Published 47/120 (39.2%), 73 remaining; Part 05 7/10. Next: Chapter 048 — Semi-joins and anti-joins using EXISTS and NOT EXISTS.**
