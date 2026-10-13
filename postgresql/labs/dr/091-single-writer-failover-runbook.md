# Chapter 091 — Single-Writer Failover Runbook

**Status:** NOT EXECUTED

## Incident authority
- Incident ticket:
- UTC declaration:
- Commander and approver:
- Old primary / region:
- Candidate standby / region:
- RPO and RTO:

## Mandatory STOP gates
- Old primary fenced:
- Independent proof of fencing:
- Direct and pooled write routes blocked:
- Candidate WAL receive/replay position:
- Business-approved potential loss:
- DR capacity and dependencies ready:
- Backups and archive available:
- Authorized promotion method:

**If fencing is not independently proven, do not promote.**

## Approved promotion
- Promotion UTC start/end:
- Operator/provider action reference:
- New primary role confirmed:
- New unique application transaction:
- All old-primary write paths rejected:
- Application read/write and p95/p99:
- Replication and backups reestablished:
- Observed RPO/RTO:

## Former primary handling
- Quarantine evidence:
- Timeline divergence:
- pg_rewind eligibility or fresh rebuild:
- Rejoined as standby:
- Independent reviewer signoff:

DNS change is not fencing. Do not store secrets in the runbook.
