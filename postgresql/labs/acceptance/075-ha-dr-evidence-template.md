# Chapter 075 — HA/DR Acceptance Evidence and Signoff

**Status:** NOT EXECUTED / NOT VERIFIED

## Service and environment

- Service:
- PostgreSQL version:
- Region/AZ topology (physical or simulated):
- HA manager / DCS versions:
- Writer endpoint:
- Backup / WAL archive:
- Approved RPO:
- Approved RTO:
- Change ticket:
- Incident commander:
- DBRE / SRE / application / backup owners:

## Test evidence

For each phase A–H, record:

- Phase and UTC start/end:
- Failure injection and isolation boundary:
- Before/after primary identity and WAL timeline:
- DCS quorum and leader lease:
- Independent fencing evidence:
- WAL receive/flush/replay LSN and slot state:
- Writer endpoint and stale-session check:
- Application request IDs and outcomes:
- First successful post-recovery write/read:
- Achieved RPO/RTO:
- Backup/PITR and archive verification:
- Alert receipt and clearance:
- PASS / FAIL / NOT VERIFIED:
- Evidence URLs or attachments:

## Critical safety gates

- [ ] Exactly one writable leader throughout the drill
- [ ] Former leader independently fenced before new writes
- [ ] No unapproved durability downgrade
- [ ] Ambiguous commits reconciled
- [ ] Former primary safely rewound/rebuilt as standby
- [ ] WAL archive, backups and replication restored
- [ ] Application SLOs recovered
- [ ] Physical failure-domain assertions verified separately from simulation

## Decision

- Overall status: NOT VERIFIED
- Exceptions / residual risks:
- Corrective actions and owners:
- DBRE approval:
- SRE approval:
- Application approval:
- DR/change approval:
- Signoff UTC time:

**Do not sign PASS for unexecuted tests or missing fencing evidence.**
