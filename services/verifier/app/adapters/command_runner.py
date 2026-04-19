from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import os
import json
import shutil
import subprocess
from typing import Any


@dataclass(slots=True)
class CommandOutput:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandExecutionError(RuntimeError):
    def __init__(self, message: str, output: CommandOutput) -> None:
        super().__init__(message)
        self.output = output


class SubprocessCommandRunner:
    def __call__(
        self,
        args: Sequence[str],
        *,
        input_text: str | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> CommandOutput:
        binary = args[0]
        if shutil.which(binary) is None:
            raise FileNotFoundError(f"command not found: {binary}")

        completed = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            cwd=cwd,
            input=input_text,
            text=True,
            env={**os.environ, **(env or {})},
        )
        return CommandOutput(
            args=tuple(args),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def require_success(output: CommandOutput, *, error_prefix: str) -> CommandOutput:
    if output.returncode == 0:
        return output

    details = output.stderr.strip() or output.stdout.strip() or "no error output"
    raise CommandExecutionError(f"{error_prefix}: {details}", output)


def parse_json_output(output: CommandOutput) -> Any:
    stdout = output.stdout.strip()
    if not stdout:
        raise ValueError("command produced no JSON output")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"command did not return valid JSON: {exc}") from exc
