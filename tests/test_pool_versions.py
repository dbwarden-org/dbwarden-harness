from collections import deque
from unittest.mock import Mock

from mcp_server.pool import ContainerPool


def test_pool_claim_respects_requested_version(monkeypatch):
    pool = ContainerPool()
    old, requested = Mock(), Mock()
    old.version.return_value = "16"
    requested.version.return_value = "17"
    old._container = requested._container = None
    pool._queues["postgresql"] = deque([old, requested])
    factory = Mock(side_effect=AssertionError("matching provider already pooled"))
    monkeypatch.setattr("mcp_server.pool.provider_for", factory)
    assert pool.claim("postgresql", "17", Mock()) is requested
    assert list(pool._queues["postgresql"]) == [old]
    requested.reset.assert_called_once()
    old.reset.assert_not_called()
