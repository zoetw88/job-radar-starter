from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from job_radar.bounded_process import run_bounded_process


@dataclass(frozen=True)
class LegacyCommandProvider:
    command: tuple[str, ...]
    runner: Callable[..., Any] = subprocess.run
    timeout: int = 120

    def __init__(
        self,
        command: Sequence[str],
        *,
        runner: Callable[..., Any] = subprocess.run,
        timeout: int = 120,
    ):
        normalized = tuple(str(part) for part in command)
        if not normalized:
            raise ValueError("AI command must not be empty")
        object.__setattr__(self, "command", normalized)
        object.__setattr__(self, "runner", runner)
        object.__setattr__(self, "timeout", timeout)

    def __call__(self, request: dict[str, Any]) -> Mapping[str, Any]:
        input_text = json.dumps(request, ensure_ascii=False)
        if self.runner is subprocess.run:
            result = run_bounded_process(
                self.command,
                input_text=input_text,
                timeout_seconds=self.timeout,
            )
        else:
            result = self.runner(
                list(self.command),
                input=input_text,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout,
            )
        if result.returncode != 0:
            raise RuntimeError(
                f"AI command failed with exit code {result.returncode}"
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ValueError("AI command output must be valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("AI command output must be a JSON object")
        return payload
