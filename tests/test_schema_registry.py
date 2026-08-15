from pathlib import Path

from schemas.registry import discover_schemas


def test_reference_schema_registry_contains_all_named_fixtures():
    schemas = discover_schemas(Path(__file__).parents[1] / "schemas")
    assert {schema.name for schema in schemas} == {"analytics", "ecommerce", "edge_cases", "rbac_complex"}
