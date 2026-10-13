# Chapter 096 — Enterprise Incident Response, Escalation and Operational Command Lab

**PostgreSQL 18 · Disposable simulation · Runtime pending**

## 1. Safety and setup

Use an isolated PostgreSQL 18 test database with a test application. No production session termination, network isolation or destructive incident injection is authorized. Assign incident commander, DBRE, SRE, communications lead and scribe before the drill.

## 2. Define the incident

Choose a bounded scenario: lock contention, connection saturation, high query latency, archive failure or replica lag. Define synthetic application SLO, SEV trigger, abort condition, escalation contacts and communication cadence.

## 3. Detect and declare

Generate or simulate a monitored symptom in the disposable environment. Record alert UTC time, incident declaration, impact, affected workload, on-call acknowledgement and initial hypotheses in [096 timeline](../labs/incident/096-incident-command-timeline.csv).

## 4. Triage

Run [096 read-only SQL](../labs/sql/096-incident-command-triage.sql). Collect host/application/pooler metrics and recent change history. Distinguish database bottleneck from upstream client retries or network failures. Record wait-event and blocking evidence before changing anything.

## 5. Approve mitigation

Document the smallest reversible action, expected effect, rollback, risk and approver. For a lock-contention lab, resolve the test transaction from its owning session rather than indiscriminately terminating backends. Do not perform production failover.

## 6. Communicate and verify

Use [096 communications template](../labs/incident/096-incident-communications-template.md). Validate application read/write transactions, p95/p99, errors, pool health, WAL/replication/backup status and return to SLO.

## 7. Post-incident review

Build a blameless timeline, distinguish confirmed facts from hypotheses, and assign preventive/detective corrective actions with owners and due dates.

## 8. Acceptance

Complete [096 scorecard](../labs/acceptance/096-incident-command-scorecard.csv). Mark drills not executed as NOT VERIFIED; do not infer production readiness from a tabletop.

**Runtime:** pending.
