# SQL Tutorials — repository tree and README target inventory (2026-11-13)

## Evidence and scope

Read GitHub `main` recursive tree at tree SHA `7c985eee50a7807d935aa82a5c7c207f1417c6af` (`truncated=false`), and fetched `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md`. All checks below are **static inventory checks**, not PostgreSQL execution or comprehensive Markdown QA.

## Observed results

| Check | Result |
|---|---:|
| Tracked files under `sql-tutorials/` | 246 |
| Numbered chapter Markdown files under `part-*/` | 120 |
| Unique chapter IDs in 001–120 | 120 |
| Missing chapter IDs | 0 |
| Duplicate chapter IDs | 0 |
| Tracked `.sql` files | 120 |
| Local relative link occurrences in README | 232 |
| README local link targets absent from tracked tree | 0 |
| Git tree response truncated | No |

The 120 SQL files are an inventory count, **not** a verified one-to-one chapter-to-lab mapping. README link check resolves relative paths from `sql-tutorials/` against the tracked tree; it does **not** verify anchors, links in other Markdown documents, case-normalization edge cases, or SQL code correctness.

## Reproducible method

1. GET `https://api.github.com/repos/sssamant21/data-platform-engineering-tutorials/git/trees/main?recursive=1`; record returned tree SHA and `truncated`.
2. Filter blob paths with prefix `sql-tutorials/`. Identify chapter paths matching `part-*/[0-9][0-9][0-9]-*.md`; parse three-digit prefixes, compare with 001–120, and check duplicates.
3. Count paths ending in `.sql`.
4. Fetch `sql-tutorials/README.md` from `main`; extract Markdown inline links, exclude absolute HTTP(S), mailto and fragment-only links, strip fragments, and resolve each relative target from `sql-tutorials/`. Compare against the tracked file paths.

## Remaining gates

- Resolve links and anchors **inside all 120 chapters**, labs documentation and other Markdown files; review image references and reference-style links.
- Inspect SQL files and fenced snippets for dialect correctness, destructive commands, isolation guards and expected-result assertions.
- Execute approved labs on a dedicated disposable PostgreSQL 18 instance; retain database version, command, exit code, stdout/stderr, timestamp and commit SHA.
- Independent editorial review and cross-engine testing remain pending.

**Status:** 120/120 authored and published; targeted tree/README inventory PASS; repository-wide link QA pending; SQL static QA pending; independently reviewed 0/120; PostgreSQL 18 runtime-validated 0/120.
