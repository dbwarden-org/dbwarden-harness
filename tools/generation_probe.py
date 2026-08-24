"""Recover the exceptions dbwarden swallows during model discovery.

``dbwarden/engine/model_discovery/extraction.py`` wraps table and column
extraction in a bare ``except Exception: return None``.  A table that fails to
extract therefore disappears, and ``make-migrations`` reports
``No tables found in models`` and exits 0 — the user is told they have no
models rather than that one of them is invalid.

That failure mode is indistinguishable from an empty project through the public
CLI, which is exactly the kind of thing this harness exists to expose.  The
probe runs the real CLI in a subprocess with ``extract_table_from_model``
instrumented so that a ``None`` return is re-executed under ``sys.settrace`` and
the original exception is printed.

This is the one place the harness reaches past the public interface.  It never
changes what dbwarden does — the probe only observes — and it is used for
diagnosis in failure output, never to make a test pass.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MARKER = "### dbwarden-harness swallowed"

_PROBE_SOURCE = f'''
import sys, traceback
import dbwarden.engine.model_discovery.extraction as extraction

_original = extraction.extract_table_from_model


def _instrumented(model_class, db_name=None):
    result = _original(model_class, db_name)
    if result is not None:
        return result
    captured = []

    def tracer(frame, event, arg):
        if event == "exception" and "dbwarden" in frame.f_code.co_filename:
            captured.append((arg, frame.f_code.co_filename, frame.f_lineno))
        return tracer

    sys.settrace(tracer)
    try:
        _original(model_class, db_name)
    finally:
        sys.settrace(None)
    for (exc_info, filename, lineno) in captured:
        if exc_info[0] is GeneratorExit:
            continue
        print(f"{MARKER} {{filename}}:{{lineno}}", file=sys.stderr)
        traceback.print_exception(*exc_info, limit=6, file=sys.stderr)
    return result


extraction.extract_table_from_model = _instrumented
for module in list(sys.modules.values()):
    if module is None:
        continue
    if getattr(module, "__name__", "").startswith("dbwarden"):
        if getattr(module, "extract_table_from_model", None) is _original:
            module.extract_table_from_model = _instrumented

from dbwarden.cli.main import main

sys.argv = ["dbwarden"] + sys.argv[1:]
sys.exit(main())
'''


@dataclass(frozen=True)
class SwallowedError:
    location: str
    exception: str
    traceback: str

    def __str__(self) -> str:
        return f"{self.exception}  (swallowed at {self.location})"


class GenerationProbe:
    """Run a dbwarden command with model-discovery error swallowing disabled."""

    def __init__(self, work_dir: Path, *, env: dict[str, str] | None = None) -> None:
        self.work_dir = Path(work_dir)
        self.env = {**os.environ, **(env or {})}

    def run(self, *args: str, timeout: float = 180.0) -> tuple[int, str, str]:
        # The probe script must live OUTSIDE the project directory: Python puts
        # the script's own directory on sys.path, and a dbwarden project has a
        # ``dbwarden.py`` config file that would shadow the installed package.
        with tempfile.TemporaryDirectory(prefix="dbwarden-probe-") as scratch:
            probe = Path(scratch) / "run_probe.py"
            probe.write_text(_PROBE_SOURCE, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(probe), *args],
                cwd=self.work_dir,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        return completed.returncode, completed.stdout, completed.stderr

    def swallowed_errors(self, *args: str) -> tuple[SwallowedError, ...]:
        """Return the exceptions discarded while discovering models."""
        _, _, stderr = self.run(*args)
        return parse_swallowed(stderr)


def parse_swallowed(stderr: str) -> tuple[SwallowedError, ...]:
    blocks = stderr.split(MARKER)[1:]
    errors: list[SwallowedError] = []
    for block in blocks:
        header, _, body = block.partition("\n")
        lines = [line for line in body.splitlines() if line.strip()]
        # The final non-empty line of a traceback is the exception itself.
        exception = ""
        for line in reversed(lines):
            if re.match(r"^\w[\w.]*(Error|Exception|Warning)\b", line.strip()):
                exception = line.strip()
                break
        errors.append(
            SwallowedError(location=header.strip(), exception=exception or lines[-1] if lines else "", traceback=body)
        )
    return tuple(errors)
