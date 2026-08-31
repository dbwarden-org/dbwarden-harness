# Safety Tests

A tool that guards destructive changes has to fail in the right places. The
safety suite checks the refusals: commands that must not invent success, and
destructive operations that must not proceed unattended.

## Files

- `suites/safety/test_cli_failures.py`

## Scenarios

| Test | Question |
| --- | --- |
| `test_invalid_cli_command_is_reported_without_synthetic_success` | Does an unknown command exit non-zero instead of printing help and succeeding? |
| `test_stateful_commands_fail_without_a_consumer_configuration` | Does a command that needs configuration say so rather than guessing? |
| `test_safety_check_reports_non_destructive_info_changes` | Are harmless changes classified as informational? |
| `test_warning_level_destructive_migration_requires_force` | Is a destructive change refused until it is explicitly forced? |

## Why failure assertions carry their own weight

A test that only asserts a non-zero exit code also passes when the tool crashes
for an unrelated reason. `harness/cli.py` therefore separates three outcomes:
`require_success`, `require_clean` (success with an empty stderr), and
`require_failure(*fragments)`, which additionally requires named text in the
output. The destructive case uses it in that stronger form: refusing a
`DROP TABLE` is only correct if the refusal says `require --force`, and the
same command with `--force` then succeeds.

## Run

```bash
uv run pytest -q suites/safety
```
