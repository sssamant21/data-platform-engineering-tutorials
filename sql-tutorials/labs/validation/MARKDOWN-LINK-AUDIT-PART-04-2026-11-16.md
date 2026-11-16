# Part 04 — Scoped Markdown Link-Path Audit (2026-11-16)

## Scope and method

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Baseline Git tree SHA: `cf6d594f1517e8d87b7e9ea22a4c7e4b8525022e`, recursive tree `truncated=false`.
- Inspected all ten existing Part 04 Markdown chapter files, 031–040, retrieved from `main`.
- Enumerated inline Markdown links matching `[label](target)` (excluding image links), resolved relative paths from each source file directory, normalized `.` and `..`, URL-decoded path components, and checked resolved targets against tracked paths in the complete Git tree.
- HTTP(S) links were inventoried, not fetched. This scoped regex audit does not fully parse Markdown, verify reference-style links, validate anchors or check external URL availability.

## Results

| Chapter | Local inline links checked | External HTTP(S) links inventoried | Missing tracked local targets |
|---|---:|---:|---:|
| 031 | 12 | 4 | 0 |
| 032 | 9 | 4 | 0 |
| 033 | 9 | 4 | 0 |
| 034 | 9 | 5 | 0 |
| 035 | 9 | 5 | 0 |
| 036 | 10 | 5 | 0 |
| 037 | 6 | 6 | 0 |
| 038 | 9 | 7 | 0 |
| 039 | 7 | 4 | 0 |
| 040 | 9 | 5 | 0 |
| **Total** | **89** | **49** | **0** |

No local fragment references were identified by the scoped pattern scan. All 89 checked local inline targets exist as tracked paths in the pinned Git tree. This is **not** evidence that their contents, anchors, or SQL examples are correct.

## Acceptance boundaries and follow-up

- **Authored/published:** 120/120 (existing tracker).
- **Targeted SQL static review:** 120/120 (previously reported, distinct from parser validation).
- **Cumulative scoped local Markdown link-path audits:** 40/120 chapters (Parts 01–04).
- **Independent editorial review:** 0/120.
- **Actual isolated PostgreSQL 18 runtime validation:** 0/120; no SQL executed during this audit.
- **Next:** Part 05 chapters 041–050 scoped link-path audit; subsequently complete Parts 06–12, reference-style and anchor verification, parser-based SQL checks, and isolated PostgreSQL 18 execution with reproducible evidence.

No production data, credentials, or databases were used.