# Targeted Markdown local-link smoke check — Chapters 031–036

Date: 2026-11-13. Scope: SQL Tutorials Part 04, chapters 031–036, on GitHub main.

## Method

Fetched current `main` versions of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md` and all six chapter Markdown files. Retrieved the recursive GitHub Git tree for `main` (tree SHA `6f74e4a9fe035877d798f457f66193cac7bdc6b5`). Extracted inline Markdown link destinations using a regular expression; separated HTTP(S) references; normalized relative paths with `..` traversal and URL decoding; tested normalized paths for exact membership in the Git tree. Fragment identifiers were stripped and **not validated**. This method does not cover reference-style links, autolinks, images, code fences, dynamic links, or complete Markdown semantics.

| Chapter | Inline local links | Missing tracked paths | External HTTP(S) links (not tested) |
|---|---:|---:|---:|
| 031 | 12 | 0 | 4 |
| 032 | 9 | 0 | 4 |
| 033 | 9 | 0 | 4 |
| 034 | 9 | 0 | 5 |
| 035 | 9 | 0 | 5 |
| 036 | 10 | 0 | 5 |
| **Total** | **58** | **0** | **27** |

## Result and boundaries

**PASS — targeted inline local-path existence only.** All 58 occurrences resolve to tracked Git paths. This is not a full Markdown link/anchor audit, not an external URL availability check, and not SQL syntax or expected-output verification. No PostgreSQL 18 SQL was executed. Independent editorial review remains **0/120**; PostgreSQL 18 runtime validation remains **0/120**.

Cumulative targeted local-path smoke coverage, including previously published 001–030 evidence: **36/120 chapters**. Next: 037–042 targeted local-path checks, followed by comprehensive Markdown/anchor QA, SQL safety and expected-output review, and isolated PostgreSQL 18 runtime acceptance with retained evidence.
