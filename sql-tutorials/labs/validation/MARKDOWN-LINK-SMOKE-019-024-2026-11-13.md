# Targeted Markdown local-link smoke check — Chapters 019–024

Date: 2026-11-13
Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`
Pinned Git tree: `df18f97d391800b99db837de7b1a4dcbea8cfcca` (`truncated=false`)

## Scope and method

Fetched all six chapter Markdown files from `main` and a complete recursive Git tree. Extracted inline Markdown link destinations using the pattern `\]\(([^)]+)\)`. Excluded external HTTP(S) URLs, mailto URLs and same-document fragments. Resolved each remaining relative path against its chapter directory, normalizing `..` and `.`, and checked membership in the pinned tracked Git tree.

| Chapter | Local link occurrences | Missing tracked targets | External URL occurrences (not tested) |
|---|---:|---:|---:|
| 019 | 10 | 0 | 4 |
| 020 | 13 | 0 | 4 |
| 021 | 11 | 0 | 3 |
| 022 | 7 | 0 | 6 |
| 023 | 7 | 0 | 5 |
| 024 | 9 | 0 | 4 |
| **Total** | **57** | **0** | **26** |

**Result:** PASS for inline local-link path existence within these six chapters. This expands the previously documented targeted coverage from 001–018 to 001–024.

## Important limits

This regex-based smoke test does **not** parse reference-style links, escaped/complex Markdown destinations, HTML links, or heading fragments; it does not test external URLs or assess whether linked content is semantically correct. It is **not** comprehensive Markdown validation, SQL syntax validation, editorial certification, or PostgreSQL 18 runtime validation.

## Follow-up

1. Continue local-link smoke checks with Chapters 025–030.
2. Run a Markdown-aware repository-wide reference/anchor and external URL audit.
3. Review SQL syntax, calculated expected results and lab safety; run labs only on an isolated PostgreSQL 18 instance with reproducible evidence.
