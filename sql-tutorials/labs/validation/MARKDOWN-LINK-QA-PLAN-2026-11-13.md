# Markdown link and anchor QA — execution plan (2026-11-13)

Baseline: 120 published chapters and 120 SQL labs. Earlier inventory checked 232 README relative links, not chapter anchors.

## Reproducible audit
1. Pin main SHA with git rev-parse HEAD.
2. Enumerate all Markdown under sql-tutorials/.
3. Parse inline, reference-style, and image links, excluding code fences and inline code.
4. Resolve paths relative to each source file and check case-sensitive existence.
5. Resolve fragment identifiers against GitHub heading slugs, repeated-heading suffixes and explicit anchors.
6. Record source file, line, link, defect class, SHA, timestamp, command and exit code.
7. Fix verified defects only; rerun the entire audit.

## Acceptance
All local targets and anchors resolve; undefined reference links are absent. Check external URLs separately. Never equate static link success with SQL correctness, independent editorial review or PostgreSQL 18 runtime acceptance.

## Current state
Plan recorded; full chapter-level link and anchor audit **not executed**. Prior README-only target check passed. Independent review 0/120; PostgreSQL 18 runtime validation 0/120.

## Next
Run pinned comprehensive link audit, publish defect evidence, then SQL syntax/safety/expected-output checks and isolated PostgreSQL 18 runtime acceptance.
