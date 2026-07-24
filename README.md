# Job Radar Starter

Local-first job radar for a single developer: official ATS adapters, transparent local scoring, optional AI review, and a privacy-first dashboard.

## What it does

- Scans public Greenhouse, Lever, and Ashby job boards.
- Normalizes listings into one JSON contract.
- Scores jobs with local rules; AI scoring is optional.
- Builds a framework-free local dashboard for list, swipe review, saved matches, filters, and decisions.
- Tracks interested, applied, hidden, and expired states locally.
- Renders review schedules without installing or enabling them automatically.

## Privacy boundary

Your resume, preferences, application history, scan output, credentials, and local status stay outside the public repository by default.

- user-data/, scans/, .env, and *.local.yaml are gitignored.
- The built-in scanner, scorer, and dashboard do not upload your resume.
- AI-command scoring receives structured preferences and public job fields, not resume contents, resume paths, prior notes, risks, or application state.
- If your scorer calls a hosted model, you are responsible for that provider's retention, training, disclosure, and deletion settings.

Do not put real resumes, interview notes, salary records, API keys, or scan results in this repository.

## Quick start

Requires Python 3.11+.

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item config.example\profile.yaml user-data\profile.yaml
job-radar --json doctor
job-radar --json run
python -m http.server 8000 --directory dashboard\public

Open http://localhost:8000.

To preview the UI with example data:

job-radar build-dashboard --jobs examples\jobs.example.json --output dashboard\public\index.html

## CLI

Put global --json before the command when machine-readable output is needed.

job-radar --json doctor
job-radar --json catalog list
job-radar --json scan --output scans\latest.json
job-radar --json score --jobs scans\latest.json --output scans\scored.json
job-radar --json review --jobs scans\latest.json --output scans\review.json
job-radar --json run
job-radar schedule render --platform windows --daily-at 08:15 --output user-data\job-radar-task.ps1

Scans are atomic by default: a failed source does not replace the last complete output. Use best-effort mode only when you accept an incomplete result. Source concurrency is bounded; tune it with --max-source-concurrency.

## Configure your profile

Copy config.example/profile.yaml to user-data/profile.yaml and edit. The profile is a local input for developer-owned extensions. Built-in components treat the resume path as a pointer and do not open or upload it.

## Repository map

- job_radar/: Python CLI, adapters, scoring, tracking, scheduling
- catalog/: Public source and company-board catalog
- dashboard/public/: Generated, dependency-free dashboard
- config.example/: Safe configuration templates
- examples/: Demo jobs and fixtures
- docs/: Operator, privacy, source, and contract documentation
- .codex/skills/job-radar/: Optional Codex workflow adapter
- optional-sync/cloudflare/: Optional self-owned sync template
- .spec/: Specs and development records

Start with:

- docs/getting-started.md
- docs/configuration.md
- docs/cli.md
- docs/architecture.md
- docs/privacy-and-data.md
- docs/source-policy.md
- docs/ai-scoring.md
- docs/scheduling.md
- docs/cloudflare-sync.md

## AI workflow

The optional .codex skill lets Codex, Claude, and other agents follow the same doctor-first, local-data, source-policy, and no-auto-install boundaries. The runtime does not require an AI vendor.

public ATS boards -> official adapters -> normalized jobs JSON -> local rules or approved AI command -> scored jobs -> local dashboard and tracking state

## Source and legal boundary

Use official public job-board endpoints only. Respect current terms, rate limits, authentication boundaries, privacy obligations, and applicable law. Verify job availability, visa support, compensation, and AI explanations on the official posting.

This project is independent and is not affiliated with any job board, ATS provider, employer, or government agency. The documentation is not legal advice.

## Development

.\.venv\Scripts\python.exe -m pytest -q

The generated dashboard has no frontend dependency or telemetry. Pushes and pull requests run Gitleaks. Review the CI result before publishing changes.

## License

MIT. See LICENSE.
