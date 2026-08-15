from harness.matrix import provider_versions


def test_provider_matrix_contains_all_declared_backend_versions():
    cases = tuple(provider_versions())

    assert len(cases) == 10
    assert ("postgres", "14") in cases
    assert ("clickhouse", "26.6") in cases
    assert ("mariadb", "11.4") in cases
