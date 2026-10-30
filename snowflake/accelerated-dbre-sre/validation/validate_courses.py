#!/usr/bin/env python3
"""Deterministic V01/V02 static gate for the Snowflake accelerated curriculum.

No Snowflake connection, secrets, third-party Python modules, or writes are used.
This is a structural/safety linter, NOT a SQL parser or runtime certification.
Run from any working directory: python3 .../validation/validate_courses.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

TRACK = Path(__file__).resolve().parents[1]
LESSONS = (
    "level-01-snowflake-fundamentals.md",
    "level-02-administration-fundamentals.md",
    "level-03-performance-query-optimization.md",
    "level-04-monitoring-observability-cost.md",
    "level-05-security-rbac-governance.md",
    "level-06-data-recovery-disaster-recovery.md",
    "level-07-production-incident-response.md",
)
REQUIRED = (
    "## Learning objectives",
    "## 60-minute lesson plan",
    "## Core concepts",
    "## Hands-on lab and expected results",
    "## DBRE/SRE troubleshooting quick reference",
    "## Knowledge check (with answers)",
    "## Operational safety and validation",
    "## Official documentation",
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|private_key|api[_-]?key)\s*[:=]\s*['\"][^'\"]{4,}['\"]"),
)
MD_LINK = re.compile(r"\]\(([^)\s]+)(?:\s+['\"][^)\n]+['\"])?\)")
SQL_BLOCK = re.compile(r"(?ms)^~~~sql\s*\n(.*?)^~~~\s*$")
AGENDA_ROW = re.compile(r"^\|[^|\n]+\|\s*(\d+)\s*min\s*\|\s*$", re.MULTILINE)


def executable_sql_statements(block: str) -> list[str]:
    """Split simple training SQL into statements, ignoring standard SQL comments.

    This intentionally does not implement Snowflake's full SQL grammar. Static
    checks are a defense-in-depth guard, never a replacement for code review.
    """
    without_blocks = re.sub(r"/\*.*?\*/", " ", block, flags=re.DOTALL)
    without_comments = "\n".join(
        line.split("--", 1)[0] for line in without_blocks.splitlines()
    )
    return [part.strip() for part in without_comments.split(";") if part.strip()]


def unsafe_sql_statements(block: str) -> list[str]:
    """Deny sensitive SQL and unexpected writes in executable lab examples."""
    problems = []
    for statement in executable_sql_statements(block):
        normalized = re.sub(r"\s+", " ", statement).strip().upper()
        # Block most privileged or destructive statements wherever they appear.
        # This also catches newlines between keywords (DROP\nTABLE, ALTER\nWAREHOUSE).
        if re.search(r"\b(?:DROP|TRUNCATE|DELETE|UPDATE|MERGE|GRANT|REVOKE)\b", normalized):
            problems.append("disallowed privileged/destructive SQL: " + normalized[:95])
            continue
        if normalized.startswith("CREATE OR REPLACE"):
            problems.append("CREATE OR REPLACE prohibited in short-course labs")
            continue
        if normalized.startswith("ALTER "):
            if not re.fullmatch(r"ALTER SESSION (?:SET QUERY_TAG\s*=\s*.+|UNSET QUERY_TAG)", normalized):
                problems.append("only session QUERY_TAG changes are allowed: " + normalized[:95])
            continue
        if normalized.startswith("CREATE "):
            if not (re.match(r"CREATE (?:TEMP|TEMPORARY) TABLE DBRE_SRE_[A-Z0-9_]+\b", normalized)
                    or re.match(r"CREATE TABLE DBRE_SRE_L6_RECOVERY\b", normalized)):
                problems.append("CREATE restricted to known scratch tables: " + normalized[:95])
            continue
        if normalized.startswith("INSERT "):
            if not re.match(r"INSERT INTO DBRE_SRE_L[136]_[A-Z0-9_]+\b", normalized):
                problems.append("INSERT target must be a training table: " + normalized[:95])
            continue
        if not re.match(r"(?:SELECT|SHOW|DESCRIBE|DESC|EXPLAIN)\b", normalized):
            problems.append("unexpected executable SQL command: " + normalized[:95])
    return problems

def check_file(path: Path, is_lesson: bool) -> tuple[list[str], dict]:
    problems = []
    if not path.is_file():
        return ["missing file: " + str(path)], {}
    raw = path.read_text(encoding="utf-8")
    rel = path.relative_to(TRACK)
    if raw.count("\n~~~") % 2:
        problems.append(str(rel) + ": unbalanced triple-tilde fences")
    if not raw.endswith("\n"):
        problems.append(str(rel) + ": missing final newline")
    for match in MD_LINK.finditer(raw):
        target = match.group(1).split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        linked = (path.parent / target).resolve()
        if not linked.is_file():
            problems.append(str(rel) + ": broken relative Markdown link " + target)
    for secret in SECRET_PATTERNS:
        if secret.search(raw):
            problems.append(str(rel) + ": possible embedded credential")
    meta = {"file": str(rel), "bytes": len(raw.encode("utf-8"))}
    if path.suffix.lower() == ".sql":
        for finding in unsafe_sql_statements(raw):
            problems.append(str(rel) + ": " + finding)
        if "level-01" in path.name:
            if "LEVEL_01_SMOKE_RESULT" not in raw or "CREATE TEMP TABLE" not in raw:
                problems.append(str(rel) + ": expected L1 assertions or TEMP scope missing")
        if "level-02" in path.name:
            if "ALTER SESSION UNSET QUERY_TAG" not in raw or "ROWCOUNT => 100" not in raw:
                problems.append(str(rel) + ": L2 query tag cleanup or row count missing")
        if "level-03" in path.name:
            if ("LEVEL_03_SMOKE_RESULT" not in raw or
                    "COUNT(DISTINCT ORDER_ID)" not in raw or
                    "SUM(AMOUNT) = 54110" not in raw or
                    "COUNT_IF(REGION_ID = 1) = 100" not in raw or
                    "SUM(IFF(REGION_ID = 1, AMOUNT, 0)) = 5060" not in raw):
                problems.append(str(rel) + ": L3 deterministic assertions missing")
        if "level-04" in path.name:
            if ("WAREHOUSE_METERING_HISTORY" not in raw or
                    "WAREHOUSE_LOAD_HISTORY" not in raw or
                    "METERING_DAILY_HISTORY" not in raw or
                    "EXECUTION_STATUS = 'fail'" not in raw):
                problems.append(str(rel) + ": L4 monitoring/billing evidence queries missing")
        if "level-05" in path.name:
            if ("CURRENT_SECONDARY_ROLES()" not in raw or
                    "SHOW GRANTS;" not in raw or
                    "ACCOUNT_USAGE.LOGIN_HISTORY" not in raw):
                problems.append(str(rel) + ": L5 RBAC and audit controls missing")
        if "level-06" in path.name:
            if ("MIN_DATA_RETENTION_TIME_IN_DAYS" not in raw or
                    "DATA_RETENTION_TIME_IN_DAYS" not in raw or
                    "AT (OFFSET => -60)" not in raw):
                problems.append(str(rel) + ": L6 retention/Time Travel controls missing")
        if "level-07" in path.name:
            if ("QUERY_HISTORY_BY_SESSION" not in raw or
                    "QUEUED_OVERLOAD_TIME" not in raw or
                    "ACCOUNT_USAGE.QUERY_HISTORY" not in raw or
                    "EXECUTION_STATUS = 'fail'" not in raw):
                problems.append(str(rel) + ": L7 incident triage controls missing")
    if is_lesson:
        for section in REQUIRED:
            if section not in raw:
                problems.append(str(rel) + ": missing " + section)
        if "**Status:** DRAFT" not in raw or "NOT RUN" not in raw:
            problems.append(str(rel) + ": explicit draft/runtime status missing")
        agenda = re.search(
            r"(?ms)^## 60-minute lesson plan\s*\n(.*?)(?=^## |\Z)", raw
        )
        minutes = [int(x) for x in AGENDA_ROW.findall(agenda.group(1))] if agenda else []
        if len(minutes) < 3 or sum(minutes) != 60:
            problems.append(str(rel) + f": agenda should total 60 minutes: {minutes}")
        if "**60 min**" not in raw:
            problems.append(str(rel) + ": missing agenda total declaration")
        if "Expected:" not in raw or "**Pass:**" not in raw:
            problems.append(str(rel) + ": missing observable expected output or pass criteria")
        blocks = SQL_BLOCK.findall(raw)
        if not blocks:
            problems.append(str(rel) + ": no fenced SQL lab")
        for i, block in enumerate(blocks, 1):
            for finding in unsafe_sql_statements(block):
                problems.append(str(rel) + f": SQL block {i}: " + finding)
        meta.update({"agenda_minutes": sum(minutes), "sql_blocks": len(blocks)})
    return problems, meta

def main() -> int:
    errors: list[str] = []
    evidence = []
    for file in (*LESSONS, "README.md", "STATUS.md", "validation/VALIDATION-PLAN.md",
                 "validation/V01-V02-INITIAL-AUDIT.md",
                 "validation/V02-SECOND-PASS-REVIEW.md",
                 "validation/V02-LEVELS-03-04-REVIEW.md",
                 "validation/RUNTIME-EVIDENCE-TEMPLATE.md",
                 "validation/runtime/README.md",
                 "validation/runtime/level-01-smoke.sql",
                 "validation/runtime/level-02-smoke.sql",
                 "validation/runtime/level-03-smoke.sql",
                 "validation/runtime/level-04-smoke.sql",
                 "validation/runtime/level-05-smoke.sql",
                 "validation/runtime/level-06-smoke.sql",
                 "validation/runtime/level-07-smoke.sql",
                 "validation/test_validator.py"):
        problems, metadata = check_file(TRACK / file, file in LESSONS)
        errors.extend(problems)
        if metadata:
            evidence.append(metadata)
    total = sum(item.get("agenda_minutes", 0) for item in evidence)
    if total != 420:
        errors.append(f"total lesson duration expected 420 minutes; got {total}")
    result = {
        "gate": "V01_V02_STATIC",
        "status": "PASS" if not errors else "FAIL",
        "lesson_count": len(LESSONS),
        "curriculum_minutes": total,
        "checks": evidence,
        "errors": errors,
        "scope": "Markdown structure, navigation, obvious secret and unsafe-SQL patterns",
        "limitations": "Not SQL execution, Snowflake permissions, production readiness or security audit",
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
