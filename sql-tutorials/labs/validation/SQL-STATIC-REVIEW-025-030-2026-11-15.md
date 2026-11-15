# SQL static review — Chapters 025–030 (2026-11-15)

## Scope and method
Read current `main` versions of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six Part 03 chapters and their six matching SQL labs. Manually inspected SQL text, synthetic inputs, expected arithmetic, negative-test exception handling, portability labels and guardrails. **No SQL was executed; no PostgreSQL 18 runtime acceptance or independent editorial certification is claimed.** This is a targeted source-based review, not comprehensive parsing or full Markdown anchor resolution.

| Chapter | Lab | Targeted reasoning and expected outputs |
|---|---|---|
| 025 Foreign keys | `../025-foreign-keys-referential-integrity.sql` | 3 customers; 4 orders; 0 orphans; 75.00 total; customer 1 has 2 orders. Child insert and referenced parent delete should raise 23503 and are caught narrowly. |
| 026 NOT NULL/CHECK/DEFAULT | `../026-not-null-check-default-validation.sql` | 3 valid rows, 1 queued, attempts sum 3; 3 invalid synthetic legacy rows. Expected 23502 and 23514 violations are caught narrowly. |
| 027 Identity/sequences/generated | `../027-identity-sequences-generated-values.sql` | ALWAYS identity IDs 100,101,102 and overridden 999; BY DEFAULT identity IDs 1,500; generated totals 25.00 + 21.75 = 46.75; temporary sequence 10 then 15. Expected explicit ALWAYS ID rejection SQLSTATE 428C9; duplicate PK 23505. |
| 028 ALTER TABLE | `../028-alter-table-safe-schema-changes.sql` | 2 existing rows backfilled to legacy, 1 new default batch row; amount sum 24.75; no NULL ingestion source; expected 23514 and 23505 rejections. |
| 029 Normalization | `../029-normalization-1nf-3nf-denormalization.sql` | 2 customers, 2 products, 2 orders, 3 order lines; total 85.00; order 100=60.00 and 101=25.00; cached total drift for order 100=5.00, exactly one mismatched cached row. |
| 030 Normalized schema lab | `../030-lab-03-normalized-operational-schema.sql` | 2 customers, 2 products, 2 orders, 3 lines; ORD-001=55.00, ORD-002=30.00, total 85.00; historical order-line price 10.00. |

## Findings and limitations
- No contradiction identified in the *targeted* expected-output arithmetic and entity counts.
- Chapters 025–028 and 030 execute temporary DDL/DML, with explicit transaction boundaries, timeouts, server/database checks and final ROLLBACK; Chapter 029 uses BEGIN READ ONLY and synthetic VALUES. They are **not safe to run on shared/production systems merely because of these checks**. Confirm disposable container/host, credentials and network target independently.
- Chapter 027 correctly warns that sequence allocation is not transactionally reversible; its temporary sequence is created inside the rollback-only transaction. PostgreSQL 18 behavior, exception SQLSTATE handling, identity/sequence semantics and expected notices still require actual isolated execution.
- SQL syntax and semantics were reviewed by reading source only. No parser, live PostgreSQL instance, complete Markdown anchor checker or independent reviewer was used. External reference URLs were not tested.
- A textual `ROLLBACK` is not a guarantee of cleanup if execution is interrupted; preserve connection and cleanup evidence in runtime acceptance.

## Acceptance backlog
1. Next targeted SQL semantic and expected-output review: Chapters **031–036**.
2. Run complete Markdown-aware path/anchor and SQL syntax checks; track failures individually.
3. Execute labs in a verified isolated disposable PostgreSQL **18** instance with `psql -X -v ON_ERROR_STOP=1`, capture `SELECT version()`, target identity, full stdout/stderr, exit status, and cleanup verification. Do not mark runtime validated until evidence exists.
4. Obtain independent editorial review separately.

**Status after this review:** authored/published 120/120; targeted structural QA 120/120 (previously reported); targeted SQL static expected-output review 30/120; independent editorial 0/120; actual PostgreSQL 18 runtime 0/120.
