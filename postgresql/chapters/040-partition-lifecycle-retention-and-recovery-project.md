# Chapter 040 — Partition Lifecycle, Retention and Recovery Project

**PostgreSQL 18 · DBRE/SRE Capstone · Status: Draft, runtime validation pending**

## Mission

Operate a monthly partitioned event table through future partition creation, late-arriving data, pruning verification, approved retention, archive validation and recovery. This capstone builds on Chapters 038 and 039.

## Lifecycle design

Ingestion routes by UTC event_time into nonoverlapping monthly RANGE partitions. Future partitions must exist before new data arrives. A late event within a retained partition is accepted; an event outside all bounds is rejected unless a DEFAULT partition exists. DEFAULT routing can mask missing partitions and complicate later attachment.

## Preflight

Capture parent/child bounds, indexes, row counts, storage, query plans, retention approvals, replicas, replication slots, backups, long transactions and disk/WAL headroom. Partition bounds are lower-inclusive and upper-exclusive. Review unique-key rules: partitioned-table unique constraints must include the partition key.

## Retention and recovery

1. Confirm the exact expired partition and approved retention cutoff.
2. Detach one partition in a controlled change window; it remains a standalone table with its data.
3. Verify detached row counts, schema and representative records.
4. Create a controlled archive and independently test restoration into a disposable database. A successful dump alone does not prove recoverability.
5. Reattach the retained table as the recovery drill; verify counts, routing and EXPLAIN pruning.
6. Remove old data only after archive verification, dependency review and explicit approval.

Production DETACH PARTITION CONCURRENTLY has PostgreSQL-specific restrictions and cannot run inside a transaction block. ATTACH may scan rows and acquire substantial locks. Never treat partition DROP as an instantly reversible operation.

## Incident scenarios

Missing future partition: inspect insert error and bounds. Unexpected DEFAULT growth: review routing and late-data policy. Detach blocked: inspect locks and long transactions. Reattach fails: inspect bounds and validation constraints without deleting the detached data. Archive mismatch: retain the original and repeat validation. Query regression: inspect pruning, local indexes and statistics.

## SRE acceptance

Record a change ticket with owners, rollback, SLOs, backup/restore evidence, WAL and replica health, retention approval and stop conditions. The [hands-on lab](../labs/040-partition-lifecycle-retention-and-recovery-project-lab.md) demonstrates a safe detach/reattach cycle without deleting the retired partition.

## References

- https://www.postgresql.org/docs/18/ddl-partitioning.html
- https://www.postgresql.org/docs/18/sql-altertable.html
- https://www.postgresql.org/docs/18/app-pgdump.html
- https://www.postgresql.org/docs/18/app-pgrestore.html

**Next:** Chapter 041 — PostgreSQL Backup Architecture and Recovery Objectives.
