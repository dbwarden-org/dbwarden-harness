# Plugin Tests

Plugin tests validate the public installation and discovery path, and the
behaviour of plugin-contributed objects against a real server.

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

`test_pgsql_rbac_roles.py` goes past discovery. It installs
`dbwarden-pgsql-rbac`, declares a role through the `pg_roles` configuration key
that plugin contributes, and walks the role through create, alter, and drop
against PostgreSQL, reading `pg_roles` after each step.

That path is only reachable here. A plugin's ops run only once the plugin is
loaded, and dbwarden's own suite deliberately does not load plugins so it stays
hermetic, so without a harness case the loaded path is untested on both sides.
The alter step carries the most weight: a handler that emits only `CREATE ROLE`
and `DROP ROLE` still converges across a create/drop pair, and only changing an
attribute of an existing role exposes the gap.

## Run

The full plugin installation test is integration marked because it installs
packages through the dbwarden CLI:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/plugin_integration
```

Composition across several plugins at once - ordering, duplicate
registrations, and version skew between them - remains the next expansion
area.
