from __future__ import annotations

import ast
import keyword
from typing import Any


class MutationError(ValueError):
    """Raised when a mutation cannot be applied to the model source."""


def apply_mutation(source: str, mutation: dict[str, Any]) -> str:
    """Edit a declared model column or index; reject unsupported source shapes.

    Source is parsed and rendered with Python's AST, so formatting and comments
    are not retained. Use write_model_file when those need to be preserved.
    """
    tree = ast.parse(source)
    table = mutation["table"]
    model = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(item, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in item.targets)
                and isinstance(item.value, ast.Constant)
                and item.value.value == table
                for item in node.body
            )
        ),
        None,
    )
    if model is None:
        raise MutationError(f"Table {table!r} not found in model source")
    columns = {
        item.target.id: item
        for item in model.body
        if isinstance(item, ast.AnnAssign)
        and isinstance(item.target, ast.Name)
        and isinstance(item.value, ast.Call)
        and isinstance(item.value.func, ast.Name)
        and item.value.func.id == "mapped_column"
    }
    kind = mutation.get("type")
    imports = set()
    if kind == "add_index":
        names = mutation["columns"]
        if not names or any(name not in columns for name in names):
            raise MutationError("Index columns must name declared columns")
        index = ast.parse(
            f"Index({'ix_' + table + '_' + '_'.join(names)!r}, {', '.join(repr(n) for n in names)}, unique={bool(mutation.get('unique', False))!r})",
            mode="eval",
        ).body
        args = next(
            (
                n
                for n in model.body
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__table_args__" for t in n.targets)
            ),
            None,
        )
        if args is None:
            model.body.append(
                ast.Assign(
                    targets=[ast.Name(id="__table_args__", ctx=ast.Store())],
                    value=ast.Tuple(elts=[index], ctx=ast.Load()),
                )
            )
        elif isinstance(args.value, ast.Dict):
            args.value = ast.Tuple(elts=[index, args.value], ctx=ast.Load())
        elif isinstance(args.value, ast.Tuple):
            args.value.elts.insert(0, index)
        else:
            raise MutationError("Index mutation requires literal __table_args__")
        imports.add("Index")
    else:
        name = mutation["column"]
        if not name.isidentifier() or keyword.iskeyword(name):
            raise MutationError("Column must be a Python identifier")
        column = columns.get(name)
        if kind == "add_column":
            if column is not None:
                raise MutationError(f"Column {name!r} already exists")
            column = ast.parse(
                f"{name}: Mapped[{mutation['column_type']}] = mapped_column({mutation['column_type']})"
            ).body[0]
            model.body.append(column)
        elif column is None:
            raise MutationError(f"Column {name!r} not found in table {table!r}")
        call = column.value
        if kind in {"add_column", "change_type"}:
            type_source = mutation["column_type" if kind == "add_column" else "new_type"]
            type_node = ast.parse(type_source, mode="eval").body
            root = type_node.func if isinstance(type_node, ast.Call) else type_node
            if not isinstance(root, ast.Name):
                raise MutationError("Column type must be a SQLAlchemy type name or constructor")
            imports.add(root.id)
            if not call.args or not isinstance(call.args[0], (ast.Name, ast.Call)):
                raise MutationError("Column type must be the first mapped_column argument")
            call.args[0] = type_node
            column.annotation = ast.parse(f"Mapped[{type_source}]", mode="eval").body
        if kind == "drop_column":
            model.body.remove(column)
        elif kind in {"add_column", "set_not_null", "drop_not_null"}:
            _set_keyword(
                call,
                "nullable",
                mutation.get("nullable", True) if kind == "add_column" else kind == "drop_not_null",
            )
            if kind == "add_column" and "default" in mutation:
                _set_keyword(call, "default", mutation["default"])
        elif kind == "set_default":
            _set_keyword(call, "default", mutation["default"])
        elif kind == "drop_default":
            call.keywords = [kw for kw in call.keywords if kw.arg != "default"]
        elif kind != "change_type":
            raise MutationError(f"Unsupported mutation type: {kind}")
    known = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    missing = sorted(imports - known)
    if missing:
        position = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.ClassDef))
        tree.body.insert(
            position,
            ast.ImportFrom(
                module="sqlalchemy", names=[ast.alias(name=n) for n in missing], level=0
            ),
        )
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def _set_keyword(call: ast.Call, name: str, value: Any) -> None:
    call.keywords = [kw for kw in call.keywords if kw.arg != name]
    call.keywords.append(ast.keyword(arg=name, value=ast.parse(repr(value), mode="eval").body))
