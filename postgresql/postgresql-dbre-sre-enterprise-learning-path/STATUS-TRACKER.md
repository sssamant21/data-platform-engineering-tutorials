# Progress and Validation Tracker

**Status date:** 2026-11-06

| Metric | Current state |
|---|---|
| Curriculum planned | 20/20 chapters |
| Chapter lessons authored | 20/20 |
| Chapter-specific labs authored | 20/20 |
| Semantic source reviews | 20/20 documented (not independently approved) |
| Documentation baseline | PostgreSQL 18 (effective 2026-11-06) — [policy](POSTGRESQL-18-BASELINE.md) |
| Version-pinned lesson/lab documentation links | Migrated to PostgreSQL 18 where present; exhaustive endpoint/anchor and semantic verification pending |
| Existing lab target | PostgreSQL 17; migration to 18 pending per lab |
| PostgreSQL 18 runtime-validated labs | 0/20 |
| Chapter inline-link inventories | 20/20 documented; exhaustive resolution pending |
| Runtime validation | 0/20 completed |
| Enterprise / production certification | Not assessed |

## Chapter status

| Chapter | Content | Lab | Runtime evidence | Review |
|---|---|---|---|---|
| 01 | Authored | Written | Not executed | Pending |
| 02 | Authored | Written | Not executed | Pending |
| 03 | Authored | Written | Not executed | Pending |
| 04 | Authored | Written | Not executed | Pending |
| 05 | Authored | Written | Not executed | Pending |
| 06 | Authored | Written | Not executed | Pending |
| 07 | Authored | Written | Not executed | Pending |
| 08 | Authored | Written | Not executed | Pending |
| 09 | Authored | Written | Not executed | Pending |
| 10 | Authored | Written | Not executed | Pending |
| 11 | Authored | Written | Not executed | Pending |
| 12 | Authored | Written | Not executed | Pending |
| 13 | Authored | Written | Not executed | Pending |
| 14 | Authored | Written | Not executed | Pending |
| 15 | Authored | Written | Not executed | Pending |
| 16 | Authored | Written | Not executed | Pending |
| 17 | Authored | Written | Not executed | Pending |
| 18 | Authored | Written | Not executed | Pending |
| 19 | Authored | Written | Not executed | Pending |
| 20 | Authored | Written | Not executed | Pending |

## Quality gates

1. **Content authored:** concept explanation, prerequisites, step-by-step instructions and expected result.
2. **Static review:** link, Markdown, SQL/shell syntax and risk-pattern checks.
3. **Runtime verified:** actual commands executed with sanitized evidence, version details, and observations.
4. **Independent review:** a second reviewer approves technical accuracy and safe usage.
5. **Production readiness:** separately scoped, with explicit change management, staging tests, and platform-owner approvals; not implied by course completion.

## Next chapter

**All 20 chapters authored; semantic source reviews recorded for all 20.** The existing [semantic review progress log](validation/semantic-review-progress.md) inventories inline Markdown links across Chapters 02–20, with partial targeted external checks. Chapter 01 and supporting-document ordinary inline links have also been inventoried; targeted non-inline syntax scans cover all 20 chapter/lab pairs. These completed inventories are recorded in [reference-resolution-audit.md](validation/reference-resolution-audit.md), and must not be repeated as unfinished inventory work. These inventories do not establish link-target, HTTP redirect, or exact HTML-fragment validity. Full parser-aware resolution of relative paths, exact fragment IDs, redirects and remaining external URLs is still pending. Next: complete this reference gate and address recorded Docker ownership/cleanup and negative-test assertion safeguards. Use the [PostgreSQL 18 baseline and lab migration policy](POSTGRESQL-18-BASELINE.md) for future technical references, then update each legacy PostgreSQL 17 lab safely to 18 and execute it in an approved isolated runtime with genuine recorded evidence. The PostgreSQL 18 Docker PGDATA/volume layout differs from 17. Obtain independent review after testing. Do not interpret link inventory or semantic review as runtime validation.

## Important

This tracker belongs only to the 20-chapter enterprise learning path. The existing 100-chapter PostgreSQL tutorial has its own independent [progress tracker](../PROGRESS.md).
