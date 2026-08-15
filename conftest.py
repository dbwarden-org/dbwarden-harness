import os
import re
import shutil
from pathlib import Path

import pytest

from tools.artifacts import ArtifactCollector


def pytest_collection_modifyitems(config, items):
    if os.getenv("DBWARDEN_HARNESS_RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="set DBWARDEN_HARNESS_RUN_INTEGRATION=1 to run Docker suites")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    artifact_root = os.getenv("DBWARDEN_HARNESS_ARTIFACT_DIR")
    if not artifact_root:
        return
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid)
    destination = Path(artifact_root) / safe_name
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "failure.txt").write_text(report.longreprtext, encoding="utf-8")
    work_dir = item.funcargs.get("tmp_path")
    if isinstance(work_dir, Path) and work_dir.exists():
        shutil.copytree(work_dir, destination / "work", dirs_exist_ok=True)
    provider = item.funcargs.get("provider")
    if provider is not None:
        ArtifactCollector().capture_provider(provider, destination)
