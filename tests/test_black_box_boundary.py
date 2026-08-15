from pathlib import Path


def test_harness_does_not_import_dbwarden_private_modules():
    root = Path(__file__).parents[1]
    violations: list[str] = []
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        private_module = "dbwarden." + "_internal"
        internal_module = "dbwarden." + "internal"
        if private_module in text or internal_module in text:
            violations.append(str(path.relative_to(root)))

    assert not violations, f"Private DBWarden imports found: {violations}"
