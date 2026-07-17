from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from job_radar.application import score_jobs
from job_radar.catalog import Catalog
from job_radar.config import UserConfig
from job_radar.domain.jobs import Job
from job_radar.job_output import write_jobs_json
from job_radar.legacy_scoring import score_jobs_with_command
from job_radar.official_sources import scan_catalog


def run_pipeline(
    catalog: Catalog,
    config: UserConfig,
    *,
    get_json: Callable[[str], Any],
    jobs_output: Path,
    dashboard_output: Path,
    dashboard_renderer: Callable[[Sequence[Job], Path], None],
    ai_command: Sequence[str] | None = None,
    command_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, int]:
    scanned = scan_catalog(catalog, get_json)
    unique = list({(job.source, job.external_id): job for job in scanned}.values())
    if ai_command:
        scored = score_jobs_with_command(
            unique,
            config,
            ai_command,
            runner=command_runner,
        )
    else:
        scored = score_jobs(unique, config)
    published = [
        job for job in scored if (job.score or 0) >= config.matching.minimum_score
    ]
    published.sort(
        key=lambda job: (
            -(job.score or 0),
            job.company.casefold(),
            job.title.casefold(),
        )
    )
    write_jobs_json(published, jobs_output)
    dashboard_renderer(published, dashboard_output)
    return {"scanned": len(unique), "published": len(published)}
