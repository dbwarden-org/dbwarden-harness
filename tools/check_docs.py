"""Check documentation links, navigation, snippets, settings, and API inventory."""
from __future__ import annotations

import ast
import json
import re
import sys
import textwrap
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("harness", "infrastructure", "tools", "mcp_server", "schemas")


def sources():
    return sorted(path for package in PACKAGES for path in (ROOT / package).rglob("*.py")
                  if path.name != "models.py" or path.parent.name == "mcp_server")


def api_reference() -> str:
    lines = ["# Python API Reference", "", "Generated from source with `uv run python -m tools.check_docs --api-reference`.",
             "Lists public definitions, constructors, methods, and dataclass fields. These are harness APIs; dbwarden is invoked through its installed CLI.",
             "Abstract provider methods define the contract implemented by concrete providers. See [MCP Server](../mcp-server.md) for remote tools and limits.", ""]
    for path in sources():
        if path.stem == "check_docs":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        definitions = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")]
        if not definitions:
            continue
        lines.extend([f"## `{path.relative_to(ROOT).as_posix()}`", ""])
        for node in definitions:
            lines.extend([f"### `{node.name}`", ""])
            doc = ast.get_docstring(node)
            if doc:
                lines.extend([doc.split("\n\n")[0].replace("\n", " "), ""])
            if isinstance(node, ast.ClassDef):
                members = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (not item.name.startswith("_") or item.name == "__init__")]
                fields = [ast.unparse(item) for item in node.body if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and not item.target.id.startswith("_")]
            else:
                members, fields = [node], []
            lines.extend(["```python", *fields])
            for member in members:
                annotation = f" -> {ast.unparse(member.returns)}" if member.returns else ""
                lines.append(f"{'async ' if isinstance(member, ast.AsyncFunctionDef) else ''}def {member.name}({ast.unparse(member.args)}){annotation}: ...")
            lines.extend(["```", ""])
    return "\n".join(lines)


def check() -> dict:
    documents = sorted({*(ROOT / "docs").rglob("*.md"), *ROOT.glob("*.md"), *(ROOT / "schemas").rglob("*.md"), *(ROOT / "suites").rglob("*.md")})
    issues = []
    api_path = ROOT / "docs/reference/python-api.md"
    if not api_path.exists() or api_path.read_text(encoding="utf-8") != api_reference():
        issues.append("Python API reference differs from source; regenerate it")
    config = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))

    def nav_paths(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from nav_paths(item)
        elif isinstance(value, list):
            for item in value:
                yield from nav_paths(item)

    nav = set(nav_paths(config["project"]["nav"]))
    for name in nav:
        if not (ROOT / "docs" / name).is_file():
            issues.append(f"Missing navigation target: {name}")
    for path in (ROOT / "docs").rglob("*.md"):
        name = path.relative_to(ROOT / "docs").as_posix()
        if name not in nav and name != "README.md":
            issues.append(f"Page missing from navigation: {name}")
    snippets = 0
    for path in documents:
        content = path.read_text(encoding="utf-8")
        for language, body in re.findall(r"^```([^\n]*)\n(.*?)^```", content, re.MULTILINE | re.DOTALL):
            if language.strip() not in {"python", "py"}:
                continue
            snippets += 1
            try:
                ast.parse(textwrap.dedent(body))
            except SyntaxError as exc:
                issues.append(f"{path.relative_to(ROOT)}: invalid Python snippet: {exc.msg}")
        for link in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", content):
            url = urlsplit(link.strip("<>"))
            if url.scheme or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.exists():
                issues.append(f"{path.relative_to(ROOT)}: broken link {link}")
    settings = set()
    for path in [*sources(), *(ROOT / "suites").rglob("*.py"), ROOT / "conftest.py"]:
        settings.update(re.findall(r'["\x27]((?:DBWARDEN_HARNESS_|MCP_)[A-Z0-9_]+)["\x27]', path.read_text(encoding="utf-8")))
    environment = (ROOT / "docs/reference/environment.md").read_text(encoding="utf-8")
    issues.extend(f"Undocumented environment variable: {name}" for name in sorted(settings) if f"`{name}`" not in environment)
    tree = ast.parse((ROOT / "mcp_server/server.py").read_text(encoding="utf-8"))
    remote = [node.name for node in tree.body if isinstance(node, ast.FunctionDef) and any(ast.unparse(d).startswith("mcp.tool(") for d in node.decorator_list)]
    guide = (ROOT / "docs/mcp-server.md").read_text(encoding="utf-8")
    issues.extend(f"Undocumented MCP tool: {name}" for name in remote if f"`{name}" not in guide)
    return {"documents": len(documents), "python_snippets": snippets, "source_modules": len(sources()), "mcp_tools": len(remote), "environment_variables": len(settings), "issues": issues}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--api-reference" in sys.argv:
        print(api_reference(), end="")
    else:
        result = check()
        print(json.dumps(result, indent=2))
        raise SystemExit(bool(result["issues"]))
