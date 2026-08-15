from pathlib import Path

import pytest

from schemas.base import ReferenceSchema
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


def test_schema_runner_reports_missing_expected_objects(tmp_path: Path):
    schema = ReferenceSchema(
        "missing",
        tmp_path / "models.py",
        ("users",),
        ("ix_users_email",),
        "sqlite",
    )
    schema.models_py.write_text("", encoding="utf-8")
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    runner = SchemaRunner(schema, player, database_type="sqlite")

    with pytest.raises(AssertionError, match="incomplete"):
        runner.assert_expected_schema()
