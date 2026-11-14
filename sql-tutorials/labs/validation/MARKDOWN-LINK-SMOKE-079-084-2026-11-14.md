# Targeted Markdown local-link smoke check — Chapters 079–084

**Date:** 2026-11-14  
**Repository:** `sssamant21/data-platform-engineering-tutorials`  
**Branch:** `main`  
**Baseline complete Git tree SHA:** `f46834713a8b93850c3b6eca5c94a6899ac2a5d4`  
**Tree response truncated:** `false`

## Scope and method

Read the current `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, and six chapter Markdown files 079–084 from `main`. The TOC and tracker state 120/120 chapters are published; therefore authoring is paused for QA.

Extracted inline Markdown link destinations from the six chapter files; excluded external HTTP(S) links and fragment-only links from file-existence checks. For local links, removed URL fragments and query strings, decoded percent escapes, and resolved `.` and `..` relative to each source chapter directory. Compared each normalized path against the non-truncated Git tree inventory from the baseline commit. This is a **targeted inline-link path-existence smoke check**, not a full Markdown parser or heading-anchor audit.

| Chapter | Local inline link occurrences | External HTTP(S) occurrences |
|---|---:|---:|
| 079 — Cohort analysis | 9 | 4 |
| 080 — Customer activity lab | 11 | 4 |
| 081 — String functions | 8 | 4 |
| 082 — Dates and time zones | 8 | 4 |
| 083 — Numeric precision | 8 | 4 |
| 084 — JSON queries | 8 | 4 |
| **Total** | **52** | **24** |

**Local targets:** 24 distinct normalized tracked paths; **missing targets: 0**. Each chapter's corresponding SQL lab path exists in the tracked tree.

## Validation boundaries

- **Passed:** targeted inline local-link path existence for Chapters 079–084 against the recorded tree.
- **Not checked:** heading fragments/anchors, reference-style links, images, HTML links, external URL reachability, full Markdown parsing, SQL syntax, expected results, or substantive lab safety.
- **Not executed:** SQL labs; `BEGIN`/`ROLLBACK` text alone is not proof of safety or successful execution.
- **Independent editorial review:** 0/120.
- **Actual isolated PostgreSQL 18 runtime validation:** 0/120; no runtime evidence has been collected.

**Cumulative targeted local-link chapter coverage:** **84/120**, including prior evidence for Chapters 001–078. This figure is smoke coverage only and must not be interpreted as comprehensive static QA.

## Next work

Check Chapters 085–090 inline local-link targets, then continue comprehensive Markdown and heading-anchor QA, SQL syntax and expected-output review, lab-safety analysis, and isolated PostgreSQL 18 runtime acceptance with reproducible command, version, exit code, and output evidence. Do not change production systems or use real data.
