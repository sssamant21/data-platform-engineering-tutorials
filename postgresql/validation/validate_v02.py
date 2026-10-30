#!/usr/bin/env python3
"""V02 PostgreSQL static code parse + privileged/destructive operation inventory.

Read-only: parses files and extracts Markdown fence types, does NOT run SQL,
PowerShell or database commands. Risk matches require manual classification.
"""
import argparse
import ast
import collections
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SQL_RISK = {
    "drop_schema": r"\bDROP\s+SCHEMA\b",
    "drop_database": r"\bDROP\s+DATABASE\b",
    "drop_table": r"\bDROP\s+TABLE\b",
    "truncate": r"\bTRUNCATE\b",
    "delete": r"\bDELETE\s+FROM\b",
    "update": r"\bUPDATE\s+[A-Za-z_]",
    "alter_system": r"\bALTER\s+SYSTEM\b",
    "backend_signal": r"\bpg_(?:terminate|cancel)_backend\s*\(",
    "reindex": r"\bREINDEX\b",
    "vacuum_full": r"\bVACUUM\s+(?:\([^)]*FULL\b|FULL\b)",
}
SHELL_RISK = {
    "recursive_delete": r"\brm\s+-(?:r|R|f){2,}\b|\bRemove-Item\b[^\n]*-Recurse\b",
    "pg_stop": r"\bpg_ctl\b[^\n]*\bstop\b",
    "docker_destroy": r"\bdocker\b[^\n]*\b(?:rm\b|down\s+-v\b)",
    "service_stop": r"\b(?:systemctl|service)\b[^\n]*\bstop\b",
}
FENCE = re.compile(r"^\s{0,3}(" + chr(96) + r"{3,}|~{3,})(.*)$")
ASSET = re.compile(r"postgresql/(?:labs|scripts|monitoring|templates|projects)/[A-Za-z0-9_./-]+\.(?:sql|py|sh|ps1|json|yml|yaml|conf)")
PGVAR = re.compile(r""":'[^']+'|:"[^"]+"|(?<!:):[A-Za-z_][A-Za-z_0-9]*""")
META = re.compile(r"^\s*\\")
INLINE_META = re.compile(r"\\(?:gexec|gset|gdesc|g|watch)\b[^\n]*", re.I)


def rel(path):
    return path.relative_to(REPO).as_posix()


def sql_prep(text):
    lines, skipped = [], 0
    for line in text.splitlines():
        if META.match(line):
            skipped += 1
        else:
            lines.append(INLINE_META.sub("", line))
    return PGVAR.sub("'__psql_variable__'", "\n".join(lines)), skipped


def command_check(args, env=None):
    p = subprocess.run(args, capture_output=True, text=True, timeout=20, env=env)
    return None if p.returncode == 0 else (p.stdout + p.stderr)[:600].strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json-out", type=Path)
    p.add_argument("--require-parsers", action="store_true")
    a = p.parse_args()
    counts = collections.Counter()
    errors, warnings, risks = [], [], []
    try:
        import pglast
        from pglast import parse_sql
        pg_version = pglast.__version__
    except ImportError:
        pg_version, parse_sql = None, None
        (errors if a.require_parsers else warnings).append(
            {"kind": "missing_pglast", "fix": "install pglast==8.7"})
    try:
        import yaml
    except ImportError:
        yaml = None
        (errors if a.require_parsers else warnings).append(
            {"kind": "missing_pyyaml", "fix": "install PyYAML==6.0.2"})
    roots = [ROOT / x for x in ("scripts", "labs", "monitoring", "chapters", "projects", "templates")]
    files = sorted(f for d in roots for f in d.rglob("*") if f.is_file())
    for f in files:
        ext = f.suffix.lower()
        if ext not in {".py", ".sh", ".ps1", ".sql", ".json", ".yml", ".yaml"}:
            continue
        counts["files_" + ext[1:]] += 1
        source = f.read_text(encoding="utf-8-sig")
        try:
            if ext == ".py":
                ast.parse(source, filename=rel(f))
            elif ext == ".sh":
                problem = command_check(["bash", "-n", str(f)])
                if problem:
                    raise SyntaxError(problem)
            elif ext == ".ps1":
                if shutil.which("pwsh"):
                    ps = ("$tokens=$null;$errors=$null;"
                          "[System.Management.Automation.Language.Parser]::ParseFile("
                          "$env:PG_V02_FILE,[ref]$tokens,[ref]$errors)|Out-Null;"
                          "if($errors.Count -gt 0){$errors|ForEach-Object{$_.ToString()};exit 1}")
                    problem = command_check(
                        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", ps],
                        env=dict(os.environ, PG_V02_FILE=str(f)))
                    if problem:
                        raise SyntaxError(problem)
                else:
                    warnings.append({"kind": "powershell_parser_missing", "file": rel(f)})
            elif ext == ".json":
                json.loads(source)
            elif ext in {".yml", ".yaml"} and yaml:
                yaml.safe_load(source)
            elif ext == ".sql" and parse_sql:
                sql, directives = sql_prep(source)
                counts["psql_directives_excluded"] += directives
                if sql.strip():
                    parse_sql(sql)
                    counts["sql_parsed"] += 1
        except Exception as exc:
            errors.append({"kind": "syntax_or_parse_failure", "file": rel(f),
                           "type": ext[1:], "message": str(exc)[:600]})
        patterns = SQL_RISK if ext == ".sql" else SHELL_RISK if ext in {".sh", ".ps1"} else {}
        for name, pattern in patterns.items():
            hits = list(re.finditer(pattern, source, flags=re.I))
            if hits:
                risks.append({"kind": name, "file": rel(f), "count": len(hits),
                              "first_line": source.count("\n", 0, hits[0].start()) + 1})
        if ext == ".sql" and "/labs/sql/" in "/" + rel(f) and "setup" in f.name:
            if re.search(r"DROP\s+SCHEMA\s+IF\s+EXISTS\b.{0,120}\bCASCADE\b", source, re.I | re.S):
                risks.append({"kind": "automatic_destructive_setup", "file": rel(f),
                              "action": "require explicit isolated-database guard or remove automatic reset"})
    fence_counts = collections.Counter()
    refs = set()
    missing = []
    for f in sorted(ROOT.rglob("*.md")):
        source = f.read_text(encoding="utf-8")
        opening = None
        for line in source.splitlines():
            marker = FENCE.match(line)
            if marker:
                symbol = marker.group(1)
                if opening is None:
                    opening = symbol
                    fence_counts[marker.group(2).strip().split(" ")[0].lower() or "(none)"] += 1
                elif opening[0] == symbol[0] and len(symbol) >= len(opening):
                    opening = None
        for match in ASSET.finditer(source):
            key = match.group(0)
            refs.add(key)
            if not (REPO / key).is_file():
                missing.append({"kind": "missing_textual_asset", "source": rel(f), "target": key})
    warnings.extend(missing)
    report = {
        "version": "V02", "execution": "STATIC_ONLY_NO_DATABASE_EXECUTION",
        "status": "FAIL" if errors else "PASS_PARSERS_PENDING_TECHNICAL_REVIEW",
        "parsers": {"pglast": pg_version, "yaml": bool(yaml), "pwsh": bool(shutil.which("pwsh"))},
        "counts": dict(sorted(counts.items())),
        "markdown_fence_languages": dict(sorted(fence_counts.items())),
        "textual_asset_references": len(refs),
        "error_count": len(errors), "warning_count": len(warnings),
        "risk_review_count": len(risks),
        "risk_categories": dict(sorted(collections.Counter(i["kind"] for i in risks).items())),
        "errors": errors, "warnings": warnings, "risk_review": risks,
    }
    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"errors", "warnings", "risk_review"}}, indent=2))
    print("Findings excerpt:", json.dumps(errors[:20] + warnings[:10] + risks[:12], indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
