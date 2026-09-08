from pathlib import Path

from schemas.registry import discover_schemas


def test_reference_schema_registry_contains_all_named_fixtures():
    schemas = discover_schemas(Path(__file__).parents[1] / "schemas")
    # The registry discovers all schemas with schema.json files.
    # This test ensures all schemas are discovered successfully.
    assert len(schemas) > 0, "No schemas discovered"
    # Check that the original core schemas are still present
    schema_names = {schema.name for schema in schemas}
    assert "analytics" in schema_names, "Missing analytics schema"
    assert "ecommerce" in schema_names, "Missing ecommerce schema"
    assert "edge_cases" in schema_names, "Missing edge_cases schema"
    assert "rbac_complex" in schema_names, "Missing rbac_complex schema"
