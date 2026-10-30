#!/usr/bin/env python3
"""V02: inventory Redis Enterprise examples and produce an offline manual-review queue.

Never executes tutorial commands or contacts Redis. AST/JSON checks are syntax only.
A nearby "expected" phrase is not proof that the expected result is correct.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

CHAPTER = re.compile(r"^\d{2}-[^/]+\.md$")
FENCE = re.compile(r"^ {0,3}((?:\x60){3,}|~{3,})(.*)$")
COMMAND_LANGS = {"redis", "bash", "sh", "shell", "console", "terminal",
                 "powershell", "ps1", "cmd"}
PYTHON_LANGS = {"python", "python3", "py"}
STRUCTURED_LANGS = {"json"}
EXPECTED = re.compile(
    r"\b(expected|output|result|returns?|responds?|verify|validated?|"
    r"assert|observe|should|pass|fails?|check the|confirm)\b", re.I)
COMMAND = re.compile(
    r"^\s*(?:redis-cli|rladmin|kubectl|curl|docker|python(?:3)?|"
    r"GET|SET|MGET|HGET|HSET|EXPIRE|TTL|DEL|UNLINK|SCAN|INFO|PING|"
    r"XADD|XREADGROUP|XACK|FT\.SEARCH|JSON\.SET|ZADD|SADD|"
    r"FLUSHALL|FLUSHDB|KEYS)\b", re.I)
SAFETY_PATTERNS = [
    ("flush_database", re.compile(r"\bFLUSH(?:ALL|DB)\b", re.I)),
    ("unbounded_keys", re.compile(r"\bKEYS\s+\*", re.I)),
    ("destructive_shell", re.compile(r"(?:^|\s)rm\s+-[^\n]*r[^\n]*f\s+", re.I)),
    ("kubectl_delete", re.compile(r"\bkubectl\s+delete\b", re.I)),
    ("tls_bypass", re.compile(r"\bcurl\s+(?:-k\b|--insecure\b)", re.I)),
    ("inline_redis_password", re.compile(r"\bredis-cli\b[^\n]*\s-a\s+\S+", re.I)),
    ("force_shutdown", re.compile(r"\bSHUTDOWN\s+(?:NOSAVE|SAVE)\b", re.I)),
]
EXPECTED_WINDOW = 22


def find_blocks(lines: list[str]) -> list[dict]:
    blocks = []
    opening = None
    for i, line in enumerate(lines):
        match = FENCE.match(line)
        if opening is None:
            if match:
                lang = match.group(2).strip().split(None, 1)
                opening = (i, match.group(1)[0], len(match.group(1)),
                           lang[0].lower() if lang else "")
        elif (match and match.group(1)[0] == opening[1] and
              len(match.group(1)) >= opening[2] and not match.group(2).strip()):
            start = opening[0]
            blocks.append({"start": start, "end": i, "line": start + 1,
                           "language": opening[3],
                           "source": "\n".join(lines[start + 1:i])})
            opening = None
    return blocks


def expected_nearby(lines: list[str], block: dict) -> bool:
    start = block["end"] + 1
    for line in lines[start:start + EXPECTED_WINDOW]:
        if re.match(r"^#{1,3} ", line):
            break
        if EXPECTED.search(line):
            return True
    before = lines[max(0, block["start"] - 5):block["start"]]
    return any(EXPECTED.search(line) for line in before)


def audit(root: Path, expected_chapters: int = 80) -> dict:
    files = sorted(p for p in root.glob("*.md") if CHAPTER.fullmatch(p.name))
    result = {
        "phase": "V02", "method": "offline inventory, AST and JSON parsing, and heuristic review; no command execution",
        "summary": {"chapters": len(files), "expected_chapters": expected_chapters,
                    "total_code_fences": 0, "explicit_command_blocks": 0,
                    "untyped_command_candidates": 0, "python_blocks": 0,
                    "json_blocks": 0, "python_syntax_findings": 0,
                    "json_syntax_review_candidates": 0,
                    "command_blocks_missing_nearby_expected_cue": 0,
                    "safety_review_candidates": 0},
        "language_counts": {},
        "chapters": [],
        "review_queue": []
    }
    totals = result["summary"]
    language_counts = Counter()
    for path in files:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        blocks = find_blocks(lines)
        ch = {"chapter": int(path.name[:2]), "file": path.name,
              "code_fences": len(blocks), "commands": 0,
              "untyped_commands": 0, "missing_expected_cues": 0,
              "python": 0, "json": 0, "syntax_review": 0,
              "safety_review": 0, "review_samples": []}
        totals["total_code_fences"] += len(blocks)
        for block in blocks:
            lang = block["language"]
            language_counts[lang or "(unlabeled)"] += 1
            source = block["source"]
            command_lines = [l for l in source.splitlines()
                             if COMMAND.search(l)]
            explicit_command = lang in COMMAND_LANGS and any(
                l.strip() and not l.lstrip().startswith("#")
                for l in source.splitlines())
            untyped = lang in {"text", "", "plaintext"} and bool(command_lines)
            if explicit_command:
                ch["commands"] += 1
                totals["explicit_command_blocks"] += 1
            if untyped:
                ch["untyped_commands"] += 1
                totals["untyped_command_candidates"] += 1
            if explicit_command or untyped:
                if not expected_nearby(lines, block):
                    ch["missing_expected_cues"] += 1
                    totals["command_blocks_missing_nearby_expected_cue"] += 1
                    if len(ch["review_samples"]) < 12:
                        ch["review_samples"].append({
                            "line": block["line"], "kind": "expected_result_review",
                            "language": lang, "note": "No expected-output cue nearby; assess manually"})
                for name, pattern in SAFETY_PATTERNS:
                    if pattern.search(source):
                        ch["safety_review"] += 1
                        totals["safety_review_candidates"] += 1
                        if len(ch["review_samples"]) < 12:
                            ch["review_samples"].append({
                                "line": block["line"], "kind": "safety_review",
                                "pattern": name, "note": "Context review required, not proof of misuse"})
            if lang in PYTHON_LANGS:
                ch["python"] += 1
                totals["python_blocks"] += 1
                try:
                    ast.parse(textwrap.dedent(source), filename=path.name)
                except SyntaxError as exc:
                    ch["syntax_review"] += 1
                    totals["python_syntax_findings"] += 1
                    if len(ch["review_samples"]) < 12:
                        ch["review_samples"].append({
                            "line": block["line"] + (exc.lineno or 1),
                            "kind": "python_syntax_review", "note": exc.msg})
            if lang in STRUCTURED_LANGS:
                ch["json"] += 1
                totals["json_blocks"] += 1
                try:
                    json.loads(source)
                except (ValueError, TypeError) as exc:
                    ch["syntax_review"] += 1
                    totals["json_syntax_review_candidates"] += 1
                    if len(ch["review_samples"]) < 12:
                        ch["review_samples"].append({
                            "line": block["line"], "kind": "json_syntax_review",
                            "note": str(exc)[:120]})
        result["chapters"].append(ch)
    result["language_counts"] = dict(sorted(language_counts.items()))
    result["review_queue"] = [
        {"chapter": x["chapter"], "file": x["file"],
         "missing_expected_cues": x["missing_expected_cues"],
         "safety_review": x["safety_review"], "syntax_review": x["syntax_review"],
         "untyped_commands": x["untyped_commands"],
         "samples": x["review_samples"]}
        for x in result["chapters"]
        if x["missing_expected_cues"] or x["safety_review"] or x["syntax_review"]
        or x["untyped_commands"]
    ]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--expected", type=int, default=80)
    ap.add_argument("--json-file", type=Path)
    args = ap.parse_args()
    result = audit(args.root, args.expected)
    s = result["summary"]
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("V02 OFFLINE INVENTORY:", json.dumps(s, sort_keys=True))
    top = sorted(result["review_queue"],
                 key=lambda c: (c["safety_review"] * 4 + c["syntax_review"] * 3
                                + c["missing_expected_cues"] + c["untyped_commands"]),
                 reverse=True)[:12]
    print("V02 TOP REVIEW CHAPTERS:", json.dumps([
        {"chapter": c["chapter"], "expected_cues": c["missing_expected_cues"],
         "safety": c["safety_review"], "untyped": c["untyped_commands"],
         "syntax": c["syntax_review"]} for c in top]))
    focus = {42, 44, 47, 51}
    print("V02 FOUR-CHAPTER FOCUS:", json.dumps([
        {"chapter": c["chapter"], "command_blocks": c["commands"],
         "untyped": c["untyped_commands"], "expected_cues": c["missing_expected_cues"],
         "safety": c["safety_review"], "syntax": c["syntax_review"]}
        for c in result["chapters"] if c["chapter"] in focus]))
    print("V02 SYNTAX SAMPLES:", json.dumps([
        {"chapter": c["chapter"], **s}
        for c in result["review_queue"] for s in c["samples"]
        if s["kind"] in {"json_syntax_review", "python_syntax_review"}
    ][:20]))
    print("V02 SAFETY SAMPLES:", json.dumps([
        {"chapter": c["chapter"], **s}
        for c in result["review_queue"] for s in c["samples"]
        if s["kind"] == "safety_review"
    ][:20]))
    print("Human review required: command correctness, expected values, release compatibility,"
          " side effects, lab reproducibility. No Redis command was executed.")
    return 0 if s["chapters"] == args.expected else 1


if __name__ == "__main__":
    sys.exit(main())
