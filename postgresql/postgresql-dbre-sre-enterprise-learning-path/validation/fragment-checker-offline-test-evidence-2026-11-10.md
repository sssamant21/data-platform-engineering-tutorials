# PostgreSQL 18 fragment checker — offline regression execution evidence

**Execution date:** 2026-11-10 UTC (automation checkpoint)  
**Documentation baseline:** PostgreSQL 18  
**Scope:** independent 20-chapter learning path only  
**Validation class:** offline unit tests of documentation link-checker logic; **not** live documentation HTTP checks or database lab runtime verification.

## Execution and reproducibility

The GitHub `main` sources `validation/check_pg18_fragments.py` and `validation/test_check_pg18_fragments.py` were read before execution. The relevant `IDs`, `TARGETS` and `inspect` logic and nine test cases were transcribed into a temporary local Python test directory because this execution container cannot resolve GitHub DNS. The locally executed code was **reconstructed from inspected source**, not checked out byte-for-byte from GitHub. This limits the result: it demonstrates behavior of the inspected logic, but is **not proof of running the exact GitHub files**.

Command executed in the temporary isolated directory:

```sh
python -m unittest discover -s /tmp/pg18validation -p 'test_check_pg18_fragments.py' -v
```

**Observed:** `Ran 9 tests in 0.011s`; `OK`; nine test methods reported `ok`. Tests exercised exact `id` and named anchors, text-only non-anchors, redirects to PostgreSQL 17 / another PostgreSQL 18 page / another host, non-HTML content, oversized responses, and simulated DNS failure. Network access was mocked; **no live documentation anchors were resolved**.

**Environment constraints:** `git ls-remote https://github.com/sssamant21/data-platform-engineering-tutorials.git HEAD` failed with `Could not resolve host: github.com`. `docker` and `psql` were not found on the execution PATH. No PostgreSQL, Docker, cloud, Kubernetes, or destructive lab operations were run. The temporary test files were not committed as repository source or treated as independent review.

## Remaining gates

1. Execute the **exact repository test file** in a checked-out, network-enabled workspace and retain command output, Python version, and source commit SHA.
2. Run `python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json` from the independent track in a network-enabled environment; inspect and sanitize evidence before committing. A successful unit test does **not** establish actual HTML fragment presence.
3. Finish external-link checks and independent Chapter 15/18 cleanup-safety review.
4. Migrate legacy PostgreSQL 17 lab images/mounts safely, using new PostgreSQL 18 volumes mounted at `/var/lib/postgresql` (default PGDATA `/var/lib/postgresql/18/docker`), then execute only disposable isolated labs and record cleanup proof.

**Statuses unchanged:** authored 20/20; semantic source review recorded 20/20 (not independently approved); PostgreSQL 17 runtime 0/20; PostgreSQL 18 runtime 0/20; independent review and production certification pending. Historical PostgreSQL 17 evidence unchanged.
