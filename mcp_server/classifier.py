from __future__ import annotations

import re
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

    all_standard_ops = all(op.get("type", op.get("kind")) in standard_ops for op in ops)
    all_standard_types = all(
        all(
            re.split(r"[\s(]", str(t).lower())[0] in standard_types
            for t in op.get(
                "column_types",
                _nested_types({key: value for key, value in op.items() if key != "type"}),
            )
        )
        for op in ops
    )

    if all_standard_ops and all_standard_types:
        return "95"
    return "5"


def _nested_types(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [str(value["type"])] if "type" in value else [
            item for child in value.values() for item in _nested_types(child)
        ]
    if isinstance(value, list):
        return [item for child in value for item in _nested_types(child)]
    return []
