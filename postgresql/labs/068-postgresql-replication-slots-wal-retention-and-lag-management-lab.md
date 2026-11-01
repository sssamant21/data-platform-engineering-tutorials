# Chapter 068 — Replication Slots, WAL Retention and Lag Management Lab

**PostgreSQL 18 · Disposable primary only · Runtime pending**

## 1. Safety

Use the isolated Chapter 004 PostgreSQL 18 primary (127.0.0.1:55432) with its verified system identifier, a new dedicated `ch068_lab` database, the `lab_admin` role, sufficient free disk and a tested backup. Verify that neither `ch068` schema nor `ch068_lab_slot` exists. All writes are forbidden on any production, shared, CDC or active-standby cluster. Establish a small WAL budget and stop immediately if WAL disk usage rises unexpectedly.

## 2. Read-only baseline

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/068-slot-and-lag-inspect.sql
```

Record wal_level, max_replication_slots, max_slot_wal_keep_size, wal_keep_size, free disk, pg_stat_wal.wal_bytes and slot inventory.

## 3. Create a uniquely named LAB slot

On the verified Chapter 004 primary, have the operator create a new **empty** `ch068_lab` database after checking that it does not already exist. Capture the actual cluster system identifier in the private lab log; do not guess it. Then execute only the gated setup script:

~~~bash
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch068_lab \
  -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v confirm_stage=068-CREATE-SLOT \
  -f postgresql/labs/sql/068-safe-slot-setup.sql
~~~

The guard refuses wrong cluster, role, IP, port, data directory, PostgreSQL major, existing schema or slot, or missing approval token. A physical slot is cluster-scoped and retains WAL immediately. **Never create it on a shared cluster.** No cleanup has been run by this tutorial.

## 4. Generate bounded WAL and measure

Generate a single bounded 1,000-row fixture **only on the dedicated lab database**; `CREATE IF NOT EXISTS` and `ON CONFLICT DO NOTHING` have deliberately been removed to refuse reuse of a preexisting table or rows:

~~~bash
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch068_lab \
  -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v confirm_stage=068-GENERATE-WAL \
  -f postgresql/labs/sql/068-safe-wal-workload.sql
~~~

Run only on a dedicated lab primary. The slot has no consumer, so retained bytes may grow. Record WAL generation rate from pg_stat_wal over an interval and calculate time-to-risk using the worksheet.

## 5. Decision and recovery simulation

Document: owner, consumer identity, slot state, safe_wal_size, WAL bytes retained, free disk, archive status, expected reinitialization effort and whether deletion is permitted. In this lab, there is **no real consumer**, so only the lab slot may be cleaned up after verifying identity.

## 6. Cleanup — lab slot only

```sql
SELECT slot_name,slot_type,active FROM pg_replication_slots
WHERE slot_name='ch068_lab_slot';
```

If, and only if, the disposable cluster identity, dedicated database, `ch068.wal_probe` fixture, inactive physical slot, and explicit cleanup approval have been independently checked, execute the **separate guarded** cleanup:

~~~bash
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch068_lab \
  -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v confirm_stage=068-DROP-LAB-SLOT \
  -f postgresql/labs/sql/068-safe-slot-cleanup.sql
~~~

The cleanup intentionally does **not** use `DROP TABLE IF EXISTS`, `DROP SCHEMA CASCADE`, or automatic database deletion. A failure can leave a partial lab fixture; preserve evidence and review manually instead of blindly retrying. Dropping a slot permanently removes its WAL retention protection—never run this on a production, CDC or shared slot.

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
