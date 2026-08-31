# Test Suites

Suites are grouped by the confidence question they answer.

| Suite | Location | Main question |
| --- | --- | --- |
| Distribution | `suites/distribution` | Can a clean install expose the expected CLI? |
| Round trips | `suites/round_trip` | Does a real database converge? |
| Semantics | `suites/semantics` | Does the server enforce what the models declare, and stay converged? |
| Adversarial | `suites/adversarial` | Do the dangerous edges of schema evolution behave? |
| Durability | `suites/durability` | Does migration history survive rollback and failure? |
| Safety | `suites/safety` | Are risky operations classified and guarded? |
| Offline | `suites/offline` | Can local artifacts support offline workflows? |
| Plugins | `suites/plugin_integration` | Do public plugins install and compose? |
| Adoption | `suites/adoption` | Can an existing schema be handed to dbwarden? |
| SQL contracts | `suites/sql_contract` | Is generated output deterministic and approved? |
| Performance | `suites/performance` | Does scale remain within the measured budget? |
| Generative | `suites/generative` | Which of hundreds of nearly-identical declarations work? |

Run one category with:

```bash
uv run pytest -q suites/distribution
```

## Tiers

Suites are not split by speed at the directory level; every suite splits along
the same marker line.

| Marker | Needs | Selected by |
| --- | --- | --- |
| none | SQLite or a generated artifact only | `pytest -m "not integration and not slow"` |
| `integration` | A container from `infrastructure/providers` | `DBWARDEN_HARNESS_RUN_INTEGRATION=1 pytest -m integration` |
| `slow` | A container, and time | Add `-m slow` explicitly |

`conftest.py` skips `integration` tests unless
`DBWARDEN_HARNESS_RUN_INTEGRATION=1` is set, so a machine without Docker still
runs the fast tier to completion instead of erroring.

Suites that can answer their question both ways keep cases in both tiers on
purpose: the SQLite case fails first and explains itself without Docker, and
the container case proves the behaviour on a real server.
