#!/usr/bin/env python3
"""V04-D Chapter 050 offline acceptance completeness; never certifies a system.

Only metadata checks. Does NOT fetch or authenticate evidence, connect to
PostgreSQL, execute fencing/promotion or issue enterprise authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any

import v04_staging_readiness as a
import v04_independent_review as b

SCHEMA = "pg-ha-dr-v04d-1"
METRICS = ("ha_rpo_seconds", "ha_rto_seconds",
           "pitr_rpo_seconds", "pitr_rto_seconds")
SCORECARD = (
    "base_backup_verified", "wal_archive_continuous",
    "isolated_pitr_valid_rows", "old_primary_independently_fenced",
    "candidate_freshness_approved", "exactly_one_writable_primary",
    "application_smoke_passed", "former_primary_rejoined_safely",
    "ha_rpo_rto_within_approved_limits",
    "pitr_rpo_rto_within_approved_limits",
    "alerts_runbooks_reviewed",
)
SCENARIOS = (
    "fence_failure_no_promotion", "stale_standby_no_promotion",
    "archive_gap_restore_refused", "failed_rewind_rebuild_fallback",
    "application_route_rollback",
)
REVIEWERS = ("dbre", "application", "security_fencing", "change_management")


def verdict(reasons: list[str], now: datetime) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "result": ("NO_GO" if reasons else
                   "READY_FOR_EXTERNAL_CERTIFICATION_REVIEW"),
        "reason_codes": sorted(set(reasons)),
        "screened_at_utc": now.isoformat(),
        "certification": "NOT_CERTIFIED",
        "authorization": "NONE",
        "execution": "NEVER",
        "evidence_authenticated_by_tool": False,
        "note": ("Only self-reported packet completeness and arithmetic were "
                 "screened. An independent authority must authenticate "
                 "original records and decide separately. No operational GO "
                 "or enterprise certification is ever issued by this script."),
    }


def screen(staging: Any, independent: Any, preflight: Any, record: Any,
           *, now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str] = []
    if any(not isinstance(x, dict) for x in
           (staging, independent, preflight, record)):
        return verdict(["packet_not_object"], now)
    if a.contains_secret_keys(record):
        errors.append("sensitive_keys_in_record")
    if record.get("schema") != SCHEMA:
        errors.append("schema_invalid")
    if record.get("mode") != "offline_certification_review_only":
        errors.append("non_review_mode_refused")
    if record.get("requested_disposition") != "submit_for_external_certification_review":
        errors.append("machine_or_self_certification_refused")
    if any(x.get("environment") != "staging" for x in (staging, independent, preflight, record)):
        errors.append("non_staging_environment")
    if record.get("operational_go") is not None or record.get("certified") is not None:
        errors.append("embedded_go_or_certification_refused")
    stage_cluster = staging.get("cluster")
    stage_cluster = stage_cluster if isinstance(stage_cluster, dict) else {}
    for field in ("environment_id", "change_ticket", "window_start_utc",
                  "window_end_utc"):
        if (not a.good_text(record.get(field)) or
                record.get(field) != staging.get(field) or
                record.get(field) != independent.get(field) or
                record.get(field) != preflight.get(field)):
            errors.append(field + "_binding_mismatch")
    sid=stage_cluster.get("system_identifier")
    if (not a.good_text(record.get("system_identifier")) or
            any(x.get("system_identifier") != sid for x in
                (independent, preflight, record))):
        errors.append("cluster_binding_mismatch")
    try:
        digests = (b.digest(staging), b.digest(independent), b.digest(preflight))
    except (ValueError, TypeError):
        errors.append("noncanonical_prior_packet")
        digests = (None, None, None)
    for key, expected in zip(("v04a_sha256", "v04b_sha256", "v04c_sha256"), digests):
        if not b.good_sha(record.get(key)) or record.get(key) != expected:
            errors.append(key + "_mismatch")
    if preflight.get("staging_manifest_sha256") != digests[0] or (
            preflight.get("independent_review_sha256") != digests[1]):
        errors.append("v04c_prior_binding_invalid")
    if independent.get("staging_manifest_sha256") != digests[0]:
        errors.append("v04b_prior_binding_invalid")
    # Historical rehearsal data may be audited after the approved window.
    # We do NOT rerun V04-C using today's timestamp or imply live preflight
    # approval from a stored self-attestation.
    if (preflight.get("mode") != "offline_preflight_only" or
            preflight.get("requested_decision") != "request_manual_authorization"):
        errors.append("v04c_request_not_review_only")
    if record.get("v04c_preflight_screen_ref") is None or not a.good_ref(
            record.get("v04c_preflight_screen_ref")):
        errors.append("v04c_preflight_audit_missing")
    if not a.good_ref(record.get("independent_fencing_recheck_ref")):
        errors.append("independent_fencing_recheck_missing")

    exercise = record.get("rehearsal")
    exercise = exercise if isinstance(exercise, dict) else {}
    if exercise.get("executed") is not True or exercise.get("outcome") != "PASS":
        errors.append("actual_staging_rehearsal_not_proven")
    operator = exercise.get("operator")
    if not a.good_text(operator):
        errors.append("operator_missing")
    start = a.parse_time(exercise.get("started_at_utc"))
    end = a.parse_time(exercise.get("ended_at_utc"))
    window_start = a.parse_time(staging.get("window_start_utc"))
    window_end = a.parse_time(staging.get("window_end_utc"))
    if (start is None or end is None or window_start is None or window_end is None
            or not (window_start <= start < end <= window_end)
            or end > now):
        errors.append("rehearsal_window_or_timeline_invalid")
    # A post-event report cannot claim that its approvals were granted AFTER
    # an operator started the rehearsal. It must bind authentic pre-action logs.
    approval_times = []
    controls = preflight.get("authorities")
    controls = controls if isinstance(controls, dict) else {}
    for control in controls.values():
        if isinstance(control, dict):
            approval_times.append(a.parse_time(control.get("attested_at_utc")))
    reviewers = independent.get("reviewers")
    reviewers = reviewers if isinstance(reviewers, dict) else {}
    for reviewer in reviewers.values():
        if isinstance(reviewer, dict):
            approval_times.append(a.parse_time(reviewer.get("reviewed_at_utc")))
    prepped = a.parse_time(preflight.get("prepared_at_utc"))
    approval_times.append(prepped)
    if start is not None and (any(t is None or t > start
                                  for t in approval_times)):
        errors.append("pre_rehearsal_approvals_invalid")
    final_obs = preflight.get("fresh_observations")
    final_obs = final_obs if isinstance(final_obs, dict) else {}
    for key in ("independent_fence","candidate_replay","application_health",
                "backup_wal_restore","rollback_ready"):
        obs = final_obs.get(key)
        obs = obs if isinstance(obs, dict) else {}
        observed_at = a.parse_time(obs.get("observed_at_utc"))
        if start is None or observed_at is None or (
                observed_at > start or (start - observed_at).total_seconds() > 300):
            errors.append("pre_rehearsal_" + key + "_stale")
    authority_at = a.parse_time(record.get("manual_change_authority_go_at_utc"))
    if (start is None or authority_at is None or authority_at > start or
            (prepped is not None and authority_at < prepped)):
        errors.append("external_go_time_invalid")
    if not a.good_ref(record.get("manual_change_authority_go_ref")):
        errors.append("external_manual_authority_record_missing")
    for k in ("fence_survived_restart_attempt", "one_writer_observed",
              "client_transactions_restored", "former_primary_rejoined_readonly",
              "no_unapproved_promotion", "abort_controls_observed"):
        if exercise.get(k) is not True:
            errors.append("rehearsal_" + k + "_unproven")
    for k in ("client_probe_evidence_ref", "old_primary_fence_evidence_ref",
              "rejoin_evidence_ref", "timeline_evidence_ref"):
        if not a.good_ref(exercise.get(k)):
            errors.append("rehearsal_" + k + "_missing")

    targets = staging.get("approved_objectives")
    targets = targets if isinstance(targets, dict) else {}
    measurements = record.get("measured_objectives")
    measurements = measurements if isinstance(measurements, dict) else {}
    for key in METRICS:
        entry=measurements.get(key)
        entry=entry if isinstance(entry, dict) else {}
        measured = entry.get("observed_seconds")
        target = targets.get(key)
        if (isinstance(measured, bool) or not isinstance(measured, (int, float))
                or not math.isfinite(measured) or measured < 0):
            errors.append(key + "_measured_missing")
        elif (isinstance(target, bool) or not isinstance(target, (int, float))
              or not math.isfinite(target) or target <= 0):
            errors.append(key + "_approved_target_missing")
        elif measured > target:
            errors.append(key + "_exceeds_approved_target")
        t0=a.parse_time(entry.get("start_utc"))
        t1=a.parse_time(entry.get("end_utc"))
        if (t0 is None or t1 is None or
                (start is not None and t0 < start) or
                (end is not None and t1 > end) or
                t0 > t1 or t1 > now):
            errors.append(key + "_timing_invalid")
        elif (isinstance(measured, (int,float)) and not isinstance(measured,bool)
              and math.isfinite(measured)
              and abs((t1 - t0).total_seconds() - measured) > .01):
            errors.append(key + "_arithmetic_mismatch")
        if not a.good_ref(entry.get("evidence_ref")) or not b.good_sha(
                entry.get("evidence_sha256")):
            errors.append(key + "_source_evidence_missing")
        if key.endswith("_rpo_seconds") and not a.good_ref(
                entry.get("acknowledged_commit_boundary_ref")):
            errors.append(key + "_commit_boundary_missing")

    for field, required in (("acceptance_gates", SCORECARD),
                            ("negative_path_scenarios", SCENARIOS)):
        obj=record.get(field)
        obj=obj if isinstance(obj, dict) else {}
        for name in required:
            row=obj.get(name)
            row=row if isinstance(row, dict) else {}
            if row.get("status") != "PASS":
                errors.append(field + "_" + name + "_not_passed")
            if (not a.good_ref(row.get("evidence_ref")) or
                    not b.good_sha(row.get("evidence_sha256")) or
                    not a.good_text(row.get("observer"))):
                errors.append(field + "_" + name + "_evidence_missing")

    signoffs=record.get("independent_final_signoffs")
    signoffs=signoffs if isinstance(signoffs, dict) else {}
    excluded=set()
    for item in (operator, preflight.get("prepared_by"),
                 independent.get("prepared_by")):
        if a.good_text(item):
            excluded.add(item.casefold())
    controls=preflight.get("authorities")
    controls=controls if isinstance(controls, dict) else {}
    for participant in controls.values():
        if isinstance(participant, dict) and a.good_text(participant.get("name")):
            excluded.add(participant["name"].casefold())
    names=set()
    for role in REVIEWERS:
        item=signoffs.get(role)
        item=item if isinstance(item, dict) else {}
        name=item.get("name")
        seen=a.parse_time(item.get("reviewed_at_utc"))
        if (not a.good_text(name) or
                item.get("disposition") != "recommend_external_certification_review"
                or not a.good_ref(item.get("attestation_ref"))):
            errors.append("final_" + role + "_signature_missing")
        if (seen is None or seen > now or
                (end is not None and seen < end)):
            errors.append("final_" + role + "_timestamp_invalid")
        if a.good_text(name):
            n=name.casefold()
            if n in names or n in excluded:
                errors.append("final_signoff_not_independent")
            names.add(n)
    return verdict(errors,now)


def main() -> int:
    p=argparse.ArgumentParser(description="V04-D offline Chapter 050 readiness")
    for key in ("staging", "review", "preflight", "acceptance"):
        p.add_argument("--" + key, required=True, type=Path)
    p.add_argument("--json-out", type=Path)
    x=p.parse_args()
    now=datetime.now(timezone.utc)
    try:
        records=[json.loads(getattr(x,k).read_text(encoding="utf-8")) for k
                 in ("staging","review","preflight","acceptance")]
        out=screen(*records,now=now)
    except (OSError,UnicodeError,ValueError,TypeError):
        out=verdict(["invalid_or_unreadable_input"],now)
    encoded=json.dumps(out,indent=2)+"\n"
    if x.json_out:
        x.json_out.parent.mkdir(parents=True,exist_ok=True)
        x.json_out.write_text(encoded,encoding="utf-8")
    print(encoded)
    return 0 if out["result"]=="READY_FOR_EXTERNAL_CERTIFICATION_REVIEW" else 2


if __name__=="__main__":
    sys.exit(main())
