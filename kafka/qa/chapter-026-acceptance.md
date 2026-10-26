# Chapter 026 in-cluster network acceptance

`python kafka/qa/run_chapter_026.py` independently uses the pinned disposable
Kafka 4.0.0/KRaft/Strimzi 0.47.0 fixture and a version-matched Java diagnostic Job.
No broker listener, Service, EndpointSlice, NetworkPolicy, PVC or public exposure
resource is changed. Only a uniquely owned synthetic topic/client Job is created.

## Manuscript learning objectives and live checks

- Labs 01/03: require an internal selector-backed bootstrap Service and its actual
  client port; resolve numeric or named targetPorts from broker container ports.
  Count only ready, non-terminating EndpointSlice targets with matching Service
  UID, Pod UID, selector, actual Pod IPs and ready Kafka containers. Unknown/not-ready
  endpoint entries are not accepted as evidence of ready brokers.
- Labs 02/04: record the diagnostic Pod's real resolver configuration without
  assuming cluster.local; resolve bootstrap and all advertised broker names. Probe
  each distinct advertised broker by TCP and Kafka Admin requests, checking cluster
  identity. Map metadata DNS/ports/IPs back to all three verified broker Pod UIDs;
  aliases that point multiple IDs at one Pod are rejected.
- Lab 05: require RF3/full ISR, valid topic leaders and KRaft quorum. Six deterministic
  acknowledged records are reconciled after the negative probes, independently of
  readiness or bare TCP success. The Chapter 025 topic need not still exist.
- Labs 07/08: a reserved .invalid hostname must fail at the DNS layer under a bounded
  daemon lookup; a verified-unused bootstrap Service port must fail TCP and Kafka
  metadata calls. DNS failure, connection refusal/unreachability and timeout are
  classified explicitly, not misreported as authentication/ACL errors.
- Labs 06/11/15: capture actual NetworkPolicy, listener, Service, EndpointSlice,
  Pod/role, PVC-context and broker API metadata plus per-operation diagnostic timing.

Positive DNS/API calls, socket connects, invalid-host resolution, wrong-port metadata
and the overall Job/workflow have bounded timeouts. No failure injection changes the
cluster: negative probes run only from the disposable client. Source and expected
assertions are tied to immutable run/head/checkout evidence.

## Boundaries

This is internal plaintext networking acceptance, not TLS/SASL/ACL execution. It
awards no secure-client handshake or authorization credit. External load balancers,
Ingress/Route, cloud firewalls, cross-zone routing and production clients remain
NOT_EXECUTED. NetworkPolicy objects do not prove CNI enforcement; no deny or
cross-namespace isolation test is claimed on kind's default networking. No universal
p95/p99 SLO, packet-loss or production recovery guarantee is inferred from samples.

Read-only KRaft quorum and role inventory distinguish controller paths from the
client listener; the client never treats a controller endpoint as a broker. Persistent
single-host volumes provide context, not independent storage resilience. Enterprise
certification and independent security/assessor signoff remain NOT_CERTIFIED/PENDING.

JSON records ready endpoints, actual advertised-to-Pod mappings, resolver and negative
probe evidence, all client assertions, timing and pending secure/external gates.
Raw Kafka/network-policy/Service/EndpointSlice data, client logs and Kubernetes
failure diagnostics are uploaded for seven days. Existing fixture mappings and
max-parallel=2 orchestration remain intact; only network dependencies select 026.
