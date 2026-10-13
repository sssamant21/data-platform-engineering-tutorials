# Chapter 068 — Replication Slots, WAL Retention and Lag Management Lab

**PostgreSQL 18 · Disposable primary only · Runtime pending**

## 1. Safety

Use a dedicated disposable PostgreSQL 18 cluster with enough free disk and a backup. Do not use a production slot, CDC connector or live standby. Establish a small WAL budget and stop immediately if pg_wal disk usage or other workload health deteriorates.

## 2. Read-only baseline

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/068-slot-and-lag-inspect.sql
```

Record wal_level, max_replication_slots, max_slot_wal_keep_size, wal_keep_size, free disk, pg_stat_wal.wal_bytes and slot inventory.

## 3. Create a uniquely named LAB slot

On the disposable primary only:

```sql
SELECT * FROM pg_create_physical_replication_slot('ch068_lab_slot', true);
```

This creates a physical slot and reserves WAL immediately. Verify the slot name is unused and belongs only to this lab. Do not create a slot on a shared cluster.

## 4. Generate bounded WAL and measure

Create a disposable table and generate a **small** bounded workload:

```sql
CREATE TABLE IF NOT EXISTS public.ch068_wal_probe(id integer PRIMARY KEY, payload text NOT NULL);
INSERT INTO public.ch068_wal_probe
SELECT g, repeat('x',100) FROM generate_series(1,1000) AS g
ON CONFLICT (id) DO NOTHING;
SELECT pg_current_wal_lsn();
SELECT slot_name,active,restart_lsn,wal_status,safe_wal_size,
       pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) AS retained_bytes
FROM pg_replication_slots WHERE slot_name='ch068_lab_slot';
```

Run only on a dedicated lab primary. The slot has no consumer, so retained bytes may grow. Record WAL generation rate from pg_stat_wal over an interval and calculate time-to-risk using the worksheet.

## 5. Decision and recovery simulation

Document: owner, consumer identity, slot state, safe_wal_size, WAL bytes retained, free disk, archive status, expected reinitialization effort and whether deletion is permitted. In this lab, there is **no real consumer**, so only the lab slot may be cleaned up after verifying identity.

## 6. Cleanup — lab slot only

```sql
SELECT slot_name,slot_type,active FROM pg_replication_slots
WHERE slot_name='ch068_lab_slot';
```

If and only if the slot is the inactive physical slot created in this lab, run:

```sql
SELECT pg_drop_replication_slot('ch068_lab_slot');
DROP TABLE IF EXISTS public.ch068_wal_probe;
```

Dropping a slot removes its WAL retention protection. Never use this cleanup against a production or CDC slot.

## 7. Acceptance

| Gate | Evidence | Status |
|---|---|---|
| Baseline settings recorded | | Pending |
| Slot ownership confirmed | | Pending |
| Retained WAL measured | | Pending |
| Time-to-risk estimated | | Pending |
| Archiver/standby impact reviewed | | Pending |
| Alert thresholds defined | | Pending |
| Only lab-owned slot removed | | Pending |

**Runtime:** pending.
