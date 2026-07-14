from dataclasses import dataclass
from typing import Any, Callable


JsonGetter = Callable[[str], Any]


@dataclass(frozen=True)
class Job:
    source: str
    external_id: str
    company: str
    title: str
    location: str
    url: str
    published_at: str
    score: int | None = None
    country: str = ""
    category: str = ""
    summary: str = ""
    risk: str = ""
    salary: str = ""
    tracks: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    first_seen: str = ""
    visa_supported: bool | None = None


def parse_greenhouse(payload: dict[str, Any], company: str) -> list[Job]:
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
        for item in payload.get("jobs", ())
    ]


def parse_lever(payload: list[dict[str, Any]], company: str) -> list[Job]:
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


def parse_ashby(payload: dict[str, Any], company: str) -> list[Job]:
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
        for item in payload.get("jobs", ())
        if item.get("isListed", True)
    ]


def fetch_greenhouse(board_token: str, company: str, get_json: JsonGetter) -> list[Job]:
    payload = get_json(f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs")
    return parse_greenhouse(payload, company)


def fetch_lever(site: str, company: str, get_json: JsonGetter) -> list[Job]:
    payload = get_json(f"https://api.lever.co/v0/postings/{site}?mode=json")
    return parse_lever(payload, company)


def fetch_ashby(board_name: str, company: str, get_json: JsonGetter) -> list[Job]:
    payload = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board_name}")
    return parse_ashby(payload, company)
