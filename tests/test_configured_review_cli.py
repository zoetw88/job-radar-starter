from __future__ import annotations

import json
import importlib
import os
import subprocess
import sys
import threading
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from job_radar.cli import main
from job_radar.data.tracking_store import LocalTrackingStore


def _job() -> dict[str, Any]:
    return {
        "source": "greenhouse",
        "external_id": "backend-1",
        "company": "Example Systems",
        "title": "Backend Engineer",
        "location": "Toronto, Canada",
        "url": "https://example.com/jobs/backend-1",
        "published_at": "2026-07-17T00:00:00Z",
        "score": 82,
        "country": "CA",
        "category": "backend",
        "summary": "Matched Go and backend.",
        "risk": "Verify work authorization.",
        "salary": "",
        "tracks": ["backend"],
        "skills": ["Go"],
        "first_seen": "",
        "visa_supported": None,
    }


def _scan() -> dict[str, Any]:
    return {
        "contract_version": 1,
        "mode": "atomic",
        "incomplete": False,
        "jobs": [_job()],
        "failures": [],
    }


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_profile(path: Path) -> Path:
    path.write_text(
        """
profile: {skills: [Go]}
preferences:
  countries: [CA]
  roles: [backend]
  tracks: [backend]
  visa_required: false
matching: {minimum_score: 50, must_have: [backend]}
""".strip(),
        encoding="utf-8",
    )
    return path


def _write_catalog(path: Path) -> Path:
    path.write_text(
        """
countries:
  CA: {name: Canada, sources: [greenhouse]}
sources:
  greenhouse:
    kind: official_api
    terms_url: https://developer.greenhouse.io/job-board.html
    enabled: true
companies:
  Example Systems:
    countries: [CA]
    source: greenhouse
    board: example
""".strip(),
        encoding="utf-8",
    )
    return path


def _write_provider(
    path: Path,
    *,
    sleep_seconds: float = 0,
    pid_path: Path | None = None,
) -> Path:
    pid_statement = (
        f"open({str(pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))"
        if pid_path is not None
        else "pass"
    )
    path.write_text(
        f"""
import json
import os
import sys
import time

request = json.load(sys.stdin)
assert set(request) == {{
    "contract_version", "stable_id", "title", "company", "country",
    "local_fit", "jd_evidence"
}}
{pid_statement}
time.sleep({sleep_seconds!r})
json.dump({{
    "contract_version": 1,
    "stable_id": request["stable_id"],
    "decision": "recommend",
    "score": request["local_fit"],
    "reason_codes": ["public_fit"],
    "summary": "Compact provider response.",
}}, sys.stdout)
""".strip(),
        encoding="utf-8",
    )
    return path


def _blocking_review_runner(
    jobs: list[dict[str, Any]],
    *,
    observed_on: str,
    repository: object,
    per_call_timeout_seconds: int,
    total_deadline_seconds: int,
    max_fast_calls: int,
) -> dict[str, Any]:
    pid_path = Path(jobs[0]["pid_path"])
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    del observed_on, repository, per_call_timeout_seconds, max_fast_calls
    time.sleep(total_deadline_seconds * 10)
    raise AssertionError("bounded runner should have killed this process")


def _pid_exists(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _force_kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass


def _read_pid_if_ready(path: Path) -> int | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
        return int(value) if value else None
    except (OSError, ValueError):
        return None


def _wait_for_pid(path: Path) -> int:
    deadline = time.monotonic() + 5
    while True:
        pid = _read_pid_if_ready(path)
        if pid is not None:
            return pid
        if time.monotonic() >= deadline:
            raise AssertionError("descendant did not publish its PID")
        time.sleep(0.01)


def test_wait_for_pid_tolerates_a_visible_file_before_the_pid_is_flushed(
    tmp_path: Path,
):
    pid_path = tmp_path / "child.pid"
    pid_path.touch()
    writer = threading.Timer(
        0.05,
        pid_path.write_text,
        args=("24680",),
        kwargs={"encoding": "utf-8"},
    )
    writer.start()

    try:
        assert _wait_for_pid(pid_path) == 24680
    finally:
        writer.cancel()


def _write_flooding_provider(
    path: Path,
    *,
    pid_path: Path,
    child_pid_path: Path,
    stream: str,
) -> Path:
    path.write_text(
        f"""
import os
import subprocess
import sys
import time

open({str(pid_path)!r}, "w", encoding="utf-8").write(str(os.getpid()))
child = subprocess.Popen([
    sys.executable,
    "-c",
    "import os,time; open({child_pid_path.as_posix()!r}, 'w', encoding='utf-8').write(str(os.getpid())); time.sleep(30)",
])
deadline = time.monotonic() + 5
while not os.path.exists({str(child_pid_path)!r}):
    if time.monotonic() >= deadline:
        raise RuntimeError("descendant did not start")
    time.sleep(0.01)
target = sys.{stream}.buffer
chunk = b"x" * 65536
for _ in range(40):
    target.write(chunk)
    target.flush()
time.sleep(30)
""".strip(),
        encoding="utf-8",
    )
    return path


def _write_immediate_exit_provider(
    path: Path,
    *,
    child_pid_path: Path,
    flood_stdout: bool,
) -> Path:
    child_code = (
        "import os,sys,time; "
        f"open({str(child_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid())); "
        + (
            "sys.stdout.buffer.write(b'x' * 1500000); sys.stdout.flush(); "
            if flood_stdout
            else ""
        )
        + "time.sleep(30)"
    )
    path.write_text(
        "\n".join(
            (
                "import subprocess",
                "import sys",
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}])",
            )
        ),
        encoding="utf-8",
    )
    return path


def _returning_review_runner_with_child(
    jobs: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    del kwargs
    child_pid_path = Path(jobs[0]["child_pid_path"])
    child_code = (
        "import os,time; "
        f"open({str(child_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid())); "
        "time.sleep(30)"
    )
    subprocess.Popen([sys.executable, "-c", child_code])
    _wait_for_pid(child_pid_path)
    return {
        "contract_version": 1,
        "reviews": [],
        "rejected": [],
        "rejected_sample": [],
        "failures": [],
        "report": {"provider_calls": 0},
    }


def test_review_cli_runs_an_explicit_compact_external_command(tmp_path: Path):
    jobs = _write_json(tmp_path / "jobs.json", _scan())
    output = tmp_path / "review.json"
    user_data = tmp_path / "user-data"
    provider = _write_provider(tmp_path / "provider.py")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "job_radar",
            "--json",
            "review",
            "--jobs",
            str(jobs),
            "--output",
            str(output),
            "--user-data",
            str(user_data),
            "--observed-on",
            "2026-07-17",
            "--provider-command",
            sys.executable,
            str(provider),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    report = json.loads(completed.stdout)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert completed.returncode == 0, completed.stderr
    assert report["mode"] == "configured"
    assert report["counts"]["provider_calls"] == 1
    assert result["reviews"][0]["summary"] == "Compact provider response."
    assert LocalTrackingStore(user_data).read("review_cache")["items"]


def test_run_cli_maps_lifecycle_jobs_into_compact_review_fields(tmp_path: Path):
    provider = _write_provider(tmp_path / "provider.py")
    stdout = StringIO()

    status = main(
        [
            "--json",
            "run",
            "--catalog",
            str(_write_catalog(tmp_path / "catalog.yaml")),
            "--profile",
            str(_write_profile(tmp_path / "profile.yaml")),
            "--jobs-output",
            str(tmp_path / "scan.json"),
            "--dashboard-output",
            str(tmp_path / "index.html"),
            "--user-data",
            str(tmp_path / "user-data"),
            "--observed-on",
            "2026-07-17",
            "--provider-command",
            sys.executable,
            str(provider),
        ],
        scan_runner=lambda *args, **kwargs: _scan(),
        stdout=stdout,
    )

    report = json.loads(stdout.getvalue())
    assert status == 0
    assert report["review"] == {"mode": "configured", "provider_calls": 1}


def test_compact_review_evidence_excludes_local_summary_and_risk():
    provider_module = importlib.import_module("job_radar.review_provider")
    job = _job()
    job.update(
        {
            "jd_evidence": ["Official posting responsibility."],
            "public_skills": ["Distributed systems"],
            "summary": "Matched local preferred company and must-have skill.",
            "risk": "Missing private must-have; verify local visa preference.",
        }
    )

    compact = provider_module.compact_review_jobs([job])

    assert compact[0]["jd_evidence"] == [
        "Official posting responsibility.",
        "Toronto, Canada",
        "Distributed systems",
    ]
    serialized = json.dumps(compact, ensure_ascii=False)
    assert "local preferred" not in serialized
    assert "private must-have" not in serialized
    assert '"Go"' not in serialized


def test_external_provider_timeout_hard_kills_the_blocking_process(tmp_path: Path):
    jobs = _write_json(tmp_path / "jobs.json", _scan())
    pid_path = tmp_path / "provider.pid"
    provider = _write_provider(
        tmp_path / "provider.py",
        sleep_seconds=30,
        pid_path=pid_path,
    )
    started = time.monotonic()

    status = main(
        [
            "review",
            "--jobs",
            str(jobs),
            "--output",
            str(tmp_path / "review.json"),
            "--user-data",
            str(tmp_path / "user-data"),
            "--observed-on",
            "2026-07-17",
            "--per-call-timeout",
            "2",
            "--total-review-deadline",
            "5",
            "--provider-command",
            sys.executable,
            str(provider),
        ]
    )

    assert status == 0
    # Provider timeout plus bounded tree cleanup is the runtime contract. Child
    # death below is deterministic; this ceiling adds loaded-Windows scheduler
    # tolerance while still rejecting the provider's 30-second sleep.
    assert time.monotonic() - started < 15
    result = json.loads((tmp_path / "review.json").read_text(encoding="utf-8"))
    assert result["failures"][0]["category"] == "provider_timeout"
    assert not _pid_exists(_wait_for_pid(pid_path))


def test_arbitrary_review_runner_is_killed_outside_its_blocking_call(tmp_path: Path):
    workflow = importlib.import_module("job_radar.public_workflow")
    repository = LocalTrackingStore(tmp_path / "user-data")
    repository.initialize()
    started = time.monotonic()
    pid_path = tmp_path / "runner.pid"

    with pytest.raises(TimeoutError, match="total deadline"):
        workflow.run_review_runner_bounded(
            _blocking_review_runner,
            [{"pid_path": str(pid_path)}],
            observed_on="2026-07-17",
            repository=repository,
            per_call_timeout_seconds=1,
            total_deadline_seconds=0.2,
            max_fast_calls=1,
        )

    # The 0.2-second deadline and dead child are the safety contract. Keep the
    # wall-clock ceiling tolerant of Windows process-start/cleanup scheduling.
    assert time.monotonic() - started < 10
    assert not _pid_exists(_wait_for_pid(pid_path))


def test_standalone_review_wraps_the_entire_runner_in_the_hard_deadline(
    tmp_path: Path,
):
    jobs = _write_json(
        tmp_path / "jobs.json",
        {"contract_version": 1, "jobs": [{"pid_path": str(tmp_path / "runner.pid")}]},
    )
    started = time.monotonic()

    status = main(
        [
            "review",
            "--jobs",
            str(jobs),
            "--output",
            str(tmp_path / "review.json"),
            "--user-data",
            str(tmp_path / "user-data"),
            "--observed-on",
            "2026-07-17",
            "--total-review-deadline",
            "0.2",
        ],
        review_runner=_blocking_review_runner,
    )

    assert status == 2
    # The 0.2-second deadline and dead child are the safety contract. Keep the
    # wall-clock ceiling tolerant of Windows process-start/cleanup scheduling.
    assert time.monotonic() - started < 10
    assert not _pid_exists(_wait_for_pid(tmp_path / "runner.pid"))


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_provider_output_overflow_kills_the_complete_process_tree_immediately(
    tmp_path: Path,
    stream: str,
):
    provider_module = importlib.import_module("job_radar.review_provider")
    parent_pid_path = tmp_path / f"{stream}-provider.pid"
    child_pid_path = tmp_path / f"{stream}-child.pid"
    provider = _write_flooding_provider(
        tmp_path / f"{stream}-provider.py",
        pid_path=parent_pid_path,
        child_pid_path=child_pid_path,
        stream=stream,
    )
    started = time.monotonic()

    with pytest.raises(ValueError, match=rf"{stream}.*1 MiB"):
        provider_module.ExternalCommandReviewProvider(
            [sys.executable, str(provider)]
        ).review_with_timeout(
            "fast",
            {"contract_version": 1},
            timeout_seconds=10,
        )

    # Process-tree death is the deterministic safety assertion below. Allow
    # loaded Windows hosts enough time for bounded taskkill/wait cleanup while
    # still rejecting the former ~32s descendant-pipe leak.
    assert time.monotonic() - started < 10
    assert not _pid_exists(_wait_for_pid(parent_pid_path))
    assert not _pid_exists(_wait_for_pid(child_pid_path))


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object regression")
def test_immediate_exit_provider_flooding_child_is_dead_before_overflow_returns(
    tmp_path: Path,
):
    provider_module = importlib.import_module("job_radar.review_provider")
    child_pid_path = tmp_path / "immediate-flood-child.pid"
    provider = _write_immediate_exit_provider(
        tmp_path / "immediate-flood-provider.py",
        child_pid_path=child_pid_path,
        flood_stdout=True,
    )
    child_pid: int | None = None

    try:
        with pytest.raises(ValueError, match=r"stdout.*1 MiB"):
            provider_module.ExternalCommandReviewProvider(
                [sys.executable, str(provider)]
            ).review_with_timeout(
                "fast",
                {"contract_version": 1},
                timeout_seconds=10,
            )
        child_pid = _wait_for_pid(child_pid_path)
        assert not _pid_exists(child_pid)
    finally:
        if child_pid is None and child_pid_path.exists():
            child_pid = _read_pid_if_ready(child_pid_path)
        if child_pid is not None and _pid_exists(child_pid):
            _force_kill_pid(child_pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object regression")
def test_immediate_exit_provider_sleeping_child_is_dead_before_timeout_returns(
    tmp_path: Path,
):
    provider_module = importlib.import_module("job_radar.review_provider")
    child_pid_path = tmp_path / "immediate-sleep-child.pid"
    provider = _write_immediate_exit_provider(
        tmp_path / "immediate-sleep-provider.py",
        child_pid_path=child_pid_path,
        flood_stdout=False,
    )
    child_pid: int | None = None

    try:
        with pytest.raises(TimeoutError, match="timed out"):
            provider_module.ExternalCommandReviewProvider(
                [sys.executable, str(provider)]
            ).review_with_timeout(
                "fast",
                {"contract_version": 1},
                timeout_seconds=5,
            )
        child_pid = _wait_for_pid(child_pid_path)
        assert not _pid_exists(child_pid)
    finally:
        if child_pid is None and child_pid_path.exists():
            child_pid = _read_pid_if_ready(child_pid_path)
        if child_pid is not None and _pid_exists(child_pid):
            _force_kill_pid(child_pid)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object regression")
def test_returning_review_runner_kills_spawned_child_before_return(tmp_path: Path):
    workflow = importlib.import_module("job_radar.public_workflow")
    repository = LocalTrackingStore(tmp_path / "user-data")
    repository.initialize()
    child_pid_path = tmp_path / "returning-runner-child.pid"
    child_pid: int | None = None

    try:
        result = workflow.run_review_runner_bounded(
            _returning_review_runner_with_child,
            [{"child_pid_path": str(child_pid_path)}],
            observed_on="2026-07-17",
            repository=repository,
            per_call_timeout_seconds=1,
            total_deadline_seconds=5,
            max_fast_calls=1,
        )
        child_pid = _wait_for_pid(child_pid_path)
        assert result["contract_version"] == 1
        assert not _pid_exists(child_pid)
    finally:
        if child_pid is None and child_pid_path.exists():
            child_pid = _read_pid_if_ready(child_pid_path)
        if child_pid is not None and _pid_exists(child_pid):
            _force_kill_pid(child_pid)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("per_call_timeout_seconds", 0),
        ("total_deadline_seconds", -1),
        ("max_fast_calls", 0),
    ],
)
def test_bounded_review_runner_rejects_unsafe_limits(
    tmp_path: Path,
    field: str,
    value: int,
):
    workflow = importlib.import_module("job_radar.public_workflow")
    repository = LocalTrackingStore(tmp_path / "user-data")
    repository.initialize()
    limits = {
        "per_call_timeout_seconds": 1,
        "total_deadline_seconds": 1,
        "max_fast_calls": 1,
    }
    limits[field] = value

    with pytest.raises(ValueError, match=field):
        workflow.run_review_runner_bounded(
            _blocking_review_runner,
            [{"pid_path": str(tmp_path / "runner.pid")}],
            observed_on="2026-07-17",
            repository=repository,
            **limits,
        )
