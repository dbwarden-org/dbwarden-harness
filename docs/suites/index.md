# Test Suites

Suites are grouped by the confidence question they answer. Fast tests verify
the harness itself. Integration tests verify real provider behavior. Slow tests
measure durability and performance.

| Suite | Location | Main question |
| --- | --- | --- |
| Distribution | `suites/distribution` | Can a clean install expose the expected CLI? |
| Round trips | `suites/round_trip` | Does a real database converge? |
| Durability | `suites/durability` | Does migration history survive rollback and failure? |
| Safety | `suites/safety` | Are risky operations classified and guarded? |
| Offline | `suites/offline` | Can local artifacts support offline workflows? |
| Plugins | `suites/plugin_integration` | Do public plugins install and compose? |
| Adoption | `suites/adoption` | Can an existing schema be handed to DBWarden? |
| SQL contracts | `suites/sql_contract` | Is generated output deterministic and approved? |
| Performance | `suites/performance` | Does scale remain within the measured budget? |

Run one category with:

```bash
uv run pytest -q suites/distribution
```

Use the integration environment variable for provider categories.
