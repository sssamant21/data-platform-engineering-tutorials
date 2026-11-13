# Markdown local-target smoke check — Chapters 001–006 (2026-11-13)

## Scope and source

GitHub `main` recursive tree SHA: `f9ed726705b56055c988d9a0990f9b5e9bf1cd20` (GitHub tree response `truncated=false`). The six chapter files were fetched from `main` during this check. This is a **targeted smoke test**, not the full Markdown link/anchor audit.

## Method

For each of Chapters 001–006, extract Markdown inline links matching `[label](destination)` (including image form), ignore external HTTP(S), mailto and fragment-only destinations, resolve the local path relative to the chapter directory, normalize `.` and `..`, and check exact case-sensitive path membership in the GitHub tree. No files were changed by the check.

## Results

| Chapter | Local links checked | Missing target paths |
|---|---:|---:|
| 001 | 4 | 0 |
| 002 | 4 | 0 |
| 003 | 6 | 0 |
| 004 | 5 | 0 |
| 005 | 6 | 0 |
| 006 | 9 | 0 |
| **Total** | **34** | **0** |

**Result: PASS for the limited local inline-link target-existence check across six chapters.**

## Limits and outstanding gates

This check does **not** validate heading anchors/fragments, reference-style links, URLs embedded in code, external links, percent-encoded edge cases, all Markdown syntax, or chapters 007–120. It is not comprehensive static QA, editorial certification, SQL syntax checking, expected-output verification, or PostgreSQL 18 runtime execution. Counts remain: 120/120 published, 0/120 independently reviewed, 0/120 PostgreSQL 18 runtime-validated.

## Next

Implement or run the comprehensive pinned-SHA Markdown parser specified in [the link QA plan](MARKDOWN-LINK-QA-PLAN-2026-11-13.md), including anchor and reference-link checks; publish defects with exact source lines and rerun after corrections. Then audit SQL safety/syntax and execute isolated PostgreSQL 18 labs with retained evidence.
