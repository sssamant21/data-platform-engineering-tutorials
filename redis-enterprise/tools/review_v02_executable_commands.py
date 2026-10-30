#!/usr/bin/env python3
"""V02 offline executable-command triage: high-risk operations and output cues.

The output is a REVIEW QUEUE, not a proof a command is unsafe or has no correct
output. It never executes tutorial code or connects to external services.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from validate_v02_examples import CHAPTER, find_blocks, expected_nearby

LANGS = {"redis", "bash", "sh", "shell", "console", "terminal",
         "powershell", "ps1", "cmd"}
RULES = [
    ("database_flush", "high", re.compile(r"\bFLUSH(?:ALL|DB)\b", re.I)),
    ("tls_verification_bypass", "high",
     re.compile(r"\bcurl\b[^\n]*(?:\s-k(?:s)?\b|\s--insecure\b)", re.I)),
    ("inline_password", "high",
     re.compile(r"\bredis-cli\b[^\n]*\s-a\s+\S+", re.I)),
    ("cluster_mutation", "high", re.compile(
        r"\brladmin\s+(?:cluster\s+)?(?:restart|remove|failover|migrate|tune|upgrade|flush)\b", re.I)),
    ("kubernetes_disruption", "high", re.compile(
        r"\bkubectl\s+(?:delete|drain|cordon|rollout\s+restart|scale)\b", re.I)),
    ("redis_config_mutation", "high", re.compile(r"\bCONFIG\s+SET\b", re.I)),
    ("acl_mutation", "high", re.compile(r"\bACL\s+(?:SETUSER|DELUSER)\b", re.I)),
    ("server_shutdown", "high", re.compile(r"\bSHUTDOWN\b", re.I)),
    ("destructive_shell", "high", re.compile(r"\brm\s+-\S*[rf]\S*\s+", re.I)),
    ("unbounded_keys", "medium", re.compile(r"\bKEYS\s+\*", re.I)),
    ("stress_load", "medium", re.compile(
        r"\b(?:redis-benchmark|memtier_benchmark|redis-benchmark|stress-ng)\b", re.I)),
    ("key_delete", "medium", re.compile(r"^\s*(?:(?:redis-cli|rcli)\s+)?(?:DEL|UNLINK)\s+\S+", re.I)),
    ("redis_key_scan", "medium", re.compile(r"^\s*(?:(?:redis-cli|rcli)\s+)?SCAN\b", re.I)),
]
EXPECTED_SYNTAX = re.compile(r"\b(expected|output|returns?|verify|assert|observe|should|pass|fails?)\b", re.I)


def inspect(root: Path) -> dict:
    items = []
    by_chapter: dict[int, dict] = {}
    for file in sorted(root.glob("*.md")):
        if not CHAPTER.fullmatch(file.name):
            continue
        number = int(file.name[:2])
        lines = file.read_text(encoding="utf-8-sig").splitlines()
        blocks = find_blocks(lines)
        stats = {"chapter": number, "blocks": len(blocks),
                 "executable_language_blocks": 0,
                 "with_nearby_expected_cue": 0,
                 "without_nearby_expected_cue": 0,
                 "high_risk_candidates": 0, "medium_risk_candidates": 0}
        for b in blocks:
            if b["language"] not in LANGS:
                continue
            stats["executable_language_blocks"] += 1
            cue = expected_nearby(lines, b)
            if cue:
                stats["with_nearby_expected_cue"] += 1
            else:
                stats["without_nearby_expected_cue"] += 1
            for line_offset, command in enumerate(b["source"].splitlines()):
                if not command.strip() or command.lstrip().startswith("#"):
                    continue
                for name, severity, rule in RULES:
                    if not rule.search(command):
                        continue
                    # Excerpt is an intentionally lossy display; never echo credentials.
                    excerpt = command.strip()[:150]
                    excerpt = re.sub(r"(\s-a\s+)\S+", r"\1[REDACTED]", excerpt)
                    item = {"chapter": number, "file": file.name, "line": b["line"] + 1 + line_offset,
                            "fence_line": b["line"], "language": b["language"],
                            "rule": name, "priority": severity,
                            "expected_cue_nearby": cue,
                            "command_excerpt": excerpt,
                            "verdict": "HUMAN_CONTEXT_REVIEW_REQUIRED"}
                    items.append(item)
                    stats["high_risk_candidates" if severity == "high" else "medium_risk_candidates"] += 1
        by_chapter[number] = stats
    ranked = sorted(items, key=lambda x: (x["priority"] != "high", x["chapter"], x["line"]))
    return {"phase": "V02", "scope": "command-level static triage; no Redis, shell or Kubernetes command executed",
            "summary": {"chapters": len(by_chapter),
                        "executable_fenced_blocks": sum(x["executable_language_blocks"] for x in by_chapter.values()),
                        "blocks_without_nearby_expected_cue": sum(x["without_nearby_expected_cue"] for x in by_chapter.values()),
                        "high_risk_candidates": sum(x["priority"] == "high" for x in items),
                        "medium_risk_candidates": sum(x["priority"] == "medium" for x in items),
                        "rules": dict(sorted(Counter(x["rule"] for x in items).items()))},
            "chapters": [by_chapter[k] for k in sorted(by_chapter)],
            "findings": ranked}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--json-file", type=Path)
    p.add_argument("--expected-chapters", type=int, default=80)
    args = p.parse_args()
    result = inspect(args.root)
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("V02 HIGH-RISK TRIAGE:", json.dumps(result["summary"], sort_keys=True))
    for item in [x for x in result["findings"] if x["priority"] == "high"][:30]:
        print("V02 HIGH-RISK SAMPLE:", json.dumps(item, sort_keys=True))
    print("V02 TOP EXECUTABLE CHAPTERS:", json.dumps(
        sorted(result["chapters"],
               key=lambda ch: (ch["high_risk_candidates"],
                               ch["without_nearby_expected_cue"]), reverse=True)[:10]))
    print("This is a heuristic review queue; no command execution or safety certification.")
    return int(result["summary"]["chapters"] != args.expected_chapters)


if __name__ == "__main__":
    raise SystemExit(main())
