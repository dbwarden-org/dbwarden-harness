from __future__ import annotations

import warnings

# FastMCP 1.x triggers a pydantic_settings forward-reference warning at import
# time that is unrelated to harness behavior.
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="pydantic_settings.sources.utils",
)

from mcp_server.server import run_server

if __name__ == "__main__":
    run_server()
