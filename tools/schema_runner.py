from __future__ import annotations

from pathlib import Path

from schemas.base import ReferenceSchema
from tools.drift_checker import DriftChecker, SchemaSnapshot
from tools.migration_player import MigrationPlayer


class SchemaRunner:
    """Materialize a reference schema into a disposable DBWarden project."""

    def __init__(
        self,
        schema: ReferenceSchema,
        player: MigrationPlayer,
        *,
        database_type: str | None = None,
    ) -> None:
        self.schema = schema
        self.player = player
        self.database_type = database_type or schema.backend

    def prepare(self) -> Path:
        self.player.write_model_source("", filename="app/__init__.py")
        return self.player.write_model_source(self.schema.source(), filename="app/models.py")

    def configure(self) -> Path:
        return self.player.configure(
            database_name=self.schema.name,
            database_type=self.database_type,
            model_paths=("app",),
        )

    def initialize(self) -> Path:
        self.player.cli.run("init", "--database", self.schema.name)
        self.prepare()
        return self.configure()

    def make_and_apply(self, message: str = "reference schema") -> None:
        self.player.make_migrations(message)
        self.player.migrate()
        self.assert_expected_schema()

    def capture_schema(self) -> SchemaSnapshot:
        return DriftChecker().capture(self.player.database_url)

    def assert_expected_schema(self) -> SchemaSnapshot:
        snapshot = self.capture_schema()
        missing_tables = set(self.schema.expected_tables) - set(snapshot.tables)
        actual_indexes = {
            index for indexes in snapshot.indexes.values() for index in indexes
        }
        missing_indexes = set(self.schema.expected_indexes) - actual_indexes
        if missing_tables or missing_indexes:
            details = []
            if missing_tables:
                details.append(f"tables={sorted(missing_tables)}")
            if missing_indexes:
                details.append(f"indexes={sorted(missing_indexes)}")
            raise AssertionError(
                f"Reference schema {self.schema.name!r} is incomplete: {', '.join(details)}"
            )
        return snapshot

    def reverse_engineer(
        self,
        output_dir: str = "generated",
        *,
        tables: str | None = None,
        exclude_tables: str | None = None,
        clickhouse_engines: bool = False,
        relationships: bool = False,
    ) -> Path:
        flags = ["--output", output_dir, "--single-file"]
        if tables:
            flags.extend(("--tables", tables))
        if exclude_tables:
            flags.extend(("--exclude-tables", exclude_tables))
        if clickhouse_engines:
            flags.append("--clickhouse-engines")
        if relationships:
            flags.append("--relationships")
        self.player.generate_models(*flags)
        generated = self.player.work_dir / output_dir / "models.py"
        if not generated.exists():
            raise AssertionError(f"DBWarden did not generate the expected model artifact: {generated}")
        return generated

    def round_trip(self, output_dir: str = "generated", *, tables: str | None = None) -> list[dict[str, object]]:
        self.reverse_engineer(output_dir, tables=tables)
        self.player.configure(model_paths=(output_dir,))
        return self.player.diff_operations()
