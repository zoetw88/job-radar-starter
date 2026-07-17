from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from job_radar.application import score_jobs_with_provider
from job_radar.config import UserConfig
from job_radar.domain.jobs import Job
from job_radar.legacy_command_adapter import LegacyCommandProvider


def score_jobs_with_command(
    jobs: Sequence[Job],
    config: UserConfig,
    command: Sequence[str],
    *,
    runner: Callable[..., Any] = subprocess.run,
    timeout: int = 120,
) -> list[Job]:
    return score_jobs_with_provider(
        jobs,
        config,
        LegacyCommandProvider(command, runner=runner, timeout=timeout),
    )


@dataclass(frozen=True)
class LegacyCommandScorer:
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
        object.__setattr__(self, "command", tuple(str(part) for part in command))
        object.__setattr__(self, "runner", runner)
        object.__setattr__(self, "timeout", timeout)

    def __call__(self, jobs: Sequence[Job], config: UserConfig) -> list[Job]:
        return score_jobs_with_command(
            jobs,
            config,
            self.command,
            runner=self.runner,
            timeout=self.timeout,
        )
