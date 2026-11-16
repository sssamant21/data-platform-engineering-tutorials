# Part 01 local Markdown link-path audit — 2026-11-16

## Scope and provenance

- Repository: `sssamant21/data-platform-engineering-tutorials`; branch: `main`
- Pinned Git tree / commit: `359709679c1ce345b17b8972faddd859873b2fff`; GitHub recursive tree reported `truncated=false`.
- Audited all **10 chapter Markdown files** under `sql-tutorials/part-01-fundamentals/` using GitHub file reads.
- Extracted standard inline Markdown links of the form `[label](target)` and resolved local targets relative to the containing Markdown file, normalizing `..` and `.` against tracked paths in the pinned Git tree.
- **62 local inline link occurrences checked; 0 missing tracked path targets**.
- **0 local fragment/anchor references** were encountered in these 10 chapter files.
- This audit does not cover reference-style links, HTML links, image references, dynamic links, or external HTTP link reachability; it does not establish comprehensive Markdown link/anchor QA across the repository.
- No SQL parser or PostgreSQL runtime was invoked. No independent editorial review was conducted.

## Reproduction

1. Fetch `https://api.github.com/repos/sssamant21/data-platform-engineering-tutorials/git/trees/359709679c1ce345b17b8972faddd859873b2fff?recursive=1` and confirm `truncated=false`.
2. Fetch the 10 `part-01-fundamentals/*.md` blobs from the pinned commit.
3. Extract inline Markdown link targets, excluding external `http:`, `https:`, `mailto:`, and `data:` targets.
4. Percent-decode local paths, resolve against each source file's directory, normalize dot segments, and compare against tracked paths.
5. Record the number of local links and unresolved targets; separately count fragment references.

## Acceptance boundary

**PASS — scoped local inline link path existence (Part 01 only).** Not a pass for full Markdown parsing, anchors across all chapters, SQL semantics, or PostgreSQL 18 execution.

## Next

Expand the audit to Parts 02–12, including Markdown reference-style links and heading anchors; then run parser-based SQL syntax checks and isolated PostgreSQL 18 acceptance with retained execution logs.
