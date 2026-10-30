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
# Dangerous commands should never be executable in a short-course SQL lab.
BLOCKED_SQL = re.compile(
    r"^\s*(?:DROP\b|TRUNCATE\b|DELETE\b|REVOKE\b|GRANT\b|"
    r"ALTER\s+(?!SESSION\b)|CREATE\s+OR\s+REPLACE\b|"
    r"CREATE\s+USER\b|CREATE\s+ROLE\b|"
    r"CREATE\s+WAREHOUSE\b)",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|private_key|api[_-]?key)\s*[:=]\s*['\"][^'\"]{4,}['\"]"),
)
MD_LINK = re.compile(r"\]\(([^)\s]+)(?:\s+['\"][^)\n]+['\"])?\)")
SQL_BLOCK = re.compile(r"(?ms)^~~~sql\s*\n(.*?)^~~~\s*$")
AGENDA_ROW = re.compile(r"^\|[^|\n]+\|\s*(\d+)\s*min\s*\|\s*$", re.MULTILINE)

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
        for line_number, line in enumerate(raw.splitlines(), 1):
            live = line.split("--", 1)[0].strip()
            if live and BLOCKED_SQL.match(live):
                problems.append(str(rel) + f": blocked runtime SQL at {line_number}: {live[:100]}")
        if "level-01" in path.name:
            if "LEVEL_01_SMOKE_RESULT" not in raw or "CREATE TEMP TABLE" not in raw:
                problems.append(str(rel) + ": expected L1 assertions or TEMP scope missing")
        if "level-02" in path.name:
            if "ALTER SESSION UNSET QUERY_TAG" not in raw or "ROWCOUNT => 100" not in raw:
                problems.append(str(rel) + ": L2 query tag cleanup or row count missing")
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
            # Check executable lines only; comments and educational prose do not count.
            for line in block.splitlines():
                live = line.split("--", 1)[0].strip()
                if live and BLOCKED_SQL.match(live):
                    problems.append(str(rel) + f": blocked lab SQL in block {i}: {live[:100]}")
        meta.update({"agenda_minutes": sum(minutes), "sql_blocks": len(blocks)})
    return problems, meta

def main() -> int:
    errors: list[str] = []
    evidence = []
    for file in (*LESSONS, "README.md", "STATUS.md", "validation/VALIDATION-PLAN.md",
                 "validation/RUNTIME-EVIDENCE-TEMPLATE.md",
                 "validation/runtime/README.md",
                 "validation/runtime/level-01-smoke.sql",
                 "validation/runtime/level-02-smoke.sql"):
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
