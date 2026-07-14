from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from job_radar.adapters import Job, fetch_ashby, fetch_greenhouse, fetch_lever
from job_radar.catalog import Catalog
from job_radar.config import UserConfig
from job_radar.dashboard import render_dashboard


_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
}

_AI_FIELDS = {
    "source",
    "external_id",
    "score",
    "summary",
    "risk",
    "tracks",
    "skills",
    "visa_supported",
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


def _terms(job: Job) -> str:
    return " ".join(
        (
            job.company,
            job.title,
            job.location,
            job.country,
            job.category,
            *job.tracks,
            *job.skills,
        )
    ).casefold()


def _contains(text: str, term: str) -> bool:
    return bool(term.strip()) and term.casefold() in text


def score_jobs(jobs: Sequence[Job], config: UserConfig) -> list[Job]:
    """Score jobs with transparent, generic local rules.

    The rules only use structured configuration. The resume path is not opened.
    """

    preferred = {company.casefold() for company in config.companies.preferred}
    excluded = {company.casefold() for company in config.companies.excluded}
    scored: list[Job] = []

    for job in jobs:
        text = _terms(job)
        company = job.company.casefold()
        blocked_keyword = next(
            (term for term in config.matching.exclude_keywords if _contains(text, term)),
            None,
        )
        if company in excluded:
            scored.append(
                replace(
                    job,
                    score=0,
                    summary="Excluded by local preferences.",
                    risk="excluded company",
                )
            )
            continue
        if blocked_keyword:
            scored.append(
                replace(
                    job,
                    score=0,
                    summary="Excluded by local preferences.",
                    risk=f"excluded keyword: {blocked_keyword}",
                )
            )
            continue

        score = 30
        matches: list[str] = []
        risks: list[str] = []

        if job.country and job.country.casefold() in {
            country.casefold() for country in config.preferences.countries
        }:
            score += 10
            matches.append("country")

        role_matches = [role for role in config.preferences.roles if _contains(text, role)]
        if role_matches:
            score += 15
            matches.append("role")

        track_matches = [track for track in config.preferences.tracks if _contains(text, track)]
        if track_matches:
            score += 10
            matches.append("track")

        skill_matches = [skill for skill in config.profile.skills if _contains(text, skill)]
        if skill_matches:
            score += min(24, 8 * len(skill_matches))
            matches.append("skills")

        if company in preferred:
            score += 10
            matches.append("preferred company")

        missing_must_have = [
            term for term in config.matching.must_have if not _contains(text, term)
        ]
        if missing_must_have:
            score -= 20
            risks.append("missing must-have: " + ", ".join(missing_must_have))
        elif config.matching.must_have:
            score += 5
            matches.append("must-have")

        if config.preferences.visa_required:
            if job.visa_supported is True:
                score += 5
                matches.append("visa")
            elif job.visa_supported is False:
                score -= 25
                risks.append("visa support not indicated")
            else:
                score -= 8
                risks.append("verify visa support")

        normalized_score = max(0, min(100, score))
        summary = (
            "Matched local preferences: " + ", ".join(matches)
            if matches
            else "No strong local preferences matched."
        )
        scored.append(
            replace(
                job,
                score=normalized_score,
                summary=summary,
                risk="; ".join(risks),
                tracks=job.tracks or tuple(track_matches),
                skills=job.skills or tuple(skill_matches),
            )
        )

    return scored


def _ai_request(jobs: Sequence[Job], config: UserConfig) -> dict[str, Any]:
    return {
        "contract_version": 1,
        "profile": {"skills": list(config.profile.skills)},
        "preferences": {
            "countries": list(config.preferences.countries),
            "roles": list(config.preferences.roles),
            "tracks": list(config.preferences.tracks),
            "visa_required": config.preferences.visa_required,
        },
        "companies": {
            "preferred": list(config.companies.preferred),
            "excluded": list(config.companies.excluded),
        },
        "matching": {
            "minimum_score": config.matching.minimum_score,
            "must_have": list(config.matching.must_have),
            "exclude_keywords": list(config.matching.exclude_keywords),
        },
        "jobs": [
            {
                "source": job.source,
                "external_id": job.external_id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "url": job.url,
                "published_at": job.published_at,
                "country": job.country,
                "category": job.category,
                "salary": job.salary,
                "tracks": list(job.tracks),
                "skills": list(job.skills),
                "first_seen": job.first_seen,
                "visa_supported": job.visa_supported,
            }
            for job in jobs
        ],
    }


def _string_list(item: dict[str, Any], field: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if field not in item:
        return fallback
    value = item[field]
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise ValueError(f"AI response {field} must be a list of strings")
    return tuple(value)


def score_jobs_with_command(
    jobs: Sequence[Job],
    config: UserConfig,
    command: Sequence[str],
    *,
    runner: Callable[..., Any] = subprocess.run,
    timeout: int = 120,
) -> list[Job]:
    """Delegate scoring over stdin/stdout JSON without invoking a shell."""

    if not command:
        raise ValueError("AI command must not be empty")
    baseline = score_jobs(jobs, config)
    result = runner(
        list(command),
        input=json.dumps(_ai_request(jobs, config), ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AI command failed with exit code {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("AI command output must be valid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("scores"), list):
        raise ValueError("AI response must contain a scores list")

    by_key = {(job.source, job.external_id): job for job in baseline}
    seen: set[tuple[str, str]] = set()
    for item in payload["scores"]:
        if not isinstance(item, dict):
            raise ValueError("AI score entries must be objects")
        unexpected = set(item) - _AI_FIELDS
        if unexpected:
            raise ValueError(f"AI response contains unsupported fields: {sorted(unexpected)}")
        source = item.get("source")
        external_id = item.get("external_id")
        if not isinstance(source, str) or not isinstance(external_id, str):
            raise ValueError("AI response source and external_id must be strings")
        key = (source, external_id)
        if key not in by_key:
            raise ValueError(f"AI response references unknown job: {source}/{external_id}")
        if key in seen:
            raise ValueError(f"AI response contains duplicate job: {source}/{external_id}")
        seen.add(key)

        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("AI response score must be an integer between 0 and 100")
        current = by_key[key]
        summary = item.get("summary", current.summary)
        risk = item.get("risk", current.risk)
        if not isinstance(summary, str) or not isinstance(risk, str):
            raise ValueError("AI response summary and risk must be strings")
        visa_supported = item.get("visa_supported", current.visa_supported)
        if visa_supported is not None and not isinstance(visa_supported, bool):
            raise ValueError("AI response visa_supported must be boolean or null")
        tracks = _string_list(item, "tracks", current.tracks)
        skills = _string_list(item, "skills", current.skills)
        if current.score == 0 and current.summary == "Excluded by local preferences.":
            continue
        by_key[key] = replace(
            current,
            score=score,
            summary=summary,
            risk=risk,
            tracks=tracks,
            skills=skills,
            visa_supported=visa_supported,
        )

    return [by_key[(job.source, job.external_id)] for job in baseline]


def write_jobs_json(jobs: Sequence[Job], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps([asdict(job) for job in jobs], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def run_pipeline(
    catalog: Catalog,
    config: UserConfig,
    *,
    get_json: Callable[[str], Any],
    jobs_output: Path,
    dashboard_output: Path,
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
    published.sort(key=lambda job: (-(job.score or 0), job.company.casefold(), job.title.casefold()))
    write_jobs_json(published, jobs_output)
    render_dashboard(published, dashboard_output)
    return {"scanned": len(unique), "published": len(published)}
