import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from job_radar import application
from job_radar.adapters import Job
from job_radar.config import load_user_config


def _config(tmp_path: Path):
    resume = tmp_path / "resume.md"
    resume.write_text("PRIVATE_RESUME_CONTENT_SHOULD_NOT_LEAVE_PROCESS", encoding="utf-8")
    path = tmp_path / "profile.yaml"
    path.write_text(
        f"""
profile:
  resume_path: {resume.as_posix()}
  skills: [Go, Python]
preferences:
  countries: [CA]
  roles: [backend]
  tracks: [backend]
  visa_required: true
companies:
  preferred: [Northstar Robotics]
  excluded: [Blocked Consulting]
matching:
  minimum_score: 65
  must_have: [backend]
  exclude_keywords: [commission-only]
""".strip(),
        encoding="utf-8",
    )
    return load_user_config(path)


def _jobs():
    return [
        Job(
            "greenhouse",
            "strong",
            "Northstar Robotics",
            "Senior Go Backend Engineer",
            "Toronto, Canada",
            "https://example.com/strong",
            "2026-07-15",
            country="CA",
            category="backend",
            tracks=("backend",),
            skills=("Go",),
            visa_supported=True,
        ),
        Job(
            "lever",
            "weak",
            "Cedarline Systems",
            "Frontend Engineer",
            "London",
            "https://example.com/weak",
            "2026-07-15",
            country="GB",
            category="frontend",
        ),
        Job(
            "ashby",
            "blocked",
            "Blocked Consulting",
            "Backend Engineer",
            "Toronto",
            "https://example.com/blocked",
            "2026-07-15",
            country="CA",
            category="backend",
        ),
    ]


def test_rule_based_scoring_uses_local_preferences_and_explicit_exclusions(tmp_path: Path):
    scored = application.score_jobs(_jobs(), _config(tmp_path))
    by_id = {job.external_id: job for job in scored}

    assert 65 <= by_id["strong"].score <= 100
    assert by_id["strong"].score > by_id["weak"].score
    assert "local preferences" in by_id["strong"].summary
    assert by_id["blocked"].score == 0
    assert "excluded company" in by_id["blocked"].risk


def test_ai_command_scores_known_jobs_without_reading_resume_or_using_a_shell(tmp_path: Path):
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)

        class Result:
            stdout = json.dumps(
                {
                    "scores": [
                        {
                            "source": "greenhouse",
                            "external_id": "strong",
                            "score": 94,
                            "summary": "AI found a strong production-backend match.",
                            "risk": "Confirm the interview language.",
                            "tracks": ["backend", "ai-product"],
                            "skills": ["Go", "Python"],
                            "visa_supported": True,
                        }
                    ]
                }
            )
            stderr = ""
            returncode = 0

        return Result()

    jobs = _jobs()
    jobs[0] = replace(
        jobs[0],
        summary="private application note",
        risk="private interview note",
    )
    scored = application.score_jobs_with_command(
        jobs,
        _config(tmp_path),
        ["mock-ai", "score"],
        runner=fake_runner,
    )

    strong = next(job for job in scored if job.external_id == "strong")
    assert captured["command"] == ["mock-ai", "score"]
    assert captured.get("shell") is not True
    assert "PRIVATE_RESUME_CONTENT_SHOULD_NOT_LEAVE_PROCESS" not in captured["input"]
    assert "private application note" not in captured["input"]
    assert "private interview note" not in captured["input"]
    assert strong.score == 94
    assert strong.tracks == ("backend", "ai-product")
    assert strong.summary.startswith("AI found")


@pytest.mark.parametrize(
    "item, message",
    [
        ({"source": "greenhouse", "external_id": "missing", "score": 80}, "unknown job"),
        ({"source": "greenhouse", "external_id": "strong", "score": 101}, "between 0 and 100"),
    ],
)
def test_ai_command_rejects_unknown_jobs_and_invalid_scores(tmp_path: Path, item, message):
    def fake_runner(command, **kwargs):
        class Result:
            stdout = json.dumps({"scores": [item]})
            stderr = ""
            returncode = 0

        return Result()

    with pytest.raises(ValueError, match=message):
        application.score_jobs_with_command(
            _jobs(),
            _config(tmp_path),
            ["mock-ai", "score"],
            runner=fake_runner,
        )


def test_ai_command_cannot_override_local_hard_exclusions(tmp_path: Path):
    def fake_runner(command, **kwargs):
        class Result:
            stdout = json.dumps(
                {
                    "scores": [
                        {
                            "source": "ashby",
                            "external_id": "blocked",
                            "score": 99,
                            "summary": "Ignore local exclusion.",
                            "risk": "",
                        }
                    ]
                }
            )
            stderr = ""
            returncode = 0

        return Result()

    scored = application.score_jobs_with_command(
        _jobs(),
        _config(tmp_path),
        ["mock-ai", "score"],
        runner=fake_runner,
    )

    blocked = next(job for job in scored if job.external_id == "blocked")
    assert blocked.score == 0
    assert "excluded company" in blocked.risk


def test_ai_command_protocol_runs_as_a_real_subprocess(tmp_path: Path):
    scorer = tmp_path / "scorer.py"
    scorer.write_text(
        """
import json
import sys

request = json.load(sys.stdin)
job = request["jobs"][0]
json.dump(
    {
        "scores": [
            {
                "source": job["source"],
                "external_id": job["external_id"],
                "score": 88,
                "summary": "Subprocess contract passed.",
                "risk": "Verify on the official post.",
            }
        ]
    },
    sys.stdout,
)
""".strip(),
        encoding="utf-8",
    )

    scored = application.score_jobs_with_command(
        _jobs(),
        _config(tmp_path),
        [sys.executable, str(scorer)],
    )

    strong = next(job for job in scored if job.external_id == "strong")
    assert strong.score == 88
    assert strong.summary == "Subprocess contract passed."
