# Chapter 094 — DR Capstone Evidence Record

**Status:** NOT EXECUTED

## Governance
- Exercise ID, date, ticket:
- Incident commander and independent observer:
- DBRE, SRE, application and security owners:
- Primary and DR region:
- Approved RPO/RTO:
- Application SLO and peak load:
- Scope, abort limits and rollback:

## Topology and baseline
- PostgreSQL 18 versions and role identity:
- Primary/standby WAL LSN and timeline:
- Replication slots and archive health:
- Backup generation and isolated restore proof:
- Application baseline and transaction markers:

## Incident timeline
| UTC timestamp | Event | Action/decision | Evidence |
|---|---|---|---|
| | | | |

## Safety and recovery
- Original writer fenced independently:
- Direct and pooled old-writer paths rejected:
- Promotion/restore method and operator:
- New writer identity:
- Recovered transaction marker:
- Observed RPO and uncertainty:
- Observed RTO:
- Application read/write and p95/p99:
- Backup and replica protection restored:
- Former primary quarantined and rejoined as standby:

## Decision
- Mandatory gates failed / NOT VERIFIED:
- Corrective actions with owners and deadlines:
- Independent signoff:
- Final status: PASS / CONDITIONAL / FAIL / NOT VERIFIED

Do not infer production regional resilience from a single-host simulation.
