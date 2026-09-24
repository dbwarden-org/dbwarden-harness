from types import SimpleNamespace

import pytest

from mcp_server.dumper import dump_database_schema


@pytest.mark.parametrize(("backend", "scheme", "key"), [
    ("postgresql", "postgresql+psycopg2", "PGPASSWORD"),
    ("mysql", "mysql+pymysql", "MYSQL_PWD"),
])
def test_dump_commands_inherit_environment_and_decode_url(monkeypatch, backend, scheme, key):
    monkeypatch.setenv("HARNESS_DUMP_SENTINEL", "keep")
    monkeypatch.setattr("mcp_server.dumper.shutil.which", lambda name: name)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="CREATE TABLE t(id INT);", stderr="")

    monkeypatch.setattr("mcp_server.dumper.subprocess.run", run)
    assert dump_database_schema(f"{scheme}://test%20user:p%40ss@localhost/db%20name", backend)
    args, options = calls[0]
    assert "test user" in args
    assert args[-1] == "db name"
    assert all("p@ss" not in arg for arg in args)
    assert options["env"][key] == "p@ss"
    assert options["env"]["HARNESS_DUMP_SENTINEL"] == "keep"
