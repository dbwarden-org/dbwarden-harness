# Failure Artifacts

Set `DBWARDEN_HARNESS_ARTIFACT_DIR` before a run to retain evidence for failed
tests.

```bash
DBWARDEN_HARNESS_ARTIFACT_DIR=artifacts uv run pytest -q
```

## Bundle contents

`ArtifactCollector` writes:

- `stdout.txt`
- `stderr.txt`
- `command.json`
- `provenance.json`
- copied migrations
- copied `.dbwarden` state
- copied paths supplied by a test

When a provider object is available to the pytest failure hook, the bundle also
contains `provider.json` and `provider.log`.

## Metadata

`command.json` records command arguments, return code, working directory,
runtime information, and harness environment variables. `provenance.json`
records installed distribution locations, versions, Python information, and
the harness lockfile digest.

## CI retention

The backend matrix uploads the artifact directory when a provider job fails.
Download the artifact before rerunning if the failure may depend on container
logs or generated files.
