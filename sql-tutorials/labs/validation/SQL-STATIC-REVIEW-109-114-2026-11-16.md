# SQL static review — Chapters 109–114 (2026-11-16)

**Scope:** Six published chapter Markdown files and six matching SQL labs on `main`. This is targeted source inspection and manually calculated expected-output review, **not** parser validation, independent editorial review, full link/anchor audit, or actual PostgreSQL 18 execution.

## Findings by chapter

| Chapter | Static expected-result checks | Boundary |
|---|---|---|
| 109 — Slow-query triage | Six observations; three >= 500 ms; two blocked; one plan-review; exact six-row classifications | Fictional samples; no measured latency, monitoring or actual incident |
| 110 — Incident/recovery decision | Four samples; three slow; two blocked; one plan-review; recovery gates accept drill_a only; source/target each 3 rows and 90.00, with one source-only and one target-only row; closure BLOCK | No real backup restore, failover, lock contention or approved RPO/RTO acceptance |
| 111 — OLTP/OLAP | Five orders; seven order lines; header and line totals 170.00; naive fan-out total 260.00; East 3/95.00, West 2/75.00 | Inline synthetic CTEs, not physical index or workload benchmarking |
| 112 — Star schema | Four facts; three dimension versions; correct revenue 100.00 (Basic 60.00, Premium 40.00); incorrect natural-key join six rows and 170.00; no missing/invalid version matches | Does not create persistent facts, dimensions, keys or SCD enforcement |
| 113 — Incremental CDC | Five delivered events, four distinct, three latest keys, two active keys totaling 80.00, one delete tombstone, zero exact-result differences | Does not test durable offsets, ordering guarantees, retries, actual MERGE or ingestion |
| 114 — Warehouse cost | Four orders, six lines; East and West 100.00 each; correct 200.00; duplicated join 270.00, 70.00 overcount; exact region checks | No warehouse billing, scan-volume, optimizer or cloud-cost measurement |

No arithmetic contradiction identified in these *targeted* calculations. The SQL scripts' version/database guards and `BEGIN READ ONLY` are not proof of independent isolation. Run only with independently verified disposable PostgreSQL 18 credentials and `psql -X -v ON_ERROR_STOP=1`. Chapter 109's SQL does not set `ON_ERROR_STOP` internally, so the CLI flag is mandatory.

## Correction

Chapter 109's navigation still called Chapter 110 “planned” despite publication. Replaced with a relative link to its published successor in commit `09a7baa04127379d80f2c98c3819af8b10b510cd`.

## QA state

- Authored/published: **120/120** (previously reported; no new chapter authored).
- Previously reported targeted structural QA: **120/120**.
- Cumulative targeted SQL source/expected-output review: **114/120 (95%)**.
- Independent editorial review: **0/120**.
- Actually isolated PostgreSQL 18 runtime validated: **0/120**.
- Comprehensive Markdown link/anchor audit and parser-based SQL validation: **pending**.

## Next

Review Chapters **115–120**, then run repository-wide Markdown link/anchor and SQL parser checks. Isolated PostgreSQL 18 runtime acceptance must retain executable commands, version and isolation proof, actual outputs, pass/fail summaries and sanitized evidence. Real DBRE/SRE integration acceptance (monitoring, recovery, physical indexing, privileges and CDC) must be separately scoped and cannot be inferred from these synthetic labs.
