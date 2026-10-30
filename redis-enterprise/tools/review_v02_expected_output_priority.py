#!/usr/bin/env python3
"""Offline review queue: rank command blocks missing nearby expected result cues.

The queue is a heuristic, not proof an example is incorrect or executable.
Never evaluates tutorial code and never contacts Redis or Kubernetes.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from validate_v02_examples import CHAPTER, COMMAND, COMMAND_LANGS, expected_nearby, find_blocks

LANG_RISK = {"redis", "bash", "sh", "shell", "console", "terminal",
             "powershell", "ps1", "cmd"}
UNLABELED = {"text", "", "plaintext"}
HIGH = re.compile(
    r"\b(?:XAUTOCLAIM|XGROUP\s+CREATE|XREADGROUP|XACK|JSON\.[A-Z]+|"
    r"FT\.(?:SEARCH|AGGREGATE|CREATE)|GETEX|HPEXPIRE|HEXPIRE|"
    r"FUNCTION\s+LOAD|EVAL|CONFIG\s+SET|ACL\s+SETUSER|"
    r"rladmin\b|kubectl\s+(?:cordon|delete|drain)|redis-benchmark)\b", re.I)
VERSIONS = re.compile(
    r"\b(?:EXPIRE\s+\S+\s+\d+\s+(?:NX|XX|GT|LT)|"
    r"SET\s+\S+\s+[^\n]*\bKEEPTTL\b|"
    r"ZRANGE\s+\S+\s+[^\n]*\b(?:REV|BYSCORE)\b|"
    r"ZREVRANGE|GETEX|XAUTOCLAIM|JSON\.[A-Z]+)\b", re.I)
WRITE = re.compile(
    r"^\s*(?:(?:redis-cli|rcli)\s+)?(?:SET|HSET|SADD|ZADD|EXPIRE|"
    r"DEL|UNLINK|LPUSH|RPUSH|XADD|INCR|PERSIST|MSET)\s+", re.I)
READ = re.compile(r"^\s*(?:(?:redis-cli|rcli)\s+)?(?:GET|HGET|TTL|PTTL|INFO|PING|TYPE|SCAN|ZRANGE|MGET)\b", re.I)
NEGATIVE = re.compile(r"\b(?:do not|never|avoid|unsafe|warning|antipattern|anti-pattern)\b", re.I)

def inspect(root: Path) -> dict:
    rows = []
    for path in sorted(root.glob("*.md")):
        if not CHAPTER.fullmatch(path.name):
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        heading = ""
        for block in find_blocks(lines):
            lang = block["language"]
            source = block["source"]
            commands = [x.strip() for x in source.splitlines() if x.strip() and
                        not x.lstrip().startswith("#")]
            explicit = lang in LANG_RISK and bool(commands)
            untyped = lang in UNLABELED and any(COMMAND.search(x) for x in commands)
            if not explicit and not untyped:
                continue
            if expected_nearby(lines, block):
                continue
            preceding = "\n".join(lines[max(0, block["start"] - 9):block["start"]])
            after = "\n".join(lines[block["end"]+1:block["end"]+8])
            prior_head = next((x.strip() for x in reversed(lines[:block["start"]])
                               if re.match(r"^#{1,4} ", x)), "")
            # A list of command names in a text fence can match JSON.SET or GETEX,
            # but is not an executable version-sensitive example.
            version = explicit and bool(VERSIONS.search(source))
            special = bool(HIGH.search(source))
            write = any(WRITE.search(x) for x in commands)
            read = any(READ.search(x) for x in commands)
            warning = bool(NEGATIVE.search(preceding+"\n"+after))
            # Prioritize executable release-sensitive commands first,
            # then other side-effecting command examples, then read-only and text.
            score = 0
            if explicit:
                score += 45
            if version:
                score += 35
            if special:
                score += 25
            if write:
                score += 15
            if read:
                score += 5
            if warning:
                score -= 20  # Cautionary examples still retained in queue.
            if not explicit:
                score -= 30
            category = ("release_sensitive" if version else
                        "enterprise_or_workflow" if special else
                        "write_side_effect" if write else
                        "read_only" if read else "generic_or_text")
            rows.append({
                "chapter": int(path.name[:2]), "file": path.name,
                "line": block["line"], "language": lang or "(unlabeled)",
                "heading": prior_head[:130], "category": category, "score": score,
                "version_sensitive": version, "caution_context": warning,
                "source_excerpt": source[:300].replace("\n", " | "),
                "disposition": "NEEDS_CONTEXTUAL_TECHNICAL_REVIEW"
            })
    rows.sort(key=lambda r: (-r["score"], r["chapter"], r["line"]))
    return {"summary": {"candidates": len(rows),
                        "executable_language_candidates": sum(x["language"] in LANG_RISK for x in rows),
                        "version_sensitive_candidates": sum(x["version_sensitive"] for x in rows),
                        "by_category": dict(sorted(Counter(x["category"] for x in rows).items())),
                        "chapters": len(list(p for p in root.glob("*.md") if CHAPTER.fullmatch(p.name)))},
            "criteria": "Expected-cue heuristic with executable, release-sensitive, write and caution weights; not runtime verification",
            "review_queue": rows}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--json-file", type=Path)
    p.add_argument("--expected-chapters", type=int, default=80)
    p.add_argument("--top", type=int, default=35)
    args = p.parse_args()
    data = inspect(args.root)
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("V02 OUTPUT PRIORITY:", json.dumps(data["summary"], sort_keys=True))
    print("V02 ALL VERSION-SENSITIVE ITEMS:", json.dumps([x for x in data["review_queue"] if x["version_sensitive"]], sort_keys=True))
    for row in data["review_queue"][:args.top]:
        print("V02 OUTPUT PRIORITY ITEM:", json.dumps(row, sort_keys=True))
    return int(data["summary"]["chapters"] != args.expected_chapters)

if __name__ == "__main__":
    raise SystemExit(main())
