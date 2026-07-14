from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Country:
    name: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class Source:
    kind: str
    terms_url: str
    enabled: bool


@dataclass(frozen=True)
class Company:
    countries: tuple[str, ...]
    source: str
    board: str


@dataclass(frozen=True)
class Catalog:
    countries: dict[str, Country]
    sources: dict[str, Source]
    companies: dict[str, Company]


def _mapping(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def load_catalog(path: Path) -> Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("catalog root must be a mapping")

    countries = {
        code: Country(name=value["name"], sources=tuple(value.get("sources", ())))
        for code, value in _mapping(raw, "countries").items()
    }
    sources = {
        name: Source(
            kind=value["kind"],
            terms_url=value["terms_url"],
            enabled=bool(value.get("enabled", False)),
        )
        for name, value in _mapping(raw, "sources").items()
    }
    companies = {
        name: Company(
            countries=tuple(value.get("countries", ())),
            source=value["source"],
            board=value["board"],
        )
        for name, value in _mapping(raw, "companies").items()
    }
    unknown_sources = {
        company.source for company in companies.values() if company.source not in sources
    }
    if unknown_sources:
        raise ValueError(f"unknown company sources: {sorted(unknown_sources)}")
    return Catalog(countries=countries, sources=sources, companies=companies)

