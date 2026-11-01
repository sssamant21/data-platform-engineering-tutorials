# PostgreSQL V03 — Chapters 067–070 Streaming and Synchronous Commit Runtime

**State:** Runtime workflow under validation. Certification remains **NOT_CERTIFIED**.  
**Exercise:** Actual PostgreSQL 18 **three-process** (one primary, two physical standbys) streaming and synchronous-commit operations in a single GitHub Actions Docker container with network mode `none` and no published ports. This is NOT three independent hosts or availability zones.

## Acceptance intent

The [disposable streaming/sync runner](v03_ch067_070_streaming_sync_disposable.sh) uses actual `pg_basebackup -R` operations to initialize two physical standby directories, starts each standby on a separate localhost-only port, and checks `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_is_in_recovery()` and data/WAL replay correctness. A bounded batch of 200 inserts demonstrates WAL movement, not a performance or SLO benchmark.

The synchronous-commit exercise captures the original configuration and its owner **before any ALTER SYSTEM**. It enables `FIRST 1 (standby_a, standby_b)`, checks sync-state selection and a `remote_apply` commit; then uses `ANY 2 (...)` to require both standbys. It intentionally stops only one disposable standby to cause a commit to wait with `statement_timeout='2000ms'`. A timeout is **not interpreted as a rollback**. The harness does not blindly retry; it restarts the standby and inspects the original primary and standby for the unique transaction ID. An outcome of 0 or 1 must be explicitly reconciled. The original configuration is restored to the recorded **default/absent auto.conf state** only after proving that state was the baseline in this fresh disposable cluster.

| Gate | Expected proof | Limits |
|---|---|---|
| Runtime isolation | PostgreSQL 18, Docker network=none, no published host ports | Multiple processes share one host and storage control plane |
| Base backup/standby bootstrap | `pg_basebackup -Fp -X stream -R`; two distinct standby PGDATA paths | No external backups or encryption verified |
| Streaming | Both named WAL receivers streaming; at least two sender rows | No real failover |
| WAL replay | Primary marker and 200 bounded rows observable on both standbys | Not a lag SLO benchmark |
| Synchronous FIRST 1 | First named standby is sync, remote_apply transaction visible | Not high-availability service SLO |
| Quorum ANY 2 | Both standbys report quorum; remote_apply record visible | Only synthetic lab |
| Bounded quorum loss | One standby stopped, client timeout recorded, transaction separately reconciled after restart | Timed-out commits may have committed locally |
| Configuration rollback | Original exact empty/default configuration source restored | Only because the disposable baseline was checked |
| HA safety | Exactly one primary and two recovery processes observed | **No external fencing, DCS, routing or promotion** |

## Fail-closed boundaries

No `pg_promote`, `pg_rewind`, production endpoint, cloud API, cross-node fencing action, or application cutover is part of the harness. A service-stop or `pg_is_in_recovery` role check does **not** prove fencing across independent failure domains. **Chapter 070 split-brain prevention and HA-manager acceptance remain NOT VERIFIED / TABLETOP ONLY.** The work here supports Chapter 067 and a subset of Chapter 069 but does not satisfy Chapter 070 operational acceptance.

This runner deliberately does not measure business RPO/RTO, p95 latency, WAL cost over hours, or genuine failover recovery. Synchronous acknowledgment behavior is demonstrated on a shared machine; it does not prove independent durability or disaster resilience. Chapter 068 physical slot guards were separately runtime-tested in [the disposable guard report](V03-CH061-070-DISPOSABLE-GUARD-EVIDENCE.md).

## Evidence and next gate

The [V03 streaming/sync CI workflow](../../.github/workflows/postgresql-v03-ch067-070-streaming-sync.yml) publishes **only sanitized synthetic outcome data**, not source databases or WAL files. A green workflow verifies this limited disposable lab, not the production HA requirements.

**Next required work:** independent PostgreSQL review of synchronous-commit timeout semantics and real independent control-plane fencing, then a distinct staging exercise authorized through change management. Until independent fencing, application traffic routing, recovery objectives and negative-path evidence are demonstrated, leave Chapter 070 and enterprise certification as **NO_GO / NOT_CERTIFIED**.

Chapter 050 V04-G certification remains independently blocked under [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45). Draft PR #46 stays open/unmerged.
