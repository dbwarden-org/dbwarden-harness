from tools.migration_player import parse_diff_output


def test_parse_diff_output_ignores_log_prefix():
    output = "INFO dbwarden - connected\n[{\"operation\": \"add_table\", \"table\": \"users\"}]"

    assert parse_diff_output(output) == [{"operation": "add_table", "table": "users"}]


def test_parse_diff_output_returns_empty_for_no_changes():
    assert parse_diff_output("INFO dbwarden - no changes\n") == []
