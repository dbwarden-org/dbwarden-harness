import pytest

from harness.matrix import DEFAULT_MATRIX
from infrastructure.providers import provider_for


@pytest.mark.parametrize(
    ("backend", "versions"),
    [
        ("postgres", DEFAULT_MATRIX.postgres),
        ("clickhouse", DEFAULT_MATRIX.clickhouse),
        ("mysql", DEFAULT_MATRIX.mysql),
        ("mariadb", DEFAULT_MATRIX.mariadb),
    ],
)
def test_matrix_versions_build_pinned_provider(backend: str, versions: tuple[str, ...]):
    for version in versions:
        provider = provider_for(backend, version)
        assert provider.version() == version


def test_provider_factory_rejects_unknown_backend():
    with pytest.raises(ValueError, match="Unsupported backend"):
        provider_for("oracle", "23")
