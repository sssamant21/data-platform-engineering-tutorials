# Chapter 085 — Production Change Evidence and Reliability Acceptance

**Status:** NOT EXECUTED / NOT VERIFIED

## Change identity
- Ticket:
- Git/IaC revision:
- Environment and PostgreSQL version:
- UTC window:
- Change commander:
- Executor:
- Independent verifier:
- Application owner:
- Approved rollback decision-maker:

## Readiness
- Backup and isolated restore proof:
- Extension compatibility:
- Effective settings and drift:
- Replication/HA status:
- Capacity and WAL headroom:
- Application SLO baseline:
- Alert and log readiness:
- Stop conditions and escalation:

## Execution timeline (UTC)
| UTC time | Step | Expected | Observed | Decision | Evidence |
|---|---|---|---|---|---|
| | Preflight | All gates pass | | | |
| | Config change | Approved setting active | | | |
| | Maintenance | Targeted job complete | | | |
| | Postchecks | DB and app healthy | | | |
| | Rollback rehearsal | Original state restored | | | |

## Acceptance
- DB availability and error rate:
- Application reads/writes:
- p95/p99 latency vs approved thresholds:
- Replication and backups:
- Audit/security checks:
- Rollback or forward recovery evidence:
- Open exceptions and owners:
- Final scorecard result:
- DBRE signoff:
- SRE signoff:
- Application signoff:

Do not include secrets, credentials or unredacted customer data.
