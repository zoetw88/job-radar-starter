from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Profile:
    skills: tuple[str, ...]
    resume_path: str


@dataclass(frozen=True)
class Preferences:
    countries: tuple[str, ...]
    roles: tuple[str, ...]
    tracks: tuple[str, ...]
    visa_required: bool


@dataclass(frozen=True)
class Companies:
    preferred: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True)
class Matching:
    minimum_score: int
    must_have: tuple[str, ...]
    exclude_keywords: tuple[str, ...]


@dataclass(frozen=True)
class UserConfig:
    profile: Profile
    preferences: Preferences
    companies: Companies
    matching: Matching


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def load_user_config(path: Path) -> UserConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("configuration root must be a mapping")

    profile = _section(raw, "profile")
    preferences = _section(raw, "preferences")
    companies = _section(raw, "companies")
    matching = _section(raw, "matching")
    minimum_score = int(matching.get("minimum_score", 0))
    if not 0 <= minimum_score <= 100:
        raise ValueError("matching.minimum_score must be between 0 and 100")
    return UserConfig(
        profile=Profile(
            skills=tuple(profile.get("skills", ())),
            resume_path=str(profile.get("resume_path", "")),
        ),
        preferences=Preferences(
            countries=tuple(preferences.get("countries", ())),
            roles=tuple(preferences.get("roles", ())),
            tracks=tuple(preferences.get("tracks", ())),
            visa_required=bool(preferences.get("visa_required", False)),
        ),
        companies=Companies(
            preferred=tuple(companies.get("preferred", ())),
            excluded=tuple(companies.get("excluded", ())),
        ),
        matching=Matching(
            minimum_score=minimum_score,
            must_have=tuple(matching.get("must_have", ())),
            exclude_keywords=tuple(matching.get("exclude_keywords", ())),
        ),
    )
