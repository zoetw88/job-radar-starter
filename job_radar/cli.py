from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from job_radar.adapters import Job
from job_radar.application import (
    run_pipeline,
    scan_catalog,
    score_jobs,
    score_jobs_with_command,
    write_jobs_json,
)
from job_radar.catalog import Catalog, load_catalog
from job_radar.config import load_user_config
from job_radar.dashboard import render_dashboard


DEFAULT_CATALOG = Path("catalog/sources.yaml")
DEFAULT_PROFILE = Path("user-data/profile.yaml")
DEFAULT_JOBS = Path("scans/latest.json")
DEFAULT_SCORED_JOBS = Path("scans/scored.json")
DEFAULT_DASHBOARD = Path("dashboard/public/index.html")
MAX_RESPONSE_BYTES = 50 * 1024 * 1024


def _add_catalog_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)


def _add_profile_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-radar",
        description="Scan official job boards, score locally, and build a private dashboard.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check local pipeline readiness")
    _add_catalog_argument(doctor)
    _add_profile_argument(doctor)
    doctor.add_argument("--jobs-output", type=Path, default=DEFAULT_JOBS)
    doctor.add_argument("--dashboard-output", type=Path, default=DEFAULT_DASHBOARD)
    doctor.add_argument("--ai-command", nargs=argparse.REMAINDER)

    catalog = commands.add_parser("catalog", help="inspect the public source catalog")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_list = catalog_commands.add_parser("list", help="list configured sources")
    _add_catalog_argument(catalog_list)

    scan = commands.add_parser("scan", help="scan enabled official job-board APIs")
    _add_catalog_argument(scan)
    scan.add_argument("--output", type=Path, default=DEFAULT_JOBS)

    score = commands.add_parser("score", help="score a normalized jobs JSON file")
    score.add_argument("--jobs", type=Path, default=DEFAULT_JOBS)
    _add_profile_argument(score)
    score.add_argument("--output", type=Path, default=DEFAULT_SCORED_JOBS)
    score.add_argument(
        "--ai-command",
        nargs=argparse.REMAINDER,
        help="executable and arguments; must be the final job-radar option",
    )

    run = commands.add_parser("run", help="scan, score, write JSON, and build the dashboard")
    _add_catalog_argument(run)
    _add_profile_argument(run)
    run.add_argument("--jobs-output", type=Path, default=DEFAULT_JOBS)
    run.add_argument("--dashboard-output", type=Path, default=DEFAULT_DASHBOARD)
    run.add_argument(
        "--ai-command",
        nargs=argparse.REMAINDER,
        help="executable and arguments; must be the final job-radar option",
    )

    schedule = commands.add_parser("schedule", help="render a scheduler configuration")
    schedule_commands = schedule.add_subparsers(dest="schedule_command", required=True)
    schedule_render = schedule_commands.add_parser(
        "render", help="print a cron or Windows Task Scheduler configuration"
    )
    schedule_render.add_argument("--platform", choices=("cron", "windows"), required=True)
    schedule_render.add_argument("--daily-at", default="08:00", metavar="HH:MM")
    schedule_render.add_argument("--project-dir", type=Path, default=Path.cwd())
    schedule_render.add_argument("--executable", type=Path)
    schedule_render.add_argument("--output", type=Path)

    build = commands.add_parser("build-dashboard", help="build from normalized jobs JSON")
    build.add_argument("--jobs", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    return parser


def http_get_json(url: str, *, timeout: int = 30) -> Any:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("official source URL must use HTTPS")
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "job-radar-starter/0.1 (local single-user client)",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("official source response exceeded 50 MiB")
    return json.loads(raw.decode("utf-8"))


def _job_from_dict(item: Any) -> Job:
    if not isinstance(item, dict):
        raise ValueError("each jobs JSON entry must be an object")
    normalized = dict(item)
    for field in ("tracks", "skills"):
        value = normalized.get(field, ())
        if not isinstance(value, (list, tuple)) or not all(
            isinstance(entry, str) for entry in value
        ):
            raise ValueError(f"job {field} must be a list of strings")
        normalized[field] = tuple(value)
    return Job(**normalized)


def _load_jobs(path: Path) -> list[Job]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("jobs JSON must be a list")
    return [_job_from_dict(item) for item in raw]


def _catalog_report(catalog: Catalog) -> dict[str, Any]:
    return {
        "countries": {name: asdict(value) for name, value in catalog.countries.items()},
        "sources": {name: asdict(value) for name, value in catalog.sources.items()},
        "companies": {name: asdict(value) for name, value in catalog.companies.items()},
    }


def _writable_parent(path: Path) -> bool:
    candidate = path.resolve().parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate.is_dir() and os.access(candidate, os.W_OK)


def _command_ready(command: list[str] | None) -> dict[str, Any]:
    if not command:
        return {"mode": "local_rules", "ready": True}
    executable = command[0]
    found = shutil.which(executable) or (str(Path(executable).resolve()) if Path(executable).exists() else None)
    return {"mode": "external_command", "ready": found is not None, "executable": executable}


def _doctor(args: argparse.Namespace) -> dict[str, Any]:
    catalog_status: dict[str, Any] = {"path": str(args.catalog.resolve()), "ready": False}
    profile_status: dict[str, Any] = {"path": str(args.profile.resolve()), "ready": False}
    try:
        loaded_catalog = load_catalog(args.catalog)
        catalog_status.update(
            ready=True,
            sources=len(loaded_catalog.sources),
            companies=len(loaded_catalog.companies),
        )
    except (OSError, ValueError) as error:
        catalog_status["error"] = str(error)
    try:
        load_user_config(args.profile)
        profile_status["ready"] = True
    except (OSError, ValueError) as error:
        profile_status["error"] = str(error)

    outputs = {
        "jobs": {
            "path": str(args.jobs_output.resolve()),
            "ready": _writable_parent(args.jobs_output),
        },
        "dashboard": {
            "path": str(args.dashboard_output.resolve()),
            "ready": _writable_parent(args.dashboard_output),
        },
    }
    ai = _command_ready(args.ai_command)
    ready = (
        catalog_status["ready"]
        and profile_status["ready"]
        and all(item["ready"] for item in outputs.values())
        and ai["ready"]
    )
    return {
        "ok": ready,
        "catalog": catalog_status,
        "profile": profile_status,
        "outputs": outputs,
        "network_auth": {"required": False, "reason": "built-in sources are public APIs"},
        "ai": ai,
    }


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _schedule_arguments() -> list[str]:
    return [
        "--json",
        "run",
        "--catalog",
        str(DEFAULT_CATALOG),
        "--profile",
        str(DEFAULT_PROFILE),
        "--jobs-output",
        str(DEFAULT_JOBS),
        "--dashboard-output",
        str(DEFAULT_DASHBOARD),
    ]


def render_schedule(
    *,
    platform: str,
    daily_at: str,
    project_dir: Path,
    executable: Path,
) -> str:
    try:
        parsed_time = datetime.strptime(daily_at, "%H:%M")
    except ValueError as error:
        raise ValueError("daily_at must use 24-hour HH:MM format") from error
    project = project_dir.resolve()
    executable = executable.resolve()
    arguments = _schedule_arguments()
    if platform == "cron":
        command = " ".join(
            [shlex.quote(str(executable)), *(shlex.quote(argument) for argument in arguments)]
        )
        log = shlex.quote(str(project / "scans" / "job-radar.log"))
        return (
            f"{parsed_time.minute} {parsed_time.hour} * * * "
            f"cd {shlex.quote(str(project))} && {command} >> {log} 2>&1\n"
        )
    if platform == "windows":
        argument_text = subprocess.list2cmdline(arguments)
        return "\n".join(
            (
                "$Action = New-ScheduledTaskAction "
                f"-Execute {_quote_powershell(str(executable))} "
                f"-Argument {_quote_powershell(argument_text)} "
                f"-WorkingDirectory {_quote_powershell(str(project))}",
                "$Trigger = New-ScheduledTaskTrigger -Daily "
                f"-At {_quote_powershell(daily_at)}",
                "Register-ScheduledTask -TaskName 'Job Radar Daily Scan' "
                "-Action $Action -Trigger $Trigger -Description 'Scan official job APIs and rebuild the local dashboard'",
                "",
            )
        )
    raise ValueError("platform must be cron or windows")


def _emit(payload: dict[str, Any], *, as_json: bool, stdout: TextIO) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=stdout)
        return
    if payload.get("ok") is False:
        print(f"not ready: {payload}", file=stdout)
        return
    operation = payload.get("operation", "doctor")
    counts = payload.get("counts")
    suffix = f" ({counts})" if counts else ""
    print(f"{operation}: ok{suffix}", file=stdout)


def main(
    argv: list[str] | None = None,
    *,
    get_json=None,
    command_runner=subprocess.run,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    args = _parser().parse_args(argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    get_json = get_json or http_get_json
    try:
        if args.command == "doctor":
            report = _doctor(args)
            _emit(report, as_json=args.json, stdout=stdout)
            return 0 if report["ok"] else 1

        if args.command == "catalog" and args.catalog_command == "list":
            catalog = load_catalog(args.catalog)
            report = {"ok": True, "operation": "catalog.list", **_catalog_report(catalog)}
            _emit(report, as_json=args.json, stdout=stdout)
            return 0

        if args.command == "scan":
            jobs = scan_catalog(load_catalog(args.catalog), get_json)
            write_jobs_json(jobs, args.output)
            report = {
                "ok": True,
                "operation": "scan",
                "counts": {"scanned": len(jobs)},
                "output": str(args.output.resolve()),
            }
            _emit(report, as_json=args.json, stdout=stdout)
            return 0

        if args.command == "score":
            jobs = _load_jobs(args.jobs)
            config = load_user_config(args.profile)
            if args.ai_command:
                scored = score_jobs_with_command(
                    jobs,
                    config,
                    args.ai_command,
                    runner=command_runner,
                )
            else:
                scored = score_jobs(jobs, config)
            write_jobs_json(scored, args.output)
            report = {
                "ok": True,
                "operation": "score",
                "counts": {"scored": len(scored)},
                "output": str(args.output.resolve()),
                "mode": "ai_command" if args.ai_command else "local_rules",
            }
            _emit(report, as_json=args.json, stdout=stdout)
            return 0

        if args.command == "run":
            counts = run_pipeline(
                load_catalog(args.catalog),
                load_user_config(args.profile),
                get_json=get_json,
                jobs_output=args.jobs_output,
                dashboard_output=args.dashboard_output,
                ai_command=args.ai_command,
                command_runner=command_runner,
            )
            report = {
                "ok": True,
                "operation": "run",
                "counts": counts,
                "jobs_output": str(args.jobs_output.resolve()),
                "dashboard_output": str(args.dashboard_output.resolve()),
                "mode": "ai_command" if args.ai_command else "local_rules",
            }
            _emit(report, as_json=args.json, stdout=stdout)
            return 0

        if args.command == "schedule" and args.schedule_command == "render":
            executable = args.executable
            if executable is None:
                executable = Path(sys.executable).with_name(
                    "job-radar.exe" if os.name == "nt" else "job-radar"
                )
            rendered = render_schedule(
                platform=args.platform,
                daily_at=args.daily_at,
                project_dir=args.project_dir,
                executable=executable,
            )
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(rendered, encoding="utf-8")
            if args.json:
                _emit(
                    {
                        "ok": True,
                        "operation": "schedule.render",
                        "platform": args.platform,
                        "installed": False,
                        "output": str(args.output.resolve()) if args.output else None,
                        "configuration": rendered,
                    },
                    as_json=True,
                    stdout=stdout,
                )
            else:
                print(rendered, end="", file=stdout)
            return 0

        if args.command == "build-dashboard":
            jobs = _load_jobs(args.jobs)
            render_dashboard(jobs, args.output)
            _emit(
                {
                    "ok": True,
                    "operation": "build-dashboard",
                    "counts": {"jobs": len(jobs)},
                    "output": str(args.output.resolve()),
                },
                as_json=args.json,
                stdout=stdout,
            )
            return 0
        raise AssertionError(f"unhandled command: {args.command}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        report = {"ok": False, "error": {"type": type(error).__name__, "message": str(error)}}
        if args.json:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=stdout)
        else:
            print(f"job-radar: {type(error).__name__}: {error}", file=stderr)
        return 2
