# Chapters 085–090 — targeted Markdown structural QA (2026-11-14)

## Scope and method
Read current `main` Master TOC, README, STATUS-TRACKER, six Part 09 Markdown chapters and their six corresponding PostgreSQL 18 SQL labs through the GitHub connector. Counted physical lines, ATX heading lines, line-start backtick-fence candidates, and inline Markdown local/external link patterns. Inspected SQL labs textually for `BEGIN`, `ROLLBACK`, `READ ONLY`, `statement_timeout`, and PostgreSQL version references. These are **heuristic textual checks**, not parser-based link/anchor verification, SQL execution, or safety certification.

| Chapter | Markdown lines | ATX headings | Fence candidates | Inline local links | Inline external links |
|---|---:|---:|---:|---:|---:|
| 085 | 121 | 8 | 6 | 9 | 5 |
| 086 | 121 | 8 | 6 | 8 | 5 |
| 087 | 113 | 8 | 6 | 6 | 5 |
| 088 | 120 | 8 | 8 | 7 | 5 |
| 089 | 148 | 11 | 12 | 8 | 5 |
| 090 | 130 | 8 | 6 | 10 | 6 |
| **Total** | **753** | **51** | **44** | **48** | **31** |

All six chapters had even line-start fence candidate counts; this alone does not establish valid Markdown. Six SQL labs were inspected (72, 73, 49, 62, 82, 94 lines; **432 lines total**). Each contained textual `BEGIN`, `ROLLBACK`, `READ ONLY`, `statement_timeout`, and version references. The presence of these strings does not prove they are correctly applied.

## Corrections published on main
- Chapter 087: link directly to published 088; commit `1f0ce2089a94d0a2fa4c854a528968ae7c4ea1ed`.
- Chapter 088: link directly to published 089; commit `fd7404f4b91f34a870c541c6bb27547416f2594e`.
- Chapter 089: link directly to published 090; commit `598d0f103a1d633c67f5afc6fe58f22712f1741a`.
- Chapter 090: remove outdated “planned” status from linked published 091; commit `2db9a5f405aa52e2245f613716934e6db3ec81dc`.

## Validation boundaries and follow-up
- Authored and published: **120/120** (per existing curriculum and index).
- Targeted structural text-audit coverage after this batch: **90/120**.
- Earlier targeted local-file path smoke coverage: **120/120** (not repeated here).
- Independent editorial review: **0/120**.
- Actually executed isolated PostgreSQL 18 runtime acceptance: **0/120**. **No SQL executed in this batch.**
- External HTTP links, Markdown anchors, comprehensive local links, SQL syntax, expected result values, security claims and safe execution remain **unverified**.
- Next: Chapters 091–096 targeted structural QA, comprehensive parser-based Markdown and SQL review, then isolated PostgreSQL 18 runtime acceptance with reproducible evidence.
