from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from harness.cli import CommandResult, DbwardenCli


class MigrationPlayer:
    """Drive a disposable DBWarden project through its public CLI."""

    def __init__(self, database_url: str, work_dir: Path) -> None:
        self.database_url = database_url
        self.work_dir = work_dir
        self.cli = DbwardenCli(work_dir)

    def init(self) -> CommandResult:
        return self.cli.run("init", clean=True)

    def configure(
        self,
        *,
        database_name: str = "primary",
        database_type: str | None = None,
        model_paths: tuple[str, ...] = (),
        dev_database_type: str | None = None,
        dev_database_url: str | None = None,
    ) -> Path:
        """Write a consumer config using only DBWarden's public function API."""
        config_path = self.work_dir / "dbwarden.py"
        resolved_type = database_type or self._database_type()
        model_lines = f"    model_paths={list(model_paths)!r},\n" if model_paths else ""
        dev_lines = "".join(
            [
                f"    dev_database_type={dev_database_type!r},\n" if dev_database_type else "",
                f"    dev_database_url={dev_database_url!r},\n" if dev_database_url else "",
            ]
        )
        config_path.write_text(
            "from dbwarden import database_config\n\n"
            "primary = database_config(\n"
            f"    database_name={database_name!r},\n"
            f"    default=True,\n"
            f"    database_type={resolved_type!r},\n"
            f"    database_url_sync={self.database_url!r},\n"
            f"{model_lines}"
            f"{dev_lines}"
            ")\n",
            encoding="utf-8",
        )
        return config_path

    def init_and_configure(self, **kwargs: object) -> Path:
        self.init()
        return self.configure(**kwargs)

    def write_model_source(self, source: str, *, filename: str = "models.py") -> Path:
        path = self.work_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def _database_type(self) -> str:
        scheme = self.database_url.split(":", 1)[0].lower()
        return {
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "mysql": "mysql",
            "mariadb": "mariadb",
            "clickhouse": "clickhouse",
            "http": "clickhouse",
            "https": "clickhouse",
            "sqlite": "sqlite",
        }.get(scheme, scheme)

    def make_migrations(self, message: str, *flags: str) -> CommandResult:
        return self.cli.run("make-migrations", message, *flags, clean=True)

    def migrate(self, *flags: str) -> CommandResult:
        return self.cli.run("migrate", *flags, clean=True)

    def rollback(self, count: int = 1, *flags: str) -> CommandResult:
        return self.cli.run("rollback", "--count", str(count), *flags, clean=True)

    def status(self, *flags: str) -> CommandResult:
        return self.cli.run("status", *flags, clean=True)

    def diff(self, *flags: str) -> CommandResult:
        return self.cli.run("diff", *flags, clean=True)

    def diff_operations(self) -> list[dict[str, Any]]:
        result = self.diff("--out", "json")
        return parse_diff_output(result.output)

    def generate_models(self, *flags: str) -> CommandResult:
        return self.cli.run("generate-models", *flags, clean=True)

    def export_models(self, *flags: str) -> CommandResult:
        return self.cli.run("export-models", *flags, clean=True)

    def check_impact(self, *flags: str) -> CommandResult:
        return self.cli.run("check-impact", *flags, clean=True)

    def assert_converged(self, *flags: str) -> None:
        result = self.diff(*flags)
        operations = parse_diff_output(result.output)
        if operations:
            details = ", ".join(
                f"{operation.get('operation')}:{operation.get('table')}" for operation in operations
            )
            raise AssertionError(f"Database is not converged: {details}")

    def assert_history_integrity(self) -> None:
        history = self.cli.run("history").plain_output
        migration_files = tuple(self.work_dir.glob("migrations/*/*.sql"))
        file_versions = {
            path.name.split("__", 1)[-1].split("_", 1)[0] for path in migration_files
        }
        history_versions = set(re.findall(r"\b(\d{4})\b[^\n]*versioned", history))
        missing_versions = sorted(history_versions - file_versions)
        if missing_versions:
            raise AssertionError(f"Migration history is missing files: {missing_versions}")


def parse_diff_output(output: str) -> list[dict[str, Any]]:
    """Extract DBWarden's JSON diff payload from log-prefixed CLI output."""
    for start, character in enumerate(output):
        if character != "[":
            continue
        try:
            payload = json.loads(output[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
            return payload
    return []
