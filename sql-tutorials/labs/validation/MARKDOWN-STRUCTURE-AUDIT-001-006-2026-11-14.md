# Markdown structural audit — Chapters 001–006 (2026-11-14)

## Scope and method

Read current `main` copies of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, and the six numbered Part 01 chapter Markdown files. Counted Markdown ATX headings, literal fenced-code delimiters, inline Markdown links, external HTTP(S) links, and link fragments. Inspected reference-link definition occurrences. This is a **targeted textual structural audit**, not a full CommonMark parser, heading-slug validator, SQL parser, external-link checker, editorial review, or database execution.

| Chapter | Lines | Headings | Fence delimiter lines | Balanced by count | Local inline links | External inline links | Fragment links |
|---|---:|---:|---:|---|---:|---:|---:|
| 001 | 236 | 17 | 10 | yes | 4 | 3 | 0 |
| 002 | 262 | 19 | 12 | yes | 4 | 7 | 0 |
| 003 | 218 | 10 | 26 | yes | 6 | 5 | 0 |
| 004 | 185 | 9 | 14 | yes | 5 | 5 | 0 |
| 005 | 232 | 15 | 14 | yes | 6 | 4 | 0 |
| 006 | 196 | 14 | 8 | yes | 9 | 4 | 0 |
| **Total** | **1329** | **84** | **84** | **6/6** | **34** | **28** | **0** |

No reference-style link definitions were found by the line-start definition pattern in these six files. There were no inline fragment targets to test in this batch. The 34 local inline links were previously checked for tracked-file existence in [the initial path smoke test](MARKDOWN-LINK-SMOKE-001-006-2026-11-13.md); this run did **not** reverify target paths against a complete Git tree. An even number of fence lines is only a heuristic: nesting, language correctness and Markdown rendering have not been independently verified.

## Reproducibility: inspected chapter blob SHAs

| Chapter | Blob SHA |
|---|---|
| 001 | `3055e7d46e408b1714a287c0a720aea6a802eaa7` |
| 002 | `afb1f435c248034f0bcc07b8432b26a3cf530891` |
| 003 | `d1117cf59f015e24b0eeca8a83468590f7fdb285` |
| 004 | `995eab74c4ed23ba47e965e8ad39357a5477a8a4` |
| 005 | `fd63989bdfb8a654c93bbb65134cc2df5db01e2d` |
| 006 | `2c8a724ce983dfa537846770154aa956db30fcef` |

## Acceptance boundaries and next steps

- Authored/published chapters: **120/120** per repository tracker; no new chapter was authored.
- Targeted local-file path smoke checks: **120/120** previously reported; this is a distinct structural check, **not** 120/120 comprehensive Markdown QA.
- Targeted structural audit: **6/120** chapters.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**. No SQL executed or database contacted in this run.
- Next: repeat structural checks for Chapters 007–012; implement Markdown-aware parsing and full heading-anchor/reference resolution across the curriculum; review SQL syntax, expected results, and lab safety; then execute isolated PostgreSQL 18 labs and preserve version, commands, outputs and cleanup evidence.

No files outside `sql-tutorials/` were changed.
