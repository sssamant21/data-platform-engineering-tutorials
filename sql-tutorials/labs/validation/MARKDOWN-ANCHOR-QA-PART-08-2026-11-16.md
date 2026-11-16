# Part 08 — Markdown fragment-anchor targeted QA (2026-11-16)

## Scope and provenance

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Read current `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md` from `main` before this check.
- Fetched all ten Part 08 chapter Markdown files (071–080) from `main`.
- Method: inspect inline Markdown destinations containing `#`, exclude external HTTP(S) destinations, compare local `../MASTER-TOC.md#...` fragment slugs with the corresponding Part 08 and Part 09 headings in `MASTER-TOC.md`. This is a **targeted static anchor check**, not a rendered GitHub Markdown parser or full CommonMark audit.

## Findings

| Chapter | Local fragment occurrences | Destination |
|---|---:|---|
| 071 | 1 | Part 08 Master TOC heading |
| 072 | 1 | Part 08 Master TOC heading |
| 073 | 1 | Part 08 Master TOC heading |
| 074 | 1 | Part 08 Master TOC heading |
| 075 | 1 | Part 08 Master TOC heading |
| 076 | 2 | Part 08 Master TOC heading |
| 077 | 3 | Part 08 Master TOC heading |
| 078 | 0 | — |
| 079 | 2 | Part 08 Master TOC heading |
| 080 | 2 | Part 09 Master TOC heading |
| **Total** | **14** | **0 heading/slug mismatches identified** |

Expected GitHub-style heading slugs:

- `part-08--window-functions--advanced-analytics` from `### Part 08 — Window Functions & Advanced Analytics`
- `part-09--sql-objects-functions--semi-structured-data` from `### Part 09 — SQL Objects, Functions & Semi-Structured Data`

These checks support the *likely* correctness of these 14 local fragment targets, but do **not** prove rendered-anchor behavior, check reference-style links or code-fence exclusions comprehensively, or validate external links. The prior scoped link-path audit for Part 08 remains separate evidence; this report must not be counted as a full Markdown parser pass.

## Validation status and next work

- Chapters authored and published: **120/120** (previously recorded).
- Targeted SQL static review: **120/120** (previously recorded; not repeated here).
- Scoped local Markdown path audits: **120/120** (previously recorded; not repeated here).
- Part 08 targeted local fragment check: **14 occurrences checked**, no mismatches identified.
- Independent editorial review: **0/120**.
- Actual isolated PostgreSQL 18 runtime validation: **0/120**. No SQL executed in this run.

Next: systematic parser-aware Markdown QA across the complete curriculum, including reference-style links, fenced-code exclusion, duplicate heading slugs, local paths and fragments, and external URL checks; then SQL parser/expected-output review and isolated PostgreSQL 18 acceptance with reproducible evidence. No production systems or credentials used.
