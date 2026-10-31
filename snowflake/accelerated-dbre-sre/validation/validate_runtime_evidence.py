#!/usr/bin/env python3
"""V03 offline audit of *manually collected* Snowflake lab evidence.

Does NOT connect to Snowflake, run SQL, or authenticate query IDs.
A valid record is eligible for independent review, never certified.
No external dependencies; JSON input remains entirely local.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

VALID_LEVELS = set(range(1, 8))
REQUIRED_ASSERTIONS = {
    1: {
        "values_rows": 3,
        "training_rows": 3,
        "east_count": 2,
        "east_sales": 170,
        "west_count": 1,
        "west_sales": 80,
        "smoke_result": "PASS",
    },
    2: {"generated_rows": 100, "tag_cleanup": "CONFIRMED"},
    3: {
        "training_rows": 1000,
        "distinct_ids": 1000,
        "total_amount": 54110,
        "region_1_rows": 100,
        "region_1_amount": 5060,
        "smoke_result": "PASS",
    },
}
REQUIRED_TESTS = {
    1: {"session_context", "sample_values", "temporary_table", "aggregates", "assertion", "session_cleanup"},
    2: {"session_context", "role_visibility", "generated_rows", "tagged_history", "tag_cleanup"},
    3: {"session_context", "namespace_check", "generated_table", "assertion", "query_profile", "session_cleanup"},
    4: {"warehouse_metering", "warehouse_load", "query_failures", "billing_history"},
    5: {"role_context", "show_grants", "show_roles"},
    6: {"account_retention", "database_retention"},
    7: {"session_context", "recent_query_history", "tabletop"},
}
OPTIONAL_TESTS = {
    5: {"login_history"},
    6: {"table_retention", "time_travel"},
    7: {"account_query_history"},
}
NONPROD = {"TRAINING", "STAGING", "SANDBOX"}
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
ISO_UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
QUERY_ID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DANGEROUS_KEYS = {
    "password", "token", "secret", "private_key", "keypair",
    "query_text", "sql_text", "user_name", "client_ip", "email", "patient",
    "raw_output", "raw_error", "access_token", "refresh_token",
}
ALLOWED_KEYS = {
    "schema_version", "level", "execution_state", "revision_sha",
    "started_at_utc", "environment", "approval_reference",
    "runner_alias", "query_ids", "tests", "assertions",
    "cleanup_verified", "redaction_checked", "evidence_reference",
    "independent_reviewer_alias", "independent_review_status",
}
ALLOWED_ENV = {"classification", "account_alias", "warehouse_alias", "role_alias", "scratch_schema_alias"}
ALLOWED_TEST = {"id", "status", "query_id", "notes_code"}
VALID_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
SECURITY_ADMIN_ROLES = {"ACCOUNTADMIN", "SECURITYADMIN", "ORGADMIN", "GLOBALORGADMIN", "USERADMIN"}

def parse_utc(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not ISO_UTC.fullmatch(value):
        errors.append(f"{field} must be an ISO-8601 UTC timestamp such as 2026-10-30T18:00:00Z")
        return
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if dt > datetime.now(timezone.utc):
            errors.append(f"{field} must not be in the future")
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")

def no_unknown_keys(data: dict, allowed: set[str], prefix: str, errors: list[str]) -> None:
    for key in data:
        if key not in allowed:
            errors.append(f"Unexpected {prefix} key: {key}; remove raw query data or unsupported fields")

def audit(data: object) -> dict:
    errors = []
    warnings = []
    if not isinstance(data, dict):
        return {"outcome": "REJECTED", "errors": ["Evidence must be a JSON object"], "warnings": []}
    no_unknown_keys(data, ALLOWED_KEYS, "top-level", errors)
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    level = data.get("level")
    if not isinstance(level, int) or isinstance(level, bool) or level not in VALID_LEVELS:
        errors.append("level must be an integer between 1 and 7")
        level = None
    state = data.get("execution_state")
    if state not in {"NOT_RUN", "EXECUTED"}:
        errors.append("execution_state must be NOT_RUN or EXECUTED")
    env = data.get("environment")
    if not isinstance(env, dict):
        errors.append("environment must be an object")
        env = {}
    no_unknown_keys(env, ALLOWED_ENV, "environment", errors)
    classification = env.get("classification")
    if classification not in NONPROD:
        errors.append("environment classification must be TRAINING, STAGING or SANDBOX (never production)")
    for key in ("account_alias", "warehouse_alias", "role_alias", "scratch_schema_alias"):
        value = env.get(key)
        if not isinstance(value, str) or len(value.strip()) < 3 or len(value) > 100:
            errors.append(f"environment.{key} must be a non-sensitive 3–100 character alias")
    role = str(env.get("role_alias", "")).upper()
    if role in SECURITY_ADMIN_ROLES:
        errors.append("administrator role prohibited for accelerated smoke evidence")
    # Sensitive values must not appear as structured output. The allowed aliases
    # must be sanitized by the human operator; we do not inspect live Snowflake data.
    if state == "NOT_RUN":
        if data.get("query_ids") or data.get("tests") or data.get("assertions"):
            errors.append("NOT_RUN template must contain no query IDs, test results or assertions")
        if data.get("independent_review_status") == "APPROVED":
            errors.append("NOT_RUN evidence cannot claim independent approval")
        return {
            "outcome": "REJECTED" if errors else "NOT_RUN",
            "level": level, "errors": errors,
            "warnings": ["No Snowflake SQL was executed; do not mark V03 PASS."],
        }
    revision = data.get("revision_sha")
    if not isinstance(revision, str) or not HEX_SHA.fullmatch(revision):
        errors.append("EXECUTED record needs a 40-character Git revision SHA")
    parse_utc(data.get("started_at_utc"), "started_at_utc", errors)
    for key in ("approval_reference", "runner_alias", "evidence_reference"):
        value = data.get(key)
        if not isinstance(value, str) or not (3 <= len(value) <= 150):
            errors.append(f"{key} must be a short, non-sensitive reference/alias")
    if data.get("redaction_checked") is not True:
        errors.append("redaction_checked must be true")
    if data.get("cleanup_verified") is not True:
        errors.append("cleanup_verified must be true")
    ids = data.get("query_ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) and QUERY_ID.fullmatch(i) for i in ids):
        errors.append("At least one properly formatted Snowflake QUERY_ID is required")
        ids = []
    if len(set(ids)) != len(ids):
        errors.append("Duplicate query IDs are not accepted")
    tests = data.get("tests")
    if not isinstance(tests, list):
        errors.append("tests must be an array of attested test records")
        tests = []
    found = set()
    test_ids = set()
    for t in tests:
        if not isinstance(t, dict):
            errors.append("each test entry must be an object")
            continue
        no_unknown_keys(t, ALLOWED_TEST, "test", errors)
        test_id = t.get("id")
        if not isinstance(test_id, str):
            errors.append("each test needs a string id")
            continue
        if test_id in test_ids:
            errors.append(f"duplicated test id: {test_id}")
        test_ids.add(test_id)
        result = t.get("status")
        if result not in VALID_STATUSES:
            errors.append(f"{test_id}: invalid status")
        if result == "PASS":
            if t.get("query_id") not in ids:
                errors.append(f"{test_id}: PASS requires a query_id in query_ids")
            found.add(test_id)
        elif result in {"FAIL", "BLOCKED", "NOT_RUN"}:
            warnings.append(f"{test_id}: {result}, not eligible for V03 acceptance")
        note = t.get("notes_code")
        if note is not None and (not isinstance(note, str) or len(note) > 60 or not re.fullmatch(r"[A-Za-z0-9_-]+", note)):
            errors.append(f"{test_id}: notes_code must be an opaque non-sensitive code")
    if level:
        valid = REQUIRED_TESTS[level] | OPTIONAL_TESTS.get(level, set())
        for test_id in test_ids - valid:
            errors.append(f"Unknown level {level} test ID: {test_id}")
        missing = REQUIRED_TESTS[level] - found
        if missing:
            errors.append("Missing mandatory PASS tests: " + ", ".join(sorted(missing)))
    assertions = data.get("assertions")
    if not isinstance(assertions, dict):
        errors.append("assertions must be an object")
        assertions = {}
    if level:
        expected = REQUIRED_ASSERTIONS.get(level, {})
        if set(assertions) - set(expected):
            errors.append("Unexpected assertion keys: " + ", ".join(sorted(set(assertions) - set(expected))))
        for key, correct in expected.items():
            if assertions.get(key) != correct:
                errors.append(f"{key}: expected {correct!r}, observed {assertions.get(key)!r}")
        if level == 2:
            if "tagged_history" in found and len(ids) < 2:
                warnings.append("Level 2: capture separate generator and history-query IDs where possible")
    if data.get("independent_review_status") not in {"PENDING", "APPROVED", "REJECTED"}:
        errors.append("independent_review_status must be PENDING, APPROVED or REJECTED")
    if data.get("independent_review_status") == "APPROVED":
        if not isinstance(data.get("independent_reviewer_alias"), str) or len(data["independent_reviewer_alias"]) < 3:
            errors.append("independent approval requires a reviewer alias")
    if data.get("independent_review_status") == "REJECTED":
        errors.append("independent reviewer rejected evidence")
    # Critical rule: passing local checks only makes records ready for an
    # independent human reviewer. No trusted source authenticated these IDs.
    outcome = "REJECTED" if errors else "READY_FOR_INDEPENDENT_REVIEW"
    return {"outcome": outcome, "level": level, "errors": errors, "warnings": warnings,
            "verification_limit": "Offline structure/expectation check only; query IDs and output claims not authenticated"}

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local V03 manual evidence (never connects to Snowflake)")
    parser.add_argument("--input", type=Path, required=True, help="Local JSON evidence; do not commit real output")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"outcome": "REJECTED", "errors": [type(exc).__name__]}))
        return 2
    result = audit(data)
    # Never print raw evidence or secrets; only invariant validation results.
    print(json.dumps(result, indent=2))
    return 0 if result["outcome"] == "READY_FOR_INDEPENDENT_REVIEW" else 2

if __name__ == "__main__":
    sys.exit(main())
