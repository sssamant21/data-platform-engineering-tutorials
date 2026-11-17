# SQL Tutorials README — scoped local link-path audit (2026-11-17)

## Source and method

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Git tree SHA at inspection: `04c363603dd40e2a6a05c5996475a8608b27d187`; recursive tree reported `truncated=false`.
- Inspected: `sql-tutorials/README.md` (47,626 characters).
- Extracted Markdown-style inline link destinations using the pattern `\]\(([^)]+)\)`, excluded HTTP(S), mailto, and fragment-only destinations, stripped query/fragment components, and checked remaining paths against the complete tracked Git tree.
- This was a **scoped pattern-based inspection**, not the published parser-aware checker. Complex Markdown destinations, escaped parentheses, reference-style links, raw HTML links, rendered anchors, external URL availability, and SQL correctness were not verified.

## Result

| Measure | Result |
|---|---:|
| Local README inline link paths checked | 232 |
| Missing tracked targets found | 0 |
| Complete Git tree | Yes (not truncated) |
| Parser-aware checker executed | No |
| PostgreSQL 18 SQL executed | No |

## Acceptance boundary

This result supports only the existence of the 232 identified local tracked paths at the inspected Git tree. It does not establish comprehensive Markdown correctness, independent editorial review, SQL syntax or expected-output correctness, or PostgreSQL 18 runtime validation.

## Next milestone

Execute `sql-tutorials/labs/validation/check_markdown_links.py --json sql-tutorials/labs/validation/markdown-qa-results.json` from a complete checkout with `markdown-it-py>=3,<5`, retain reproducible JSON output and commit SHA, triage any findings, then advance SQL parser/expected-output and isolated PostgreSQL 18 runtime QA.
