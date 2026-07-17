from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture()
def lifecycle() -> ModuleType:
    try:
        return importlib.import_module("job_radar.lifecycle_merge")
    except ModuleNotFoundError as error:
        if error.name != "job_radar.lifecycle_merge":
            raise
        pytest.fail(
            "production API missing: implement job_radar.lifecycle_merge",
            pytrace=False,
        )


def _scan_job(
    *,
    source: str = "greenhouse",
    external_id: str = "42",
    company: str = "Northstar Robotics",
    title: str = "Backend Engineer",
    location: str = "Toronto",
    url: str = "https://example.test/jobs/42",
    published_at: str = "2026-07-01T00:00:00Z",
    country: str = "CA",
    category: str = "backend",
    salary: str = "",
) -> dict[str, Any]:
    return {
        "source": source,
        "external_id": external_id,
        "company": company,
        "title": title,
        "location": location,
        "url": url,
        "published_at": published_at,
        "score": None,
        "country": country,
        "category": category,
        "summary": "",
        "risk": "",
        "salary": salary,
        "tracks": [],
        "skills": [],
        "first_seen": "",
        "visa_supported": None,
    }


def _scan(*jobs: dict[str, Any], incomplete: bool = False) -> dict[str, Any]:
    return {
        "contract_version": 1,
        "mode": "best-effort" if incomplete else "atomic",
        "incomplete": incomplete,
        "jobs": list(jobs),
        "failures": (
            [
                {
                    "source": "greenhouse",
                    "company": "Unavailable Board",
                    "category": "timeout",
                    "message": "source exceeded 1 seconds",
                }
            ]
            if incomplete
            else []
        ),
    }


def _empty_state() -> dict[str, Any]:
    return {
        "contract_version": 1,
        "jobs": [],
        "statuses": {},
    }


def _merge(
    lifecycle: ModuleType,
    prior: dict[str, Any],
    scan: dict[str, Any],
    observed_on: str,
    *,
    aliases: dict[str, Any] | None = None,
    statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    return lifecycle.merge_scan_state(
        prior_state=prior,
        scan_result=scan,
        observed_on=observed_on,
        aliases=aliases
        or {
            "contract_version": 1,
            "company_aliases": {},
            "title_aliases": {},
        },
        statuses=statuses or {},
        stale_after_days=14,
        expired_after_days=30,
    )


def test_first_scan_adds_stable_key_and_deterministic_lifecycle_dates(
    lifecycle: ModuleType,
):
    result = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )

    assert result["contract_version"] == 1
    assert set(result) == {"contract_version", "jobs", "statuses"}
    assert len(result["jobs"]) == 1
    job = result["jobs"][0]
    assert job["stable_id"].startswith("job_")
    assert job["first_seen"] == "2026-07-01"
    assert job["last_seen"] == "2026-07-01"
    assert job["freshness"] == "active"
    assert job["legacy_status_keys"] == [
        "greenhouse:42",
        "https://example.test/jobs/42",
    ]


def test_reordered_scan_and_duplicate_provider_records_produce_identical_state(
    lifecycle: ModuleType,
):
    alpha = _scan_job(external_id="1", company="Alpha Systems", url="https://example.test/1")
    duplicate = _scan_job(
        external_id="1",
        company="Zulu Display Name",
        title="Duplicate display",
        url="https://example.test/zulu",
    )
    beta = _scan_job(external_id="2", company="Beta Systems", url="https://example.test/2")

    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(duplicate, beta, alpha),
        "2026-07-01",
    )
    second = _merge(
        lifecycle,
        _empty_state(),
        _scan(alpha, duplicate, beta),
        "2026-07-01",
    )

    assert first == second
    assert [job["external_id"] for job in first["jobs"]] == ["1", "2"]
    assert first["jobs"][0]["company"] == "Alpha Systems"


def test_user_owned_company_and_title_aliases_stabilize_fallback_identity(
    lifecycle: ModuleType,
):
    aliases = {
        "contract_version": 1,
        "company_aliases": {"Example Incorporated": "Example"},
        "title_aliases": {"Sr Platform Engineer": "Senior Platform Engineer"},
    }
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(
            _scan_job(
                source="authorized-feed",
                external_id="",
                company="Example, Inc.",
                title="Senior Platform Engineer",
            )
        ),
        "2026-07-01",
        aliases=aliases,
    )
    second = _merge(
        lifecycle,
        first,
        _scan(
            _scan_job(
                source="AUTHORIZED FEED",
                external_id="",
                company="Example Incorporated",
                title="Sr. Platform Engineer",
            )
        ),
        "2026-07-02",
        aliases=aliases,
    )

    assert len(second["jobs"]) == 1
    assert second["jobs"][0]["stable_id"] == first["jobs"][0]["stable_id"]
    assert second["jobs"][0]["first_seen"] == "2026-07-01"
    assert second["jobs"][0]["last_seen"] == "2026-07-02"


def test_updated_provider_fields_replace_old_values_but_curated_fields_survive(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )
    first["jobs"][0].update(
        {
            "score": 91,
            "summary": "Strong platform overlap.",
            "risk": "Verify work authorization.",
            "tracks": ["backend"],
            "skills": ["Go", "Kubernetes"],
            "visa_supported": True,
        }
    )

    second = _merge(
        lifecycle,
        first,
        _scan(
            _scan_job(
                company="Northstar Robotics Inc.",
                title="Senior Backend Engineer",
                location="Remote - Canada",
                url="https://example.test/jobs/42-updated",
                published_at="2026-07-02T00:00:00Z",
                salary="CAD 150k",
            )
        ),
        "2026-07-02",
    )
    job = second["jobs"][0]

    assert job["title"] == "Senior Backend Engineer"
    assert job["location"] == "Remote - Canada"
    assert job["url"] == "https://example.test/jobs/42-updated"
    assert job["salary"] == "CAD 150k"
    assert job["score"] == 91
    assert job["summary"] == "Strong platform overlap."
    assert job["risk"] == "Verify work authorization."
    assert job["tracks"] == ["backend"]
    assert job["skills"] == ["Go", "Kubernetes"]
    assert job["visa_supported"] is True


@pytest.mark.parametrize(
    ("observed_on", "expected"),
    [
        ("2026-07-14", "active"),
        ("2026-07-15", "stale"),
        ("2026-07-30", "stale"),
        ("2026-07-31", "expired"),
    ],
)
def test_disappeared_jobs_are_retained_with_deterministic_freshness(
    lifecycle: ModuleType,
    observed_on: str,
    expected: str,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )

    missing = _merge(lifecycle, first, _scan(), observed_on)

    assert len(missing["jobs"]) == 1
    assert missing["jobs"][0]["first_seen"] == "2026-07-01"
    assert missing["jobs"][0]["last_seen"] == "2026-07-01"
    assert missing["jobs"][0]["freshness"] == expected


def test_reappearing_job_keeps_first_seen_and_updates_last_seen_to_return_date(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )
    missing = _merge(lifecycle, first, _scan(), "2026-07-20")
    returned = _merge(
        lifecycle,
        missing,
        _scan(_scan_job(title="Backend Engineer - Reopened")),
        "2026-07-22",
    )

    job = returned["jobs"][0]
    assert job["first_seen"] == "2026-07-01"
    assert job["last_seen"] == "2026-07-22"
    assert job["freshness"] == "active"


def test_partial_scan_does_not_age_jobs_from_a_failed_source(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )

    partial = _merge(
        lifecycle,
        first,
        _scan(incomplete=True),
        "2026-08-15",
    )

    assert partial["jobs"][0]["freshness"] == "active"
    assert partial["jobs"][0]["last_seen"] == "2026-07-01"


def test_legacy_statuses_migrate_to_stable_key_and_stable_key_wins(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )
    stable_id = first["jobs"][0]["stable_id"]

    migrated = _merge(
        lifecycle,
        first,
        _scan(_scan_job()),
        "2026-07-02",
        statuses={
            "greenhouse:42": "skip",
            "https://example.test/jobs/42": "interested",
            stable_id: "applied",
        },
    )

    assert migrated["statuses"] == {stable_id: "applied"}


def test_status_from_old_url_survives_provider_url_change(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )
    stable_id = first["jobs"][0]["stable_id"]

    changed = _merge(
        lifecycle,
        first,
        _scan(_scan_job(url="https://example.test/jobs/new-42")),
        "2026-07-02",
        statuses={"https://example.test/jobs/42": "interested"},
    )

    assert changed["statuses"] == {stable_id: "interested"}
    assert changed["jobs"][0]["legacy_status_keys"] == [
        "greenhouse:42",
        "https://example.test/jobs/42",
        "https://example.test/jobs/new-42",
    ]


def test_repeating_the_same_scan_is_idempotent(
    lifecycle: ModuleType,
):
    scan = _scan(_scan_job(), _scan_job(external_id="43", url="https://example.test/43"))
    once = _merge(lifecycle, _empty_state(), scan, "2026-07-01")
    twice = _merge(lifecycle, once, scan, "2026-07-01")

    assert twice == once


def test_invalid_version_or_future_observation_is_rejected_without_mutating_inputs(
    lifecycle: ModuleType,
):
    prior = _empty_state()
    scan = _scan(_scan_job())
    original = json.loads(json.dumps(scan))

    with pytest.raises(ValueError, match="version"):
        lifecycle.merge_scan_state(
            prior_state=prior,
            scan_result={**scan, "contract_version": 2},
            observed_on="2026-07-01",
            aliases={
                "contract_version": 1,
                "company_aliases": {},
                "title_aliases": {},
            },
            statuses={},
        )
    with pytest.raises(ValueError, match="future|published"):
        _merge(lifecycle, prior, scan, "2026-06-30")

    assert scan == original
    assert prior == _empty_state()


def test_lifecycle_merge_is_application_only_and_does_not_import_adapters(
    lifecycle: ModuleType,
):
    source = Path(lifecycle.__file__).read_text(encoding="utf-8")

    assert "job_radar.data" not in source
    assert "job_radar.dashboard" not in source
    assert "job_radar.adapters" not in source
    assert "pathlib" not in source


def test_untracked_expired_jobs_are_pruned_after_deterministic_retention(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )

    retained = lifecycle.merge_scan_state(
        prior_state=first,
        scan_result=_scan(),
        observed_on="2026-10-29",
        aliases={
            "contract_version": 1,
            "company_aliases": {},
            "title_aliases": {},
        },
        statuses={},
        expired_after_days=30,
        untracked_expired_retention_days=90,
    )
    pruned = lifecycle.merge_scan_state(
        prior_state=retained,
        scan_result=_scan(),
        observed_on="2026-10-30",
        aliases={
            "contract_version": 1,
            "company_aliases": {},
            "title_aliases": {},
        },
        statuses={},
        expired_after_days=30,
        untracked_expired_retention_days=90,
    )

    assert len(retained["jobs"]) == 1
    assert retained["jobs"][0]["freshness"] == "expired"
    assert pruned["jobs"] == []


def test_tracked_expired_jobs_survive_untracked_retention_pruning(
    lifecycle: ModuleType,
):
    first = _merge(
        lifecycle,
        _empty_state(),
        _scan(_scan_job()),
        "2026-07-01",
    )
    stable_id = first["jobs"][0]["stable_id"]

    result = lifecycle.merge_scan_state(
        prior_state=first,
        scan_result=_scan(),
        observed_on="2027-01-01",
        aliases={
            "contract_version": 1,
            "company_aliases": {},
            "title_aliases": {},
        },
        statuses={stable_id: "interested"},
        expired_after_days=30,
        untracked_expired_retention_days=90,
    )

    assert [job["stable_id"] for job in result["jobs"]] == [stable_id]
    assert result["jobs"][0]["freshness"] == "expired"
    assert result["statuses"] == {stable_id: "interested"}


def test_alias_example_is_invented_blank_configuration():
    path = Path(__file__).resolve().parents[1] / "examples" / "aliases.example.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8").casefold()

    assert payload == {
        "contract_version": 1,
        "company_aliases": {},
        "title_aliases": {},
    }
    assert ("private-" + "owner") not in text
    assert "private" not in text
