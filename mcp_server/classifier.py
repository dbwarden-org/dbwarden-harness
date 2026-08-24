from __future__ import annotations

from typing import Any


def classify_divergence(plan: dict[str, Any] | None, diff_summary: dict[str, Any]) -> str:
    """Deterministic 95/5 classification based on dbwarden's emitted plan."""
    if plan is None:
        return "95"

    ops = plan.get("operations", [])
    if not ops:
        return "5"

    standard_ops = {
        "add_column",
        "create_table",
        "create_index",
        "drop_column",
        "add_constraint",
        "drop_constraint",
        "alter_column_type",
        "set_not_null",
        "drop_not_null",
        "set_default",
        "drop_default",
    }
    standard_types = {
        "integer",
        "bigint",
        "varchar",
        "text",
        "boolean",
        "timestamptz",
        "timestamp",
        "date",
        "numeric",
        "float",
        "double",
        "jsonb",
        "uuid",
    }

    all_standard_ops = all(op.get("kind") in standard_ops for op in ops)
    all_standard_types = all(
        any(
            t in standard_types
            for t in op.get("column_types", [])
        )
        for op in ops
    )

    if all_standard_ops and all_standard_types:
        return "95"
    return "5"
