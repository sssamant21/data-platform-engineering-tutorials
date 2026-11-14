# Markdown structural audit — Chapters 025–030 (2026-11-14)

## Scope and method

Target: `main`, `sql-tutorials/part-03-modeling/` Chapters 025–030. Each complete chapter Markdown file was fetched through the GitHub connector. Textual counts use physical newline-separated lines, ATX heading lines matching `^#{1,6} `, backtick fence delimiter candidate lines matching `^\\s*\\`\\`\\``, and inline Markdown link patterns. These are **heuristic checks**, not a Markdown parser or proof of balanced nesting. External HTTP(S) URLs were counted but not requested.

| Chapter | Lines | ATX headings | Fence candidates | Inline local links | Inline external links |
|---|---:|---:|---:|---:|---:|
| 025 | 131 | 8 | 8 | 9 | 4 |
| 026 | 129 | 8 | 8 | 9 | 4 |
| 027 | 122 | 8 | 6 | 9 | 5 |
| 028 | 121 | 9 | 6 | 9 | 4 |
| 029 | 153 | 10 | 6 | 9 | 4 |
| 030 | 120 | 9 | 6 | 13 | 4 |
| **Total** | **776** | **52** | **40** | **58** | **25** |

Each file has an even number of backtick fence candidates. This does not establish fence pairing or complete Markdown validity.

## Findings and corrections

Chapters 025–029 linked their successor labels to `../MASTER-TOC.md` rather than the already-published successor chapter. Corrected the five direct next-chapter links, preserving all chapter text and other tracks.

- 025 → 026: `43f7a8335faee757229d60c58386454a86a4862a`
- 026 → 027: `d9e54a24724b2a67131da903698c95820a185d31`
- 027 → 028: `e08d2177051170ea35b6933140b19acca669d402`
- 028 → 029: `69cf406cff43b12f4a21dfc71565fb6e97d060c2`
- 029 → 030: `489e619ae716ecfd0074091c3d0d68d51807df69`

Corresponding SQL lab paths are recorded in the README. **No SQL was executed**, and no independent editorial certification, SQL syntax/expected-output verification, or full Markdown/anchor validation is claimed. These findings are targeted static inspection only.

## Progress and next acceptance steps

All 120 chapters are published. Limited structural audits now cover **30/120** chapters; prior targeted local-file smoke coverage is **120/120**. Independently reviewed **0/120**; actually executed and validated on isolated PostgreSQL 18 **0/120**.

Next: Chapters 031–036 structural audit; Markdown-aware link/fragment validation; SQL syntax, expected-result and lab safety checks; isolated PostgreSQL 18 execution with captured version, commands, outputs and cleanup evidence. Do not mark runtime-validated until evidence exists.
