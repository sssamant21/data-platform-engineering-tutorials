# Runbook validation and production certification record (copy into Jira)

| Field | Value |
|---|---|
| Runbook number / revision | |
| Environment and cluster UUID | |
| Elasticsearch exact version / deployment model | |
| Test UTC date, operator, independent reviewer | |
| Jira change / approved maintenance window | |
| Client version / shell / authentication privilege | |
| Source data classification (no raw sensitive records) | |
| Expected impact and test boundaries | |
| Backups/recovery, writer synchronization, required capacity | |
| Pre-execution metrics/commands and redacted outputs | |
| Exact reviewed request files, hashes and approval identifiers | |
| Mutation/operation performed (or read-only only) | |
| Exit criteria, error/failure scenario and result | |
| Actual after-change metrics, data, query and alias validation | |
| Rollback or recovery rehearsal with evidence | |
| Follow-up defects and risk acceptance | |
| DBRE/SRE review | |
| Data/Business/Index Owner review (if applicable) | |
| Application Engineering review (if applicable) | |
| FinOps and Change Authority review (if applicable) | |
| Decision: untested / partial / stage-validated / production-approved | |
| Scope of certification and expiration/revalidation trigger | |

**Do not mark this form completed on the basis of documentation review alone.** A green cluster is not proof of accurate data, correct routing or a safe write cutover. Use sanitized evidence only.
