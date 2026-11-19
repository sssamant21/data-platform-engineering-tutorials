# Complete-checkout Markdown and SQL acceptance — execution runbook

**Status:** Procedure authored; full-checkout execution and PostgreSQL 18 runtime acceptance **not yet performed**. This document is not test evidence.

## Preconditions and isolation

1. Use a disposable workspace. Check out the exact `main` commit and record its full SHA.
2. Do not use production credentials or production databases. For runtime SQL testing, independently verify a disposable PostgreSQL 18 server/container and endpoint; a database-name/version guard alone is insufficient.
3. Install `markdown-it-py>=3,<5` in an isolated Python environment. Preserve Python and dependency versions.
4. Work only inside `sql-tutorials/` when publishing corrections or evidence.

## Phase A — full Markdown and relative-link QA (no database)

From the repository root:

```bash
git fetch origin main
git checkout --detach origin/main
git rev-parse HEAD
python -m venv .venv
. .venv/bin/activate
python -m pip install 'markdown-it-py>=3,<5'
python -m pip freeze
mkdir -p sql-tutorials/labs/validation/evidence
python sql-tutorials/labs/validation/check_markdown_links.py \
  --json sql-tutorials/labs/validation/evidence/markdown-links.json
checker_exit_code=$?
printf 'checker_exit_code=%s\n' "$checker_exit_code" | tee sql-tutorials/labs/validation/evidence/markdown-checker.exit.txt
```

Record the detached HEAD SHA and use that same checkout for both Phase A and A2; do not pull or switch branches between phases. Save the checker exit code immediately, before any other command can overwrite `$?`. A nonzero checker exit must remain a failed QA result even when `tee` succeeds.\n\nThe checker must inspect **all** `sql-tutorials/**/*.md` files and enforce unique chapter numbering 001–120. Review `issues` and `limitations` in the JSON. A zero exit code is a scoped static result, **not** editorial acceptance, external-link availability, or SQL correctness. Investigate all missing paths, fragments, and image sources. Raw HTML links, GitHub-specific anchor edge cases, and external HTTP(S) URLs require separate checks. Do not publish a passing result when the checker was not run on a complete checkout.

Record a companion `evidence/markdown-run-metadata.json` with: UTC timestamp, repository, full commit SHA, Python version, markdown-it-py version, exact command, exit code, number of Markdown files and chapter files, issue count, reviewer, and unresolved limitations. Do not hand-populate observed results before execution.

## Phase A2 — execute checker regression tests (synthetic, no database)

After Phase A dependencies are installed, run the existing regression suite separately:

```bash
python -m unittest sql-tutorials/labs/validation/test_check_markdown_links.py -v \
  > sql-tutorials/labs/validation/evidence/markdown-regression.stdout.log 2> sql-tutorials/labs/validation/evidence/markdown-regression.stderr.log
regression_exit_code=$?
printf 'regression_exit_code=%s\n' "$regression_exit_code" | tee sql-tutorials/labs/validation/evidence/markdown-regression.exit.txt
```

Retain the exact command, exit code, stdout/stderr, Python/dependency versions, pinned repository SHA, and UTC execution timestamp. Count tests from the actual runner output; the number of authored test methods is not evidence that they executed or passed. A regression pass validates checker behavior on synthetic fixtures only, not the real repository's links. Do not continue to report full Markdown QA as passing unless **both** the checker and regression suite have successful recorded exits and findings are resolved. Use a fresh isolated workspace and review evidence before committing it.

## Phase B — SQL source and expected-output review

Enumerate `sql-tutorials/labs/*.sql` and link each numbered lab to its chapter. Inspect every SQL file for: dialect/version annotations, psql-only commands, expected row counts and deterministic ordering, synthetic fixtures, read-only versus rollback-only transaction behavior, timeouts, `ON_ERROR_STOP`, and fail-closed isolation checks. Flag unsafe `COMMIT`, external connections, unqualified writes, and claims of runtime success without logs. Review SQL blocks embedded in chapter Markdown separately; static parsing alone is not execution.

Record findings per chapter with file path, line number, severity, expected behavior, and proposed fix. Keep a distinct status for *source inspected*, *static syntax reviewed*, *expected output reviewed*, *editorially accepted*, and *runtime executed*.

## Phase C — isolated PostgreSQL 18 runtime acceptance

Provision a fresh, disposable PostgreSQL 18 instance with synthetic datasets only. Independently verify container identity, server address, port, `SELECT version()`, `current_database()`, `current_user`, and the absence of production network access before invoking any lab. Use least-privilege test credentials and fail-closed `psql -X -v ON_ERROR_STOP=1`. Never point a lab at a shared or production server. Record command, exit code, stdout/stderr, schema/setup fixture SHA, assertions, cleanup, and server version for each lab. Rollback-only labs must end with no persisted changes; prove this with before/after assertions. Treat any mismatch as a failed test, not a pass.

Only increment PostgreSQL 18 runtime-validated chapter counts after actual execution on the isolated instance and retention of reproducible evidence. Do not infer validation from source inspection or `psql` directives.

## Acceptance and publication

Publish evidence and issue fixes exclusively under `sql-tutorials/`. Re-fetch changed paths from `main` and record exact commit SHAs. Update `STATUS-TRACKER.md` **after** evidence is retained and verified. If checkout, Docker, or PostgreSQL 18 is unavailable, leave the relevant phase **pending** and record the blocker; never fabricate JSON results or runtime logs.
