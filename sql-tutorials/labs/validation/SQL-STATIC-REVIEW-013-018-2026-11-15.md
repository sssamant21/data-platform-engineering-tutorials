# SQL static review — Chapters 013–018 (2026-11-15)

**Scope:** Targeted manual SQL reasoning against the six `main` branch lab files listed below. **No SQL executed; no PostgreSQL 18 instance used.** This is not independent editorial review, comprehensive syntax validation, or runtime acceptance.

| Chapter | Lab | Static expected-result reasoning | Result |
|---|---|---|---|
| 013 — NULL and three-valued logic | [013](../013-null-three-valued-logic.sql) | NULL statuses 402/406; four non-NULL amounts sum to 115; `NOT IN` with NULL yields UNKNOWN; NULL-safe inequality includes 402/403/404/406 | No contradiction found |
| 014 — IN, BETWEEN and ranges | [014](../014-in-between-range-predicates.sql) | Membership 501/502/503/506; inclusive 50–100 gives 502/503/504; half-open Nov 1 gives 501/502/503; reversed BETWEEN yields zero | No contradiction found |
| 015 — LIKE and ILIKE | [015](../015-like-wildcards-ilike.sql) | Case-sensitive prefix A gives 101/104/106; ILIKE al gives 101/102/106; escaped percent gives 102/104; escaped underscore gives 104; single-character wildcard matches 101/103 | No contradiction found |
| 016 — DISTINCT | [016](../016-distinct-duplicate-handling.sql) | Six rows, five non-NULL regions, two distinct non-NULL regions, three categories including NULL, four region/status pairs, repeated customer 101 | No contradiction found |
| 017 — deterministic sorting | [017](../017-order-by-deterministic-sorting.sql) | Priority/time/ID order 102/103/105/101/106/104; explicit unresolved-first 101/103/106/104/102/105; C-collation service order api/billing/ingest | No contradiction found |
| 018 — pagination | [018](../018-limit-offset-fetch-top.sql) | First page 201/202; OFFSET page 203/204; keyset 205/206; severity 1 ties produce 202/203/206 | No contradiction found |

## Scope and safeguards

- Read six complete SQL files from GitHub `main`; inspected their inline `VALUES` datasets, expected comments, SQL predicates, and assertion expressions.
- All six use `BEGIN READ ONLY`, end in `ROLLBACK`, use synthetic inline data, and check PostgreSQL major version 18 and database name `sql_tutorials`.
- **Finding QA-004 (improvement):** Chapter 013 lacks the `SET LOCAL statement_timeout = '10s'` used in Chapters 014–018. Add it before runtime execution; the omission does not establish a semantic error in the sample queries.
- Database-name and version checks are **not proof of isolation**; verify container, connection target, credentials, and disposable dataset independently.
- Assertion queries use division-by-zero failure conditions; `psql -X -v ON_ERROR_STOP=1` is required to propagate failure. Static reasoning cannot prove PostgreSQL optimizer behavior, parsing, or runtime output.
- The PostgreSQL-specific `ILIKE`, `COLLATE "C"`, `NULLS FIRST`, and `LIMIT` forms are not universal portable SQL. Chapter 018's T-SQL `TOP` is discussed, not executed in PostgreSQL.
- External documentation URLs and Markdown anchors were not tested. No changes outside `sql-tutorials/`.

## Next acceptance milestones

1. Review SQL labs 019–024, recording exact expected results and any semantic defects.
2. Fix QA-004 and perform comprehensive Markdown-aware links/anchors and SQL syntax checks.
3. Execute only in an independently verified isolated PostgreSQL **18** environment, preserve command, container identity, server version, SQL file SHA, stdout/stderr, exit code, and cleanup evidence before marking runtime-validated.
4. Independent editorial review remains **0/120**; isolated PostgreSQL 18 runtime validation remains **0/120**.
