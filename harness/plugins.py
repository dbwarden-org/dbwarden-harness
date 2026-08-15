from __future__ import annotations

from pathlib import Path

from harness.cli import CommandResult, DbwardenCli

REQUIRED_PLUGINS = (
    "dbwarden-pgsql-types",
    "dbwarden-pgsql-rbac",
    "dbwarden-pgsql-extensions",
    "dbwarden-ch-rbac",
    "dbwarden-fastapi",
    "dbwarden-sandbox",
    "dbwarden-seeds",
)

PLUGIN_VERSION_MATRIX = {plugin: (None,) for plugin in REQUIRED_PLUGINS}


class PluginInstaller:
    """Install plugins through DBWarden's public plugin CLI."""

    def __init__(self, work_dir: Path) -> None:
        self.cli = DbwardenCli(work_dir)

    def add(self, distribution: str, *, version: str | None = None) -> CommandResult:
        return self.cli.run(*self.build_add_command(distribution, version=version))

    def build_add_command(self, distribution: str, *, version: str | None = None) -> tuple[str, ...]:
        package = f"{distribution}=={version}" if version else distribution
        return ("plugin", "add", package)

    def add_many(self, distributions: list[str] | tuple[str, ...]) -> list[CommandResult]:
        return [self.add(distribution) for distribution in distributions]

    def add_required(self) -> list[CommandResult]:
        return self.add_many(REQUIRED_PLUGINS)

    def list(self) -> CommandResult:
        return self.cli.run("plugin", "list")

    def info(self, distribution: str) -> CommandResult:
        return self.cli.run("plugin", "info", distribution)

    def remove(self, distribution: str) -> CommandResult:
        return self.cli.run("plugin", "remove", distribution)

    @staticmethod
    def assert_discovered(result: CommandResult, distributions: tuple[str, ...] = REQUIRED_PLUGINS) -> None:
        output = result.output.lower()
        missing = [distribution for distribution in distributions if distribution.lower() not in output]
        if missing:
            raise AssertionError(f"Plugins missing from discovery output: {missing}\n{result.output}")
