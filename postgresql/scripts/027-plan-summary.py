#!/usr/bin/env python3
"""Summarize one EXPLAIN JSON plan; does not execute SQL or diagnose automatically."""
import argparse
import json
import math
from pathlib import Path

NODE_TYPES = {
    "Result", "ProjectSet", "ModifyTable", "Append", "Merge Append", "Recursive Union",
    "BitmapAnd", "BitmapOr", "Seq Scan", "Sample Scan", "Gather", "Gather Merge",
    "Index Scan", "Index Only Scan", "Bitmap Heap Scan", "Bitmap Index Scan",
    "Tid Scan", "Tid Range Scan", "Subquery Scan", "Function Scan", "Table Function Scan",
    "Values Scan", "CTE Scan", "Named Tuplestore Scan", "WorkTable Scan", "Foreign Scan",
    "Custom Scan", "Nested Loop", "Merge Join", "Hash Join", "Materialize", "Memoize",
    "Sort", "Incremental Sort", "Group", "Aggregate", "WindowAgg", "Unique",
    "SetOp", "LockRows", "Limit", "Hash"
}
BUFFER_FIELDS = ("Shared Hit Blocks", "Shared Read Blocks", "Shared Dirtied Blocks",
                 "Shared Written Blocks", "Temp Read Blocks", "Temp Written Blocks")


def number(value, field):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid numeric field: " + field)
    return value


def optional(node, field):
    return number(node[field], field) if field in node else None


def summarize(document):
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ValueError("one EXPLAIN JSON document required")
    top = document[0]
    if not isinstance(top.get("Plan"), dict):
        raise ValueError("root Plan required")
    nodes, stack = [], [(top["Plan"], "0", 0)]
    while stack:
        node, path, depth = stack.pop()
        if not isinstance(node, dict) or depth > 64 or len(nodes) >= 1000:
            raise ValueError("invalid/excessive plan structure")
        node_type = node.get("Node Type")
        if not isinstance(node_type, str):
            raise ValueError("Node Type required")
        estimated = optional(node, "Plan Rows")
        actual = optional(node, "Actual Rows")
        loops = optional(node, "Actual Loops")
        if (actual is None) != (loops is None):
            raise ValueError("actual rows and loops must appear together")
        ratio, row_product = None, None
        if actual is None:
            comparison = "not_measured"
        elif loops == 0:
            comparison, row_product = "not_executed", 0
        else:
            row_product = actual * loops
            if not math.isfinite(row_product):
                raise ValueError("nonfinite row product")
            if estimated is None:
                comparison = "estimate_missing"
            elif estimated == 0:
                comparison = "both_zero" if actual == 0 else "positive_output_with_zero_estimate"
            else:
                comparison, ratio = "measured_ratio_not_a_diagnosis", actual / estimated
                if not math.isfinite(ratio):
                    raise ValueError("nonfinite row ratio")
        nodes.append({
            "path": path, "depth": depth,
            "node_type": node_type if node_type in NODE_TYPES else "Other",
            "estimated_rows_per_invocation": estimated,
            "actual_rows_per_loop": actual, "actual_loops": loops,
            "approx_rows_across_loops": row_product,
            "actual_to_estimated_rows": ratio, "comparison": comparison,
            "startup_cost_units": optional(node, "Startup Cost"),
            "total_cost_units": optional(node, "Total Cost"),
            "buffers_as_reported_inclusive": {k: number(node[k], k) for k in BUFFER_FIELDS if k in node}
        })
        children = node.get("Plans", [])
        if not isinstance(children, list):
            raise ValueError("Plans must be a list")
        for index in range(len(children) - 1, -1, -1):
            stack.append((children[index], path + "." + str(index), depth + 1))
    return {
        "schema_version": 1,
        "planning_time_ms": optional(top, "Planning Time"),
        "execution_time_ms": optional(top, "Execution Time"),
        "nodes": nodes,
        "limitations": [
            "Rows can be averaged/rounded and producers can stop early; products are approximate.",
            "Parent buffers/times can include child work: do not add inclusive observations.",
            "No conditions, outputs, relation names or query text exported; raw plans remain restricted.",
            "A plan summary does not establish statement safety, client latency or a tuning decision."
        ]
    }


def reject_constant(value):
    raise ValueError("nonfinite JSON value")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("plan")
    args = cli.parse_args()
    try:
        path = Path(args.plan)
        if path.stat().st_size > 10_000_000:
            raise ValueError("plan input exceeds 10 MB")
        document = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
        result = summarize(document)
    except (ValueError, OSError, OverflowError, RecursionError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
