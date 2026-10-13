# Chapter 088 — Storage Growth, Retention and Lifecycle Optimization Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Safety and prerequisites

Use a disposable PostgreSQL 18 database with adequate disk space. Capture a backup before any cleanup. Never run destructive partition retention or `VACUUM FULL` against production as part of this lab. Do not delete WAL files manually.

## 2. Establish baseline

Run [088 storage inspection SQL](../labs/sql/088-storage-lifecycle-inspect.sql). Record database/table/index/TOAST sizes, dead tuple estimates, autovacuum history, XID age, WAL/slot/archiver health, filesystem free space and UTC time.

## 3. Controlled data churn

In a disposable database:

```sql
CREATE TABLE public.ch088_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 event_date date NOT NULL,
 payload text NOT NULL
);
INSERT INTO public.ch088_events(event_date,payload)
SELECT current_date - (g % 30),repeat(md5(g::text),10)
FROM generate_series(1,20000) AS g;
UPDATE public.ch088_events SET payload=payload||'changed' WHERE id % 4=0;
DELETE FROM public.ch088_events WHERE id % 10=0;
```

Measure size and estimated dead tuples. Run `VACUUM (ANALYZE) public.ch088_events;` as a separate top-level command; remeasure. Explain why file size may not decrease.

## 4. Partition retention design

Create a separate disposable range-partitioned test table with monthly partitions and test data. Produce a candidate list with partition bounds, age, expected rows, backup/export evidence and hold status. Fill [088 retention manifest](../labs/retention/088-partition-retention-manifest.csv). **Do not drop any partition until an explicit lab approval and verified backup exist.** Demonstrate retention using a tabletop review if approval is unavailable.

## 5. WAL and storage headroom

Collect two timestamped `pg_stat_wal` samples and compute WAL byte deltas, accounting for reset. Inspect replication slots and archiver. Calculate free-space headroom for a hypothetical 4-hour CDC outage and an index rebuild. Record the source of physical volume metrics separately.

## 6. Reclaim method decision

Compare regular VACUUM, REINDEX CONCURRENTLY, VACUUM FULL and partition removal on locking, disk scratch, outage, WAL and reversibility. Do not execute heavyweight rewrites without a separate approved rehearsal.

## 7. Acceptance

Complete [088 scorecard](../labs/acceptance/088-storage-lifecycle-scorecard.csv). Verify application reads, row counts, backups and recovery expectations. Preserve logs and mark unexecuted destructive retention tests NOT VERIFIED.

**Runtime:** pending.
