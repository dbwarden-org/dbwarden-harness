"""Every object kind the public API can declare must reach the database.

``dbwarden.databases.clickhouse`` exports builders for dictionaries, named
collections, data operations and six RBAC specs, and ``dbwarden.databases``
exports ``seed_data``.  A model that uses them is accepted, migrates cleanly and
reports success -- so nothing in a normal test run distinguishes "this feature
works" from "this feature emits no SQL at all".

These tests assert the minimum contract: if a declaration is accepted, some
corresponding DDL must appear in the migration.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_, module

pytestmark = pytest.mark.integration

SOURCE_TABLE = ClickHouseTable(
    name="src",
    class_name="Src",
    columns=(Column_("id", primary_key=True), Column_("amt", "Float")),
).render()

QUOTE = chr(39)
DICT_SOURCE = f"CLICKHOUSE(TABLE {QUOTE}src{QUOTE})"

DICTIONARY_LAYOUTS = {
    "flat": f'dictionary(layout="FLAT()", source="{DICT_SOURCE}", lifetime=300, primary_key="id")',
    "hashed": f'dictionary(layout="HASHED()", source="{DICT_SOURCE}", lifetime=0, primary_key="id")',
    "cache": f'dictionary(layout="CACHE(SIZE_IN_CELLS 1000)", source="{DICT_SOURCE}", lifetime="MIN 1 MAX 10", primary_key="id")',
    "complex_key": f'dictionary(layout="COMPLEX_KEY_HASHED()", source="{DICT_SOURCE}", lifetime=60, primary_key=["id","name"])',
}


def _dictionary_source(spec: str) -> str:
    table = ClickHouseTable(
        name="d",
        class_name="D",
        columns=(Column_("id", primary_key=True), Column_("name", "String")),
        raw_meta=f"ch = {spec}",
    )
    return module("clickhouse", SOURCE_TABLE, table.render())


@pytest.mark.parametrize("layout", sorted(DICTIONARY_LAYOUTS))
def test_dictionary_declaration_emits_create_dictionary(clickhouse_runner, layout):
    result = clickhouse_runner.run(
        GenerationCase(
            f"dictionary_{layout}",
            "clickhouse",
            (_dictionary_source(DICTIONARY_LAYOUTS[layout]),),
            capture_schema=True,
        )
    )
    sql = result.steps[0].sql
    assert "CREATE DICTIONARY" in sql.upper(), (
        f"dictionary(layout={layout!r}) generated a plain table instead of a "
        f"dictionary; layout, source, lifetime and primary key were all discarded:\n{sql}"
    )


MODULE_LEVEL_OBJECTS = {
    "role": ('ROLE = ChRoleSpec(name="analyst")', "CREATE ROLE"),
    "user": ('USER = ChUserSpec(name="bob")', "CREATE USER"),
    "named_collection": (
        'NC = named_collection("creds", user="admin", password="pw")',
        "NAMED COLLECTION",
    ),
    "data_op": (
        'OP = data_op(name="bf", forward="INSERT INTO src (id, amt) VALUES (1, 1.0)",'
        ' rollback="TRUNCATE TABLE src")',
        "INSERT INTO src",
    ),
    "seed": ('SEED = seed_data("src", [{"id": 1, "amt": 1.0}])', "INSERT"),
}


@pytest.mark.parametrize("kind", sorted(MODULE_LEVEL_OBJECTS))
def test_module_level_object_reaches_the_migration(clickhouse_runner, kind):
    declaration, expected = MODULE_LEVEL_OBJECTS[kind]
    preamble = "from dbwarden.databases import seed_data, Seed, SeedRow\n"
    source = module("clickhouse", SOURCE_TABLE, declaration + "\n", preamble=preamble)
    result = clickhouse_runner.run(
        GenerationCase(f"object_{kind}", "clickhouse", (source,))
    )
    sql = result.steps[0].sql
    assert expected.upper() in sql.upper(), (
        f"{kind} was declared through the public API, the migration succeeded, and "
        f"no {expected!r} statement was generated:\n{sql}"
    )


VIEW_BASES = ["Base", "ChView", "MaterializedView"]


def test_view_base_class_does_not_change_the_object_graph(clickhouse_runner):
    """The same view declaration must not mean three different things."""
    spec = (
        'materialized_view(select="SELECT id, sum(amt) AS total FROM src GROUP BY id",'
        ' engine=merge_tree(), order_by=["id"])'
    )
    shapes = {}
    for base in VIEW_BASES:
        view = ClickHouseTable(
            name="v",
            class_name="V",
            columns=(Column_("id", primary_key=True), Column_("total", "Float")),
            base=base,
            meta_base="CHViewMeta",
            raw_meta=f"ch = {spec}",
        )
        source = module("clickhouse", SOURCE_TABLE, view.render())
        result = clickhouse_runner.run(
            GenerationCase(f"view_base_{base}", "clickhouse", (source,), capture_schema=True)
        )
        created = sorted(
            line.split()[0] for line in result.live_schema.splitlines() if line.strip()
        )
        shapes[base] = created

    distinct = {tuple(value) for value in shapes.values()}
    assert len(distinct) == 1, (
        "an identical view declaration produced different sets of database objects "
        f"depending only on the base class:\n{shapes}"
    )
