# Markdown local-link smoke check — Chapters 025–030 (2026-11-13)

## Scope and reproducibility

Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
Pinned pre-evidence Git tree: `06641da0aaf4154601b65f7a77016dce3e89e2e2` (non-truncated).
Inspected the complete Markdown source of each chapter 025–030 under `sql-tutorials/part-03-modeling/`. Extracted Markdown inline links matching `[label](target)` (excluding image links), separated HTTP(S) destinations, resolved relative local paths from each chapter's directory, normalized `.` and `..`, and tested path existence against tracked Git tree entries. No file changes or SQL execution.

| Chapter | Inline local links | Missing local paths | External HTTP(S) links identified, not tested |
|---|---:|---:|---:|
| 025 — Foreign keys | 9 | 0 | 4 |
| 026 — NOT NULL, CHECK, DEFAULT | 9 | 0 | 4 |
| 027 — Identity and sequences | 9 | 0 | 5 |
| 028 — ALTER TABLE | 9 | 0 | 4 |
| 029 — Normalization | 9 | 0 | 4 |
| 030 — Normalized schema lab | 13 | 0 | 4 |
| **Total** | **58** | **0** | **25** |

## Acceptance and limits

**PASS — targeted local inline-link path existence (025–030).** All 58 checked local-link occurrences resolve to tracked files. Repeated links count as occurrences, not unique destinations. This is not a full Markdown parser: reference-style links, angle-bracket autolinks, encoded paths, anchors/heading slugs, external HTTP responses, and dynamically generated links were not checked. No editorial certification, SQL correctness check, or PostgreSQL 18 runtime validation is claimed.

Cumulative targeted local-link smoke-check coverage: **30/120 chapters** (001–030), based on earlier evidence for 001–024. Next: 031–036 local-link smoke check, then comprehensive Markdown link/anchor audit, SQL syntax and expected-output review, lab-safety checks, and isolated PostgreSQL 18 runtime acceptance with retained evidence.
