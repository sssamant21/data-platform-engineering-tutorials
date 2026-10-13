# Chapter 090 — Regional Failover and Failback Runbook

**Status:** DESIGN / NOT EXECUTED

## 1. Incident declaration
- Incident ID and UTC time:
- Incident commander:
- Original primary and region:
- DR candidate and region:
- RPO/RTO target:
- Application owner and approver:

## 2. Pre-promotion STOP gates
- Original primary fenced at infrastructure/control-plane level:
- Evidence old writer cannot accept writes:
- Network partition vs confirmed primary loss distinguished:
- DR standby WAL/replay position and potential data loss:
- Backup/archive and alternate recovery options reviewed:
- DR capacity and application routing ready:
- Promotion explicitly authorized:

**If fencing or writer authority is uncertain: STOP. Do not promote.**

## 3. Promotion (approved disposable test or real incident only)
- UTC start:
- Supported operator/provider/HA promotion method:
- Resulting timeline and primary status:
- Successful controlled write:
- Application routing updated:
- Old primary access still blocked:
- UTC service restoration:
- Observed RPO/RTO:

## 4. Verification
- Exactly one writable primary:
- Application read/write and p95/p99:
- Replica health and WAL archive:
- Backups restarted in new active region:
- Security, secrets and monitoring:
- Stakeholder notification:

## 5. Failback
- Preserve and quarantine old primary:
- Identify timeline divergence:
- Determine supported pg_rewind/reseed/rebuild:
- Rejoin as standby only after validation:
- Controlled switchover approval and test:
- Final evidence and signoff:

Do not treat DNS updates alone as sufficient fencing.
