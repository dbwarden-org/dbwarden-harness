"""Drive the full reverse-engineering loop and report where it stops converging.

``suites/round_trip`` already checks that a schema survives migrate + inspect.
This driver closes the loop the way an adopting user does:

    declare models -> make-migrations -> migrate
        -> generate-models          (reverse engineer the live database)
        -> replace app/ with the generated models
        -> diff  and  make-migrations   (should both be empty)

A converged tool produces no diff and no new migration.  Anything else is drift
that a user would discover only after committing generated models to their
repository, so the driver records both signals separately: ``diff`` and
``make-migrations`` are different code paths in dbwarden and they do not always
agree.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.cli import DbwardenCli
from tools.case_runner import _parse_diff, strip_ansi

BOOKKEEPING = ("dbwarden_lock", "dbwarden_migrations", "_dbwarden_migrations")


@dataclass
class RoundTripResult:
    shape_id: str
    work_dir: Path
    database: str | None = None
    make_returncode: int = 0
    migrate_returncode: int = 0
    generate_returncode: int = 0
    generate_output: str = ""
    generated_files: tuple[str, ...] = ()
    generated_sources: dict[str, str] = field(default_factory=dict)
    live_schema: str = ""
    rediff_output: str = ""
    remake_output: str = ""
    remake_returncode: int = 0
    remake_sql: str = ""

    @property
    def diff_operations(self) -> list[dict[str, Any]]:
        return _parse_diff(self.rediff_output)

    @property
    def diff_is_clean(self) -> bool:
        return not self.diff_operations

    @property
    def regenerated_migration(self) -> bool:
        return "Created migration file" in self.remake_output

    @property
    def bookkeeping_models(self) -> tuple[str, ...]:
        """Generated model files that describe dbwarden's own tables."""
        return tuple(
            name
            for name in self.generated_files
            if any(marker in name for marker in BOOKKEEPING)
        )

    @property
    def setup_ok(self) -> bool:
        """Did the declare/migrate/generate phase actually produce anything?

        Without this, a round trip that failed before it started looks like a
        clean one: no models were generated, so there is nothing to diff and
        nothing to regenerate.
        """
        return (
            self.make_returncode == 0
            and self.migrate_returncode == 0
            and self.generate_returncode == 0
            and bool(self.generated_files)
        )

    @property
    def converged(self) -> bool:
        return (
            self.setup_ok
            and self.diff_is_clean
            and not self.regenerated_migration
            and not self.bookkeeping_models
        )

    def unimportable(self) -> dict[str, str]:
        """Generated modules that cannot be imported, keyed by filename.

        Imported in a subprocess rather than analysed statically: a generated
        model is only useful if Python can actually load it, and the failure
        text is what the user would see.
        """
        broken: dict[str, str] = {}
        for name in self.generated_files:
            if name == "__init__.py":
                continue
            path = self.work_dir / "gen" / name
            probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import importlib.util, sys\n"
                        "spec = importlib.util.spec_from_file_location('generated', sys.argv[1])\n"
                        "module = importlib.util.module_from_spec(spec)\n"
                        "spec.loader.exec_module(module)\n"
                    ),
                    str(path),
                ],
                capture_output=True,
                text=True,
                cwd=tempfile.gettempdir(),
                timeout=120,
                check=False,
            )
            if probe.returncode:
                last = [line for line in probe.stderr.splitlines() if line.strip()]
                broken[name] = last[-1] if last else "import failed"
        return broken

    def summary(self) -> str:
        if not self.setup_ok:
            return (
                f"{self.shape_id}: round trip never started "
                f"(make={self.make_returncode} migrate={self.migrate_returncode} "
                f"generate={self.generate_returncode} files={list(self.generated_files)})\n"
                f"{self.generate_output[-600:]}"
            )
        flags = []
        if not self.diff_is_clean:
            flags.append(f"diff={[o.get('operation') for o in self.diff_operations]}")
        if self.regenerated_migration:
            flags.append("regenerated-migration")
        if self.bookkeeping_models:
            flags.append(f"bookkeeping={list(self.bookkeeping_models)}")
        broken = self.unimportable()
        if broken:
            flags.append(f"unimportable={broken}")
        return f"{self.shape_id}: " + ("converged" if not flags else "; ".join(flags))


class RoundTripDriver:
    """Run one model shape through the full reverse-engineering loop."""

    def __init__(
        self,
        root: Path,
        *,
        url_for: Any,
        backend: str,
        env: dict[str, str] | None = None,
        prepare_database: Any = None,
    ) -> None:
        """``prepare_database(name)`` creates the target database, if the backend
        needs one to exist before dbwarden connects (ClickHouse does)."""
        self.root = Path(root)
        self.url_for = url_for
        self.backend = backend
        self.env = env
        self.prepare_database = prepare_database

    def run(self, shape_id: str, model_source: str) -> RoundTripResult:
        work_dir = self.root / f"rt__{re.sub(r'[^A-Za-z0-9_]+', '_', shape_id)}"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        (work_dir / "app").mkdir()
        (work_dir / "app" / "__init__.py").write_text("", encoding="utf-8")

        database_url, database = self.url_for(shape_id, work_dir)
        if self.prepare_database is not None and database:
            self.prepare_database(database)
        cli = DbwardenCli(work_dir, env=self.env)

        def invoke(*args: str) -> tuple[int, str]:
            command = cli.run(*args, check=False)
            return command.returncode, strip_ansi(command.stdout) + strip_ansi(command.stderr)

        invoke("init")
        (work_dir / "dbwarden.py").write_text(
            "from dbwarden import database_config\n\n"
            "primary = database_config(\n"
            "    database_name='primary', default=True,\n"
            f"    database_type={self.backend!r},\n"
            f"    database_url_sync={database_url!r},\n"
            "    model_paths=['app'],\n)\n",
            encoding="utf-8",
        )
        (work_dir / "app" / "models.py").write_text(model_source, encoding="utf-8")

        result = RoundTripResult(shape_id, work_dir, database)
        result.make_returncode, _ = invoke("make-migrations", "declare")
        result.migrate_returncode, _ = invoke("migrate")

        generated = work_dir / "gen"
        generated.mkdir()
        result.generate_returncode, result.generate_output = invoke(
            "generate-models", "--output", "gen"
        )
        files = sorted(generated.glob("*.py"))
        result.generated_files = tuple(path.name for path in files)
        result.generated_sources = {
            path.name: path.read_text(encoding="utf-8") for path in files
        }

        # Adopt the generated models exactly as a user would.
        (work_dir / "app" / "models.py").unlink(missing_ok=True)
        for path in files:
            if path.name == "__init__.py":
                continue
            shutil.copy(path, work_dir / "app" / path.name)

        _, result.rediff_output = invoke("diff", "--out", "json")
        migrations = work_dir / "migrations" / "primary"
        before = set(migrations.glob("*.sql")) if migrations.exists() else set()
        result.remake_returncode, result.remake_output = invoke("make-migrations", "adopt")
        after = set(migrations.glob("*.sql")) if migrations.exists() else set()
        result.remake_sql = "\n\n".join(
            path.read_text(encoding="utf-8") for path in sorted(after - before)
        )
        return result
