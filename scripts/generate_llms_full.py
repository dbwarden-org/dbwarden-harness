"""Generate one plain text file containing the complete harness documentation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT = DOCS_DIR / "llms-full.txt"
SITE_URL = "https://dbwarden-org.github.io/dbwarden-harness"
SKIP_FILES = {"llms.txt", "llms-full.txt"}
SKIP_DIRS = {"overrides", "stylesheets"}


def route_path_from_file(filepath: Path) -> str:
    relative = filepath.relative_to(DOCS_DIR)
    parts = list(relative.parts)
    if parts[-1] == "index.md":
        parts.pop()
        return "/" if not parts else "/" + "/".join(parts) + "/"
    return "/" + str(Path(*parts).with_suffix("")) + "/"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def main() -> int:
    markdown_files = sorted(DOCS_DIR.rglob("*.md"))
    markdown_files = [
        path
        for path in markdown_files
        if path.name not in SKIP_FILES and not any(directory in path.parts for directory in SKIP_DIRS)
    ]
    sections = [
        "# DBWarden Test Harness Documentation",
        "> Full documentation for black-box DBWarden release validation",
        f"> Source: {SITE_URL}",
        f"> Pages: {len(markdown_files)}",
        "",
    ]
    for markdown_file in markdown_files:
        route = route_path_from_file(markdown_file)
        sections.extend(
            [
                "=" * 72,
                f"PAGE: {SITE_URL.rstrip('/')}{route}",
                "=" * 72,
                "",
                strip_frontmatter(markdown_file.read_text(encoding="utf-8")).strip(),
                "",
            ]
        )
    OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Written {OUTPUT} ({len(markdown_files)} pages, {size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
