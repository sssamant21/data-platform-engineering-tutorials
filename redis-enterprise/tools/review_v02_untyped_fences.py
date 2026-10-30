#!/usr/bin/env python3
"""V02 triage of command-like lines inside text/unlabeled Markdown fences.

This is an OFFLINE, heuristic queue only: a detected command token in a
textual diagram/checklist is not proof a block should be executable.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from validate_v02_examples import CHAPTER, COMMAND, find_blocks

UNLABELED = {"", "text", "plaintext"}
OPERATIONS = (
    r"GET|SET|MGET|HGET|HSET|EXPIRE|TTL|DEL|UNLINK|SCAN|INFO|PING|"
    r"XADD|XREADGROUP|XACK|ZADD|SADD|KEYS|FLUSHALL|FLUSHDB|"
    r"INCR|HINCRBY|HGETALL|LRANGE|RPUSH|LPUSH|TYPE|MEMORY|"
    r"FT\.SEARCH|JSON\.SET|JSON\.GET"
)
CLI = r"redis-cli|rladmin|kubectl|curl|docker|python(?:3)?"
OPERATIVE = re.compile(rf"^\s*(?:{OPERATIONS}|{CLI})\b(?:\s+\S+)+", re.I)
NOUN_LIST = re.compile(r"^[A-Z][A-Z0-9_.-]{1,28}$")
FORMULA = re.compile(r"^[A-Z][A-Z0-9_-]*\s*(?:=|->|:|/)\s*", re.I)
TABLE = re.compile(r"^\s*(?:[^\n]*\s(?:->|<-|=>|\|)\s[^\n]*)$")
SAFE_TOKEN = re.compile(r"(?:^|\s)(?:--password|-a)\s+\S+")


def bucket(source: str, preceding: str) -> tuple[str, str]:
    lines = [x.strip() for x in source.splitlines() if x.strip()]
    runnable = [x for x in lines if OPERATIVE.match(x)]
    # Symbolic examples such as TTL = 3600 resemble commands but are not
    # executable Redis command lines. Test BEFORE generic command-argument logic.
    if lines and all(FORMULA.match(x) for x in lines):
        return ("formula_or_symbolic_text", "Symbolic description, not Redis CLI syntax")
    # Plain shell snippets with args, complete Redis instructions, or concrete
    # arguments are legitimate potential copy/paste hazards, even if illustrative.
    if runnable:
        if re.search(r"\b(?:do not|never|avoid|unsafe|prohibit|anti.pattern)\b",
                     preceding, re.I):
            return ("potential_negative_example", "Complete command under negative/warning context")
        return ("possible_runnable_command", "Has command plus arguments: check intent and environment")
    if any(FORMULA.match(x) for x in lines):
        return ("formula_or_symbolic_text", "Symbolic description, not Redis CLI syntax")
    if len(lines) >= 2 and sum(bool(NOUN_LIST.fullmatch(x)) for x in lines) >= 2:
        return ("command_vocabulary_list", "Bare tokens in an inventory/list")
    if any(TABLE.match(x) for x in lines):
        return ("diagram_or_comparison", "Diagram/arrow/comparison, not paste-ready commands")
    return ("ambiguous_reference_text", "Command-like words within text; human classification needed")


def inspect(root: Path) -> dict:
    rows = []
    files = sorted(p for p in root.glob("*.md") if CHAPTER.fullmatch(p.name))
    for file in files:
        lines = file.read_text(encoding="utf-8-sig").splitlines()
        for block in find_blocks(lines):
            if block["language"] not in UNLABELED:
                continue
            matching = [s for s in block["source"].splitlines() if COMMAND.search(s)]
            if not matching:
                continue
            before = "\n".join(lines[max(0, block["start"] - 8):block["start"]])
            category, rationale = bucket(block["source"], before)
            excerpt = block["source"].strip().replace("\n", " | ")[:180]
            excerpt = SAFE_TOKEN.sub(lambda m: m.group(0).split()[0] + " [REDACTED]", excerpt)
            rows.append({
                "chapter": int(file.name[:2]), "file": file.name,
                "line": block["line"], "language": block["language"] or "(unlabeled)",
                "category": category, "reason": rationale,
                "matched_command_lines": len(matching),
                "excerpt": excerpt, "preceding": before[-220:].replace("\n", " | "),
                "review_verdict": "HUMAN_REVIEW_REQUIRED"
            })
    counts = dict(sorted(Counter(x["category"] for x in rows).items()))
    return {
        "scope": "80 numbered chapters; command-like tokens inside text/unlabeled Markdown fences; no execution",
        "summary": {"chapters": len(files), "candidates": len(rows),
                    "by_category": counts,
                    "priority_candidates": sum(x["category"] == "possible_runnable_command" for x in rows)},
        "entries": rows
    }


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
    print("V02 UNTYPED CLASSIFICATION:", json.dumps(result["summary"], sort_keys=True))
    for x in result["entries"]:
        if x["chapter"] in {1, 3, 4, 10, 11}:
            print("V02 FOCUS UNTYPED:", json.dumps(x, sort_keys=True))
    print("V02 FIRST RUNNABLE CANDIDATES:", json.dumps(
        [x for x in result["entries"] if x["category"] == "possible_runnable_command"][:25]))
    print("Categories are heuristic priorities, not reviewed approvals.")
    return int(result["summary"]["chapters"] != args.expected_chapters)


if __name__ == "__main__":
    raise SystemExit(main())
