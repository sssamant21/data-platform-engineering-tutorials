# Targeted Markdown structure and lab-guardrail audit — Chapters 049–054

Date: 2026-11-14. Scope: **sql-tutorials/** only; GitHub `main`.

## Scope and method

Read `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md` on `main`, then fetched the six numbered chapter Markdown files and their six SQL labs via the GitHub connector. Inspected heading and fenced-code delimiter patterns, inline Markdown link references, end-of-chapter navigation, and textual safety patterns. This is **targeted inspection**, not a Markdown parser, a complete link/anchor resolver, independent editorial sign-off, or SQL execution.

| Chapter | Markdown lines (including final newline) | Headings | Opening fence markers | SQL lab |
|---|---:|---:|---:|---|
| 049 | 142 | 13 | 12 | `labs/049-duplicate-rows-fanout-null-join-pitfalls.sql` |
| 050 | 160 | 13 | 6 | `labs/050-lab-05-consolidate-customers-orders-payments.sql` |
| 051 | 141 | 13 | 10 | `labs/051-count-sum-avg-min-max.sql` |
| 052 | 183 | 13 | 16 | `labs/052-group-by-aggregation-grain.sql` |
| 053 | 203 | 18 | 16 | `labs/053-having-versus-where.sql` |
| 054 | 153 | 13 | 8 | `labs/054-conditional-aggregation-case-filter.sql` |
| **Total** | **982** | **83** | **68 delimiter lines** | **6 labs** |

All six Markdown files have an even number of line-start code-fence markers. This does **not** prove valid nesting, language tags, or correct Markdown rendering. Inline Markdown links were enumerated; **external destinations were not tested** and a complete relative-path/anchor resolver was not run in this pass. Previous targeted local-path smoke evidence is a separate limited check.

## Findings and corrections

- Chapter 049's final next-chapter navigation linked only to the Master TOC; changed it to a direct relative link to the already-published Chapter 050. The Chapter 050 filename is corroborated by the README chapter index.
- Chapters 050–054 still link successor references to the Master TOC in some concluding paragraphs. These are functional navigation choices, not confirmed broken links; future editorial navigation consistency review may improve them.
- No independent reviewer sign-off or execution transcript was produced.

## SQL lab guardrail text review

All six fetched lab SQL files contain `BEGIN;`, `ROLLBACK;`, a PostgreSQL 18 server-version guard, a disposable database guard, `CREATE TEMP` fixture use, `RAISE EXCEPTION` assertions, and local timeout settings. These are **textual observations only**; transaction behavior, assertions, exact expected outputs, database identity, and safety are **not runtime certified**. SQL is PostgreSQL-specific and must not be treated as portable SQL without adaptation.

## Remaining acceptance work

1. Markdown-aware parsing, all local links and anchors, and external reference checks.
2. Semantic SQL review: verify aggregate grain, NULL handling, fan-out, numeric expectations, and failure behavior.
3. Execute each lab against an **isolated PostgreSQL 18** instance with synthetic data, capturing exact version, connection identity, command, exit status, output, and rollback evidence. Never use production credentials.
4. Independent editorial review and tracked issue closure.

**State after this pass:** Authored/published 120/120 (as recorded in repository tracker); targeted structural QA 54/120 including this batch; independent editorial review 0/120; actual isolated PostgreSQL 18 runtime validation 0/120. Next structural batch: **055–060**.
