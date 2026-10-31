# Page 01 — Snowflake DBRE Ownership, Responsibilities & RACI

**Document ID:** SF-DBRE-OPS-001 | **Owner:** Snowflake DBRE | **Status:** DRAFT — Stakeholder approval required | **Review:** Quarterly

## 1. Mission and scope

Snowflake DBRE ensures the **operational reliability, performance, observability, recoverability, security implementation, and cost efficiency** of the organization's Snowflake data platform. Snowflake operates managed infrastructure; DBRE does not administer its underlying nodes, storage servers, patching or cloud service control plane.

**In scope:** Snowflake accounts and regions, warehouse sizing and concurrency, service reliability, query diagnostics, resource monitors/budgets, tasks, Snowpipe operational monitoring, data storage trends, access controls implementation, recovery and replication coordination, incident response, change control and automation.

**Outside sole DBRE ownership:** Business data correctness, transformation/business SQL semantics, source ingestion contracts, organizational security policies, application-facing SLAs, legal retention requirements and Snowflake-managed infrastructure. Snowflake Support/provider handles service-side failures.

## 2. Role dictionary

| Code | Team | Primary accountability |
|---|---|---|
| DBRE | Data/Database Reliability Engineering | Snowflake operations, triage, performance, cost controls, observability, technical recoveries |
| APP | Application / BI / Analytics owners | Query/application logic, reporting accuracy, end-user SLO and functional acceptance |
| DATA | Data Engineering / Business Data Owner | Source correctness, pipelines, transformations, retention and data disposition |
| PLT | Platform / Cloud SRE | Network, identity integrations, connectivity, orchestration infrastructure and integration endpoints |
| SEC | Security / Compliance | Enterprise RBAC policies, encryption/data policy, audits, regulatory requirements |
| FIN | FinOps / Finance | Billing allocation, budget ownership, verified savings |
| SM | Incident / Change Management | Major incident command, communications, production change approvals |
| SF | Snowflake Support | Vendor-managed platform service investigations, contract-supported escalations |

RACI: **A** = single accountable decision owner; **R** = executes work; **C** = consulted; **I** = informed. Where an activity has joint implementers, there must still be one business accountable decision owner.

## 3. Core operational RACI

| Activity | DBRE | APP | DATA | PLT | SEC | FIN | SM |
|---|---|---|---|---|---|---|---|
| Account operational health and monitoring | A/R | C | C | C | I | I | I |
| Warehouse performance, concurrency and sizing | A/R | R | C | C | — | C | I |
| Application query design and business query semantics | C | A/R | R | I | — | I | I |
| Query execution diagnostics, workload isolation | A/R | R | C | C | — | C | I |
| Ingestion/data-freshness functional target | C | C | A/R | R | I | I | I |
| Snowpipe/task/dynamic-table technical monitoring | R | C | A/R | C | I | I | I |
| Data correctness and source-to-target reconciliation | C | R | A/R | I | C | I | I |
| Account/warehouse access implementation | R | C | C | R | A | I | I |
| Organizational access and privacy policy | R | C | C | C | A/R | I | I |
| Monthly warehouse credit/cost optimization | A/R | C | R | C | I | R | I |
| Enterprise spend forecast and budget authorization | R | C | R | C | I | A/R | I |
| Time Travel/UNDROP technical recovery | A/R | R | R | C | C | I | C |
| Business recovery priority and data retention | R | C | A/R | C | C | I | I |
| Cross-account DR technical readiness | A/R | R | R | R | C | C | C |
| DR service RPO/RTO and app acceptance | R | A/R | R | C | C | I | I |
| Snowflake service/platform vendor escalation | A/R | C | C | R | C | I | I |
| Snowflake technical incident RCA | A/R | R | R | C | C | I | I |
| Major incident coordination | R | R | R | R | C | I | A/R |
| Formal production change authorization | R | C | C | C | C | C | A/R |
| Business table/database deletion authorization | R | C | A/R | I | C | I | C |
| Approved object-change execution | A/R | R | R | C | C | I | C |

**Important boundaries:** Snowflake query latency can result from APP SQL design, DATA model, warehouse scheduling or service issues. DBRE owns infrastructure-style diagnosis, not all application query code. A resource monitor is **not** complete account-spend protection, and credentials/roles for security-critical actions must be approved by SEC.

## 4. Decision and approval matrix

| Change | Technical lead | Required approvals |
|---|---|---|
| Read-only diagnostics, query/warehouse history | DBRE | Assigned least-privilege monitoring role |
| Change warehouse size, auto-suspend, multi-cluster | DBRE | APP/DATA workload review, FIN cost review, SM where required |
| Suspend or resume a production warehouse | DBRE | APP/DATA impact assessment and incident/change policy |
| Adjust query timeouts or resource monitor actions | DBRE | APP/DATA + FIN + SM; possible service interruption |
| Create/modify tasks, Snowpipe, dynamic tables | DATA | DBRE reliability input, APP functional review, SM |
| Query/access policy change | SEC | SEC approval; DBRE implementation |
| Change Time Travel/retention or permanent/transient classification | DATA | SEC/legal + APP; DBRE impact/recovery assessment |
| UNDROP / clone / recover live data | DBRE | DATA/APP validation and authorized incident/change |
| Promote failover group or switch account clients | DBRE | Incident command + APP/DATA + SEC/PLT as appropriate |
| Drop tables/schemas/databases/shares | DATA for business permission | Independent DATA/APP approval, SEC if relevant, SM authorization, restricted executor |

**No one-person irreversible data deletion.** Business disposal authorization and technical execution are distinct. Review account/edition limits before approving DR or retention plans.

## 5. Ownership register template

| Attribute | Entry |
|---|---|
| Account/org/region/cloud/edition | |
| Account URL / environments | |
| Primary DBRE and backup | |
| Data/application owners | |
| Warehouse catalog + workload owner | |
| Key databases/schemas and classification | |
| Task/Pipe/dynamic table owners | |
| SLO: query success/latency/freshness | |
| DR capability, recovery tier, RPO/RTO | |
| Access, network, identity and security owner | |
| Credit budget and cost center | |
| Alerting/on-call escalation | |
| Most recent owner review / sign-off | |

## 6. Vendor versus customer responsibility

Snowflake manages the underlying service infrastructure and storage/compute platform. DBRE operates customer-configured accounts, warehouses, objects, monitoring, queries, policies and recovery features. For regional/service incidents, DBRE verifies impact, raises vendor case and supplies sanitized query IDs/time windows while incident management handles communications. DBRE cannot independently restart Snowflake-managed nodes.

## 7. Incident escalation

- **DBRE:** queues, warehouses, query performance, metering spikes, account object administration, vendor support cases.
- **APP:** timeouts caused by application SQL, client retry storms, dashboard errors, business SLOs.
- **DATA:** task/pipe/stream/dynamic-table freshness, ingestion failures and record reconciliation.
- **PLT:** DNS/network/private connectivity, identity provider, cloud integrations and orchestration.
- **SEC:** access denials, compromised credentials, sensitive data, classification and audits.
- **FIN:** runaway spend, credit forecasts and budget-owner decisions.
- **SM:** major incident command, approvals, updates, change freeze/rollback.

## 8. Required artifacts and acceptance

- [ ] Snowflake account, edition/region, owner and warehouse inventories.
- [ ] Named application/data owners for each critical service, pipeline and object.
- [ ] RACI and escalation rules approved by DBRE, APP, DATA, PLT, SEC, FIN, SM.
- [ ] Access control delegated via approved monitoring roles (no routine ACCOUNTADMIN usage).
- [ ] Change matrix and data deletion decisions signed off.
- [ ] SLOs, pipeline freshness, RPO/RTO and account spend owner approved.
- [ ] Recovery/DR edition dependencies and vendor escalation documented.
- [ ] Confluence ownership register linked, reviewed quarterly.

**Completion:** Stakeholder-approved RACI and verified production ownership inventory, not just GitHub publication.

## References
- [Snowflake access-control overview](https://docs.snowflake.com/en/user-guide/security-access-control-overview)
- [Snowflake Account Usage views](https://docs.snowflake.com/en/sql-reference/account-usage)
- [Business continuity / disaster recovery](https://docs.snowflake.com/en/user-guide/replication-intro)
