# STATUS-TRACKER.md scoped local link-path audit — 2026-11-17

## Source and method

- Source: `sql-tutorials/STATUS-TRACKER.md` on `main`, read during this audit (240,408 characters).
- Complete recursive Git tree: `b35ce3ee038e84698e089da201661419e377b90a` (`truncated=false`).
- Read-only pattern scan of inline Markdown link destinations of the form `[label](target)`, excluding images, external URLs, and fragment-only links.
- Resolve relative paths against `sql-tutorials/`, normalize `.` and `..`, URL-decode path portions, and compare to tracked paths in the Git tree.

## Results

| Check | Result |
|---|---:|
| Local inline link paths examined | 505 |
| Missing tracked file targets | 0 |
| External HTTP(S) links matching pattern | 0 |
| Tree truncated | No |

## Limitations

This is **pattern-based scoped static QA**, not execution of `check_markdown_links.py`. It does not validate GitHub-rendered fragments, reference-style links, angle-bracket destinations, Markdown parser semantics, raw HTML links, external network URLs, SQL syntax, expected query output, or database execution. Counts reflect matching occurrences, not unique destinations. The Git tree SHA is the inspected snapshot; the evidence commit necessarily advances `main` afterward.

## Curriculum and next milestone

Previously reported chapter authorship remains **120/120**. Independent editorial review and actual isolated PostgreSQL 18 runtime acceptance remain **0/120**. Next: run the parser-aware Markdown checker against a full checkout and preserve JSON output, then SQL syntax/expected-output review and isolated PostgreSQL 18 runtime testing. No production database was accessed.
