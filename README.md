# Job Radar Starter

> A local-first job radar for one developer.

Find better roles from official ATS boards, score them transparently on your machine, and review them in a private dashboard.

[Quick start](#quick-start) · [Privacy](#privacy) · [Docs](#docs)

## Why this exists

Job search gets noisy when listings, preferences, and decisions live in separate places. Job Radar turns them into one local workflow:

public job boards → normalized jobs → local scoring → review dashboard → decisions

## Highlights

- Official Greenhouse, Lever, and Ashby adapters
- Local rules by default; AI scoring is optional
- Ranked cards, filters, swipe review, saved matches, and keyboard controls
- Local tracking for interested, applied, hidden, and expired jobs
- Atomic scans, bounded source concurrency, and JSON contracts for agents and scripts
- No automatic applications, telemetry, or vendor lock-in

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

Preview with example data:

job-radar build-dashboard --jobs examples\jobs.example.json --output dashboard\public\index.html

## Configure

Copy config.example/profile.yaml to user-data/profile.yaml, then set your countries, roles, skills, preferred companies, exclusions, and minimum score.

The local profile may point to a resume, but built-in components do not open or upload it.

## Privacy

Your resume, preferences, application history, scan output, credentials, and browser status stay local by default.

Do not commit real resumes, interview notes, salary records, API keys, or scan results.

Optional AI scoring receives structured preferences and public job fields. It does not receive resume contents, resume paths, prior notes, risks, or application state. If your command calls a hosted model, review that provider's retention and deletion policy.

## Repository map

- job_radar/ — Python CLI, adapters, scoring, tracking, and scheduling
- catalog/ — public source and company-board catalog
- dashboard/public/ — generated dependency-free dashboard
- config.example/ — safe configuration templates
- examples/ — demo data and fixtures
- docs/ — operator and contract documentation
- optional-sync/cloudflare/ — optional self-owned sync template
- .codex/skills/job-radar/ — optional agent workflow adapter

## Docs

- docs/getting-started.md
- docs/configuration.md
- docs/cli.md
- docs/architecture.md
- docs/privacy-and-data.md
- docs/source-policy.md
- docs/ai-scoring.md
- docs/scheduling.md
- docs/cloudflare-sync.md

## Boundaries

Use official public job-board endpoints. Respect current terms, rate limits, authentication boundaries, privacy obligations, and applicable law. Verify job availability, visa support, compensation, and AI explanations on the official posting.

This project is independent and is not affiliated with any job board, ATS provider, employer, or government agency.

## Development

.\.venv\Scripts\python.exe -m pytest -q

## License

MIT
