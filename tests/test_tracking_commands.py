from __future__ import annotations

import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture()
def commands() -> ModuleType:
    try:
        return importlib.import_module("job_radar.tracking_commands")
    except ModuleNotFoundError as error:
        if error.name != "job_radar.tracking_commands":
            raise
        pytest.fail(
            "production API missing: implement job_radar.tracking_commands",
            pytrace=False,
        )


class FakeTrackingRepository:
    """Structural fake: commands may only use read/write, never adapter internals."""

    def __init__(self, state: dict[str, dict[str, Any]] | None = None):
        self.state = deepcopy(state or {})
        self.writes: list[tuple[str, dict[str, Any]]] = []

    def read(self, kind: str) -> dict[str, Any]:
        return deepcopy(
            self.state.get(kind, {"contract_version": 1, "items": []})
        )

    def write(self, kind: str, document: dict[str, Any]) -> None:
        copied = deepcopy(document)
        self.state[kind] = copied
        self.writes.append((kind, copied))

    def commit_application_event(
        self,
        applications: dict[str, Any],
        events: dict[str, Any],
    ) -> None:
        copied_applications = deepcopy(applications)
        copied_events = deepcopy(events)
        self.state.update(
            {
                "applications": copied_applications,
                "events": copied_events,
            }
        )
        self.writes.extend(
            [
                ("applications", copied_applications),
                ("events", copied_events),
            ]
        )


def _application(
    *,
    job_id: str = "job_01",
    application_id: str | None = None,
    company: str = "Northstar Robotics",
    title: str = "Backend Engineer",
    status: str = "applied",
    applied_at: str = "2026-07-01T09:00:00Z",
    updated_at: str | None = None,
    resume_version: str = "backend-v1",
    channel: str = "company-site",
    country: str = "CA",
    rejection_stage: str | None = None,
    promised_response_date: str | None = None,
    offer_deadline: str | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": job_id,
        "company": company,
        "title": title,
        "status": status,
        "applied_at": applied_at,
        "updated_at": updated_at or applied_at,
        "resume_version": resume_version,
        "channel": channel,
        "country": country,
    }
    if application_id is not None:
        payload["application_id"] = application_id
    if rejection_stage is not None:
        payload["rejection_stage"] = rejection_stage
    if promised_response_date is not None:
        payload["promised_response_date"] = promised_response_date
    if offer_deadline is not None:
        payload["offer_deadline"] = offer_deadline
    return payload


def _state(*applications: dict[str, Any], events: list[dict[str, Any]] | None = None):
    return {
        "applications": {"contract_version": 1, "items": list(applications)},
        "events": {"contract_version": 1, "items": list(events or [])},
    }


def test_upsert_generates_stable_id_and_identical_replay_is_write_free(
    commands: ModuleType,
):
    repository = FakeTrackingRepository()
    payload = _application()

    first = commands.upsert_application(repository, payload)
    writes_after_first = len(repository.writes)
    replay = commands.upsert_application(repository, dict(reversed(list(payload.items()))))

    assert first == replay
    assert first["application_id"].startswith("application_")
    assert repository.read("applications")["items"] == [first]
    assert len(repository.writes) == writes_after_first


def test_upsert_preserves_created_identity_and_updates_mutable_fields(
    commands: ModuleType,
):
    repository = FakeTrackingRepository()
    original = commands.upsert_application(repository, _application())

    updated = commands.upsert_application(
        repository,
        _application(
            company="Northstar Robotics Incorporated",
            title="Senior Backend Engineer",
            updated_at="2026-07-02T09:00:00Z",
        ),
    )

    assert updated["application_id"] == original["application_id"]
    assert updated["job_id"] == original["job_id"]
    assert updated["applied_at"] == original["applied_at"]
    assert updated["title"] == "Senior Backend Engineer"
    assert repository.read("applications")["items"] == [updated]


def test_status_and_interview_events_update_state_and_are_retry_safe(
    commands: ModuleType,
):
    repository = FakeTrackingRepository()
    application = commands.upsert_application(repository, _application())

    interview = commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="interview_completed",
        occurred_at="2026-07-15T01:30:00Z",
        details={"round": 1, "channel": "video"},
        status="interview",
    )
    writes_after_first_event = len(repository.writes)
    replay = commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="INTERVIEW_COMPLETED",
        occurred_at="2026-07-15T09:30:00+08:00",
        details={"channel": "video", "round": 1},
        status="interview",
    )

    assert interview == replay
    assert interview["event_id"].startswith("event_")
    assert len(repository.read("events")["items"]) == 1
    assert repository.read("applications")["items"][0]["status"] == "interview"
    assert len(repository.writes) == writes_after_first_event


def test_status_event_uses_one_atomic_repository_operation(commands: ModuleType):
    class AtomicOnlyRepository(FakeTrackingRepository):
        def __init__(self):
            super().__init__()
            self.atomic_commits = 0

        def write(self, kind: str, document: dict[str, Any]) -> None:
            if kind == "applications":
                super().write(kind, document)
                return
            raise AssertionError("event command must not perform separate writes")

        def commit_application_event(
            self,
            applications: dict[str, Any],
            events: dict[str, Any],
        ) -> None:
            self.atomic_commits += 1
            super().commit_application_event(applications, events)

    repository = AtomicOnlyRepository()
    application = commands.upsert_application(repository, _application())

    commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="interview_completed",
        occurred_at="2026-07-15T01:30:00Z",
        details={"round": 1},
        status="interview",
    )

    assert repository.atomic_commits == 1
    assert repository.read("applications")["items"][0]["status"] == "interview"
    assert len(repository.read("events")["items"]) == 1


@pytest.mark.parametrize(
    ("status", "details"),
    [
        ("offer", {"round": 1, "channel": "video"}),
        ("interview", {"round": 2, "channel": "video"}),
    ],
)
def test_conflicting_event_replay_is_rejected_without_changing_state(
    commands: ModuleType,
    status: str,
    details: dict[str, Any],
):
    repository = FakeTrackingRepository()
    application = commands.upsert_application(repository, _application())
    commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="interview_completed",
        occurred_at="2026-07-15T01:30:00Z",
        details={"round": 1, "channel": "video"},
        status="interview",
    )
    before = deepcopy(repository.state)
    writes_before = len(repository.writes)

    with pytest.raises(ValueError, match="conflicting.*replay|replay.*conflict"):
        commands.record_application_event(
            repository,
            application_id=application["application_id"],
            event_type="INTERVIEW_COMPLETED",
            occurred_at="2026-07-15T09:30:00+08:00",
            details=details,
            status=status,
        )

    assert repository.state == before
    assert len(repository.writes) == writes_before


def test_invalid_transition_does_not_write_or_corrupt_existing_state(
    commands: ModuleType,
):
    accepted = _application(
        application_id="application_accepted",
        status="accepted",
    )
    repository = FakeTrackingRepository(_state(accepted))
    before = deepcopy(repository.state)

    with pytest.raises(ValueError, match="transition"):
        commands.record_application_event(
            repository,
            application_id="application_accepted",
            event_type="status_changed",
            occurred_at="2026-07-16T02:00:00Z",
            details={},
            status="applied",
        )

    assert repository.state == before
    assert repository.writes == []


def test_repository_write_failure_does_not_mutate_the_commands_input(
    commands: ModuleType,
):
    class FailingRepository(FakeTrackingRepository):
        def write(self, kind: str, document: dict[str, Any]) -> None:
            raise OSError("simulated repository failure")

    repository = FailingRepository()
    payload = _application()
    before = deepcopy(payload)

    with pytest.raises(OSError, match="simulated repository failure"):
        commands.upsert_application(repository, payload)

    assert payload == before
    assert repository.state == {}


def test_rejection_event_records_stage_on_application_and_auditable_event(
    commands: ModuleType,
):
    repository = FakeTrackingRepository()
    application = commands.upsert_application(repository, _application())

    event = commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="rejected",
        occurred_at="2026-07-16T02:00:00Z",
        details={"stage": "technical-interview", "reason_code": "experience"},
        status="rejected",
    )

    stored = repository.read("applications")["items"][0]
    assert stored["status"] == "rejected"
    assert stored["rejection_stage"] == "technical-interview"
    assert event["details"]["reason_code"] == "experience"


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-07-08T09:00:00Z", True),
        ("2026-07-11T08:59:59Z", True),
        ("2026-07-11T09:00:01Z", False),
    ],
)
def test_application_follow_up_is_due_only_during_day_7_to_10_window(
    commands: ModuleType,
    as_of: str,
    expected: bool,
):
    repository = FakeTrackingRepository(_state(_application()))

    action_types = {
        item["action"]
        for item in commands.due_actions(repository, as_of=as_of)
    }

    assert ("application_follow_up" in action_types) is expected


def test_no_response_review_is_suggested_at_day_14(
    commands: ModuleType,
):
    repository = FakeTrackingRepository(_state(_application()))

    before = commands.due_actions(
        repository,
        as_of="2026-07-15T08:59:59Z",
    )
    due = commands.due_actions(
        repository,
        as_of="2026-07-15T09:00:00Z",
    )

    assert "no_response_review" not in {item["action"] for item in before}
    assert "no_response_review" in {item["action"] for item in due}


def test_existing_follow_up_event_suppresses_follow_up_and_no_response_actions(
    commands: ModuleType,
):
    application = _application(application_id="application_01")
    follow_up = {
        "event_id": "event_follow_up",
        "application_id": "application_01",
        "event_type": "follow_up_sent",
        "occurred_at": "2026-07-08T09:00:00Z",
        "details": {},
    }
    repository = FakeTrackingRepository(_state(application, events=[follow_up]))

    action_types = {
        item["action"]
        for item in commands.due_actions(
            repository,
            as_of="2026-07-16T09:00:00Z",
        )
    }

    assert "application_follow_up" not in action_types
    assert "no_response_review" not in action_types


def test_interview_thank_you_is_due_until_24_hours_and_then_expires(
    commands: ModuleType,
):
    application = _application(
        application_id="application_01",
        status="interview",
    )
    interview = {
        "event_id": "event_interview",
        "application_id": "application_01",
        "event_type": "interview_completed",
        "occurred_at": "2026-07-16T02:00:00Z",
        "details": {},
    }
    repository = FakeTrackingRepository(_state(application, events=[interview]))

    within_window = commands.due_actions(
        repository,
        as_of="2026-07-17T01:59:59Z",
    )
    after_window = commands.due_actions(
        repository,
        as_of="2026-07-17T02:00:01Z",
    )

    assert "interview_thank_you" in {item["action"] for item in within_window}
    assert "interview_thank_you" not in {item["action"] for item in after_window}


def test_thank_you_event_suppresses_interview_thank_you_action(
    commands: ModuleType,
):
    application = _application(
        application_id="application_01",
        status="interview",
    )
    events = [
        {
            "event_id": "event_interview",
            "application_id": "application_01",
            "event_type": "interview_completed",
            "occurred_at": "2026-07-16T02:00:00Z",
            "details": {},
        },
        {
            "event_id": "event_thanks",
            "application_id": "application_01",
            "event_type": "thank_you_sent",
            "occurred_at": "2026-07-16T03:00:00Z",
            "details": {},
        },
    ]
    repository = FakeTrackingRepository(_state(application, events=events))

    actions = commands.due_actions(
        repository,
        as_of="2026-07-16T04:00:00Z",
    )

    assert "interview_thank_you" not in {item["action"] for item in actions}


def test_promised_response_adds_two_business_days_across_weekend(
    commands: ModuleType,
):
    application = _application(
        application_id="application_01",
        status="interview",
        promised_response_date="2026-07-17",
    )
    repository = FakeTrackingRepository(_state(application))

    monday = commands.due_actions(
        repository,
        as_of="2026-07-20T23:59:59Z",
    )
    tuesday = commands.due_actions(
        repository,
        as_of="2026-07-21T00:00:00Z",
    )

    assert "promised_response_follow_up" not in {
        item["action"] for item in monday
    }
    action = next(
        item
        for item in tuesday
        if item["action"] == "promised_response_follow_up"
    )
    assert action["due_at"] == "2026-07-21"


def test_offer_deadline_is_reported_with_exact_date_and_high_priority(
    commands: ModuleType,
):
    application = _application(
        application_id="application_01",
        status="offer",
        offer_deadline="2026-07-19",
    )
    repository = FakeTrackingRepository(_state(application))

    action = next(
        item
        for item in commands.due_actions(
            repository,
            as_of="2026-07-18T00:00:00Z",
        )
        if item["action"] == "offer_deadline"
    )

    assert action["due_at"] == "2026-07-19"
    assert action["priority"] == "high"


def _metric_application(index: int, **overrides: Any) -> dict[str, Any]:
    statuses = ("applied", "interview", "offer", "rejected", "accepted")
    payload = _application(
        job_id=f"job_{index:02d}",
        application_id=f"application_{index:02d}",
        company=f"Example Company {index:02d}",
        title="Backend Engineer",
        status=statuses[index % len(statuses)],
        applied_at=f"2026-07-{(index % 9) + 1:02d}T09:00:00Z",
        resume_version="backend-v1" if index < 10 else "platform-v2",
        channel="company-site" if index % 2 == 0 else "referral",
        country="CA" if index < 10 else "GB",
        rejection_stage="screen" if statuses[index % len(statuses)] == "rejected" else None,
    )
    payload.update(overrides)
    return payload


def test_metrics_are_deterministic_for_funnel_slices_and_rejection_stages(
    commands: ModuleType,
):
    applications = [_metric_application(index) for index in range(12)]
    repository = FakeTrackingRepository(_state(*reversed(applications)))

    first = commands.build_metrics(repository)
    repository.state["applications"]["items"].reverse()
    second = commands.build_metrics(repository)

    assert first == second
    assert first["contract_version"] == 1
    assert first["total"] == 12
    assert first["funnel"] == {
        "accepted": 2,
        "applied": 3,
        "interview": 3,
        "offer": 2,
        "rejected": 2,
    }
    assert first["rejection_stages"] == {"screen": 2}
    assert set(first["slices"]) == {"resume_version", "channel", "country"}
    assert first["slices"]["resume_version"]["backend-v1"] == {
        "count": 10,
        "insufficient": False,
    }
    assert first["slices"]["resume_version"]["platform-v2"] == {
        "count": 2,
        "insufficient": True,
    }
    assert first["slices"]["country"]["GB"]["insufficient"] is True


def test_metrics_json_is_sorted_compact_short_and_reproducible(
    commands: ModuleType,
):
    repository = FakeTrackingRepository(
        _state(*[_metric_application(index) for index in range(12)])
    )

    first = commands.metrics_json(repository)
    second = commands.metrics_json(repository)

    assert first == second
    assert first == json.dumps(
        json.loads(first),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert "\n" not in first
    assert ": " not in first
    assert len(first.encode("utf-8")) <= 4096


def test_commands_use_repository_protocol_and_do_not_import_filesystem_adapter(
    commands: ModuleType,
):
    source = Path(commands.__file__).read_text(encoding="utf-8")

    assert "LocalTrackingStore" not in source
    assert "job_radar.data" not in source
    assert "pathlib" not in source


def test_temp_directory_end_to_end_works_through_repository_protocol(
    commands: ModuleType,
    tmp_path: Path,
):
    storage = importlib.import_module("job_radar.data.tracking_store")
    repository = storage.LocalTrackingStore(tmp_path / "user-data")
    repository.initialize()

    application = commands.upsert_application(repository, _application())
    event = commands.record_application_event(
        repository,
        application_id=application["application_id"],
        event_type="interview_completed",
        occurred_at="2026-07-16T02:00:00Z",
        details={"round": 1},
        status="interview",
    )
    metrics = commands.build_metrics(repository)

    assert repository.read("applications")["items"][0]["status"] == "interview"
    assert repository.read("events")["items"] == [event]
    assert metrics["total"] == 1
    assert metrics["funnel"] == {"interview": 1}


def test_temp_directory_second_write_failure_leaves_no_status_or_event(
    commands: ModuleType,
    tmp_path: Path,
):
    storage = importlib.import_module("job_radar.data.tracking_store")
    root = tmp_path / "user-data"
    normal = storage.LocalTrackingStore(root)
    normal.initialize()
    application = commands.upsert_application(normal, _application())
    failed_once = False

    def fail_event_replace(source: Path, destination: Path) -> None:
        nonlocal failed_once
        if destination == normal.path_for("events") and not failed_once:
            failed_once = True
            raise OSError("simulated event replace failure")
        source.replace(destination)

    failing = storage.LocalTrackingStore(root, replace_file=fail_event_replace)

    with pytest.raises(OSError, match="simulated event replace failure"):
        commands.record_application_event(
            failing,
            application_id=application["application_id"],
            event_type="interview_completed",
            occurred_at="2026-07-16T02:00:00Z",
            details={"round": 1},
            status="interview",
        )

    assert normal.read("applications")["items"][0]["status"] == "applied"
    assert normal.read("events")["items"] == []
