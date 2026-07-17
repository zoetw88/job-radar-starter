from typing import Any, Callable

from job_radar.domain.jobs import Job


JsonGetter = Callable[[str], Any]


class SourcePayloadTooLarge(ValueError):
    pass


def parse_greenhouse(
    payload: dict[str, Any],
    company: str,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    items = payload.get("jobs", ())
    if max_jobs is not None and isinstance(items, list) and len(items) > max_jobs:
        raise SourcePayloadTooLarge
    return [
        Job(
            source="greenhouse",
            external_id=str(item["id"]),
            company=company,
            title=str(item["title"]),
            location=str((item.get("location") or {}).get("name", "")),
            url=str(item["absolute_url"]),
            published_at=str(item.get("updated_at", "")),
        )
        for item in items
    ]


def parse_lever(
    payload: list[dict[str, Any]],
    company: str,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    if max_jobs is not None and len(payload) > max_jobs:
        raise SourcePayloadTooLarge
    return [
        Job(
            source="lever",
            external_id=str(item["id"]),
            company=company,
            title=str(item["text"]),
            location=str((item.get("categories") or {}).get("location", "")),
            url=str(item["hostedUrl"]),
            published_at=str(item.get("createdAt", "")),
        )
        for item in payload
    ]


def parse_ashby(
    payload: dict[str, Any],
    company: str,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    items = payload.get("jobs", ())
    if max_jobs is not None and isinstance(items, list) and len(items) > max_jobs:
        raise SourcePayloadTooLarge
    return [
        Job(
            source="ashby",
            external_id=str(item["id"]),
            company=company,
            title=str(item["title"]),
            location=str(item.get("location", "")),
            url=str(item.get("jobUrl") or item.get("applyUrl") or ""),
            published_at=str(item.get("publishedAt", "")),
        )
        for item in items
        if item.get("isListed", True)
    ]


def fetch_greenhouse(
    board_token: str,
    company: str,
    get_json: JsonGetter,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    payload = get_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs")
    return parse_greenhouse(payload, company, max_jobs=max_jobs)


def fetch_lever(
    site: str,
    company: str,
    get_json: JsonGetter,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    payload = get_json(f"https://api.lever.co/v0/postings/{site}?mode=json")
    return parse_lever(payload, company, max_jobs=max_jobs)


def fetch_ashby(
    board_name: str,
    company: str,
    get_json: JsonGetter,
    *,
    max_jobs: int | None = None,
) -> list[Job]:
    payload = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board_name}")
    return parse_ashby(payload, company, max_jobs=max_jobs)
