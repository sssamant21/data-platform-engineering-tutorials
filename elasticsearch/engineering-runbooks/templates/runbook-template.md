# NN — [Operation title]

> Status: Draft / Staging validated / Production approved  
> Technical owner: [team] · Reviewers: [teams]  
> Elasticsearch versions tested: [versions] · Last verified: [date]

## Trigger / purpose

[Specific signal and impact; excluded operations]

## Prerequisites / authorization

[Cluster and index identity, Jira change, approvals, backups, dependencies, recovery, threshold]

## Read-only diagnosis

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" "$ES_URL/_cluster/health?pretty"
```

## Approved execution

[Version-specific steps, reviewed request files, capacity and maintenance gates]

## Monitoring and stop-work conditions

[Objective abort thresholds and incident escalation]

## Validation / evidence

[Data and service correctness, before/after metrics, owners' signoff]

## Rollback / recovery

[Known feasible recovery path; partial tasks/data updates]

## References / revision history

[Official vendor links; tested commands; peer-review notes]
