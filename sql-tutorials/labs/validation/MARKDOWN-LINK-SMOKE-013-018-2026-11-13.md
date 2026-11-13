# Markdown local-link smoke test — Chapters 013–018

Date: 2026-11-13. Branch: `main`. Pinned recursive Git tree SHA: `c106089a06628e0743ba32723cbecdb3b01207ee` (`truncated=false`).

## Method

Fetched `sql-tutorials/README.md` and Chapters 013–018 directly from GitHub `main`. Extracted inline Markdown links matching `[label](target)` in each chapter. For local links, removed any fragment, resolved `.` and `..` relative to the chapter directory, and checked target existence against the pinned recursive Git tree. Repeated occurrences were counted separately. External HTTP(S) links were counted, not tested.

| Chapter | Local link occurrences | Missing local paths |
|---|---:|---:|
| 013 | 9 | 0 |
| 014 | 9 | 0 |
| 015 | 10 | 0 |
| 016 | 10 | 0 |
| 017 | 10 | 0 |
| 018 | 10 | 0 |
| **Total** | **58** | **0** |

25 external HTTP(S) link occurrences were identified but not checked.

## Scope and limitations

**PASS for the targeted inline local-path smoke test only.** This is not comprehensive Markdown parsing: reference-style links, HTML links, fragments/heading slugs, code-fence exclusion, external URL reachability, and all remaining chapters have not been verified by this test. No SQL execution or independent editorial review occurred. Published curriculum: 120/120; independently reviewed: 0/120; actual isolated PostgreSQL 18 runtime-validated: 0/120.

## Next

Continue Chapters 019–024 local-link smoke testing; implement repository-wide Markdown-aware path and anchor validation, then SQL syntax/expected-output/lab-safety QA and isolated PostgreSQL 18 runtime acceptance with reproducible evidence.
