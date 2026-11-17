# Part 10 — Targeted Markdown fragment and fence QA (2026-11-16)

## Scope and method
Read `sql-tutorials/MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, and the ten chapter Markdown files 091–100 directly from GitHub `main`. Identified chapter paths from README links. Inspected inline Markdown link destinations containing `#`, lines beginning with triple-backtick fence markers, and lines matching reference-style definition patterns.

## Observations
- Chapters inspected: **10/10** (091–100).
- Inline fragment-bearing destinations: **1**, an **external** PostgreSQL documentation URL in Chapter 099 (`https://www.postgresql.org/docs/18/functions-comparisons.html#ROW-WISE-COMPARISON`).
- **Local** fragment-bearing destinations: **0**. No local anchor resolution was required in this narrow scan.
- Triple-backtick fence-marker counts by chapter: 091=4, 092=6, 093=10, 094=10, 095=10, 096=10, 097=10, 098=10, 099=6, 100=6. All counts even; this is **not** proof of balanced CommonMark fences.
- Reference-style link definition lines matching `^\\s*\\[[^\\]]+\\]:`: **0**.

## Limitations and next steps
This is a **targeted text-pattern static inspection**, not CommonMark/GFM parser validation. It does not prove heading-slug resolution, nested/tilde fence correctness, inline links within escaped contexts, external URL availability, SQL syntax, expected query outputs, or PostgreSQL 18 execution. No production credentials or databases were accessed. No SQL was executed.

Curriculum state (from tracker): 120/120 chapters authored/published; 120/120 previously reported targeted SQL static reviews and scoped link-path audits; 0/120 independent editorial reviews; 0/120 isolated PostgreSQL 18 runtime validations.

**Next:** parser-aware Markdown QA across all 120 chapters, then SQL syntax/expected-output validation and reproducible isolated PostgreSQL 18 runtime acceptance.
