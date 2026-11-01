# PostgreSQL V02-D — Chapters 061–070 Phase Two Safety Remediation

**Scope:** Existing PostgreSQL 18 tutorial chapters and labs 061–067, 070.  
**State:** Static review and guarded example remediation only. **No database was contacted, no backup or slot was taken, no HA failover or PITR was run.** All lab runtime execution and independent sign-off remain PENDING.

## Findings addressed

| ID | Severity | Scope | Change | Runtime proof |
|---|---|---|---|---|
| PG-V02D-064 | HIGH | PITR lab fixture and UTC restore target | Replaced CREATE IF NOT EXISTS with one-time staged, identity-bound transactional fixture; recorded timezone-aware commit bracketing; archive and backup commands stop on failure | PENDING |
| PG-V02D-066 | HIGH | DR capstone fixture and WAL archive | Removed silent CREATE IF NOT EXISTS and ON CONFLICT DO NOTHING, added system ID/PGDATA/role/stage validation and transaction boundary; ensure archived WAL available before PITR | PENDING |
| PG-V02D-070 | HIGH | HA switchover marker and split-brain | Replaced silent public-schema marker reuse with one-time ch070 schema/table and system-ID-scoped stage; strengthened independent fencing/no-quorum tabletop condition | PENDING |
| PG-V02D-061/062 | MEDIUM | Logical backup file collision | Reject preexisting dump or directory archive; abort if pg_dump/pg_restore/TOC operations fail | PENDING |
| PG-V02D-063 | MEDIUM | Physical backup and isolated restored instance | Refuse existing base backup directory; verify readiness, query and shutdown exit codes | PENDING |
| PG-V02D-065 | MEDIUM | Time-named backup collision | Refuse overwrite if generated dump path already exists | PENDING |
| PG-V02D-067 | REVIEWED | Replication standby setup | Retained documented isolation, empty PGDATA, secure -R review and failover fencing requirements | PENDING |

All scripts with physical effects require an **operator-supplied, independently verified cluster system identifier, data directory, lab role and explicit stage token**. They verify PostgreSQL 18, primary role, expected disposable database and unused one-time schema. These are **defense-in-depth safeguards**; user-supplied identity fields alone do not prove the host is non-production. An authorized operator must verify network/DCS/PGDATA ownership and resource isolation before executing anything.

### PITR exactness

PITR must use a recovery point that lies **after the source base backup finished**, and strictly between the first confirmed committed transaction and the second modification. The source client records timezone-aware timestamps with an explicit offset; using AT TIME ZONE 'UTC' in a display can strip the offset and produce a misleading timestamp. Retain the original WAL archive and complete timeline history. A successful pg_switch_wal or pg_verifybackup alone does not prove the archive chain can meet RPO/RTO.

Official references:
- [PostgreSQL 18 continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [pg_basebackup options](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [pg_control_system cluster identifier](https://www.postgresql.org/docs/18/functions-info.html)

### Evidence and automation boundary

The [phase-two offline test suite](test_v02d_ch061_070_phase2.py) checks script identity gates, one-time fixture structure, failure exits, prior config restoration from phase one, no silent reruns, and continued explicit PENDING lab status. The [new offline workflow](../../.github/workflows/postgresql-v02d-ch061-070-phase2.yml) must pass; the preexisting V01/V02 checks must also be reviewed against the new commit.

**Remaining:** Execute fixture guards and their refusal scenarios against an isolated disposable PostgreSQL 18 lab; check actual WAL/PITR behavior and archive targets; test backup file refusal and true HA-manager fencing; independently review examples and scored outcomes. Production and authorized staging changes are out of scope.

**Separate blocker:** Chapter 050 V04-G independent staging certification remains BLOCKED under [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45). This PR does not relax or alter that hold.
