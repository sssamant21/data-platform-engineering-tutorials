# Part 09 — scoped Markdown link-path audit (2026-11-16)

## Scope and reproducibility

- Repository: `sssamant21/data-platform-engineering-tutorials`; branch: `main`.
- Pinned Git tree before this evidence commit: `f49ac2cff79d31c9f3c2222cd8c0c4bca99ee80b` (`truncated=false`; 1,694 entries).
- Chapter Markdown files inspected: `sql-tutorials/part-09-functions-views-json/081-*.md` through `090-*.md` (all ten tracked chapter files).
- Procedure: retrieve each complete Markdown file via GitHub connector; extract inline Markdown destinations using a scoped regular-expression scan; normalize relative paths (including `..`) against the containing file; URL-decode target paths; compare with all tracked paths from the complete recursive tree. Inventory external HTTP(S) destinations and fragments separately.

## Findings

| Metric | Result |
|---|---:|
| Chapter files inspected | 10 |
| Local inline Markdown link-path occurrences | 83 |
| Missing tracked local target paths | **0** |
| External HTTP(S) link occurrences (not fetched/tested) | 47 |
| Local fragment-link occurrences | 9 |
| Reference-style link definitions detected by scoped pattern | 0 |

Nine fragment-link occurrences in Chapters 081–086 point to `../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data`. The corresponding Part 09 heading is present in `MASTER-TOC.md`, but GitHub-rendered anchor resolution was **not** tested.

Local link-path occurrences by chapter: 081=8; 082=8; 083=8; 084=8; 085=9; 086=8; 087=7; 088=8; 089=9; 090=10.

## Limitations and next steps

This is a **scoped inline Markdown link-path existence audit**, not comprehensive Markdown parsing. It does not validate rendered anchors, image links, autolinks, reference-style usages, external URLs, SQL syntax, expected outputs, or PostgreSQL runtime behavior. Regex-based extraction can miss complex Markdown constructs.

Authored/published chapters: **120/120**. Previously reported targeted SQL static review: **120/120**. Cumulative scoped link-path audit after this part: **90/120** (Parts 01–09). Independent editorial review: **0/120**. Actual isolated PostgreSQL 18 runtime validation: **0/120**.

Next: Part 10 (091–100) scoped link audit; Parts 11–12; comprehensive parser-based Markdown and SQL validation; isolated PostgreSQL 18 runtime acceptance with reproducible evidence. No SQL or production access was used for this audit.
