# Chapter 037 — Table and Index Maintenance Strategy

**Baseline:** PostgreSQL 18. **Status:** Draft; runtime validation pending.

## Decision framework

Use ANALYZE for stale planner statistics; VACUUM for dead-tuple cleanup and freezing; REINDEX CONCURRENTLY only for evidenced index maintenance needs with sufficient disk/WAL; and reserve VACUUM FULL or CLUSTER for approved table rewrites with explicit lock and outage budgets. A large table or index alone is not evidence of bloat.

## Operational checklist

Capture relation sizes, vacuum timestamps, dead-tuple estimates, index definitions and validity, query plans, oldest transactions, XID/multixact ages, replica lag, WAL retention and storage headroom. Review constraints before index retirement. Distinguish estimated statistics from measured storage. Avoid disabling autovacuum or cancelling anti-wraparound vacuum.

## Change process

1. Establish query SLO and baseline evidence.
2. Choose least disruptive effective maintenance.
3. Review locks, disk, WAL, replication, backups, rollback and change approval.
4. Execute bounded maintenance and observe progress and application errors.
5. Compare query plans, latency, space, freeze age and replica health.
6. Record the result and prevention plan.

## Hands-on lab

See [Chapter 037 lab](../labs/037-table-and-index-maintenance-strategy-lab.md) for a disposable synthetic table, bounded churn, ANALYZE and VACUUM comparisons, and a maintenance decision worksheet.

## References

- https://www.postgresql.org/docs/18/routine-vacuuming.html
- https://www.postgresql.org/docs/18/sql-vacuum.html
- https://www.postgresql.org/docs/18/sql-reindex.html
- https://www.postgresql.org/docs/18/sql-cluster.html

**Next:** Chapter 038 — Table Partitioning Fundamentals and Operational Tradeoffs.
