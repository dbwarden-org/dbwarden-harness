from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    def require_success(self) -> CommandResult:
        if self.returncode != 0:
            raise RuntimeError(
                f"Command failed ({self.returncode}): {' '.join(self.args)}\n"
                f"stdout:\n{self.stdout}\nstderr:\n{self.stderr}"
            )
        return self

    def require_clean(self) -> CommandResult:
        self.require_success()
        if self.stderr.strip():
            raise RuntimeError(
                f"Command emitted stderr: {' '.join(self.args)}\n{self.stderr}"
            )
        return self

    def require_failure(self, *fragments: str) -> CommandResult:
        if self.returncode == 0:
            raise AssertionError(f"Expected command to fail: {' '.join(self.args)}")
        output = f"{self.stdout}\n{self.stderr}".lower()
        missing = [fragment for fragment in fragments if fragment.lower() not in output]
        if missing:
            raise AssertionError(f"Missing failure details {missing} in output:\n{output}")
        return self

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}"

    @property
    def plain_output(self) -> str:
        return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", self.output)


class DbwardenCli:
    """Invoke the installed dbwarden CLI without importing implementation modules."""

    def __init__(
        self,
        work_dir: Path,
        *,
        executable: str = "dbwarden",
        env: dict[str, str] | None = None,
    ) -> None:
        self.work_dir = work_dir
        self.executable = executable
        self.env = {**os.environ, **(env or {})}

    def run(
        self,
        *args: str,
        check: bool = True,
        timeout: float = 120.0,
        clean: bool = False,
    ) -> CommandResult:
        command = (self.executable, *args)
        completed = subprocess.run(
            command,
            cwd=self.work_dir,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        result = CommandResult(command, completed.returncode, completed.stdout, completed.stderr)
        if clean:
            return result.require_clean()
        return result.require_success() if check else result

    def run_raw(
        self,
        command: Sequence[str],
        *,
        check: bool = True,
        timeout: float = 120.0,
    ) -> CommandResult:
        completed = subprocess.run(
            tuple(command),
            cwd=self.work_dir,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        result = CommandResult(tuple(command), completed.returncode, completed.stdout, completed.stderr)
        return result.require_success() if check else result
