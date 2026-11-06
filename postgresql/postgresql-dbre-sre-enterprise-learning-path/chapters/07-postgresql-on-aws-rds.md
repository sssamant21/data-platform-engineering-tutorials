# Chapter 07 — PostgreSQL on AWS RDS

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Audience:** DBRE/SRE, database/platform engineers, application architects  
**Duration:** 60 minutes · **Local reference:** PostgreSQL 17 via Docker · **Cloud:** Amazon RDS for PostgreSQL (not Aurora)  
**Publication state:** Authored; no AWS resources created; local/AWS runtime evidence and independent review pending  
**Last reviewed against AWS documentation:** 2026-11-02

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 07 lab](../labs/chapter-07/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Outcomes and lesson plan

By the end, an engineer should be able to (1) describe the AWS/customer responsibility split, (2) distinguish RDS Single-AZ, Multi-AZ DB **instance**, Multi-AZ DB **cluster**, and read replicas, (3) identify security, backup, restore, observability and parameter-group decisions, (4) review a proposed RDS deployment against an SLO and RPO/RTO, and (5) collect non-destructive evidence.

| Minutes | Activity | Deliverable |
|---|---|---|
| 0–10 | Architecture and ownership | Responsibility matrix |
| 10–20 | Availability modes and scaling | Deployment comparison |
| 20–30 | Security, backups, parameter groups and monitoring | Control checklist |
| 30–53 | [Cost-free local lab](../labs/chapter-07/README.md) | SQL and restore evidence |
| 53–60 | Design review and acceptance | One-page RDS recommendation |

**No AWS account is required for the core lab.** Optional AWS CLI inventory commands are read-only and require existing authorized access. Do not provision billable RDS, VPC, CloudWatch, KMS or backup resources for this chapter.

## 2. Where RDS fits

Amazon RDS for PostgreSQL is a managed relational database service. AWS operates underlying hosts, storage integration, supported patch/deployment workflows, managed backups and certain HA mechanics. The customer still owns workload suitability, schema/SQL, access governance, backup retention decisions, restore drills, SLOs, capacity choices, change management and spend.

```text
Client / application
        |
Network path: VPC, subnet routing, security groups, TLS
        |
RDS for PostgreSQL endpoint
        |
+-----------------------------------------------+
| PostgreSQL engine: schema, SQL, MVCC, indexes |
| RDS management: host, storage, backups, HA    |
+-----------------------------------------------+
        |
Customer-controlled configuration and governance
IAM + database roles + KMS + monitoring + recovery policy
```

Do not confuse **RDS for PostgreSQL** with **Amazon Aurora PostgreSQL-Compatible Edition**: they have different storage architectures, feature sets, failure behavior, operational limits and pricing.

### Ownership matrix

| Area | AWS managed aspects | DBRE/SRE and application responsibilities |
|---|---|---|
| Host and storage | Host OS/platform operations and managed storage | Capacity, storage class, autoscaling policy, alerts and cost |
| PostgreSQL configuration | Supported engine builds and managed deployment controls | Parameter-group values, compatibility and change review |
| Networking | AWS VPC/security-group infrastructure | Private access design, allowed paths, TLS and least privilege |
| Access | IAM integrations and managed secret options | DB roles, grants, credential rotation and application identity |
| Backups | Automated backup infrastructure and snapshots | Retention, restore testing, RPO/RTO, off-region strategy |
| HA | Supported Multi-AZ failover mechanisms | Architecture selection, client reconnect behavior and testing |
| Monitoring | RDS metrics, logs and CloudWatch integration | SLO dashboards, alerts, triage, response and evidence |
| Lifecycle | Engine version options and maintenance features | Version support, testing, scheduling, rollback plan |

**RDS privilege boundary:** the initial administrative PostgreSQL account commonly has `rds_superuser` privileges, but **not** true PostgreSQL `SUPERUSER` and no direct host OS access. RDS internal administrative roles are not for application use. This matters when porting extensions, file-based maintenance scripts, or superuser-only procedures. [AWS role reference](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Roles.rds_superuser.html).

## 3. Availability topology: choose the correct RDS mode

| Mode | Topology | Can a standby/reader serve reads? | Primary purpose |
|---|---|---|---|
| Single-AZ DB instance | One active DB instance in an AZ | No separate standby | Lower complexity; noncritical or explicitly accepted risk |
| Multi-AZ **DB instance** | Primary plus synchronous standby in another AZ | **No**: standby is not a read endpoint | HA/failover |
| Multi-AZ **DB cluster** | One writer plus two readable DB instances across three AZs | **Yes**: cluster readers can serve reads | HA plus read capacity |
| DB instance read replica | Separate asynchronously replicated DB instance | **Yes**, but eventual consistency | Read scaling / some DR scenarios |

A **read replica** is not the same thing as the synchronous Multi-AZ DB instance standby, and asynchronous replica lag must be accounted for. Multi-AZ DB cluster readers have different replication and failover semantics than independent read replicas. Neither HA nor a replica replaces tested backups or application-level recovery planning.

### Endpoint and application behavior

- Application write traffic must target the **writer** endpoint.
- A Multi-AZ DB cluster provides separate writer and reader endpoints; the reader endpoint is for read-only workloads and does not imply read-after-write consistency.
- DB instance failover can change underlying infrastructure. Applications must implement DNS-aware reconnection, transaction retries where safe, connection pool recovery and idempotency.
- Do not claim zero downtime, zero data loss or a guaranteed RTO from selecting a topology. Measure actual behavior against approved targets.

Official: [Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html), [Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html), [read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html).

## 4. Backups, restore and RPO/RTO

RDS automated backups cover the DB instance or Multi-AZ DB cluster storage and support point-in-time recovery (PITR) within the configured retention window, subject to available restorable times and platform limits.

- For a **DB instance**, retention can be **0–35 days**; **0 disables automated backups**. For a **Multi-AZ DB cluster**, retention is **1–35 days**.
- Creation defaults depend on interface: AWS CLI/API DB instance default is **1 day** if unspecified; console default is **7 days**. Always explicitly configure policy rather than relying on a default.
- A point-in-time restore **creates a new DB instance** rather than overwriting the source; restored configuration and permissions must be reviewed.
- The `LatestRestorableTime` field is important for assessing available recovery points. Do not equate a configured retention window with proof of a particular RPO.
- Changing an existing DB instance's backup retention between zero and nonzero can cause an outage; treat as a reviewed change.
- Backup copies, encryption keys, access boundaries and cross-region recovery requirements are design decisions, not automatic guarantees.

**Recovery acceptance:** test a separate restore, validate row counts and application behavior, record timestamps and actual RPO/RTO, and retain approvals. An RDS snapshot existing in the console is **not** sufficient evidence.

Official: [automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html), [retention](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html), [PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html).

## 5. Security and access controls

Use a private networking posture by default, narrowly scoped security-group ingress, approved TLS settings, encryption at rest using an appropriate KMS key policy, least-privilege database roles, and a credential rotation mechanism. Where appropriate, evaluate IAM database authentication and AWS Secrets Manager.

**Three distinct permissions layers:**

1. **AWS IAM:** who can describe or modify the RDS resource and related AWS services.
2. **VPC/security groups and TLS:** who can reach the endpoint securely.
3. **PostgreSQL roles/GRANT:** who can connect and access database objects.

Passing one layer does not grant the others. Never commit database passwords, connection strings containing credentials, or unredacted logs. A lab PostgreSQL superuser is **not** an accurate simulation of `rds_superuser`.

## 6. Parameter groups and lifecycle

RDS parameter groups expose supported engine settings. Some parameters are dynamic; static parameters or association changes can require a reboot. Associating a different parameter group does not necessarily apply its modified values until a reboot; verify the exact parameter and its `pending-reboot` state.

**DBRE change workflow:** identify engine version and family → baseline values → review performance impact → stage test → approved window for any reboot/failover → apply → validate actual settings and application behavior → retain rollback/evidence.

Useful read-only SQL (also works locally):

```sql
SELECT name, setting, unit, context, pending_restart
FROM pg_settings
WHERE name IN ('max_connections','shared_buffers','work_mem','log_min_duration_statement')
ORDER BY name;
```

Do not directly edit a managed RDS host's `postgresql.conf` or assume OS-level privileges exist. [AWS parameter-group behavior](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.Associating.html).

## 7. Observability and incident response

A basic RDS PostgreSQL dashboard should correlate:

- **Availability:** instance state, failover/restart events, application connection errors and endpoint health.
- **Saturation:** CPU, FreeableMemory, FreeStorageSpace, connections, IOPS, throughput and latency.
- **Database:** long transactions, locks, deadlocks, autovacuum, transaction age, cache behavior and query plans.
- **Recovery:** automated backup status, latest restorable time, restore-drill outcome and replication lag where relevant.
- **Cost:** instance hours, provisioned storage/IOPS, backups, data transfer, monitoring tiers and replicas.

**2026 observability update:** AWS retired the older Performance Insights **console experience on July 31, 2026** in favor of CloudWatch Database Insights. The Performance Insights API continues to exist; choose Database Insights Standard/Advanced capabilities and retention deliberately, and check current billing and supported engines. Do not write new runbooks that depend on the old console. [AWS documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.Overview.html).

For a latency incident, first correlate application request time with RDS metrics, connection pools, database waits and query workload. Avoid blindly increasing instance size or terminating sessions without an incident plan.

## 8. Cost and architecture tradeoffs

RDS is managed, not automatically inexpensive. Consider instance class, AZ topology, storage/IOPS, backup retention, log/monitoring retention, data transfer, read replicas and cross-region strategy. An extra replica may improve read capacity but also adds cost and replication-lag complexity.

### Architecture review scenario

An order-processing service has high write consistency needs, 1,000 connections from microservices, read-heavy reporting, an availability SLO and strict recovery requirements. The DBRE team should:

1. Quantify peak transactions, active versus idle connections and pool sizing.
2. Compare Multi-AZ instance vs Multi-AZ cluster vs read replicas with workload evidence.
3. Document expected failover behavior and retry semantics.
4. Specify backup retention, off-region recovery strategy and **tested** RPO/RTO.
5. Review schema/query plans and isolate reporting from latency-critical writes.
6. Define capacity, security, patching, alerting, ownership and monthly cost estimates.

**No topology is selected as universally best.** Write down assumptions and what would falsify them.

## 9. Hands-on lab and optional AWS inventory

Follow [Chapter 07 lab](../labs/chapter-07/README.md). The required portion uses **only the existing local Docker PostgreSQL 17 container** to collect settings/health evidence, practice least-privilege database grants, and restore a small logical backup to a separate disposable database. This is a **comparison exercise**, not an RDS emulator.

An **optional, explicitly authorized, read-only** AWS CLI section demonstrates `describe-db-instances` and `describe-db-clusters`. It makes no create/modify/delete requests and requires no new AWS resources.

## 10. Troubleshooting

| Symptom | Likely category | Safe first response |
|---|---|---|
| Connection refused/timeouts | SG/VPC route/DNS/TLS/endpoint | Confirm approved network path, RDS status and client errors |
| Access denied | IAM vs DB role vs TLS confusion | Identify failing permission layer; do not grant `rds_superuser` to app |
| Pending reboot after parameter change | Static/association setting | Review impact and schedule approved restart |
| Slow reads after adding replica | Lag, routing, SQL plan | Measure replica lag and query plans before traffic shift |
| Restore appears slow | Data initialization, instance size | Validate restore status and workload; measure, don't assume |
| Storage near full | Growth, WAL, temp files, retention | Check FreeStorageSpace and growth trend; escalate safely |
| Cloud monitoring dashboard missing | Legacy Performance Insights UI | Use current CloudWatch Database Insights and verify entitlement |

## 11. Acceptance checklist

- [ ] Explain RDS vs self-managed PostgreSQL and the `rds_superuser` limitation.
- [ ] Correctly distinguish Multi-AZ DB instance, Multi-AZ DB cluster and read replica.
- [ ] Explain retention, latest restorable time and restore-to-new-instance behavior.
- [ ] Describe security, parameter groups, monitoring and cost ownership.
- [ ] Complete the local lab and retain **actual** evidence if run.
- [ ] Mark optional AWS inventory **skipped** unless real authorized read-only output exists.
- [ ] Produce a one-page architecture recommendation with SLO, RPO/RTO, risks and costs.
- [ ] Obtain independent technical review before calling this validated.

**Publication ≠ runtime validation ≠ enterprise certification.**

## 12. Official references

- [Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Understanding `rds_superuser`](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Roles.rds_superuser.html)
- [Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html)
- [Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)
- [RDS automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Point-in-time restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Parameter-group association](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.Associating.html)
- [CloudWatch Database Insights / Performance Insights transition](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.Overview.html)
- [PostgreSQL 18: pg_settings](https://www.postgresql.org/docs/18/view-pg-settings.html)
