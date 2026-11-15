#!/usr/bin/env python3
"""Static documentation guardrails for Elasticsearch engineering runbooks.

No Elasticsearch cluster is contacted. Passing this check NEVER certifies a runbook
for production use; see PRODUCTION-READINESS.md and VALIDATION-MATRIX.md.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "## When to use",
    "## Execution guardrails",
    "## Prechecks / read-only diagnostics",
    "## Approved procedure",
    "## Stop / escalate",
    "## Success criteria and evidence",
    "## Rollback / recovery",
    "## Official references",
]
errors: list[str] = []
docs = sorted(ROOT.glob("[0-9][0-9]-*.md"))
if len(docs) != 15:
    errors.append(f"Expected 15 runbooks, found {len(docs)}")
if len({p.name[:2] for p in docs}) != len(docs):
    errors.append("Duplicate runbook numbers")

for path in docs + sorted(ROOT.rglob("*.md")):
    if path not in docs and path.name != "README.md":
        # Templates and non-numbered docs are still checked for insecure commands.
        pass
    raw = path.read_text(encoding="utf-8")
    name = path.relative_to(ROOT)
    if path in docs:
        for heading in REQUIRED:
            if heading not in raw:
                errors.append(f"{name}: missing section {heading}")
        if "DRAFT" not in raw and "Draft" not in raw:
            errors.append(f"{name}: expected unvalidated status")
    if "--cacert" in raw or "ES_CA_CERT" in raw:
        errors.append(f"{name}: unexpected certificate-file argument")
    if raw.count("```") % 2:
        errors.append(f"{name}: unbalanced Markdown code fence")
    for m in re.finditer(r"```(bash|sh|powershell)\n([\s\S]*?)```", raw):
        lang, source = m.group(1), m.group(2)
        if re.search(r"(?<!\w)(?:--insecure|--cacert)(?!\w)", source):
            errors.append(f"{name}: insecure/certificate flag in shell example")
        if lang in ("bash", "sh"):
            for line in source.splitlines():
                if re.match(r"\s*curl\s", line):
                    if "--basic" not in line or not re.search(r"(?:--user\s+|-u\s+)", line):
                        errors.append(f"{name}: curl lacks username-only Basic Auth: {line[:90]}")
                    if re.search(r"(?:--user|-u)\s+\S+:[^\s'\"$]", line):
                        errors.append(f"{name}: possible embedded Basic Auth password")
            if not source.strip():
                continue
            result = subprocess.run(["bash", "-n"], input=source, text=True, capture_output=True, check=False)
            if result.returncode:
                errors.append(f"{name}: invalid bash example: {result.stderr.strip()[:180]}")

for path in sorted((ROOT / "templates" / "payloads").glob("*.json")):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")

if errors:
    print("\n".join("ERROR: " + e for e in errors))
    print(f"FAILED: {len(errors)} static check(s)")
    sys.exit(1)
print(f"PASS: {len(docs)} runbooks; Markdown/Basic Auth/bash syntax and example JSON checks")
print("NOTE: This does not validate Elasticsearch API compatibility, live cluster behavior, approvals, or safety.")
