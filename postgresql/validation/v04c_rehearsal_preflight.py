#!/usr/bin/env python3
"""V04-C offline staging rehearsal preflight; NO operational actions or GO.

Requires a complete V04-A evidence packet, V04-B independent review metadata,
and a fresh V04-C authorization-request packet tied to BOTH exact files.
Metadata checks do NOT authenticate evidence or grant permission for failover.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

import v04_staging_readiness as a
import v04_independent_review as b

SCHEMA = "pg-ha-dr-v04c-1"
MAX_AGE = timedelta(minutes=5)
REQUIRED_FRESH = ("independent_fence", "candidate_replay",
                  "application_health", "backup_wal_restore", "rollback_ready")
AUTHORITY_ROLES = ("change_authority", "incident_commander")


def result(codes: list[str], now: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "result": ("NO_GO" if codes else "REQUIRES_LIVE_CHANGE_AUTHORITY_GO"),
        "reason_codes": sorted(set(codes)),
        "screened_at_utc": now.isoformat(),
        "authorization": "NONE",
        "execution": "NEVER",
        "fencing_verified_by_tool": False,
        "note": ("Offline metadata cannot authenticate evidence, prove "
                 "old-primary fencing or authorize a staging action. "
                 "A separately recorded and reverified live change-authority "
                 "decision is mandatory; this script cannot return GO."),
    }


def screen(staging: Any, review: Any, request: Any, *,
           now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issues: list[str] = []

    if not isinstance(staging, dict):
        issues.append("staging_packet_invalid")
        staging = {}
    if not isinstance(review, dict):
        issues.append("review_packet_invalid")
        review = {}
    if not isinstance(request, dict):
        return result(issues + ["rehearsal_packet_invalid"], now)

    stage_result = a.screen(staging, now=now)
    if stage_result["result"] != "EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW":
        issues.append("v04a_no_go")
        issues.extend("v04a_" + c for c in stage_result["reason_codes"])
    review_result = b.screen(staging, review, now=now)
    if review_result["result"] != "REVIEW_PACKET_COMPLETE_UNAUTHENTICATED":
        issues.append("v04b_no_go")
        issues.extend("v04b_" + c for c in review_result["reason_codes"])

    if a.contains_secret_keys(request):
        issues.append("sensitive_keys_not_allowed")
    if request.get("schema") != SCHEMA:
        issues.append("rehearsal_schema_invalid")
    if request.get("mode") != "offline_preflight_only":
        issues.append("operational_mode_refused")
    if request.get("requested_decision") != "request_manual_authorization":
        issues.append("automatic_go_refused")
    if request.get("environment") != "staging":
        issues.append("production_or_nonstaging_refused")

    # Identity and freshness gate: a review cannot be reused for another ticket,
    # cluster, window or after the evidence packet was changed.
    for field in ("environment_id", "change_ticket", "window_start_utc",
                  "window_end_utc"):
        v=request.get(field)
        if not a.good_text(v) or v != staging.get(field) or v != review.get(field):
            issues.append(f"{field}_binding_invalid")
    cluster = staging.get("cluster")
    cluster = cluster if isinstance(cluster, dict) else {}
    expected_id = cluster.get("system_identifier")
    if (not a.good_text(request.get("system_identifier")) or
            request.get("system_identifier") != expected_id or
            request.get("system_identifier") != review.get("system_identifier")):
        issues.append("system_identifier_binding_invalid")

    try:
        stage_sha = b.digest(staging)
        review_sha = b.digest(review)
    except (ValueError, TypeError):
        stage_sha = None
        review_sha = None
        issues.append("metadata_digest_invalid")
    if request.get("staging_manifest_sha256") != stage_sha or not b.good_sha(
            request.get("staging_manifest_sha256")):
        issues.append("staging_digest_mismatch")
    if request.get("independent_review_sha256") != review_sha or not b.good_sha(
            request.get("independent_review_sha256")):
        issues.append("independent_review_digest_mismatch")

    timestamp = a.parse_time(request.get("prepared_at_utc"))
    if timestamp is None or timestamp > now or now - timestamp > MAX_AGE:
        issues.append("rehearsal_request_not_fresh")

    approvals = staging.get("approvals")
    approvals = approvals if isinstance(approvals, dict) else {}
    reviewers = review.get("reviewers")
    reviewers = reviewers if isinstance(reviewers, dict) else {}
    prohibited_names = set()
    for packet in (approvals, reviewers):
        for value in packet.values():
            if isinstance(value, dict) and a.good_text(value.get("name")):
                prohibited_names.add(value["name"].casefold())
    if a.good_text(review.get("prepared_by")):
        prohibited_names.add(review["prepared_by"].casefold())

    authorities = request.get("authorities")
    authorities = authorities if isinstance(authorities, dict) else {}
    chosen = set()
    for role in AUTHORITY_ROLES:
        entry = authorities.get(role)
        entry = entry if isinstance(entry, dict) else {}
        person = entry.get("name")
        time = a.parse_time(entry.get("attested_at_utc"))
        if (not a.good_text(person) or not a.good_ref(entry.get("attestation_ref"))
                or entry.get("disposition") != "ready_for_independent_decision"):
            issues.append(f"{role}_attestation_missing")
        if time is None or time > now or now - time > MAX_AGE:
            issues.append(f"{role}_attestation_stale")
        if a.good_text(person):
            normalized = person.casefold()
            if normalized in prohibited_names or normalized in chosen:
                issues.append("authority_not_independent")
            chosen.add(normalized)

    # These are self-reported observations, not externally verified by code.
    fresh = request.get("fresh_observations")
    fresh = fresh if isinstance(fresh, dict) else {}
    for name in REQUIRED_FRESH:
        observation = fresh.get(name)
        observation = observation if isinstance(observation, dict) else {}
        checked = a.parse_time(observation.get("observed_at_utc"))
        if observation.get("reported_safe") is not True:
            issues.append(f"{name}_not_proven")
        if not a.good_ref(observation.get("evidence_ref")) or not b.good_sha(
                observation.get("evidence_sha256")):
            issues.append(f"{name}_evidence_missing")
        if checked is None or checked > now or now - checked > MAX_AGE:
            issues.append(f"{name}_observation_stale")
        if timestamp is not None and checked is not None and checked < timestamp:
            issues.append(f"{name}_observation_predates_request")

    # A fake/fabricated "GO" in an uploaded JSON file can never bypass the gate.
    if request.get("operational_go") is not None:
        issues.append("embedded_operational_go_refused")
    return result(issues, now)


def main() -> int:
    parser = argparse.ArgumentParser(description="V04-C offline NO-GO/preflight screen")
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    try:
        stage=json.loads(args.staging.read_text(encoding="utf-8"))
        review=json.loads(args.review.read_text(encoding="utf-8"))
        request=json.loads(args.request.read_text(encoding="utf-8"))
        verdict=screen(stage,review,request,now=now)
    except (OSError, UnicodeError, TypeError, ValueError):
        verdict=result(["invalid_or_unreadable_json"],now)
    output=json.dumps(verdict,indent=2)+"\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output,encoding="utf-8")
    print(output)
    return 0 if verdict["result"] == "REQUIRES_LIVE_CHANGE_AUTHORITY_GO" else 2


if __name__ == "__main__":
    sys.exit(main())
