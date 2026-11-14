# Targeted Markdown local-link smoke check — Chapters 073–078

**Date:** 2026-11-13 (America/New_York)  
**Repository:** `sssamant21/data-platform-engineering-tutorials`, branch `main`  
**Pinned pre-check Git tree:** `4bb55a2b8f87965dec618ee04fe43c29bfd06fda` (GitHub recursive tree response: `truncated=false`)  
**Scope:** `sql-tutorials/part-08-window-functions/` Chapters 073–078 only.

## Method

Read each of the six full chapter Markdown files from `main`. Extract inline Markdown links matching `[label](destination)` (also image-style links), excluding fragment-only and `mailto:` links. Decode percent-encoding, remove URL fragments and queries, normalize relative paths against the chapter directory, and compare each normalized local target with the complete tracked Git tree. Count external HTTP(S) occurrences separately without requesting them. This is a narrow path-existence smoke check, not a complete Markdown parser.

## Results

| Chapter | Local inline link occurrences | Missing tracked targets | External HTTP(S) occurrences (not tested) |
|---|---:|---:|---:|
| 073 — LAG and LEAD | 7 | 0 | 3 |
| 074 — Running totals | 7 | 0 | 3 |
| 075 — Rolling averages | 7 | 0 | 3 |
| 076 — FIRST_VALUE / LAST_VALUE | 5 | 0 | 3 |
| 077 — NTILE / percentiles | 6 | 0 | 3 |
| 078 — Gaps and islands | 4 | 0 | 4 |
| **Total** | **36** | **0** | **19** |

All six numbered chapter files and their corresponding `sql-tutorials/labs/073-*.sql` through `078-*.sql` files exist in the pinned tree. The six SQL lab files were also read to inspect their initial read-only transaction, synthetic data, guardrails and concluding `ROLLBACK`; **they were not executed**. Each begins with `BEGIN READ ONLY`, applies transaction-local timeouts and PostgreSQL version/database-name checks, and ends with `ROLLBACK`. These superficial guardrail observations are not a comprehensive lab-safety or SQL-syntax certification.

## Limitations and pending acceptance

- Does **not** validate reference-style Markdown links, heading anchors, HTML links, external URL reachability, Markdown rendering or complete navigation.
- Does **not** validate SQL syntax, expected outputs, semantic correctness, execution safety or dialect portability.
- **Independent editorial review:** 0/120 confirmed.
- **Actual isolated PostgreSQL 18 runtime validation:** 0/120 confirmed; no SQL execution or reproducible PostgreSQL 18 runtime evidence was produced in this pass.
- **Cumulative targeted local-inline-link coverage:** 78/120 chapters, counting previously recorded 001–072 batches.

**Next:** Chapters 079–084 targeted local-link smoke check; then comprehensive repository-wide Markdown/anchor and SQL/expected-output/safety QA, followed by isolated PostgreSQL 18 runtime acceptance with retained reproducible evidence. Do not count this smoke check as runtime or editorial acceptance.
