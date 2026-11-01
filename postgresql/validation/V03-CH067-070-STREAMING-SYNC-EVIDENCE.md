# PostgreSQL V03 — Chapters 067–070 Streaming and Synchronous Commit Runtime

**State:** **42/42 real PostgreSQL 18 disposable runtime checks PASS**, [successful CI #41311860442](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41311860442). Certification remains **NOT_CERTIFIED**.  
**Exercise:** Actual PostgreSQL 18 **three-process** (one primary, two physical standbys) streaming and synchronous-commit operations in a single GitHub Actions Docker container with network mode `none` and no published ports. This is NOT three independent hosts or availability zones.

## Acceptance intent

The [disposable streaming/sync runner](v03_ch067_070_streaming_sync_disposable.sh) uses actual `pg_basebackup -R` operations to initialize two physical standby directories, starts each standby on a separate localhost-only port, and checks `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_is_in_recovery()` and data/WAL replay correctness. A bounded batch of 200 inserts demonstrates WAL movement, not a performance or SLO benchmark.

The synchronous-commit exercise captures the original configuration and its owner **before any ALTER SYSTEM**. It enables `FIRST 1 (standby_a, standby_b)`, checks sync-state selection and a `remote_apply` commit; then uses `ANY 2 (...)` to require both standbys. It stops one disposable standby to require a second acknowledgement, configures `statement_timeout='2000ms'`, and independently observes the primary backend's `SyncRep` wait. An earlier test assumed the server timeout would bound the acknowledgement wait, stalled, and was cancelled by CI. The corrected harness imposes a separate **9-second client deadline** and treats a lost acknowledgement as an **unknown commit outcome, never a rollback**. After restarting the disconnected standby, the harness queries the unique transaction ID on the primary and the restarted standby without blindly retrying; 0 or 1 records must be reconciled consistently. The original configuration is restored to the recorded **default/absent auto.conf state** only after proving that state was the baseline in this fresh disposable cluster.

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

The [V03 streaming/sync CI workflow](../../.github/workflows/postgresql-v03-ch067-070-streaming-sync.yml) publishes **only sanitized synthetic outcome data**, not source databases or WAL files. The corrected-head [GitHub Actions workflow #41311860442](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41311860442) **completed successfully with 42/42 actual SQL and infrastructure checks**. Its evidence includes an observed `SyncRep` wait, enforced client deadline, return of both quorum standbys, transaction reconciliation and exact original setting restoration. A green workflow verifies this limited disposable lab, not production HA requirements.

**Next required work:** independent PostgreSQL review of synchronous-commit timeout semantics and real independent control-plane fencing, then a distinct staging exercise authorized through change management. Until independent fencing, application traffic routing, recovery objectives and negative-path evidence are demonstrated, leave Chapter 070 and enterprise certification as **NO_GO / NOT_CERTIFIED**.

Chapter 050 V04-G certification remains independently blocked under [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45). Draft PR #46 stays open/unmerged.
