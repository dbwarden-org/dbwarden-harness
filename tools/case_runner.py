"""Run many disposable dbwarden projects through the public CLI, in parallel.

``MigrationPlayer`` drives one project through one flow.  The generative suites
need the opposite shape: hundreds of small projects, each differing in one
declared property, each taken through the same multi-revision flow, with the
outcome of every step captured rather than asserted inline.

A :class:`GenerationCase` is a list of model-module revisions.  The runner
creates a project, writes revision *n*, runs ``make-migrations``, optionally
applies it, and repeats — so revision *n+1* is always generated against the
state revision *n* left behind.  Everything observable is recorded on
:class:`CaseResult`: the generated SQL, the CLI streams, whether the server
accepted the migration, the live schema, the result of an executed rollback and
the online/offline diff.

The runner asserts nothing.  Suites classify results through
:meth:`CaseResult.verdict` and assert the contract they care about, which keeps
"dbwarden emitted nothing" distinguishable from "dbwarden emitted SQL the server
rejected" — a distinction that matters because the two have different causes.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from harness.cli import CommandResult, DbwardenCli

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CLICKHOUSE_ERROR = re.compile(r"(Code: \d+\. DB::Exception: .*?)(?: \(version|\n)", re.S)
SQLITE_ERROR = re.compile(r"(sqlite3\.\w+Error: .*?)\n")

NO_CHANGES = "No new migrations to generate"
NO_TABLES = "No tables found"


def strip_ansi(text: str) -> str:
    return ANSI.sub("", text)


@dataclass
class StepResult:
    """One ``make-migrations`` (+ optional ``migrate``) revision."""

    index: int
    returncode: int
    stdout: str
    stderr: str
    new_files: tuple[str, ...] = ()
    sql: str = ""
    migrate_returncode: int | None = None
    migrate_output: str = ""

    @property
    def upgrade(self) -> str:
        return self.sql.split("-- rollback", 1)[0].replace("-- upgrade", "").strip()

    @property
    def rollback(self) -> str:
        parts = self.sql.split("-- rollback", 1)
        return parts[1].strip() if len(parts) > 1 else ""

    @property
    def generated(self) -> bool:
        return self.returncode == 0 and bool(self.sql)

    @property
    def silently_skipped(self) -> bool:
        """dbwarden exited 0 but produced no migration."""
        return self.returncode == 0 and not self.sql

    @property
    def reported_no_changes(self) -> bool:
        return NO_CHANGES in self.stdout

    @property
    def reported_no_tables(self) -> bool:
        return NO_TABLES in self.stdout

    @property
    def server_error(self) -> str:
        match = CLICKHOUSE_ERROR.search(self.migrate_output) or SQLITE_ERROR.search(
            self.migrate_output
        )
        return match.group(1).replace("\n", " ").strip() if match else ""

    def verdict(self) -> str:
        if self.returncode != 0:
            return "generate-failed"
        if not self.sql:
            return "no-tables" if self.reported_no_tables else "no-migration"
        if self.migrate_returncode:
            return "server-rejected"
        return "applied" if self.migrate_returncode == 0 else "generated"


@dataclass
class CaseResult:
    case_id: str
    backend: str
    work_dir: Path
    database: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    harness_error: str | None = None
    live_schema: str = ""
    schema_after_rollback: str = ""
    rollback_returncode: int | None = None
    rollback_output: str = ""
    diff_online: str = ""
    diff_offline: str = ""

    @property
    def last(self) -> StepResult:
        return self.steps[-1]

    def verdict(self) -> str:
        if self.harness_error:
            return "harness-error"
        return self.last.verdict() if self.steps else "no-steps"

    def diff_operations(self, *, offline: bool = False) -> list[dict[str, Any]]:
        return _parse_diff(self.diff_offline if offline else self.diff_online)

    def summary(self) -> str:
        parts = [f"{self.case_id} [{self.backend}] {self.verdict()}"]
        if self.harness_error:
            parts.append(self.harness_error)
        elif self.steps:
            error = self.last.server_error
            if error:
                parts.append(error[:160])
        return " :: ".join(parts)


@dataclass
class GenerationCase:
    """One project taken through ``revisions`` successive model revisions."""

    case_id: str
    backend: str
    revisions: Sequence[str]
    flags: Sequence[Sequence[str]] | None = None
    apply: bool = True
    rollback: int = 0
    capture_schema: bool = False
    capture_diff: bool = False
    config_extra: str = ""
    model_paths: tuple[str, ...] = ("app",)

    def flags_for(self, index: int) -> tuple[str, ...]:
        if not self.flags or index >= len(self.flags):
            return ()
        return tuple(self.flags[index])


class CaseRunner:
    """Materialize and drive :class:`GenerationCase` projects."""

    def __init__(
        self,
        root: Path,
        *,
        url_for: Any,
        clickhouse_http: str | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """``url_for(case_id, work_dir)`` returns ``(database_url, database_name)``."""
        self.root = Path(root)
        self.url_for = url_for
        self.clickhouse_http = clickhouse_http
        self.env = env

    # ---- ClickHouse helpers -------------------------------------------------

    def clickhouse_query(self, sql: str, database: str | None = None) -> tuple[int, str]:
        if not self.clickhouse_http:
            raise RuntimeError("CaseRunner was not given a clickhouse_http endpoint")
        query = urllib.parse.urlencode({"database": database} if database else {})
        request = urllib.request.Request(
            f"{self.clickhouse_http}?{query}", data=sql.encode(), method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return 0, response.read().decode()
        except Exception as error:  # noqa: BLE001 - urllib raises many shapes
            body = ""
            reader = getattr(error, "read", None)
            if reader is not None:
                try:
                    body = reader().decode()
                except Exception:  # noqa: BLE001
                    body = ""
            return 1, f"{error}\n{body}"

    def clickhouse_schema(self, database: str) -> str:
        _, out = self.clickhouse_query(
            "SELECT name, create_table_query FROM system.tables "
            f"WHERE database='{database}' "
            "AND name NOT LIKE '%dbwarden%' AND name NOT LIKE '.inner%' "
            "ORDER BY name FORMAT TSV"
        )
        return out

    # ---- Execution ----------------------------------------------------------

    def run(self, case: GenerationCase) -> CaseResult:
        work_dir = self.root / f"{case.backend}__{_slug(case.case_id)}"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        (work_dir / "app").mkdir()
        (work_dir / "app" / "__init__.py").write_text("", encoding="utf-8")

        database_url, database = self.url_for(case.case_id, work_dir)
        if case.backend == "clickhouse" and database:
            # Every case gets its own database so the matrix can run in
            # parallel against one server instead of one container per case.
            self.clickhouse_query(f"DROP DATABASE IF EXISTS {database}")
            self.clickhouse_query(f"CREATE DATABASE {database}")
        result = CaseResult(case.case_id, case.backend, work_dir, database)

        cli = DbwardenCli(work_dir, env=self.env)

        def invoke(*args: str) -> CommandResult:
            command = cli.run(*args, check=False)
            return CommandResult(
                command.args, command.returncode,
                strip_ansi(command.stdout), strip_ansi(command.stderr),
            )

        invoke("init")
        self._write_config(work_dir, case, database_url)

        migrations = work_dir / "migrations" / "primary"
        for index, source in enumerate(case.revisions):
            (work_dir / "app" / "models.py").write_text(source, encoding="utf-8")
            before = set(migrations.glob("*.sql")) if migrations.exists() else set()
            made = invoke("make-migrations", f"revision{index}", *case.flags_for(index))
            after = set(migrations.glob("*.sql")) if migrations.exists() else set()
            new = sorted(after - before)
            step = StepResult(
                index=index,
                returncode=made.returncode,
                stdout=made.stdout,
                stderr=made.stderr,
                new_files=tuple(path.name for path in new),
                sql="\n\n".join(path.read_text(encoding="utf-8") for path in new),
            )
            if case.apply and step.generated:
                applied = invoke("migrate")
                step.migrate_returncode = applied.returncode
                if applied.returncode:
                    step.migrate_output = applied.stdout + applied.stderr
            result.steps.append(step)

        if case.rollback:
            reverted = invoke("rollback", "--count", str(case.rollback))
            result.rollback_returncode = reverted.returncode
            result.rollback_output = reverted.stdout + reverted.stderr
            if case.backend == "clickhouse" and database:
                result.schema_after_rollback = self.clickhouse_schema(database)

        if case.capture_diff:
            online = invoke("diff", "--out", "json")
            result.diff_online = online.stdout + online.stderr
            offline = invoke("diff", "--offline", "--out", "json")
            result.diff_offline = offline.stdout + offline.stderr

        if case.capture_schema and case.backend == "clickhouse" and database:
            result.live_schema = self.clickhouse_schema(database)

        return result

    def run_all(
        self, cases: Iterable[GenerationCase], *, workers: int = 8
    ) -> list[CaseResult]:
        cases = list(cases)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(self._run_guarded, cases))

    def _run_guarded(self, case: GenerationCase) -> CaseResult:
        try:
            return self.run(case)
        except Exception as error:  # noqa: BLE001 - a broken case must not abort the matrix
            return CaseResult(
                case.case_id, case.backend, self.root / _slug(case.case_id),
                harness_error=f"{type(error).__name__}: {error}",
            )

    def _write_config(self, work_dir: Path, case: GenerationCase, database_url: str) -> None:
        (work_dir / "dbwarden.py").write_text(
            "from dbwarden import database_config\n\n"
            "primary = database_config(\n"
            "    database_name='primary',\n"
            "    default=True,\n"
            f"    database_type={case.backend!r},\n"
            f"    database_url_sync={database_url!r},\n"
            f"    model_paths={list(case.model_paths)!r},\n"
            f"{case.config_extra}"
            ")\n",
            encoding="utf-8",
        )


def sqlite_urls(case_id: str, work_dir: Path) -> tuple[str, None]:
    return f"sqlite:///{work_dir / 'app.db'}", None


def clickhouse_urls(base_url: str):
    """Build a ``url_for`` that gives every case its own ClickHouse database."""
    parsed = urllib.parse.urlparse(base_url)
    authority = parsed.netloc

    def factory(case_id: str, work_dir: Path) -> tuple[str, str]:
        database = f"t_{_slug(case_id)}"[:60]
        return f"clickhouse://{authority}/{database}", database

    return factory


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


def _parse_diff(output: str) -> list[dict[str, Any]]:
    """Extract dbwarden's JSON diff payload from log- and warning-prefixed output."""
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


def report(results: Sequence[CaseResult]) -> str:
    """One line per case — the format the generative suites put in failure text."""
    return "\n".join(result.summary() for result in results)


def verdict_counts(results: Sequence[CaseResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.verdict()] = counts.get(result.verdict(), 0) + 1
    return counts
