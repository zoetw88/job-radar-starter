from __future__ import annotations

from dataclasses import dataclass


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
