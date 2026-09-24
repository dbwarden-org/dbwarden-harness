from __future__ import annotations

import os
from pathlib import Path

from mcp_server.bundle import assemble_proof_bundle
from mcp_server.classifier import classify_divergence
from mcp_server.comparator import compare_schemas, normalize_schema_dump
from mcp_server.models import TrackResult
from mcp_server.mutations import apply_mutation
from mcp_server.workspace import Workspace

SAMPLE_MODELS = """\
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
"""


def test_normalize_schema_dump_sorts_statements():
    dump = """\
CREATE TABLE users (id integer NOT NULL);
CREATE TABLE orders (id integer NOT NULL);
"""
    normalized = normalize_schema_dump(dump)
    lines = normalized.strip().splitlines()
    assert lines == ['CREATE TABLE "orders" ("id" INT NOT NULL);', 'CREATE TABLE "users" ("id" INT NOT NULL);']


def test_compare_schemas_detects_divergence():
    a = "CREATE TABLE users (id integer NOT NULL);"
    b = "CREATE TABLE users (id bigint NOT NULL);"
    result = compare_schemas(a, b)
    assert not result.identical
    assert "BIGINT" in result.diff
    assert any(item["column"] == '"id"' for item in result.summary.type_mismatches)


def test_compare_schemas_reports_identical():
    dump = "CREATE TABLE users (id integer NOT NULL);"
    result = compare_schemas(dump, dump)
    assert result.identical
    assert result.diff == ""


def test_classify_standard_ops_95():
    plan = {"operations": [{"kind": "add_column", "column_types": ["integer"]}]}
    assert classify_divergence(plan, {}) == "95"


def test_classify_exotic_type_5():
    plan = {"operations": [{"kind": "add_column", "column_types": ["geometry"]}]}
    assert classify_divergence(plan, {}) == "5"


def test_classify_generation_failure_95():
    assert classify_divergence(None, {}) == "95"


def test_apply_mutation_add_column():
    mutation = {"type": "add_column", "table": "users", "column": "bio", "column_type": "Text"}
    result = apply_mutation(SAMPLE_MODELS, mutation)
    assert "bio: Mapped[Text] = mapped_column(Text, nullable=True)" in result


def test_apply_mutation_change_type():
    mutation = {"type": "change_type", "table": "users", "column": "email", "new_type": "Text"}
    result = apply_mutation(SAMPLE_MODELS, mutation)
    assert "email: Mapped[Text]" in result
    assert "mapped_column(Text" in result


def test_assemble_proof_bundle(tmp_path: Path) -> None:
    work_dir = tmp_path / "ws"
    work_dir.mkdir()
    (work_dir / "dbwarden.py").write_text("primary = None\n", encoding="utf-8")

    workspace = Workspace(
        workspace_id="ws-test",
        backend="sqlite",
        db_version="local",
        work_dir=work_dir,
        network=None,
        track_a_provider=None,  # type: ignore[arg-type]
        track_b_provider=None,  # type: ignore[arg-type]
        track_a_url="sqlite://",
        track_b_url="sqlite://",
    )

    track_a = TrackResult(success=True, stage="complete", schema_dump="CREATE TABLE a (id integer);")
    track_b = TrackResult(success=True, stage="complete", schema_dump="CREATE TABLE a (id bigint);")
    comparison = compare_schemas(track_a.schema_dump, track_b.schema_dump)

    os.environ["DBWARDEN_HARNESS_BUG_REPORTS_DIR"] = str(tmp_path / "bug-reports")
    result = assemble_proof_bundle(
        workspace,
        SAMPLE_MODELS,
        SAMPLE_MODELS,
        track_a,
        track_b,
        comparison,
        "nuclear",
    )

    assert result.passed is False
    assert result.proof_bundle_path is not None
    assert (result.proof_bundle_path / "manifest.json").exists()
    assert (result.proof_bundle_path / "classification.json").exists()
    assert (result.proof_bundle_path / "reproduction" / "reproduce.sh").exists()
    assert (result.proof_bundle_path / "comparator" / "diff.patch").exists()
