#!/usr/bin/env python3
"""Offline V04 staging HA/DR evidence completeness check.

NO database connections, cloud APIs, shell commands, or operational actions.
This is an evidence-presence and freshness SCREEN, not proof of authenticity,
independent fencing, or authorization to promote a server.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "pg-ha-dr-v04-1"
REQUIRED_APPROVERS = ("dbre", "application_owner", "fencing_owner", "change_manager")
REQUIRED_FENCE = (
    "direct_write_denied", "old_primary_restart_denied",
    "orchestrator_restart_denied", "routing_bypass_denied",
    "storage_exclusion_verified", "independent_observation_confirmed",
)
METRICS = ("ha_rpo_seconds", "ha_rto_seconds", "pitr_rpo_seconds", "pitr_rto_seconds")
PLACEHOLDER = re.compile(r"(<[^>]*>|\b(REPLACE|TBD|TODO|PENDING|UNKNOWN)\b)", re.I)
IDENT = re.compile(r"^\d{8,25}$")
SENSITIVE_KEYS = {"password", "passwd", "secret", "private_key", "access_token",
                  "client_secret", "api_key", "connection_password"}


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def good_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.search(value)


def good_ref(value: Any) -> bool:
    # External immutable trace/evidence references only. Never fetch or follow them.
    return (good_text(value) and
            (value.startswith("https://") or value.startswith("evidence://")) and
            len(value) <= 2048)


def contains_secret_keys(document: Any) -> bool:
    if isinstance(document, dict):
        if any(str(k).lower() in SENSITIVE_KEYS for k in document):
            return True
        return any(contains_secret_keys(v) for v in document.values())
    if isinstance(document, list):
        return any(contains_secret_keys(v) for v in document)
    return False


def screen(document: Any, *, now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issues: list[str] = []

    def fail(code: str):
        if code not in issues:
            issues.append(code)

    if not isinstance(document, dict):
        return {
            "schema": SCHEMA, "result": "NO_GO",
            "reason_codes": ["document_not_object"],
            "authorization": "NONE", "execution": "NEVER",
            "note": "No operational actions can be taken from this tool.",
        }
    if contains_secret_keys(document):
        fail("sensitive_keys_not_allowed")
    if document.get("schema") != SCHEMA:
        fail("invalid_schema")
    if document.get("mode") != "evidence_review_only":
        fail("non_review_mode_refused")
    if document.get("environment") != "staging":
        fail("non_staging_environment_refused")
    if not good_text(document.get("environment_id")):
        fail("environment_identity_missing")
    if not good_text(document.get("change_ticket")):
        fail("change_ticket_missing")
    if not good_ref(document.get("change_ticket_ref")):
        fail("change_ticket_evidence_missing")

    start = parse_time(document.get("window_start_utc"))
    end = parse_time(document.get("window_end_utc"))
    if start is None or end is None or start >= end:
        fail("maintenance_window_invalid")
    elif not (start <= now <= end):
        fail("maintenance_window_not_current")

    cluster = document.get("cluster")
    cluster = cluster if isinstance(cluster, dict) else {}
    if cluster.get("postgres_major") != 18:
        fail("postgres18_identity_required")
    if not good_text(cluster.get("system_identifier")) or not IDENT.fullmatch(
            str(cluster.get("system_identifier", ""))):
        fail("cluster_system_identifier_missing")
    for label, expected_role in (("old_primary", "primary"), ("candidate", "standby")):
        node = cluster.get(label)
        node = node if isinstance(node, dict) else {}
        if node.get("role") != expected_role or not all(
                good_text(node.get(k)) for k in ("endpoint", "pgdata", "node_id")):
            fail(f"{label}_identity_missing")
    old = cluster.get("old_primary")
    candidate = cluster.get("candidate")
    if isinstance(old, dict) and isinstance(candidate, dict):
        for key in ("endpoint", "pgdata", "node_id"):
            if good_text(old.get(key)) and old.get(key) == candidate.get(key):
                fail(f"same_node_{key}")
    if not good_ref(cluster.get("topology_evidence_ref")):
        fail("topology_evidence_missing")

    # Self-attested fields are screened for completeness, never independently verified.
    approvals = document.get("approvals")
    approvals = approvals if isinstance(approvals, dict) else {}
    people = []
    for role in REQUIRED_APPROVERS:
        attestation = approvals.get(role)
        attestation = attestation if isinstance(attestation, dict) else {}
        name = attestation.get("name")
        approved = parse_time(attestation.get("approved_at_utc"))
        if (not good_text(name) or not good_ref(attestation.get("evidence_ref"))
                or approved is None or approved > now
                or now - approved > timedelta(days=14)):
            fail(f"approval_{role}_missing_or_stale")
        elif name.casefold() in people:
            fail("approvers_not_independent")
        else:
            people.append(name.casefold())

    targets = document.get("approved_objectives")
    targets = targets if isinstance(targets, dict) else {}
    for metric in METRICS:
        v = targets.get(metric)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or (
                not math.isfinite(v) or v <= 0):
            fail(f"objective_{metric}_missing")
    if not good_ref(targets.get("approval_evidence_ref")):
        fail("objectives_approval_missing")

    baseline = document.get("baseline")
    baseline = baseline if isinstance(baseline, dict) else {}
    observed = parse_time(baseline.get("observed_at_utc"))
    if (observed is None or observed > now or now - observed > timedelta(minutes=15)
            or baseline.get("healthy") is not True or
            not good_ref(baseline.get("evidence_ref"))):
        fail("healthy_fresh_baseline_missing")
    if (baseline.get("candidate_marker_replayed") is not True or
            not good_ref(baseline.get("candidate_replay_evidence_ref"))):
        fail("candidate_replay_proof_missing")
    gap = baseline.get("replay_gap_bytes")
    if isinstance(gap, bool) or not isinstance(gap, (int, float)) or (
            not math.isfinite(gap) or gap < 0):
        fail("replay_gap_measurement_missing")

    fence = document.get("fencing")
    fence = fence if isinstance(fence, dict) else {}
    if not good_text(fence.get("mechanism")) or not good_ref(fence.get("evidence_ref")):
        fail("independent_fencing_record_missing")
    fenced_at = parse_time(fence.get("verified_at_utc"))
    if fenced_at is None or fenced_at > now or now - fenced_at > timedelta(minutes=15):
        fail("independent_fencing_observation_stale")
    for check in REQUIRED_FENCE:
        if fence.get(check) is not True:
            fail(f"fence_{check}_unproven")
    observer = fence.get("observer")
    if not good_text(observer) or (
            good_text(approvals.get("dbre", {}).get("name"))
            and observer.casefold() == approvals["dbre"]["name"].casefold()):
        fail("independent_fencing_observer_missing")

    for section in ("backup", "application", "rollback"):
        value = document.get(section)
        value = value if isinstance(value, dict) else {}
        required = {
            "backup": ("base_backup_verified", "wal_archive_verified",
                       "isolated_restore_verified"),
            "application": ("routing_smoke_plan_verified", "rollback_route_verified"),
            "rollback": ("rejoin_or_rebuild_plan_verified", "incident_owner_assigned"),
        }[section]
        for key in required:
            if value.get(key) is not True:
                fail(f"{section}_{key}_unproven")
        if not good_ref(value.get("evidence_ref")):
            fail(f"{section}_evidence_missing")

    result = "NO_GO" if issues else "EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW"
    return {
        "schema": SCHEMA, "result": result,
        "reason_codes": sorted(issues),
        "screened_at_utc": now.isoformat(),
        "authorization": "NONE", "execution": "NEVER",
        "note": ("Field completeness does not authenticate evidence, prove "
                 "fencing, or authorize promotion/failover. An independent "
                 "staging change review and live observation remain mandatory."),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Offline non-operational HA/DR evidence screen")
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args()
    try:
        doc = json.loads(args.evidence.read_text(encoding="utf-8"))
        result = screen(doc)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"schema": SCHEMA, "result": "NO_GO", "reason_codes": ["invalid_input"],
                  "authorization": "NONE", "execution": "NEVER",
                  "note": f"Cannot parse evidence file: {type(exc).__name__}"}
    encoded = json.dumps(result, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(encoded, encoding="utf-8")
    print(encoded)
    return 0 if result["result"] == "EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW" else 2


if __name__ == "__main__":
    sys.exit(main())
