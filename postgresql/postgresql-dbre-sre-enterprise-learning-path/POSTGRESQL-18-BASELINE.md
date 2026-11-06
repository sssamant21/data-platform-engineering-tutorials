# PostgreSQL 18 — Documentation Baseline and Lab Migration Policy

**Effective date:** 2026-11-06  
**Applies only to:** `postgresql/postgresql-dbre-sre-enterprise-learning-path/`  
**Decision:** PostgreSQL **18** is the authoritative documentation and technical reference baseline for this independent 20-chapter curriculum.  
**Migration state:** Documentation baseline adopted; existing PostgreSQL 17 labs **not yet migrated or runtime-verified on 18**.

## Authoritative references

- [Official PostgreSQL 18 manual](https://www.postgresql.org/docs/18/index.html)
- [PostgreSQL 18 release notes and migration requirements](https://www.postgresql.org/docs/18/release-18.html)
- [PostgreSQL 18 monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [Official Docker postgres image documentation](https://hub.docker.com/_/postgres)

Use version-pinned `https://www.postgresql.org/docs/18/<topic>.html` references when writing or revising lessons. Avoid `/docs/current/` for reproducibility. The documentation baseline is independent of the installed database minor version, which must be captured during lab execution.

## What is and is not complete

1. **Effective now:** PostgreSQL 18 is the canonical documentation version for fundamentals, administration, SQL, monitoring, performance, backup, recovery, and operations decisions.
2. **Existing legacy material:** Chapters/labs authored for PostgreSQL 17, plus historical semantic reports, remain accurately described as 17-targeted until individually reconciled.
3. **Not yet complete:** Updating every chapter's links and version-sensitive explanations to PostgreSQL 18; changing lab container images, command expectations, and recovery procedures to PostgreSQL 18; executing those labs; independent sign-off.
4. **Do not claim:** PostgreSQL 18 runtime acceptance on the basis of 17 source-level review, link migration or this policy document.

Historical validation reports referencing PostgreSQL 17 should be kept intact as an audit record. New results should explicitly identify `documentation_baseline=18`, the exact server/client versions tested, and whether the test was executed or reviewed only.

## Critical Docker Official Image compatibility change

The **PostgreSQL 18+** official Docker image uses a major-version-specific data directory; for 18, the default `PGDATA` is `/var/lib/postgresql/18/docker` and the image `VOLUME` is `/var/lib/postgresql`. PostgreSQL 17 and older official images commonly use `/var/lib/postgresql/data`.

**Therefore: never globally replace `postgres:17` with `postgres:18` in the existing labs while retaining the old mount target.** Use an entirely new, disposable volume and the correct 18 mount layout; prove persistence and recovery in isolation. Never repurpose, automatically migrate, or delete the original training volume to test the new version.

See [Docker official Postgres image documentation](https://hub.docker.com/_/postgres) and the [Docker PostgreSQL guide](https://docs.docker.com/guides/postgresql/).

## PostgreSQL 18 behavior differences to review

Use the PostgreSQL 18 release notes to review these and any other version-relevant changes before updating commands or expected results:

- PostgreSQL 18 adds asynchronous I/O capabilities that may change query and I/O performance observations.
- PostgreSQL 18 enables data checksums by default during `initdb`, affecting initialization and migration assumptions.
- The planner includes B-tree skip-scan improvements; `EXPLAIN` results and index choices can differ from PostgreSQL 17.
- Backup/restore, WAL, monitoring view columns, vacuum behavior, extensions, locale/collation and client/server compatibility should be checked against version-pinned documentation.
- For managed AWS PostgreSQL and Kubernetes operators, document the actual supported engine/operator versions separately from the tutorial reference version.

## Required migration and validation sequence

1. Inventory the twenty lessons, twenty labs, supporting SQL and YAML, Docker mounts, and `/docs/17/` links.
2. Review each version-sensitive command or statement against the official PostgreSQL 18 manual, then update lessons and references in scoped, auditable changes.
3. Create new **isolated** PostgreSQL 18 lab resources. Pin the major version and record the exact minor version and immutable image digest. Verify Docker context, owner labels, persistent mounts, port use, and resource identity before running commands or cleanup.
4. Test SQL, transactions, indexing and monitoring on PostgreSQL 18, then backup/restore, PITR and replication in explicitly isolated environments with split-brain and data-loss safeguards.
5. Retain sanitized observed output, exit status, measured results, rollback/cleanup proof, and all deviations from the expected results. No inference from PostgreSQL 17 evidence.
6. Update the track's [status tracker](STATUS-TRACKER.md) *only* when actual PostgreSQL 18 evidence exists; obtain independent technical review separately.

## Scope and safety

This baseline policy does **not** modify the separate 100-chapter PostgreSQL tutorials. No live cloud environments, databases or clusters are authorized for testing by this document. AWS and Kubernetes exercises remain optional and may incur cost if provisioned, so no provisioning is implicit.
