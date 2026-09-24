import ast
import sys
import types

import pytest

from mcp_server.classifier import classify_divergence
from mcp_server.comparator import compare_schemas
from mcp_server.inspector import sqlalchemy_url
from mcp_server.mutations import MutationError, apply_mutation
from mcp_server.track_b import _load_models_module
from tests.test_mcp_server_smoke import SAMPLE_MODELS


@pytest.mark.parametrize(
    ("left", "right", "backend"),
    [
        ("CREATE TABLE t(x TEXT DEFAULT 'a  b')", "CREATE TABLE t(x TEXT DEFAULT 'a b')", "sqlite"),
        ("CREATE TABLE t(x TEXT DEFAULT '--a')", "CREATE TABLE t(x TEXT DEFAULT '--b')", "sqlite"),
        (
            "CREATE TABLE t(x TEXT DEFAULT 'x;y,(z)')",
            "CREATE TABLE t(x TEXT DEFAULT 'x;y,(q)')",
            "sqlite",
        ),
        ('CREATE TABLE "Users"(x INT)', 'CREATE TABLE "users"(x INT)', "postgresql"),
        ("CREATE TABLE first.t(x INT)", "CREATE TABLE second.t(x INT)", "postgresql"),
        ("CREATE TABLE t(x INT) ENGINE=InnoDB", "CREATE TABLE t(x INT) ENGINE=MyISAM", "mysql"),
        (
            "CREATE TABLE t(x INTEGER PRIMARY KEY AUTOINCREMENT)",
            "CREATE TABLE t(x INTEGER PRIMARY KEY)",
            "sqlite",
        ),
        ("CREATE TABLE t(x INT CHECK(x > 0))", "CREATE TABLE t(x INT CHECK(x > 1))", "sqlite"),
    ],
)
def test_comparator_preserves_semantic_differences(left, right, backend):
    assert not compare_schemas(left, right, backend).identical


def test_comparator_equivalent_constraints_and_quoted_names():
    left = "CREATE TABLE t(id INTEGER NOT NULL PRIMARY KEY, n TEXT, CONSTRAINT uq_n UNIQUE(n))"
    right = 'CREATE TABLE t("id" INTEGER NOT NULL, "n" TEXT, PRIMARY KEY(id), CONSTRAINT uq_n UNIQUE(n))'
    assert compare_schemas(left, right, "sqlite").identical


def test_comparator_reports_missing_objects_from_reference():
    result = compare_schemas(
        "CREATE TABLE t(id INT)", "CREATE TABLE t(id INT, n TEXT); CREATE TABLE other(id INT)"
    )
    assert result.summary.missing_tables == ['"other"']
    assert result.summary.missing_columns == [{"table": '"t"', "column": '"n"'}]


def test_clickhouse_provider_url_uses_installed_driver():
    url = sqlalchemy_url("https://tester:p%40ss@localhost/example")
    assert url.drivername == "clickhousedb"
    assert url.port == 8443
    assert url.password == "p@ss"
    assert url.query == {"secure": "true"}


def test_sqlite_integer_primary_key_is_distinct_from_int_primary_key():
    assert not compare_schemas("CREATE TABLE t(id INT PRIMARY KEY)", "CREATE TABLE t(id INTEGER PRIMARY KEY)", "sqlite").identical


def load_model(source):
    module = types.ModuleType("harness_mutation_test")
    sys.modules[module.__name__] = module
    try:
        exec(compile(source, "<mutation>", "exec"), module.__dict__)  # noqa: S102 - test fixture
        return module.User.__table__
    finally:
        sys.modules.pop(module.__name__, None)


def test_mutations_reach_sqlalchemy_metadata():
    source = apply_mutation(
        SAMPLE_MODELS,
        {"type": "add_column", "table": "users", "column": "bio", "column_type": "Text"},
    )
    assert str(load_model(source).c.bio.type) == "TEXT"
    source = apply_mutation(
        source, {"type": "change_type", "table": "users", "column": "bio", "new_type": "String(80)"}
    )
    assert load_model(source).c.bio.type.length == 80
    for kind, nullable in [("set_not_null", False), ("drop_not_null", True)]:
        source = apply_mutation(source, {"type": kind, "table": "users", "column": "bio"})
        assert load_model(source).c.bio.nullable is nullable
    value = "hello, ') world"
    source = apply_mutation(
        source, {"type": "set_default", "table": "users", "column": "bio", "default": value}
    )
    assert load_model(source).c.bio.default.arg == value
    source = apply_mutation(source, {"type": "drop_default", "table": "users", "column": "bio"})
    assert load_model(source).c.bio.default is None
    source = apply_mutation(source, {"type": "drop_column", "table": "users", "column": "bio"})
    assert "bio" not in load_model(source).c


@pytest.mark.parametrize("unique", [True, False])
def test_index_mutation_preserves_all_columns_and_uniqueness(unique):
    source = apply_mutation(
        SAMPLE_MODELS,
        {"type": "add_index", "table": "users", "columns": ["id", "email"], "unique": unique},
    )
    (index,) = load_model(source).indexes
    assert list(index.columns.keys()) == ["id", "email"]
    assert index.unique is unique


def test_duplicate_column_mutation_fails():
    with pytest.raises(MutationError, match="already exists"):
        apply_mutation(
            SAMPLE_MODELS,
            {"type": "add_column", "table": "users", "column": "email", "column_type": "Text"},
        )
    ast.parse(SAMPLE_MODELS)


@pytest.mark.parametrize(("column_type", "expected"), [("VARCHAR(80)", "95"), ("geometry", "5")])
def test_classifier_reads_current_plan_schema(column_type, expected):
    assert (
        classify_divergence(
            {"operations": [{"type": "add_column", "definition": {"type": column_type}}]}, {}
        )
        == expected
    )


def test_reference_loader_uses_current_source_with_same_size(tmp_path):
    path = tmp_path / "models.py"
    assert _load_models_module(path, "value = 1\n").value == 1
    assert _load_models_module(path, "value = 2\n").value == 2
