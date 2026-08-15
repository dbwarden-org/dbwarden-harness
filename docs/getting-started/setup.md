# Setup

## Requirements

- Python 3.12.7 or newer
- `uv`
- Docker for integration suites
- Network access to PyPI for a clean dependency resolution
- A Docker daemon with enough memory for database containers

The fast suite does not require Docker. Provider tests are marked
`integration` and skipped unless explicitly enabled.

## Install the locked environment

From the repository root:

```bash
uv venv
uv sync --locked
```

The lockfile includes DBWarden database extras, Testcontainers, pytest, Ruff,
benchmark tooling, Zensical, and the SEO extension used by the documentation.

## Confirm the consumer package

```bash
uv run dbwarden version
uv run pytest -q tests/test_distribution.py
```

The distribution tests verify that DBWarden is installed, exposes its expected
package files, has a console entry point, and does not resolve from a source
checkout.

## Confirm Docker

```bash
docker info
```

The harness providers use Testcontainers directly. The compose files under
`infrastructure` are available for local service inspection, but the pytest
providers own their container lifecycle.
