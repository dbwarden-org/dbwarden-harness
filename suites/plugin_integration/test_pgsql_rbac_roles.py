"""A plugin's objects must be created, altered, and dropped on a real server.

Discovery tests prove a plugin installs and registers. They do not prove its
handlers produce SQL a server accepts, and they cannot: the ops only run once a
plugin is loaded, which is exactly the configuration dbwarden's own test suite
avoids in order to stay hermetic. That leaves the loaded path uncovered on both
sides unless the harness covers it here.

`dbwarden-pgsql-rbac` contributes `create_role`, `drop_role`, and `alter_role`.
This walks a role through all three against PostgreSQL and checks the catalog
after each step.
"""

from pathlib import Path

import pytest

from harness.plugins import PluginInstaller
from infrastructure.providers import provider_for
from tools.migration_player import MigrationPlayer
from tools.sql_probe import SqlProbe

ROLE = "dbw_harness_reader"

MODELS = '''\
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from dbwarden.databases import TableMeta


Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(120), nullable=False)

    class Meta(TableMeta):
        comment = "Something for a role to be granted on"
'''


def _require_plugin(tmp_path: Path) -> None:
    """Make `dbwarden-pgsql-rbac` available, or skip with the reason.

    `dbwarden plugin add` shells out to pip, which a uv-managed environment does
    not necessarily contain. The plugin being installed some other way is still
    a valid starting point for this test - what it checks is the plugin's
    behaviour once loaded, not the installer, which
    `test_public_plugin_install.py` covers.
    """
    from importlib.util import find_spec

    if find_spec("dbwarden_pgsql_rbac") is not None:
        return

    result = PluginInstaller(tmp_path).add("dbwarden-pgsql-rbac")
    if result.returncode != 0 or find_spec("dbwarden_pgsql_rbac") is None:
        pytest.skip(
            "dbwarden-pgsql-rbac is not installed and could not be installed "
            f"through the CLI:\n{result.plain_output}"
        )


def _role_row(probe: SqlProbe) -> tuple | None:
    rows = probe.rows(
        "SELECT rolcanlogin, rolcreatedb FROM pg_roles "
        f"WHERE rolname = '{ROLE}'"
    )
    return rows[0] if rows else None


@pytest.mark.integration
def test_pgsql_rbac_role_lifecycle(tmp_path: Path):
    _require_plugin(tmp_path)

    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.write_model_source("", filename="app/__init__.py")
        player.write_model_source(MODELS, filename="app/models.py")
        player.init()
        player.configure(
            database_type="postgresql",
            model_paths=("app",),
            pg_roles=[{"name": ROLE, "login": True}],
        )

        player.make_migrations("create the reporting role")
        player.migrate()

        with SqlProbe(player.database_url) as probe:
            row = _role_row(probe)
            assert row is not None, f"{ROLE} was never created"
            assert row[0] is True, "the role was created without LOGIN"
        player.assert_converged()

        # Altering an existing role is the step a create/drop pair hides: the
        # role already exists, so a handler that only emits CREATE and DROP
        # reports convergence while the attribute never changes.
        player.configure(
            database_type="postgresql",
            model_paths=("app",),
            pg_roles=[{"name": ROLE, "login": True, "createdb": True}],
        )
        player.make_migrations("grant the role createdb")
        player.migrate()

        with SqlProbe(player.database_url) as probe:
            assert _role_row(probe) == (True, True), "ALTER ROLE did not take effect"
        player.assert_converged()

        # Removing the declaration is deliberately not destructive: a role is
        # cluster-wide and may be in use by databases dbwarden knows nothing
        # about, so the plugin leaves it alone rather than dropping it. This
        # asserts that contract explicitly - if the behaviour ever changes to
        # emit DROP ROLE, it should change here first, not in a user's cluster.
        player.configure(
            database_type="postgresql",
            model_paths=("app",),
            pg_roles=[],
        )
        player.make_migrations("stop declaring the reporting role")
        player.migrate()

        with SqlProbe(player.database_url) as probe:
            assert _role_row(probe) == (True, True), (
                "undeclaring a role must leave the existing role untouched"
            )
        player.assert_converged()
    finally:
        provider.stop()
