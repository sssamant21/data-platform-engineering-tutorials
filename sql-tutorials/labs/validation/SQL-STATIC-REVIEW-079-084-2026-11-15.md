# Targeted SQL static review — Chapters 079–084 (2026-11-15)

## Scope and method
Reviewed the current `main` versions of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six chapter Markdown files (079–084) and their six companion SQL files. Inspected synthetic input rows, SQL expression semantics, expected multisets and fail-closed assertions by source-based reasoning. **No PostgreSQL SQL execution, parser-based verification, independent editorial review, or full Markdown anchor/link validation was performed.** The assertions are authored, not execution evidence.

## Chapter-by-chapter observations

| Chapter | Targeted checks and reasoning | Outcome |
|---|---|---|
| 079 — Cohort retention | Six users, ten events; cohort sizes 3/2/1 by Monday starting Jan 5/12/19; retention 3→2→1, 2→1, 1; seven assertion predicates, bidirectional EXCEPT ALL | No discrepancy identified statically |
| 080 — Customer activity capstone | Four customers, seven events, five purchases, 115 total spend; Aster/Birch tied at 50, Cedar 15, Dune 0; row-number 1–4 and dense-rank 1/1/2/3; sequencing and cumulative checks | No discrepancy identified statically |
| 081 — Strings/regex | Five records; two valid, two invalid, one missing case-sensitive codes; lowercase/trim, NULL behavior, masking and exact expected multiset | No discrepancy identified statically |
| 082 — Temporal/DST | 2026-03-08 06:30 UTC maps to 01:30 New York, 07:30 UTC to 03:30 after DST switch; March 9 00:00 UTC maps to March 8 20:00; elapsed hour vs wall-clock jump | No discrepancy identified statically |
| 083 — Numeric precision | Raw total 30.100, rounded total 30.10, per-line rounded sum 30.11; integer quotient 2, numeric quotient 2.5; NULL denominator and numeric rounding semantics | No discrepancy identified statically |
| 084 — JSON | Four events, three non-SQL-NULL JSON payloads, two API, one file, two tags; one explicit JSON null, one absent priority key, one SQL NULL payload; exact multiset checks | No discrepancy identified statically |

## Safety and limits
All six companion labs use synthetic inline `VALUES` datasets and `READ ONLY` transaction boundaries, with timeout and database/version guards (Chapter 084 uses a single combined guard). No production connection or credentials were used. Database-name and version checks **do not establish independent isolation**; operators must separately verify the disposable PostgreSQL 18 endpoint and credentials before executing. Chapter 084 does not include the `psql` `ON_ERROR_STOP` meta-command found in the other five labs; run it with `psql -X -v ON_ERROR_STOP=1` to stop on SQL errors. No runtime success is claimed.

## Outstanding acceptance work
1. Next targeted semantic/expected-output review: Chapters **085–090**.
2. Full repository Markdown-aware relative-link and heading-anchor validation, parser-based SQL syntax checks, and review of external references.
3. Independently verified isolated PostgreSQL **18** runtime execution, with recorded version, connection identity, commands, outputs, failure cases and reproducible evidence.
4. Independent editorial review and issue tracking. These remain separate from targeted static reasoning.

**Coverage after this batch (previously reported + this batch):** authored/published 120/120; targeted structural QA 120/120 (previously reported); targeted SQL semantic/expected-output static review **84/120**; independent editorial review 0/120; actual isolated PostgreSQL 18 runtime validation 0/120.
