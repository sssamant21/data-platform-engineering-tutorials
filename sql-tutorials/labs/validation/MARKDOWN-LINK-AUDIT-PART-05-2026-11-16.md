# Part 05 — scoped Markdown link-path audit (2026-11-16)

## Scope and method

- Repository: `sssamant21/data-platform-engineering-tutorials`, branch `main`.
- Pinned pre-audit recursive Git tree: `4169bde130e0f53eeb2cb5e56a38c0823672a018`; `truncated=false`, 1,690 entries.
- Files: all ten published Part 05 Markdown chapters (041–050) in `sql-tutorials/part-05-joins/`.
- For each file, enumerated Markdown inline link destinations using a scoped regular-expression scan, resolved relative paths against the chapter directory, normalized `.`/`..`, and compared targets against the pinned tracked tree. Counted external HTTP(S) links separately; did not request them.
- The scan is **not** a complete Markdown parser. It does not validate inline-link syntax with nested parentheses, reference-style links, anchors, external URL reachability, or content semantics.

## Per-chapter results

| Chapter | Local inline links | Missing tracked targets | External HTTP(S) links inventoried |
|---|---:|---:|---:|
| 041 | 8 | 0 | 3 |
| 042 | 7 | 0 | 3 |
| 043 | 6 | 0 | 2 |
| 044 | 5 | 0 | 4 |
| 045 | 5 | 0 | 3 |
| 046 | 5 | 0 | 4 |
| 047 | 6 | 0 | 3 |
| 048 | 6 | 0 | 3 |
| 049 | 7 | 0 | 4 |
| 050 | 6 | 0 | 5 |
| **Total** | **61** | **0** | **34** |

No local fragment destinations or reference-style link definitions were found by the scoped patterns. No missing tracked target was identified. This does **not** certify external links, fragment anchors, reference-style links, or comprehensive Markdown correctness.

## Validation classification

- Authored/published chapters: **120/120** (pre-existing status; no chapter authored this run).
- Targeted SQL static review: **120/120** (previously reported; not repeated here).
- Scoped inline local link-path audits: **50/120** chapters (Parts 01–05).
- Independent editorial review: **0/120**.
- Actually executed isolated PostgreSQL 18 runtime acceptance: **0/120**.
- No SQL executed, no production systems or credentials accessed, and no PostgreSQL runtime claim made.

## Next work

Part 06 (051–060) scoped Markdown audit; then Parts 07–12. Follow with a comprehensive Markdown parser/anchor/reference-style audit, SQL syntax/parser verification, and isolated PostgreSQL 18 runtime acceptance with retained logs, exact version, environment identity, commands, and expected/actual results.
