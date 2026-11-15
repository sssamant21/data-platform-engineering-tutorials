# Targeted structural audit — Chapters 091–096 (2026-11-15)

## Scope and method

Read current `main` copies of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, six Part 10 chapter Markdown files, and six matching lab SQL files. This is a limited textual audit, **not** comprehensive Markdown-aware link resolution, semantic SQL review, independent editorial review, or PostgreSQL runtime acceptance.

| Chapter | Markdown lines | ATX headings | Line-start backtick fence candidates | Inline local link occurrences | Inline external link occurrences | Lab SQL lines |
|---|---:|---:|---:|---:|---:|---:|
| 091 | 114 | 8 | 4 | 6 | 4 | 88 |
| 092 | 121 | 11 | 6 | 7 | 4 | 66 |
| 093 | 142 | 12 | 10 | 8 | 6 | 98 |
| 094 | 157 | 12 | 10 | 8 | 5 | 118 |
| 095 | 149 | 12 | 10 | 8 | 5 | 128 |
| 096 | 161 | 13 | 10 | 8 | 6 | 84 |
| **Total** | **844** | **68** | **50** | **45** | **30** | **582** |

All chapter files had even counts of line-start backtick fence candidates; this does not prove Markdown fence correctness. No obvious stale successor-publication wording matched the limited search (`not yet published`, `will be published`, `planned chapter`, `coming soon`). All six SQL files contained textual `BEGIN`, `ROLLBACK`, `READ ONLY`, `statement_timeout`, and PostgreSQL/version indicators. Presence of strings does not prove guardrails are effective or that SQL executes safely.

## Validation states

- Authored/published: 120/120, as reported by current `main` curriculum index and tracker.
- Targeted structural audit: 96/120 cumulative, including this batch; limited scope only.
- Previously reported targeted local path smoke checks: 120/120; not re-executed here.
- Independently editorially reviewed: 0/120.
- Actually PostgreSQL 18 runtime validated: 0/120. **No SQL was executed in this audit.**
- External URLs, heading anchors, comprehensive Markdown parsing, SQL syntax and expected outputs, and lab safety certification: pending.

## Next

Inspect Chapters 097–102 and corresponding labs; then perform comprehensive Markdown-aware link/anchor checking, semantic SQL and expected-output verification, and isolated PostgreSQL 18 runtime acceptance with reproducible logs and explicit version/database identity. Do not use production credentials or systems.
