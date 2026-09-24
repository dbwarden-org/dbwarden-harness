from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateColumn

from mcp_server.dumper import dump_database_schema
from mcp_server.inspector import sqlalchemy_url
from mcp_server.models import TrackResult
from mcp_server.workspace import Workspace


def run_track_b_nuclear(workspace: Workspace, mutated_models_source: str) -> TrackResult:
    """Drop and recreate the schema from the mutated model module."""
    models_module = _load_models_module(
        workspace.work_dir / "app" / "models.py", mutated_models_source
    )
    base = _find_declarative_base(models_module)
    if base is None:
        return TrackResult(
            success=False,
            stage="reference-load",
            error="No SQLAlchemy DeclarativeBase subclass found in model module",
        )

    engine = create_engine(sqlalchemy_url(workspace.track_b_url))
    try:
        base.metadata.drop_all(engine)
        base.metadata.create_all(engine)
    except Exception as error:  # noqa: BLE001
        return TrackResult(success=False, stage="reference-ddl", error=str(error))
    finally:
        engine.dispose()

    try:
        schema_dump = dump_database_schema(workspace.track_b_url, workspace.backend)
    except Exception as error:  # noqa: BLE001
        return TrackResult(success=False, stage="schema-dump", error=str(error))

    return TrackResult(success=True, stage="complete", schema_dump=schema_dump)


def run_track_b_incremental(
    workspace: Workspace,
    base_models_source: str,
    mutated_models_source: str,
) -> TrackResult:
    """Best-effort incremental reference path.

    Creates the base schema and applies supported mutations via raw Core DDL.
    Unsupported mutations fall back to the nuclear path.
    """
    unsupported = any(
        mutation.get("type") not in {"add_column"} for mutation in workspace.mutations
    )
    if unsupported or not workspace.mutations:
        return run_track_b_nuclear(workspace, mutated_models_source)

    mutated_module = _load_models_module(
        workspace.work_dir / "app" / "models.py", mutated_models_source
    )
    mutated_base = _find_declarative_base(mutated_module)
    base_module = _load_models_module(workspace.work_dir / "app" / "models.py", base_models_source)
    base = _find_declarative_base(base_module)
    if base is None or mutated_base is None:
        return TrackResult(
            success=False,
            stage="reference-load",
            error="No SQLAlchemy DeclarativeBase subclass found in base model module",
        )

    engine = create_engine(sqlalchemy_url(workspace.track_b_url))
    try:
        base.metadata.drop_all(engine)
        base.metadata.create_all(engine)
        with engine.begin() as connection:
            for mutation in workspace.mutations:
                if mutation.get("type") == "add_column":
                    table = mutation["table"]
                    column = mutation["column"]
                    column_ddl = CreateColumn(
                        mutated_base.metadata.tables[table].c[column]
                    ).compile(dialect=engine.dialect)
                    table_name = engine.dialect.identifier_preparer.format_table(
                        mutated_base.metadata.tables[table]
                    )
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))
    except Exception as error:  # noqa: BLE001
        return TrackResult(success=False, stage="reference-ddl", error=str(error))
    finally:
        engine.dispose()

    try:
        schema_dump = dump_database_schema(workspace.track_b_url, workspace.backend)
    except Exception as error:  # noqa: BLE001
        return TrackResult(success=False, stage="schema-dump", error=str(error))

    return TrackResult(success=True, stage="complete", schema_dump=schema_dump)


def _load_models_module(path: Path, source: str) -> types.ModuleType:
    """Load a model module from disk so its Base/metadata can be used by Core DDL."""
    path.write_text(source, encoding="utf-8")
    module_name = f"mcp_models_{path.stem}_{path.parent.name}"
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102 - trusted user models
    return module


def _find_declarative_base(module: types.ModuleType):
    """Return the first DeclarativeBase subclass with a metadata attribute."""
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and hasattr(obj, "metadata")
            and hasattr(obj.metadata, "create_all")
        ):
            return obj
    return None
