# Plugin Tests

Plugin tests validate the public installation and discovery path.

## Declared plugins

- `dbwarden-pgsql-types`
- `dbwarden-pgsql-rbac`
- `dbwarden-pgsql-extensions`
- `dbwarden-ch-rbac`
- `dbwarden-fastapi`
- `dbwarden-sandbox`
- `dbwarden-seeds`

## Current checks

`PluginInstaller` builds public CLI commands, installs required distributions,
lists discovered plugins, and inspects installed package metadata. Unit tests
also verify command construction and explicit version pinning.

## Run

The full plugin installation test is integration marked because it installs
packages through the DBWarden CLI:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/plugin_integration
```

Plugin composition with real backend objects is the next expansion area. The
current suite intentionally separates package discovery from backend behavior.
