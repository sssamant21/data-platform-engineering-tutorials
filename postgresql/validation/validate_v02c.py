#!/usr/bin/env python3
"""V02-C: inventory and statically parse embedded PostgreSQL tutorial examples.

No tutorial example is EXECUTED. Review-needed examples are not silently
accepted as runnable. Produces per-block JSON evidence for independent review.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from validate_v02 import sql_prep

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
FENCE = re.compile(r"^ {0,3}(" + chr(96) + r"{3,}|~{3,})(.*)$")
LANGUAGE = {"sql": "sql", "postgresql": "sql", "psql": "sql",
            "bash": "bash", "sh": "bash", "shell": "bash",
            "powershell": "powershell", "ps1": "powershell"}
DANGEROUS = re.compile(
    r"\b(?:DROP\s+(?:SCHEMA|DATABASE|TABLE|INDEX)|TRUNCATE|"
    r"DELETE\s+FROM|ALTER\s+SYSTEM|CREATE\s+INDEX\s+CONCURRENTLY|"
    r"REINDEX|pg_terminate_backend|pg_cancel_backend|"
    r"pg_drop_replication_slot|pg_promote|pg_ctl\s+\S*\s*(?:stop|restart)|"
    r"rm\s+-[A-Za-z]*r[A-Za-z]*f)\b", re.I)
EXTERNAL = re.compile(
    r"postgresql/(?:labs|scripts|monitoring|templates|projects)/[A-Za-z0-9_./-]+"
    r"\.(?:sql|py|sh|ps1|json|yml|yaml|conf)")
CONTEXT = re.compile(
    r"\b(?:expected|should\s+(?:show|return|display)|verify|result|output|"
    r"acceptance|observe|evidence|check\s+(?:that|for)|compare)\b", re.I)
PLACEHOLDER = re.compile(
    r"<(?:HOST|PORT|USER|PASSWORD|DATABASE|PATH|YOUR|REPLACE|PID|VALUE|"
    r"TARGET|CLUSTER)[^>]*>|REPLACE_WITH_|YOUR_[A-Z_]+|\b(?:PRIMARY_HOST|STANDBY_HOST)\b")
PWSH = (
    "$tokens=$null;$errs=$null;"
    "[System.Management.Automation.Language.Parser]::ParseFile("
    "$env:PG_V02C_PATH,[ref]$tokens,[ref]$errs)|Out-Null;"
    "if($errs.Count){$errs|ForEach-Object{$_.ToString()};exit 1}"
)


def extract(text):
    blocks = []
    marker = None
    language = ""
    first = 0
    collected = []
    for i, line in enumerate(text.splitlines(), start=1):
        found = FENCE.match(line)
        if marker is None:
            if found:
                marker = found.group(1)
                language = found.group(2).strip().split(maxsplit=1)[0].lower() if found.group(2).strip() else ""
                first = i
                collected = []
        elif found and found.group(1)[0] == marker[0] and len(found.group(1)) >= len(marker) and not found.group(2).strip():
            blocks.append((first, i, language, "\n".join(collected)))
            marker = None
        else:
            collected.append(line)
    return blocks, marker is not None


def parse_bash(code):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".sh", delete=False) as temp:
        temp.write(code)
        name = temp.name
    try:
        result = subprocess.run(["bash", "-n", name], capture_output=True, text=True, timeout=15)
        return None if result.returncode == 0 else result.stderr.strip()[:300]
    finally:
        Path(name).unlink(missing_ok=True)


def parse_powershell(code):
    if not shutil.which("pwsh"):
        return "PowerShell parser unavailable"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ps1", delete=False) as temp:
        temp.write(code)
        name = temp.name
    try:
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-NonInteractive", "-Command", PWSH],
            capture_output=True, text=True, timeout=20, env=dict(os.environ, PG_V02C_PATH=name))
        return None if result.returncode == 0 else (result.stdout + result.stderr).strip()[:300]
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json-out", type=Path)
    p.add_argument("--require-parsers", action="store_true")
    args = p.parse_args()
    try:
        from pglast import parse_sql
    except ImportError:
        parse_sql = None
    problems = []
    if args.require_parsers and not parse_sql:
        problems.append({"type": "missing_sql_parser", "detail": "install requirements-v02.txt"})
    records = []
    totals = collections.Counter()
    categories = collections.Counter()
    for file in sorted((ROOT / "chapters").glob("*.md")) + sorted((ROOT / "labs").rglob("*.md")):
        text = file.read_text(encoding="utf-8")
        lines = text.splitlines()
        blocks, unclosed = extract(text)
        if unclosed:
            problems.append({"type": "unclosed_fence", "file": str(file.relative_to(REPO))})
        for start, end, language, code in blocks:
            totals["all_blocks"] += 1
            lang = LANGUAGE.get(language, "other")
            totals["language_" + lang] += 1
            if lang == "other":
                continue
            label = "runnable_candidate"
            reason = []
            syntax = "NOT_ATTEMPTED"
            if not code.strip():
                label = "manual_review"
                reason.append("empty snippet")
            if PLACEHOLDER.search(code):
                label = "manual_review"
                reason.append("environment-specific placeholder")
            if re.search(r"^\s*(?:\$\s+|PS>\s+|postgres(?:=#|->)|\.\.\.)", code, re.M | re.I):
                label = "manual_review"
                reason.append("prompt or incomplete pseudocode")
            try:
                if label == "runnable_candidate":
                    if lang == "sql":
                        if not parse_sql:
                            syntax = "PARSER_UNAVAILABLE"
                        else:
                            clean, _ = sql_prep(code)
                            if clean.strip():
                                parse_sql(clean)
                                syntax = "PARSE_OK"
                            else:
                                label = "manual_review"
                                reason.append("psql client meta commands only")
                                syntax = "NOT_SQL"
                    elif lang == "bash":
                        issue = parse_bash(code)
                        if issue is None:
                            syntax = "PARSE_OK"
                        else:
                            label = "manual_review"
                            syntax = "PARSE_REVIEW"
                            reason.append(issue)
                    elif lang == "powershell":
                        issue = parse_powershell(code)
                        if issue is None:
                            syntax = "PARSE_OK"
                        else:
                            label = "manual_review"
                            syntax = "PARSE_REVIEW"
                            reason.append(issue)
                else:
                    syntax = "SKIPPED_REQUIRES_CONTEXT"
            except Exception as exc:
                label = "manual_review"
                syntax = "PARSE_REVIEW"
                reason.append(str(exc)[:280])
            context = "\n".join(lines[max(0, start - 12):min(len(lines), end + 15)])
            evidence_context = bool(CONTEXT.search(context))
            risky = sorted(set(x.group(0).upper() for x in DANGEROUS.finditer(code)))
            refs = sorted(set(EXTERNAL.findall(code)))
            missing = [ref for ref in refs if not (REPO / ref).is_file()]
            if missing:
                problems.append({"type": "missing_example_asset", "file": str(file.relative_to(REPO)),
                                 "start_line": start, "targets": missing})
            if risky:
                categories["contains_potentially_destructive_command"] += 1
            if not evidence_context:
                categories["no_nearby_expected_result_language"] += 1
            totals["classification_" + label] += 1
            totals["syntax_" + syntax] += 1
            records.append({"file": str(file.relative_to(REPO)), "line": start,
                            "language": lang, "classification": label, "syntax": syntax,
                            "reasons": reason, "nearby_result_or_evidence_guidance": evidence_context,
                            "risk_tokens": risky, "referenced_assets": refs,
                            "preview": code[:130].replace("\n", " ")})
    status = "FAIL" if problems else "PASS_INVENTORY_WITH_REVIEW_ITEMS"
    report = {"version": "V02-C", "status": status,
              "scope": "chapters and labs fenced blocks; static only, zero commands executed",
              "totals": dict(totals), "review_flags": dict(categories),
              "blocking_errors": problems, "examples": records}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "examples"}
    summary["sample_review_items"] = [r for r in records if r["classification"] == "manual_review"][:20]
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
