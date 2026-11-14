# Markdown structural audit — Chapters 007–012 (2026-11-14)

## Scope and method

Read the six chapter Markdown files on GitHub `main` under `sql-tutorials/part-01-fundamentals/` (007–010) and `sql-tutorials/part-02-filtering/` (011–012). Counted physical lines, ATX headings (`#` through `######` followed by a space), fence-opening/closing delimiter candidate lines beginning with triple backticks or tildes, and inline Markdown link matches using a regular expression. Classified HTTP(S) destinations as external, other inline destinations as local, and destinations with a fragment as fragment links. No SQL was executed.

| Chapter | Lines | ATX headings | Fence delimiter candidate lines | Local inline links | External inline links | Local links with fragments |
|---|---:|---:|---:|---:|---:|---:|
| 007 | 209 | 15 | 14 | 7 | 3 | 0 |
| 008 | 171 | 14 | 16 | 7 | 4 | 0 |
| 009 | 161 | 13 | 14 | 7 | 5 | 0 |
| 010 | 134 | 12 | 8 | 7 | 5 | 0 |
| 011 | 168 | 14 | 8 | 7 | 5 | 0 |
| 012 | 172 | 14 | 8 | 10 | 4 | 0 |
| **Total** | **1,015** | **82** | **68** | **45** | **26** | **0** |

All six files have an even number of fence delimiter candidate lines. This is only a *heuristic*: it does not verify valid fence pairing, nesting, code-block language labels, reference-style links, inline HTML, or GitHub heading-anchor generation. Previous targeted local-file-path smoke evidence for 007–012 is recorded in [MARKDOWN-LINK-SMOKE-007-012-2026-11-13.md](MARKDOWN-LINK-SMOKE-007-012-2026-11-13.md); this pass did **not** repeat path-target resolution. External HTTP(S) destinations were counted but **not checked**.

## Findings and limitations

- No odd fence delimiter counts were found in this narrow textual check.
- No local inline fragment links were found in these six files; this does **not** establish global anchor correctness.
- Some navigation wording is stale (for example Chapter 007 describes Chapter 008 as planned, and Chapter 012 labels Chapter 013 planned) even though the full curriculum is published. Track for editorial cleanup; no content changes were made in this pass.
- This is targeted structural static QA only, **not** comprehensive Markdown certification, independent editorial review, SQL syntax/semantic review, expected-output verification, lab-safety certification, or PostgreSQL runtime validation.

## Acceptance state and next work

Authored/published: **120/120**. Targeted local-file-path smoke coverage: **120/120** (prior evidence). Targeted Markdown structural audit coverage after this report: **12/120**. Independently editorially reviewed: **0/120**. Actually executed and runtime-validated on isolated PostgreSQL 18 with retained evidence: **0/120**.

Next: Chapters 013–018 structural audit, then a Markdown-aware link and heading-anchor validator across all 120 chapters, SQL syntax/expected-output and safety review, and isolated PostgreSQL 18 execution with reproducible logs and approvals. Never use production credentials or datasets.
