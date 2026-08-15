# Environment Variables

| Variable | Effect |
| --- | --- |
| `DBWARDEN_HARNESS_RUN_INTEGRATION` | Enables Docker and provider tests when set to `1`. |
| `DBWARDEN_HARNESS_RUN_SCALE` | Enables scale benchmarks when set to `1`. |
| `DBWARDEN_HARNESS_RUN_500_MIGRATION` | Enables the expensive 500 migration benchmark when set to `1`. |
| `DBWARDEN_HARNESS_DEFER_EXECUTABLE` | Points benchmark comparison at a DBWarden checkout executable. |
| `DBWARDEN_HARNESS_DEFER_SNAPSHOTS` | Enables deferred snapshot mode in benchmark helpers. |
| `DBWARDEN_HARNESS_BACKEND` | Limits provider matrix lifecycle cases to one backend. |
| `DBWARDEN_HARNESS_VERSIONS` | Limits provider matrix lifecycle cases to listed versions. |
| `DBWARDEN_HARNESS_ARTIFACT_DIR` | Writes failed test artifacts to the selected directory. |

Variables beginning with `DBWARDEN_HARNESS_` are included in command artifact
metadata so a run can be reproduced.
