# Progress and Validation Tracker

**Status date:** 2026-11-05

| Metric | Current state |
|---|---|
| Curriculum planned | 20/20 chapters |
| Chapter lessons authored | 20/20 |
| Chapter-specific labs authored | 20/20 |
| Semantic source reviews | 20/20 documented (not independently approved) |
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

**All 20 chapters authored; semantic source reviews recorded for all 20.** The existing [semantic review progress log](validation/semantic-review-progress.md) inventories inline Markdown links across Chapters 02–20, with partial targeted external checks. The Chapter 01 and supporting-file links, reference-style definitions, anchors, raw HTML/autolinks, redirects and remaining external URLs still need exhaustive verification. Next: complete this reference gate and address recorded Docker ownership/cleanup and negative-test assertion safeguards. Only then execute approved, isolated PostgreSQL 17 labs and obtain independent review. Do not interpret link inventory or semantic review as runtime validation.

## Important

This tracker belongs only to the 20-chapter enterprise learning path. The existing 100-chapter PostgreSQL tutorial has its own independent [progress tracker](../PROGRESS.md).
