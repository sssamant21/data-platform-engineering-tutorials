#!/usr/bin/env python3
"""Non-executing Kafka curriculum fenced-block inventory and static validation.

No commands are executed. YAML requires PyYAML; without it YAML blocks are SKIPPED.
Usage: python kafka/qa/validate_code_blocks.py --root kafka --output kafka/qa/evidence/code-block-audit.json
Exit: 0 no syntax failures, 1 syntax failures, 2 setup/input error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
LANGUAGES = {
    "yaml": "yaml", "yml": "yaml", "json": "json", "jsonl": "jsonl", "ndjson": "jsonl",
    "powershell": "powershell", "pwsh": "powershell", "ps1": "powershell",
    "bash": "shell", "sh": "shell", "shell": "shell", "console": "shell",
    "python": "python", "py": "python", "properties": "properties",
    "text": "text", "plaintext": "text",
}
# Indicators require human review; never execute extracted content.
RISK_PATTERNS = [
    ("kubernetes_delete", re.compile(r"\bkubectl\s+delete\b", re.I)),
    ("namespace_delete", re.compile(r"\bkubectl\s+delete\s+(?:ns|namespace)\b", re.I)),
    ("force_delete", re.compile(r"--force\b|--grace-period[= ]0\b", re.I)),
    ("disk_delete", re.compile(r"\b(?:rm\s+-rf|Remove-Item\b.*-Recurse|mkfs\.)", re.I)),
    ("topic_delete", re.compile(r"\bkafka-topics(?:\.sh)?\b[^\n]*--delete\b", re.I)),
    ("secret_exposure", re.compile(r"(?i)(?:password|secret|token)\s*[:=]\s*['\"]?[^\s\"']{8,}")),
]
PLACEHOLDER = re.compile(r"(?i)\b(REPLACE|YOUR_|EXAMPLE_|TODO|TBD|CHANGEME)\b|<[^>\n]+>|\$\{[^}]+\}")


def extract(text: str):
    opener = None
    length = 0
    language = ""
    start = 0
    buf = []
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if opener is None:
            if match:
                token, info = match.groups()
                opener, length = token[0], len(token)
                language = info.strip().split()[0].lower() if info.strip() else ""
                start, buf = number, []
        elif match and match.group(1)[0] == opener and len(match.group(1)) >= length and not match.group(2).strip():
            yield start, number, language, "\n".join(buf), False
            opener, length, language, buf = None, 0, "", []
        else:
            buf.append(line)
    if opener is not None:
        yield start, None, language, "\n".join(buf), True


def validate(root: Path) -> dict:
    if not root.is_dir():
        raise ValueError(f"Directory not found: {root}")
    blocks = []
    files = sorted(root.rglob("*.md"))
    for file in files:
        rel = file.relative_to(root).as_posix()
        content = file.read_text(encoding="utf-8")
        for start, end, lang, body, unclosed in extract(content):
            kind = LANGUAGES.get(lang, lang or "untyped")
            flags = [name for name, pattern in RISK_PATTERNS if pattern.search(body)]
            placeholder = bool(PLACEHOLDER.search(body))
            result = "NOT_CHECKED"
            details = ""
            if unclosed:
                result, details = "FAIL", "Unclosed code fence"
            elif kind == "json":
                if placeholder:
                    result, details = "REVIEW", "Contains template placeholders; JSON parsing not definitive"
                else:
                    try:
                        json.loads(body)
                        result = "PASS"
                    except json.JSONDecodeError as exc:
                        result, details = "FAIL", f"JSON parse: {exc}"
            elif kind == "jsonl":
                if placeholder:
                    result, details = "REVIEW", "Contains template placeholders; JSON Lines parsing not definitive"
                else:
                    try:
                        records = [line for line in body.splitlines() if line.strip()]
                        if not records:
                            raise ValueError("JSON Lines fixture has no records")
                        for index, line in enumerate(records, 1):
                            try:
                                json.loads(line)
                            except json.JSONDecodeError as exc:
                                raise ValueError(f"JSON Lines record {index}: {exc}") from exc
                        result = "PASS"
                    except ValueError as exc:
                        result, details = "FAIL", str(exc)
            elif kind == "yaml":
                if placeholder:
                    result, details = "REVIEW", "Contains template placeholders; YAML parsing not definitive"
                elif yaml is None:
                    result, details = "SKIPPED", "PyYAML unavailable; install with python -m pip install PyYAML"
                else:
                    try:
                        list(yaml.safe_load_all(body))
                        result = "PASS"
                    except yaml.YAMLError as exc:
                        result, details = "FAIL", f"YAML parse: {str(exc).splitlines()[0]}"
            elif kind in ("shell", "powershell", "python"):
                result, details = "REVIEW", "Syntax/execution not checked by this tool"
            elif kind in ("text", "untyped", "properties"):
                result = "NOT_APPLICABLE"
            if flags and result == "PASS":
                details = "Syntax valid; operational risk flags still require review"
            blocks.append({
                "path": rel, "start_line": start, "end_line": end,
                "language": lang, "kind": kind, "lines": len(body.splitlines()),
                "has_placeholders": placeholder, "risk_flags": flags,
                "result": result, "detail": details,
            })
    counts = dict(sorted(Counter(b["result"] for b in blocks).items()))
    risk_counts = dict(sorted(Counter(flag for b in blocks for flag in b["risk_flags"]).items()))
    failures = [b for b in blocks if b["result"] == "FAIL"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Static fenced-block extraction and JSON/YAML parsing only; no execution, Kubernetes schema validation or shell lint.",
        "markdown_files": len(files), "code_blocks": len(blocks),
        "pyyaml_available": yaml is not None,
        "results": counts, "risk_flag_counts": risk_counts,
        "status": "FAIL" if failures else "PASS_WITH_REVIEW",
        "failures": failures, "blocks": blocks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("kafka"))
    parser.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/code-block-audit.json"))
    args = parser.parse_args()
    try:
        report = validate(args.root.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 2
    print(f"{report['status']}: {report['code_blocks']} blocks from {report['markdown_files']} Markdown files")
    print(f"Results: {report['results']}")
    print(f"Risk flags: {report['risk_flag_counts']}")
    print(f"Evidence: {args.output}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
