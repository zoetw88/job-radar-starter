from __future__ import annotations

import importlib
from datetime import date, datetime, timezone
from types import ModuleType

import pytest


@pytest.fixture()
def tracking() -> ModuleType:
    """Load the production contract without turning a missing module into a collection error."""

    try:
        return importlib.import_module("job_radar.domain.tracking")
    except ModuleNotFoundError as error:
        if error.name != "job_radar.domain":
            raise
        pytest.fail(
            "production API missing: implement job_radar.domain.tracking",
            pytrace=False,
        )


def _application_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_version": 1,
        "application_id": "application_01",
        "job_id": "job_01",
        "company": "Northstar Robotics",
        "title": "Backend Engineer",
        "status": "applied",
        "created_at": "2026-07-10T09:00:00Z",
        "updated_at": "2026-07-10T09:00:00Z",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def test_stable_job_id_prefers_provider_identity_over_display_text(tracking: ModuleType):
    original = tracking.stable_job_id(
        source="greenhouse",
        external_id="  JOB-42 ",
        company="Example, Inc.",
        title="Senior Backend Engineer",
    )
    renamed = tracking.stable_job_id(
        source="GreenHouse",
        external_id="job-42",
        company="Example Incorporated",
        title="Sr. Backend Engineer (Platform)",
    )

    assert original == renamed
    assert original.startswith("job_")
    assert len(original) <= 68


def test_fallback_job_id_normalizes_punctuation_whitespace_and_user_aliases(
    tracking: ModuleType,
):
    aliases = {
        "Example Incorporated": "Example",
        "Sr Backend Engineer": "Senior Backend Engineer",
    }

    first = tracking.stable_job_id(
        source="authorized-feed",
        external_id="",
        company="Example, Inc.",
        title="Senior Backend Engineer",
        aliases=aliases,
    )
    second = tracking.stable_job_id(
        source="AUTHORIZED FEED",
        external_id=None,
        company=" Example Incorporated ",
        title="Sr. Backend Engineer!",
        aliases=aliases,
    )

    assert first == second


def test_alias_resolution_is_casefolded_transitive_and_cycle_safe(tracking: ModuleType):
    aliases = {
        "Example, Inc.": "Example Incorporated",
        "example incorporated": "Example",
    }

    assert tracking.canonicalize_alias(" EXAMPLE, INC. ", aliases) == "Example"

    with pytest.raises(ValueError, match="alias cycle"):
        tracking.canonicalize_alias("A", {"A": "B", "B": "A"})


def test_application_id_is_stable_across_mutable_application_fields(tracking: ModuleType):
    job_id = tracking.stable_job_id(
        source="lever",
        external_id="abc-123",
        company="Cedar Systems",
        title="Platform Engineer",
    )

    assert tracking.stable_application_id(job_id) == tracking.stable_application_id(
        job_id.strip().upper()
    )


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("interested", "applied"),
        ("applied", "interview"),
        ("interview", "offer"),
        ("offer", "accepted"),
        ("applied", "rejected"),
        ("interview", "withdrawn"),
        ("applied", "applied"),
    ],
)
def test_valid_application_state_transitions_are_accepted(
    tracking: ModuleType,
    current: str,
    target: str,
):
    assert tracking.transition_application(current, target) == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("accepted", "applied"),
        ("rejected", "interview"),
        ("interested", "offer"),
        ("unknown", "applied"),
        ("applied", "unknown"),
    ],
)
def test_invalid_application_state_transitions_are_rejected(
    tracking: ModuleType,
    current: str,
    target: str,
):
    with pytest.raises(ValueError, match="transition|status"):
        tracking.transition_application(current, target)


def test_event_id_is_retry_safe_and_dict_order_independent(tracking: ModuleType):
    first = tracking.stable_event_id(
        application_id="application_01",
        event_type="interview_scheduled",
        occurred_at="2026-07-17T09:30:00+08:00",
        details={"round": 1, "channel": "video"},
    )
    replay = tracking.stable_event_id(
        application_id=" APPLICATION_01 ",
        event_type="INTERVIEW_SCHEDULED",
        occurred_at="2026-07-17T01:30:00Z",
        details={"channel": "video", "round": 1},
    )
    changed = tracking.stable_event_id(
        application_id="application_01",
        event_type="interview_scheduled",
        occurred_at="2026-07-17T01:31:00Z",
        details={"channel": "video", "round": 1},
    )

    assert first == replay
    assert first != changed
    assert first.startswith("event_")


def test_lifecycle_observation_preserves_earliest_and_latest_seen_dates(
    tracking: ModuleType,
):
    lifecycle = tracking.JobLifecycle(
        job_id="job_01",
        first_seen=date(2026, 7, 10),
        last_seen=date(2026, 7, 12),
    )

    lifecycle = lifecycle.observe(date(2026, 7, 8))
    lifecycle = lifecycle.observe(date(2026, 7, 16))
    lifecycle = lifecycle.observe(date(2026, 7, 11))

    assert lifecycle.first_seen == date(2026, 7, 8)
    assert lifecycle.last_seen == date(2026, 7, 16)


@pytest.mark.parametrize(
    ("last_seen", "expected"),
    [
        ("2026-07-03", "active"),
        ("2026-07-02", "stale"),
        ("2026-06-18", "stale"),
        ("2026-06-17", "expired"),
    ],
)
def test_freshness_boundaries_are_deterministic(
    tracking: ModuleType,
    last_seen: str,
    expected: str,
):
    assert (
        tracking.freshness_state(
            last_seen=last_seen,
            as_of="2026-07-16",
            stale_after_days=14,
            expired_after_days=29,
        )
        == expected
    )


def test_freshness_rejects_inverted_thresholds_and_future_last_seen(
    tracking: ModuleType,
):
    with pytest.raises(ValueError, match="threshold"):
        tracking.freshness_state(
            last_seen="2026-07-01",
            as_of="2026-07-16",
            stale_after_days=30,
            expired_after_days=14,
        )
    with pytest.raises(ValueError, match="future"):
        tracking.freshness_state(
            last_seen="2026-07-17",
            as_of="2026-07-16",
        )


def test_legacy_status_migration_is_order_independent_and_stable_key_wins(
    tracking: ModuleType,
):
    jobs = [
        {
            "stable_id": "job_01",
            "legacy_status_keys": ["greenhouse:42", "https://example.test/jobs/42"],
        },
        {
            "stable_id": "job_02",
            "legacy_status_keys": ["lever:abc"],
        },
    ]
    statuses = {
        "https://example.test/jobs/42": "interested",
        "greenhouse:42": "skip",
        "job_01": "applied",
        "lever:abc": "dead",
    }

    expected = {"job_01": "applied", "job_02": "dead"}
    assert tracking.migrate_legacy_statuses(statuses, jobs) == expected
    assert tracking.migrate_legacy_statuses(
        dict(reversed(list(statuses.items()))),
        list(reversed(jobs)),
    ) == expected


def test_legacy_status_migration_rejects_unknown_status_values(tracking: ModuleType):
    with pytest.raises(ValueError, match="status"):
        tracking.migrate_legacy_statuses(
            {"greenhouse:42": "maybe"},
            [{"stable_id": "job_01", "legacy_status_keys": ["greenhouse:42"]}],
        )


def test_application_record_round_trip_is_versioned_and_rejects_unknown_fields(
    tracking: ModuleType,
):
    payload = _application_payload()
    record = tracking.ApplicationRecord.from_dict(payload)

    assert record.to_dict() == payload

    with pytest.raises(ValueError, match="unknown|unsupported"):
        tracking.ApplicationRecord.from_dict(
            _application_payload(private_owner_note="must not be accepted")
        )
    with pytest.raises(ValueError, match="version"):
        tracking.ApplicationRecord.from_dict(
            _application_payload(contract_version=2)
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("application_id", ""),
        ("application_id", "a" * 129),
        ("job_id", "j" * 129),
        ("company", "c" * 201),
        ("title", "t" * 301),
        ("notes", "n" * 10_001),
    ],
)
def test_application_record_enforces_string_bounds(
    tracking: ModuleType,
    field: str,
    value: str,
):
    with pytest.raises(ValueError, match=field):
        tracking.ApplicationRecord.from_dict(_application_payload(**{field: value}))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-16", date(2026, 7, 16)),
        ("2026-07-16T01:30:00Z", datetime(2026, 7, 16, 1, 30, tzinfo=timezone.utc)),
        (
            "2026-07-16T09:30:00+08:00",
            datetime(2026, 7, 16, 1, 30, tzinfo=timezone.utc),
        ),
    ],
)
def test_iso_date_parsing_is_strict_and_normalizes_datetimes(
    tracking: ModuleType,
    value: str,
    expected: date | datetime,
):
    assert tracking.parse_iso_date_or_datetime(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "16/07/2026",
        "2026-7-16",
        "2026-02-30",
        "2026-07-16 01:30:00",
        "2026-07-16T01:30:00",
        20260716,
    ],
)
def test_iso_date_parsing_rejects_malformed_or_naive_values(
    tracking: ModuleType,
    value: object,
):
    with pytest.raises((TypeError, ValueError), match="date|datetime|ISO"):
        tracking.parse_iso_date_or_datetime(value)
