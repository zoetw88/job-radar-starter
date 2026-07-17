from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from job_radar.adapters import fetch_ashby, fetch_greenhouse, fetch_lever
from job_radar.catalog import Catalog
from job_radar.domain.jobs import Job


_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
}


def scan_catalog(catalog: Catalog, get_json: Callable[[str], Any]) -> list[Job]:
    jobs: list[Job] = []
    for company_name, company in catalog.companies.items():
        source = catalog.sources[company.source]
        if not source.enabled:
            continue
        fetch = _FETCHERS[company.source]
        try:
            fetched = fetch(company.board, company_name, get_json)
        except Exception as error:
            raise RuntimeError(
                f"{company_name} ({company.source}) scan failed: {error}"
            ) from error
        country = company.countries[0] if len(company.countries) == 1 else ""
        jobs.extend(replace(job, country=country) for job in fetched)
    return jobs
