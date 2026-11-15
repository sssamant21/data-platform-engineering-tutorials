# Reviewable request-body templates — nonproduction only

These are **illustrative, valid JSON** inputs intended for staging, not operational defaults or approved production settings. Index names use `sandbox-` prefix. A production change needs its own exact payload attached to the Jira ticket, hash/review, a documented source-to-target schema, routing and update handling, capacity review, and explicit operator approval. Never blindly run these JSON files against production.

| Sample | Intended runbook | Caution |
|---|---|---|
| sandbox-index.json | 04 | Shards, replicas, mapping and refresh are workload-specific |
| sandbox-reindex.json | 03/05 | Snapshot-based copy does not capture later writes |
| sandbox-alias-actions.json | 05 | Removes and adds only **existing reviewed alias targets**; validate writer behavior |
| sandbox-ilm-policy.json | 06 | 30-day deletion is illustrative; not a business-approved retention period |
| sandbox-restore.json | 09 | Requires existing approved repository/snapshot, compatible index, isolated target |
| sandbox-allocation-explain.json | 12 | Read-only explanation; works only for an actually unassigned matching replica |

All samples intentionally exclude credentials, patient data, cluster settings, and irreversible DELETE calls. Replace each with a service-specific reviewed payload during maintenance preparation.
