# Chapter 45 --- Redis Enterprise Kubernetes Operations, Scheduling & Platform Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 7 --- Platform, Kubernetes & Cloud Operations\
**Level:** Advanced → Production Kubernetes Platform Engineering\
**Audience:** SREs, DBREs, Platform Engineers, Kubernetes
Administrators, Redis Administrators\
**Lab type:** Operator and CRD discovery, topology inspection,
scheduling, node labels, affinity/anti-affinity, taints/tolerations,
resource requests and limits, storage, disruption controls, node drains,
failure domains, monitoring, backup integration, controlled failure
injection, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Running Redis Enterprise on Kubernetes introduces an additional control
plane between Redis and the infrastructure.

The operational model becomes:

``` text
application
    |
    v
Redis database
    |
    v
Redis Enterprise
    |
    v
Redis Enterprise Kubernetes operator
    |
    v
Kubernetes scheduler/controllers
    |
    v
nodes + network + storage
```

A Redis incident can therefore originate from:

``` text
Redis
Kubernetes
node
storage
network
operator
configuration
application
```

By the end of this chapter, you should be able to:

-   understand the Redis Enterprise Kubernetes architecture;
-   inventory operator and CRD versions;
-   validate version compatibility;
-   inspect Redis Enterprise custom resources;
-   understand scheduling and placement;
-   use labels, affinity, anti-affinity, taints, and tolerations safely;
-   design failure-domain placement;
-   size CPU and memory resources;
-   understand persistent storage dependencies;
-   plan PodDisruptionBudgets;
-   perform safe node maintenance;
-   troubleshoot Pending, restarting, and unhealthy Redis pods;
-   analyze node pressure and eviction;
-   validate networking and DNS;
-   integrate monitoring and backup;
-   rehearse Kubernetes failures;
-   operate production Kubernetes runbooks.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not troubleshoot Redis on Kubernetes as if Kubernetes does not exist.

Always consider both layers:

``` text
Redis health
+
Kubernetes health
```

------------------------------------------------------------------------

# Part 1 --- Architecture

## 3. Components

A Redis Enterprise Kubernetes deployment can include:

``` text
Redis Enterprise operator
Redis Enterprise cluster resources
Redis Enterprise database resources
pods
services
persistent volumes
secrets
configuration
Kubernetes nodes
```

Exact resource names and schemas depend on the deployed Redis Enterprise
operator/version.

------------------------------------------------------------------------

# Part 2 --- Operator

## 4. Responsibility

The operator reconciles declared Redis Enterprise state with Kubernetes
resources.

Conceptually:

``` text
desired custom resource
       |
       v
operator reconciliation
       |
       v
Redis Enterprise resources
```

------------------------------------------------------------------------

# Part 3 --- Reconciliation

## 5. Important

Manual changes to operator-managed resources may be reverted.

Before modifying a generated Kubernetes object, determine whether:

``` text
operator owns it
GitOps owns it
platform automation owns it
```

Change the authoritative source instead of fighting reconciliation.

------------------------------------------------------------------------

# Part 4 --- Version Inventory

## 6. Record

Maintain:

``` text
Kubernetes version
Redis Enterprise operator version
Redis Enterprise version
CRD versions
container images
storage driver/CSI version
monitoring integration
```

------------------------------------------------------------------------

# Part 5 --- Compatibility

## 7. Validate

Before upgrade or platform maintenance, validate the exact supported
compatibility matrix for:

``` text
Kubernetes
operator
Redis Enterprise
CRDs
```

Do not assume the newest versions are mutually compatible.

------------------------------------------------------------------------

# Part 6 --- CRD Discovery

## 8. Lab Commands

Inspect Redis-related CRDs:

``` bash
kubectl get crd | grep -i redis
```

Describe a CRD:

``` bash
kubectl describe crd <redis-crd-name>
```

Use the actual CRD names installed in your cluster.

------------------------------------------------------------------------

# Part 7 --- Operator Discovery

## 9. Locate

Examples:

``` bash
kubectl get deployments -A | grep -i redis
kubectl get pods -A | grep -i redis
```

Do not assume a namespace; discover it.

------------------------------------------------------------------------

# Part 8 --- Resource Inventory

## 10. Inspect

Use:

``` bash
kubectl api-resources | grep -i redis
```

Then inspect the exact custom resources installed by your Redis
Enterprise operator.

------------------------------------------------------------------------

# Part 9 --- Namespaces

## 11. Boundary

Document:

``` text
operator namespace
Redis Enterprise namespace
application namespaces
monitoring namespace
backup integration
```

Namespace boundaries affect RBAC, secrets, policies, and
troubleshooting.

------------------------------------------------------------------------

# Part 10 --- Pod Inventory

## 12. Commands

``` bash
kubectl get pods -n <namespace> -o wide
```

Record:

``` text
pod
node
status
restarts
IP
age
```

------------------------------------------------------------------------

# Part 11 --- Node Inventory

## 13. Commands

``` bash
kubectl get nodes -o wide
kubectl describe node <node>
```

Inspect:

``` text
capacity
allocatable
conditions
labels
taints
```

------------------------------------------------------------------------

# Part 12 --- Scheduling

## 14. Scheduler Inputs

Pod placement can depend on:

``` text
resource requests
node selectors
node affinity
pod anti-affinity
taints/tolerations
topology constraints
volume topology
```

------------------------------------------------------------------------

# Part 13 --- Node Labels

## 15. Purpose

Labels can identify:

``` text
node pool
zone
instance class
storage capability
dedicated workload
```

Example inspection:

``` bash
kubectl get nodes --show-labels
```

------------------------------------------------------------------------

# Part 14 --- Node Selectors

## 16. Use Carefully

A selector can ensure Redis runs only on approved nodes.

Too-restrictive selectors can leave pods Pending.

------------------------------------------------------------------------

# Part 15 --- Node Affinity

## 17. Flexible Placement

Affinity can express:

``` text
required placement
preferred placement
```

Use required rules only when the cluster has enough matching capacity.

------------------------------------------------------------------------

# Part 16 --- Pod Anti-Affinity

## 18. Failure Isolation

Anti-affinity can reduce the chance that redundant Redis components
share the same failure domain.

But overly strict anti-affinity can block scheduling during maintenance.

------------------------------------------------------------------------

# Part 17 --- Topology Spread

## 19. Goal

Spread critical pods across:

``` text
nodes
zones
failure domains
```

where supported by the Redis Enterprise architecture and Kubernetes
design.

------------------------------------------------------------------------

# Part 18 --- Taints

## 20. Dedicated Nodes

Inspect:

``` bash
kubectl describe node <node> | grep -A5 Taints
```

Taints prevent pods without matching tolerations from scheduling.

------------------------------------------------------------------------

# Part 19 --- Tolerations

## 21. Not Placement by Themselves

A toleration permits scheduling onto a tainted node.

It does not necessarily force the pod onto that node.

Combine with appropriate placement rules when required.

------------------------------------------------------------------------

# Part 20 --- Dedicated Redis Node Pool

## 22. Benefits

Possible advantages:

``` text
resource isolation
predictable CPU/memory
controlled maintenance
failure-domain planning
```

Evaluate cost and operational complexity.

------------------------------------------------------------------------

# Part 21 --- Resource Requests

## 23. Scheduler

CPU/memory requests influence scheduling.

If requests exceed available allocatable capacity:

``` text
pod -> Pending
```

------------------------------------------------------------------------

# Part 22 --- CPU Limits

## 24. Caution

CPU limits can cause throttling.

For latency-sensitive Redis workloads, understand the platform and Redis
Enterprise vendor guidance before applying restrictive CPU limits.

Monitor throttling when limits are used.

------------------------------------------------------------------------

# Part 23 --- Memory Limits

## 25. Critical

Memory limits can trigger container termination if usage exceeds the
limit.

Redis memory planning must include:

``` text
dataset
process overhead
buffers
replication
persistence
operational headroom
```

------------------------------------------------------------------------

# Part 24 --- OOMKilled

## 26. Diagnose

Check:

``` bash
kubectl describe pod <pod> -n <namespace>
```

and:

``` bash
kubectl get pod <pod> -n <namespace> \
  -o jsonpath='{.status.containerStatuses[*].lastState}'
```

Correlate with memory metrics.

------------------------------------------------------------------------

# Part 25 --- Node Memory Pressure

## 27. Condition

Inspect:

``` bash
kubectl describe node <node>
```

Look for:

``` text
MemoryPressure
DiskPressure
PIDPressure
```

Node pressure can affect Redis even when Redis itself is correctly
configured.

------------------------------------------------------------------------

# Part 26 --- Kubernetes Eviction

## 28. Distinguish

Kubernetes pod eviction is not Redis key eviction.

``` text
Redis eviction      -> keys removed due to Redis memory policy
Kubernetes eviction -> pod removed due to node/platform pressure
```

Do not confuse the two during incidents.

------------------------------------------------------------------------

# Part 27 --- Persistent Storage

## 29. Dependency

Where persistent volumes are used, inventory:

``` text
StorageClass
PVC
PV
CSI driver
capacity
IOPS/throughput
zone
reclaim policy
```

------------------------------------------------------------------------

# Part 28 --- PVC Inspection

## 30. Commands

``` bash
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc> -n <namespace>
```

------------------------------------------------------------------------

# Part 29 --- PV Inspection

## 31. Commands

``` bash
kubectl get pv
kubectl describe pv <pv>
```

Understand the relationship between Redis data, PVCs, and infrastructure
disks.

------------------------------------------------------------------------

# Part 30 --- Storage Performance

## 32. Watch

Persistence, backup, restore, and recovery can expose storage
bottlenecks.

Monitor:

``` text
latency
IOPS
throughput
queueing
capacity
```

at the infrastructure layer.

------------------------------------------------------------------------

# Part 31 --- Volume Topology

## 33. Scheduling

A volume may constrain which zone/node can host a pod.

During rescheduling, check volume topology before assuming scheduler
failure.

------------------------------------------------------------------------

# Part 32 --- Reclaim Policy

## 34. Understand

Know whether the StorageClass/PV policy is:

``` text
Retain
Delete
```

or another supported behavior.

Never discover data-destruction semantics during an incident.

------------------------------------------------------------------------

# Part 33 --- PodDisruptionBudget

## 35. Purpose

PDBs can limit simultaneous voluntary disruption.

They do not guarantee application availability by themselves.

------------------------------------------------------------------------

# Part 34 --- PDB Inspection

## 36. Command

``` bash
kubectl get pdb -A
kubectl describe pdb <pdb> -n <namespace>
```

Understand:

``` text
minAvailable
maxUnavailable
disruptionsAllowed
```

------------------------------------------------------------------------

# Part 35 --- PDB vs. Drain

## 37. Expected

A node drain may block because disruption would violate the PDB.

That can be correct protection, not an error.

------------------------------------------------------------------------

# Part 36 --- Node Drain

## 38. Prechecks

Before maintenance:

``` text
Redis health
replication/redundancy
capacity
pod placement
PDB
volume topology
other node availability
```

------------------------------------------------------------------------

# Part 37 --- Drain Safety

## 39. Do Not Force Blindly

Avoid overriding disruption protections merely to make a drain complete.

Understand Redis Enterprise maintenance guidance first.

------------------------------------------------------------------------

# Part 38 --- Cordon

## 40. Purpose

``` bash
kubectl cordon <node>
```

prevents new scheduling on a node. **This is an explanation of a cluster-scoped operation, not a safe copy-and-paste instruction for an arbitrary node.** A cordon can prevent replacement pods from scheduling, creating availability risk if placement/headroom is inadequate.

Cordon does not evict existing pods. Before any real cordon/uncordon change, confirm the approved cluster/context, node ownership, remaining Redis failure tolerance, workload/PDB placement, monitoring, and maintenance/rollback plan. Treat this as **NOT EXECUTED** until an authorized Kubernetes owner approves it.

------------------------------------------------------------------------

# Part 39 --- Uncordon

## 41. After Maintenance

``` bash
kubectl uncordon <node>
```

Then validate node and Redis health.

------------------------------------------------------------------------

# Part 40 --- Node Failure

## 42. Unplanned

When a node fails, investigate:

``` text
Redis failover
pod rescheduling
volume availability
remaining capacity
PDB/topology
client recovery
```

------------------------------------------------------------------------

# Part 41 --- Failure Domains

## 43. Node

Do not place all redundant Redis components on one Kubernetes node.

------------------------------------------------------------------------

# Part 42 --- Zone

## 44. AZ/Zone

Where architecture supports multi-zone placement, verify Redis
redundancy is actually distributed across intended zones.

------------------------------------------------------------------------

# Part 43 --- Capacity After Failure

## 45. N-1

The remaining nodes must have enough:

``` text
CPU
memory
network
storage
```

to handle the workload and recovery.

------------------------------------------------------------------------

# Part 44 --- Cluster Autoscaler

## 46. Interaction

Autoscaling can add/remove Kubernetes nodes, but Redis Enterprise
placement and persistent storage may impose constraints.

Do not assume autoscaler behavior alone guarantees Redis availability.

------------------------------------------------------------------------

# Part 45 --- Scale Down Risk

## 47. Important

Node-pool scale-down can cause disruption.

Validate:

``` text
PDB
Redis topology
persistent volume placement
minimum node count
failure domains
```

------------------------------------------------------------------------

# Part 46 --- HPA

## 48. Application Side

Application HPA can dramatically increase Redis:

``` text
connections
ops/sec
network
```

Redis capacity planning must include maximum application scale.

------------------------------------------------------------------------

# Part 47 --- Redis Scaling

## 49. Product-Specific

Scale Redis Enterprise using supported Redis Enterprise/operator
procedures.

Do not treat Redis pods like a generic stateless Deployment.

------------------------------------------------------------------------

# Part 48 --- Services

## 50. Inspect

``` bash
kubectl get svc -n <namespace>
kubectl describe svc <service> -n <namespace>
```

Check:

``` text
type
cluster IP
ports
selectors
endpoints
```

------------------------------------------------------------------------

# Part 49 --- Endpoint Discovery

## 51. Validate

Use the current Kubernetes API resources appropriate to the cluster to
inspect service endpoints.

Confirm traffic is routed to healthy Redis Enterprise components.

------------------------------------------------------------------------

# Part 50 --- DNS

## 52. Troubleshooting

From an approved diagnostic pod:

``` bash
nslookup <redis-service>
```

or another available DNS tool.

Check:

``` text
name
namespace
search domain
CoreDNS
network policy
```

------------------------------------------------------------------------

# Part 51 --- NetworkPolicy

## 53. Security

Inspect:

``` bash
kubectl get networkpolicy -A
```

A new NetworkPolicy can look like a Redis outage to applications.

------------------------------------------------------------------------

# Part 52 --- Connectivity Test

## 54. From Application Namespace

Use an approved diagnostic container and test:

``` text
DNS
TCP connection
TLS
Redis authentication
```

in that order.

------------------------------------------------------------------------

# Part 53 --- TLS Secrets

## 55. Rotation

When Kubernetes Secrets or external secret controllers deliver TLS
material, validate:

``` text
secret updated
pod/operator reload behavior
client trust
certificate actually served
```

------------------------------------------------------------------------

# Part 54 --- External Secret Integration

## 56. Failure Mode

If an external secret provider fails:

``` text
existing secret may remain
new pod may fail
rotation may fail
```

Understand controller behavior.

------------------------------------------------------------------------

# Part 55 --- RBAC

## 57. Kubernetes Access

Operator and administrators require Kubernetes permissions.

Use least privilege and validate ServiceAccount/Role/RoleBinding or
ClusterRole bindings according to product requirements.

------------------------------------------------------------------------

# Part 56 --- Operator Service Account

## 58. Do Not Arbitrarily Restrict

Changing operator RBAC without understanding required permissions can
break reconciliation.

Validate against official operator documentation.

------------------------------------------------------------------------

# Part 57 --- Admission Policies

## 59. Compatibility

Admission controllers/policies can reject Redis Enterprise resources.

Check events when creation/update unexpectedly fails.

------------------------------------------------------------------------

# Part 58 --- Pod Security

## 60. Policies

Pod-security controls can affect:

``` text
user/group
capabilities
volumes
host access
```

Validate operator compatibility before enforcement changes.

------------------------------------------------------------------------

# Part 59 --- Kubernetes Events

## 61. Essential

``` bash
kubectl get events -n <namespace> \
  --sort-by='.lastTimestamp'
```

Events can reveal:

``` text
FailedScheduling
FailedMount
BackOff
Unhealthy
Evicted
```

------------------------------------------------------------------------

# Part 60 --- Describe Pod

## 62. First-Line Tool

``` bash
kubectl describe pod <pod> -n <namespace>
```

Review:

``` text
state
last state
readiness
conditions
volumes
node
events
```

------------------------------------------------------------------------

# Part 61 --- Logs

## 63. Current

``` bash
kubectl logs <pod> -n <namespace> -c <container>
```

For a restarted container:

``` bash
kubectl logs <pod> -n <namespace> \
  -c <container> --previous
```

------------------------------------------------------------------------

# Part 62 --- Operator Logs

## 64. Reconciliation

When custom resources do not converge, inspect operator logs using the
discovered operator pod/deployment.

Correlate by timestamp and resource.

------------------------------------------------------------------------

# Part 63 --- Pending Pod

## 65. Decision Tree

``` text
Pending
  |
  +-- insufficient CPU/memory?
  +-- node selector/affinity?
  +-- taint/toleration?
  +-- PVC/volume topology?
  +-- PDB/maintenance interaction?
  +-- admission policy?
```

Start with `kubectl describe pod`.

------------------------------------------------------------------------

# Part 64 --- CrashLoopBackOff

## 66. Decision Tree

``` text
CrashLoopBackOff
  |
  +-- application/process error?
  +-- config/secret?
  +-- TLS?
  +-- storage?
  +-- memory/OOM?
  +-- version incompatibility?
```

Check current and previous logs.

------------------------------------------------------------------------

# Part 65 --- ImagePullBackOff

## 67. Check

``` text
image name/tag
registry connectivity
imagePullSecret
registry permissions
DNS
```

------------------------------------------------------------------------

# Part 66 --- FailedMount

## 68. Check

``` text
PVC/PV
CSI driver
zone
attachment
permissions
storage service
```

------------------------------------------------------------------------

# Part 67 --- Readiness Failure

## 69. Important

A Running pod is not necessarily ready.

Inspect readiness conditions and Redis Enterprise health.

------------------------------------------------------------------------

# Part 68 --- Liveness

## 70. Caution

Do not modify liveness/readiness probes casually to suppress failures.

Fix the underlying issue or follow vendor guidance.

------------------------------------------------------------------------

# Part 69 --- Restart Count

## 71. Trend

``` bash
kubectl get pods -n <namespace>
```

A rising restart count can indicate instability even if pods are
currently Running.

------------------------------------------------------------------------

# Part 70 --- Node CPU Pressure

## 72. Investigate

Check:

``` text
node CPU
pod CPU
requests
limits
CPU throttling
other workloads
```

Dedicated nodes may reduce noisy-neighbor risk.

------------------------------------------------------------------------

# Part 71 --- Node Memory Pressure

## 73. Investigate

Check:

``` text
Redis memory
container memory
node memory
requests/limits
eviction events
other workloads
```

------------------------------------------------------------------------

# Part 72 --- Disk Pressure

## 74. Node

`DiskPressure` can disrupt scheduling and workloads.

Investigate:

``` text
node filesystem
container images
logs
ephemeral storage
persistent storage
```

------------------------------------------------------------------------

# Part 73 --- Ephemeral Storage

## 75. Often Missed

Logs and temporary files can consume node ephemeral storage even when
Redis persistent volumes are healthy.

------------------------------------------------------------------------

# Part 74 --- Monitoring

## 76. Layers

Monitor:

``` text
Redis database
Redis node/shard
Redis Enterprise
operator
pod/container
Kubernetes node
PVC/storage
network
```

------------------------------------------------------------------------

# Part 75 --- Dashboard Correlation

## 77. Same Timeline

Correlate:

``` text
Redis P99
pod restart
node pressure
Kubernetes event
storage latency
operator reconciliation
```

on one incident timeline.

------------------------------------------------------------------------

# Part 76 --- Alerting

## 78. Useful Kubernetes Alerts

Examples:

``` text
Redis pod not ready
restart spike
Pending pod
node not ready
memory pressure
disk pressure
PVC capacity
operator unavailable
reconciliation failure
```

Tune alerts to architecture.

------------------------------------------------------------------------

# Part 77 --- Monitoring the Operator

## 79. Important

If the operator is unhealthy, Redis may continue serving while
lifecycle/reconciliation operations fail.

Alert separately on operator health.

------------------------------------------------------------------------

# Part 78 --- Backup Integration

## 80. Validate

Understand:

``` text
Redis Enterprise backup mechanism
object storage/network dependency
credentials
Kubernetes secret dependency
restore workflow
```

------------------------------------------------------------------------

# Part 79 --- Backup Is Not PVC Snapshot by Default

## 81. Caution

Do not assume an arbitrary Kubernetes volume snapshot is a supported
Redis Enterprise backup.

Use supported Redis Enterprise backup/recovery procedures.

------------------------------------------------------------------------

# Part 80 --- Disaster Recovery

## 82. Include Kubernetes Dependencies

DR must account for:

``` text
operator
CRDs/manifests
secrets
certificates
storage
network
DNS
Redis backup
application routing
```

------------------------------------------------------------------------

# Part 81 --- GitOps

## 83. Desired State

If GitOps manages Redis Enterprise resources:

``` text
Git
  |
controller
  |
Kubernetes CR
  |
Redis operator
  |
Redis Enterprise
```

Know which controller owns which layer.

------------------------------------------------------------------------

# Part 82 --- GitOps During Incident

## 84. Avoid Configuration Fight

An emergency manual fix may be reverted by GitOps.

Use the approved incident procedure for reconciliation control.

------------------------------------------------------------------------

# Part 83 --- Change Management

## 85. Kubernetes Changes

Treat changes to:

``` text
node pool
storage class
network policy
operator
CRD
resources
affinity
PDB
```

as Redis-impacting production changes.

------------------------------------------------------------------------

# Part 84 --- Node Pool Upgrade

## 86. Plan

Before upgrading Kubernetes nodes:

``` text
verify Redis health
verify N-1 capacity
verify PDB
verify placement
verify storage
cordon/drain according to supported process
validate after each node
```

------------------------------------------------------------------------

# Part 85 --- Kubernetes Upgrade

## 87. Compatibility First

Before Kubernetes control-plane/node upgrade:

``` text
check Redis operator support
check Redis Enterprise support
check CRD compatibility
check CSI/network plugin compatibility
```

------------------------------------------------------------------------

# Part 86 --- Operator Upgrade

## 88. Separate Change

Treat operator upgrades as controlled production changes.

Validate:

``` text
supported source/target
CRD changes
Redis Enterprise compatibility
rollback/recovery
```

------------------------------------------------------------------------

# Part 87 --- Redis Enterprise Upgrade

## 89. Use Chapter 42

Apply the upgrade/change engineering principles from Chapter 42 plus
Kubernetes-specific compatibility and scheduling checks.

------------------------------------------------------------------------

# Part 88 --- Hands-On Lab

## 90. Safety

Use a disposable or approved nonproduction Kubernetes environment.

Do not deliberately evict production Redis pods for training.

------------------------------------------------------------------------

# Part 89 --- Lab: Discover Environment

## 91. Commands

``` bash
kubectl version
kubectl get nodes -o wide
kubectl get crd | grep -i redis
kubectl api-resources | grep -i redis
kubectl get pods -A | grep -i redis
```

Record the actual operator and resource names.

------------------------------------------------------------------------

# Part 90 --- Lab: Pod Placement

## 92. Inspect

``` bash
kubectl get pods -n <namespace> -o wide
kubectl get nodes --show-labels
```

Map each Redis Enterprise pod to:

``` text
node
zone
node pool
```

------------------------------------------------------------------------

# Part 91 --- Lab: Resource Requests

## 93. Inspect

``` bash
kubectl get pod <pod> -n <namespace> -o yaml
```

Review container:

``` text
requests
limits
```

Compare with node allocatable capacity.

------------------------------------------------------------------------

# Part 92 --- Lab: PDB

## 94. Inspect

``` bash
kubectl get pdb -n <namespace>
kubectl describe pdb <pdb> -n <namespace>
```

Record:

``` text
desired healthy
current healthy
disruptions allowed
```

------------------------------------------------------------------------

# Part 93 --- Lab: PVC/PV

## 95. Inspect

``` bash
kubectl get pvc -n <namespace>
kubectl get pv
```

Trace:

``` text
pod -> PVC -> PV -> StorageClass
```

------------------------------------------------------------------------

# Part 94 --- Lab: Events

## 96. Inspect

``` bash
kubectl get events -n <namespace> \
  --sort-by='.lastTimestamp'
```

Identify normal and abnormal scheduling/storage events.

------------------------------------------------------------------------

# Part 95 --- Lab: DNS

## 97. Test

From an approved disposable diagnostic pod in the application namespace,
resolve the Redis endpoint.

Verify:

``` text
DNS name
IP
port
TLS hostname
```

------------------------------------------------------------------------

# Part 96 --- Lab: Connectivity

## 98. Layers

Test in order:

``` text
DNS
TCP
TLS
Redis authentication
Redis PING/smoke operation
```

This isolates failures quickly.

------------------------------------------------------------------------

# Part 97 --- Lab: Cordon

## 99. Disposable Node

This rehearsal is **not a routine inspection command**. Use a dedicated **nonproduction, disposable node with no critical workloads**, only after approval from the Kubernetes/Redis platform owner. First record your `kubectl config current-context`, the full node name, existing pod placement, PDB state and recovery/uncordon owner. Never use a production node as a shortcut.

**Preflight (read-only):**

``` bash
kubectl config current-context
kubectl get node <lab-node> -o wide
kubectl get pods -A --field-selector spec.nodeName=<lab-node>
kubectl get node <lab-node> -o jsonpath='{.spec.unschedulable}'
```

**Expected:** Context identifies the approved test cluster; the selected node exists and is reserved for this exercise. The final field is blank or `false` when schedulable. If it already reports `true`, stop and investigate ownership rather than changing it.

**Only after separate approval**, cordon the exact lab node and inspect its scheduling state:

``` bash
kubectl cordon <lab-node>
kubectl get node <lab-node> -o jsonpath='{.spec.unschedulable}'
```

**Expected:** The cordon command confirms the selected node is marked unschedulable; the JSONPath query returns `true`. This **does not evict existing pods** and does **not** prove failover, pod recovery or N-1 capacity.

In the same approved change, restore scheduling:

``` bash
kubectl uncordon <lab-node>
kubectl get node <lab-node> -o jsonpath='{.spec.unschedulable}'
```

**Expected:** The exact node is reported uncordoned and the JSONPath field is absent or `false`. Recheck scheduling, Redis redundancy and application metrics. If the postcondition fails, stop and follow the owner-approved recovery procedure; do not move on to a drain or failover exercise.

**Evidence:** Context, node, owner/ticket, PDB and remaining headroom, before/after unschedulable field, active workload inventory, rollback decision, and `PASS / FAIL / NOT EXECUTED`. Any unperformed step is `NOT EXECUTED`; documentation alone is not runtime validation.

References: [kubectl cordon](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_cordon/), [kubectl uncordon](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_uncordon/).

------------------------------------------------------------------------

# Part 98 --- Lab: Drain Rehearsal

## 100. Controlled

Using the supported Redis Enterprise/Kubernetes maintenance procedure,
rehearse a node drain.

Record:

``` text
PDB behavior
pod movement
Redis health
application P99
replication
recovery time
```

Do not force the drain through failed safety gates.

------------------------------------------------------------------------

# Part 99 --- Lab: Node Failure

## 101. Disposable

Simulate a lab node failure through an approved mechanism.

Measure:

``` text
detection
Redis failover
pod recovery
application errors
reconnect
redundancy restoration
```

------------------------------------------------------------------------

# Part 100 --- Lab: Pending Pod

## 102. Failure Injection

Create a disposable test pod with impossible resource/placement
requirements.

Use:

``` bash
kubectl describe pod
```

to identify the scheduling reason.

Do not modify Redis production resources for this test.

------------------------------------------------------------------------

# Part 101 --- Lab: Memory Pressure

## 103. Disposable

Use a controlled test workload/node environment to demonstrate
Kubernetes memory pressure.

Observe:

``` text
node condition
events
pod behavior
```

Stop before affecting shared workloads.

------------------------------------------------------------------------

# Part 102 --- Lab: NetworkPolicy

## 104. Controlled

Apply a lab-only policy that blocks a disposable client from Redis.

Observe application failure.

Restore policy and verify recovery.

------------------------------------------------------------------------

# Part 103 --- Lab: Secret Failure

## 105. Disposable Client

Provide an invalid lab Redis credential to a test client.

Confirm:

``` text
pod runs
network works
Redis authentication fails
```

This distinguishes platform health from credential failure.

------------------------------------------------------------------------

# Part 104 --- Failure Injection

## 106. Ten Scenarios

1.  Redis pod Pending due to insufficient CPU.
2.  Redis/test pod Pending due to affinity/taint mismatch.
3.  PVC mount failure.
4.  Pod OOMKilled.
5.  Kubernetes node MemoryPressure.
6.  Node drain blocked by PDB.
7.  Node failure triggers Redis recovery.
8.  NetworkPolicy blocks application traffic.
9.  Secret/credential error breaks Redis authentication.
10. Operator reconciliation becomes unavailable.

For each record:

``` text
detection
Redis impact
application impact
Kubernetes evidence
mitigation
recovery
prevention
```

------------------------------------------------------------------------

# Part 105 --- Troubleshooting Matrix

## 107. Symptoms

  ------------------------------------------------------------------------
  Symptom                 Kubernetes Checks        Redis Checks
  ----------------------- ------------------------ -----------------------
  Pod Pending             events, resources,       topology/capacity
                          affinity, taints, PVC    

  CrashLoopBackOff        logs, previous logs,     Redis process/health
                          OOM, secret              

  App timeout             DNS, policy, service,    Redis latency/health
                          node                     

  Auth failure            secret delivery          Redis identity/ACL

  High latency            node CPU, throttling,    shard CPU/P99
                          network, storage         

  Failover issue          node/pod events,         replication/topology
                          placement                

  Backup failure          secret/network/storage   backup job/status

  Pod evicted             node pressure/events     redundancy/recovery

  Drain blocked           PDB                      Redis maintenance state

  CR not converging       operator logs/events     Redis target state
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# Part 106 --- Runbook 1: Redis Pod Pending

## 108. Procedure

``` text
1. Describe pod.
2. Read FailedScheduling events.
3. Check CPU/memory availability.
4. Check node selector/affinity.
5. Check taints/tolerations.
6. Check PVC/volume topology.
7. Check admission policy.
8. Correct authoritative configuration.
9. Verify scheduling.
10. Validate Redis health.
```

------------------------------------------------------------------------

# Part 107 --- Runbook 2: Redis Pod Restart / CrashLoop

## 109. Procedure

``` text
1. Confirm restart count.
2. Describe pod.
3. Check last termination reason.
4. Read current/previous logs.
5. Check OOM/resources.
6. Check secrets/config/TLS.
7. Check storage.
8. Correct root cause.
9. Validate Redis replication/health.
10. Validate application recovery.
```

------------------------------------------------------------------------

# Part 108 --- Runbook 3: Node Drain

## 110. Procedure

``` text
1. Confirm approved maintenance.
2. Check Redis health/redundancy.
3. Check N-1 capacity.
4. Check PDB/disruptions allowed.
5. Check storage topology.
6. Cordon node.
7. Drain using supported procedure.
8. Monitor Redis/application.
9. Complete node maintenance and uncordon.
10. Verify placement/redundancy.
```

------------------------------------------------------------------------

# Part 109 --- Runbook 4: Kubernetes Node Failure

## 111. Procedure

``` text
1. Confirm node failure.
2. Confirm affected Redis pods.
3. Check Redis failover.
4. Check application errors/P99.
5. Check pod rescheduling.
6. Check PVC/volume attachment.
7. Check remaining capacity.
8. Restore/replace node as appropriate.
9. Restore Redis redundancy.
10. Record RTO/evidence.
```

------------------------------------------------------------------------

# Part 110 --- Runbook 5: Application Cannot Reach Redis

## 112. Procedure

``` text
1. Confirm application scope.
2. Resolve Redis DNS.
3. Test TCP path.
4. Test TLS.
5. Test Redis authentication.
6. Check Service/endpoints.
7. Check NetworkPolicy/firewall.
8. Check Redis health.
9. Restore failing layer.
10. Validate application.
```

------------------------------------------------------------------------

# Part 111 --- Runbook 6: PVC / Storage Failure

## 113. Procedure

``` text
1. Identify affected pod/PVC.
2. Describe pod and PVC.
3. Check PV/StorageClass.
4. Check CSI events.
5. Check zone/node attachment.
6. Check storage platform health.
7. Protect Redis redundancy.
8. Follow supported storage recovery.
9. Validate Redis data/replication.
10. Validate application and backup.
```

------------------------------------------------------------------------

# Part 112 --- Kubernetes Inventory Template

## 114. Record

``` text
Cluster:
Kubernetes version:
Redis operator version:
Redis Enterprise version:
Namespaces:
Node pools:
Zones:
StorageClass:
CSI:
Network plugin:
GitOps controller:
Monitoring:
Backup integration:
```

------------------------------------------------------------------------

# Part 113 --- Redis Pod Placement Template

## 115. Record

  Pod   Role   Node   Zone   Node Pool   PVC   Status
  ----- ------ ------ ------ ----------- ----- --------
                                               

------------------------------------------------------------------------

# Part 114 --- Node Maintenance Checklist

## 116. Before

-   [ ] Redis healthy.
-   [ ] Replication healthy.
-   [ ] No active incident.
-   [ ] N-1 capacity sufficient.
-   [ ] PDB reviewed.
-   [ ] Pod placement reviewed.
-   [ ] PVC topology reviewed.
-   [ ] Application monitoring active.
-   [ ] Rollback/recovery understood.
-   [ ] Change approved.

## 117. After

-   [ ] Node Ready.
-   [ ] Redis pods healthy.
-   [ ] Redis databases healthy.
-   [ ] Replication restored.
-   [ ] P99 normal.
-   [ ] Error rate normal.
-   [ ] PVCs healthy.
-   [ ] PDB healthy.
-   [ ] Node placement acceptable.
-   [ ] Change evidence recorded.

------------------------------------------------------------------------

# Part 115 --- Production Acceptance Checklist

## 118. Kubernetes Platform Engineering

-   [ ] Kubernetes version inventoried.
-   [ ] Redis Enterprise operator version inventoried.
-   [ ] Redis Enterprise version inventoried.
-   [ ] CRDs inventoried.
-   [ ] Compatibility matrix validated.
-   [ ] Operator namespace/health documented.
-   [ ] Redis custom resources documented.
-   [ ] Pod placement documented.
-   [ ] Node labels documented.
-   [ ] Affinity/anti-affinity reviewed.
-   [ ] Taints/tolerations reviewed.
-   [ ] Failure-domain placement validated.
-   [ ] CPU requests reviewed.
-   [ ] CPU throttling monitored where applicable.
-   [ ] Memory requests/limits reviewed.
-   [ ] OOM monitoring active.
-   [ ] Node pressure alerts active.
-   [ ] PVC/PV/StorageClass documented.
-   [ ] Storage performance monitored.
-   [ ] Reclaim policy understood.
-   [ ] PDB reviewed and tested.
-   [ ] Node drain procedure rehearsed.
-   [ ] N-1 node capacity validated.
-   [ ] Services/endpoints documented.
-   [ ] DNS tested.
-   [ ] NetworkPolicy reviewed.
-   [ ] TLS/secret delivery validated.
-   [ ] Kubernetes RBAC reviewed.
-   [ ] Operator monitoring active.
-   [ ] Backup integration validated.
-   [ ] DR includes Kubernetes dependencies.
-   [ ] GitOps ownership documented.
-   [ ] Six production runbooks validated.
-   [ ] Ten failure scenarios exercised.

------------------------------------------------------------------------

# Knowledge Validation

## 119. Questions

1.  Why does Kubernetes add another troubleshooting layer for Redis?
2.  What does the Redis Enterprise operator do?
3.  Why can manual changes be reverted?
4.  Which versions belong in the platform inventory?
5.  Why must operator/Kubernetes/Redis compatibility be validated?
6.  What can cause a pod to remain Pending?
7.  What is the difference between node affinity and toleration?
8.  Why use pod anti-affinity?
9.  Why can strict anti-affinity hurt maintenance?
10. What is the purpose of CPU requests?
11. Why can CPU limits affect latency?
12. What can cause OOMKilled?
13. What is the difference between Redis eviction and Kubernetes
    eviction?
14. Why does volume topology affect scheduling?
15. Why must PV reclaim policy be understood?
16. What does a PodDisruptionBudget protect?
17. Why can a drain legitimately block?
18. Why should drain protections not be bypassed blindly?
19. Why is N-1 capacity important for Kubernetes maintenance?
20. How can application HPA affect Redis?
21. Why should Redis not be scaled like a generic stateless Deployment?
22. How can NetworkPolicy mimic a Redis outage?
23. Why are Kubernetes events valuable?
24. Why should previous container logs be checked after restart?
25. What can cause FailedMount?
26. Why monitor the operator separately from Redis?
27. Why is an arbitrary PVC snapshot not automatically a Redis backup?
28. Why must GitOps ownership be understood during incidents?
29. What should be validated before a Kubernetes node upgrade?
30. What must pass before Redis Enterprise Kubernetes operations are
    production-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 120. Lab Completion

-   [ ] Discovered Kubernetes/Redis versions.
-   [ ] Discovered Redis CRDs.
-   [ ] Located operator.
-   [ ] Mapped Redis pods to nodes/zones.
-   [ ] Reviewed resource requests/limits.
-   [ ] Reviewed PDB.
-   [ ] Traced pod to PVC/PV/StorageClass.
-   [ ] Reviewed Kubernetes events.
-   [ ] Tested DNS.
-   [ ] Tested layered connectivity.
-   [ ] Rehearsed cordon/uncordon.
-   [ ] Rehearsed supported node drain.
-   [ ] Tested disposable node failure.
-   [ ] Diagnosed Pending pod.
-   [ ] Observed controlled node pressure.
-   [ ] Tested NetworkPolicy denial.
-   [ ] Tested invalid Redis secret.
-   [ ] Exercised ten failure scenarios.
-   [ ] Used troubleshooting matrix.
-   [ ] Reviewed six production runbooks.
-   [ ] Completed Kubernetes inventory.
-   [ ] Completed pod-placement table.
-   [ ] Completed node-maintenance checklist.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 121. Lab Cleanup

Remove only disposable Chapter 45 resources:

``` text
diagnostic pods
test workloads
lab NetworkPolicies
temporary secrets
temporary labels/taints
failure-injection objects
```

Restore lab nodes:

``` bash
kubectl uncordon <lab-node>
```

if they were cordoned.

Verify:

``` text
nodes Ready
Redis pods healthy
Redis databases healthy
PDB healthy
PVCs healthy
```

Do not delete operator-managed Redis resources unless the lab
specifically created them for disposal.

------------------------------------------------------------------------

# 122. Key Takeaways

1.  Redis Enterprise on Kubernetes must be operated as both a Redis and
    Kubernetes system.
2.  The operator is a reconciliation control plane; change authoritative
    desired state.
3.  Kubernetes, operator, Redis Enterprise, and CRD versions must be
    compatible.
4.  Pod scheduling depends on resources, affinity, taints, topology, and
    storage.
5.  Anti-affinity improves failure isolation but can reduce
    schedulability.
6.  Resource requests influence placement; limits can influence runtime
    behavior.
7.  Kubernetes OOM and eviction are distinct from Redis key eviction.
8.  Persistent storage topology can determine where Redis pods can
    recover.
9.  PDBs protect voluntary disruption but do not guarantee application
    availability.
10. Node drains require Redis health, redundancy, capacity, PDB, and
    storage prechecks.
11. Do not force through failed disruption protections without
    understanding impact.
12. N-1 capacity is essential for maintenance and node failure.
13. Application autoscaling can multiply Redis connections and traffic.
14. Redis Enterprise should be scaled using supported product/operator
    procedures.
15. DNS, Services, NetworkPolicy, TLS, and secrets can all cause
    apparent Redis outages.
16. Kubernetes events and previous container logs are core incident
    evidence.
17. Running does not mean Ready or healthy.
18. Monitor Redis, operator, pods, nodes, storage, and network together.
19. Redis backup must use supported Redis Enterprise recovery
    mechanisms.
20. DR includes operator, CRDs, secrets, PKI, storage, network, and
    Redis data.
21. GitOps can revert emergency manual changes if ownership is not
    understood.
22. Kubernetes node and operator upgrades are Redis-impacting changes.
23. Failure drills should cover scheduling, storage, memory, network,
    node, and operator failures.
24. Node maintenance needs before-and-after acceptance checks.
25. Production readiness requires Kubernetes failure testing in addition
    to Redis testing.

------------------------------------------------------------------------

# 123. References

Validate exact Redis Enterprise Kubernetes resource names, schemas,
compatibility, scheduling recommendations, storage requirements, and
maintenance procedures against the deployed product/operator versions.

Recommended official documentation areas:

-   Redis Enterprise for Kubernetes
-   Redis Enterprise Kubernetes operator
-   Redis Enterprise custom resources / CRDs
-   Redis Enterprise Kubernetes compatibility
-   Redis Enterprise Kubernetes deployment
-   Redis Enterprise Kubernetes persistent storage
-   Redis Enterprise Kubernetes networking
-   Redis Enterprise Kubernetes security
-   Redis Enterprise backup and restore
-   Redis Enterprise upgrades on Kubernetes
-   Kubernetes scheduling
-   Kubernetes affinity and anti-affinity
-   Kubernetes taints and tolerations
-   Kubernetes PodDisruptionBudgets
-   Kubernetes persistent volumes
-   Kubernetes node pressure and eviction
-   Kubernetes NetworkPolicy
-   Kubernetes node maintenance and drain

------------------------------------------------------------------------

# Next Chapter

**Chapter 46 --- Redis Enterprise Cloud Infrastructure, Networking &
Storage Engineering**

Chapter 46 will cover:

-   cloud architecture
-   VM/node sizing
-   availability zones
-   private networking
-   DNS
-   load balancers
-   security groups/firewalls
-   network throughput
-   latency
-   persistent disks
-   IOPS/throughput
-   storage failure
-   cloud maintenance
-   capacity
-   multi-zone design
-   failure injection
-   troubleshooting
-   cloud infrastructure runbooks
-   production acceptance
