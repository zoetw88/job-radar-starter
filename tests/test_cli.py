import json
from io import StringIO
from pathlib import Path

from job_radar import cli
from job_radar.cli import main


def test_build_dashboard_command_reads_normalized_json(tmp_path: Path):
    jobs = tmp_path / "jobs.json"
    output = tmp_path / "public" / "index.html"
    jobs.write_text(
        json.dumps([
            {
                "source": "greenhouse",
                "external_id": "1",
                "company": "Example",
                "title": "Backend Engineer",
                "location": "Toronto",
                "url": "https://example.com/jobs/1",
                "published_at": "2026-07-13T00:00:00Z"
            }
        ]),
        encoding="utf-8",
    )

    assert main(["build-dashboard", "--jobs", str(jobs), "--output", str(output)]) == 0
    assert "Backend Engineer" in output.read_text(encoding="utf-8")


def test_help_exposes_the_complete_daily_pipeline():
    help_text = cli._parser().format_help()

    for command in ("doctor", "catalog", "scan", "score", "run", "schedule", "build-dashboard"):
        assert command in help_text


def test_schedule_render_is_safe_and_does_not_install_anything(tmp_path: Path):
    cron = cli.render_schedule(
        platform="cron",
        daily_at="08:15",
        project_dir=tmp_path,
        executable=tmp_path / ".venv" / "bin" / "job-radar",
    )
    windows = cli.render_schedule(
        platform="windows",
        daily_at="08:15",
        project_dir=tmp_path,
        executable=tmp_path / ".venv" / "Scripts" / "job-radar.exe",
    )

    assert cron.startswith("15 8 * * *")
    assert "job-radar" in cron
    assert "New-ScheduledTaskAction" in windows
    assert "08:15" in windows
    assert "Register-ScheduledTask" in windows


def test_run_command_emits_machine_readable_counts_and_paths(tmp_path: Path):
    catalog = tmp_path / "catalog.yaml"
    profile = tmp_path / "profile.yaml"
    jobs = tmp_path / "scans" / "latest.json"
    dashboard = tmp_path / "dashboard" / "index.html"
    catalog.write_text(
        """
countries:
  CA: {name: Canada, sources: [greenhouse]}
sources:
  greenhouse:
    kind: official_api
    terms_url: https://developer.greenhouse.io/job-board.html
    enabled: true
companies:
  Example:
    countries: [CA]
    source: greenhouse
    board: example
""".strip(),
        encoding="utf-8",
    )
    profile.write_text(
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

    def fake_get_json(url):
        return {
            "jobs": [
                {
                    "id": 1,
                    "title": "Go Backend Engineer",
                    "absolute_url": "https://example.com/jobs/1",
                    "location": {"name": "Canada"},
                }
            ]
        }

    stdout = StringIO()
    status = main(
        [
            "--json",
            "run",
            "--catalog",
            str(catalog),
            "--profile",
            str(profile),
            "--jobs-output",
            str(jobs),
            "--dashboard-output",
            str(dashboard),
        ],
        get_json=fake_get_json,
        stdout=stdout,
    )

    report = json.loads(stdout.getvalue())
    assert status == 0
    assert report["ok"] is True
    assert report["counts"] == {"scanned": 1, "published": 1}
    assert report["jobs_output"] == str(jobs.resolve())
    assert report["dashboard_output"] == str(dashboard.resolve())
